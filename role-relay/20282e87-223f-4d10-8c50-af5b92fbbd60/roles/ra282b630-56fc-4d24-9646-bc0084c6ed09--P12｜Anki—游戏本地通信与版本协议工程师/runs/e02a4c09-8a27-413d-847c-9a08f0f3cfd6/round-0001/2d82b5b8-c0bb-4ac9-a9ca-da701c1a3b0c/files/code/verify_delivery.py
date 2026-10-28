"""Offline exact-file verification, not a functional or independent approval."""
from pathlib import Path,PurePosixPath
import argparse,csv,hashlib,json,sys

def verify(root,receipt=None):
 manifest=root/'delivery_manifest.sha256.tsv';rows=list(csv.DictReader(manifest.open(encoding='utf-8'),delimiter='\t'))
 names=set();errors=[]
 for row in rows:
  rel=PurePosixPath(row['relative_path'])
  if rel.is_absolute() or '..' in rel.parts or '\\' in str(rel):errors.append('UNSAFE_PATH:'+str(rel));continue
  if str(rel) in names:errors.append('DUPLICATE_ENTRY:'+str(rel));continue
  names.add(str(rel));p=root/str(rel)
  if not p.is_file() or p.is_symlink():errors.append('MISSING_OR_LINK:'+str(rel));continue
  raw=p.read_bytes()
  if len(raw)!=int(row['actual_bytes']) or hashlib.sha256(raw).hexdigest()!=row['sha256']:errors.append('SIZE_OR_HASH_MISMATCH:'+str(rel))
 actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=manifest and '__pycache__' not in p.parts and p.suffix!='.pyc'}
 errors+=['UNLISTED_FILE:'+x for x in sorted(actual-names)];errors+=['LISTED_BUT_MISSING:'+x for x in sorted(names-actual)]
 source=json.loads((root/'source_input_receipt.json').read_text(encoding='utf-8'));count=0
 for r in source['consumed_files']:
  p=root/r['relative_path'];raw=p.read_bytes()
  if len(raw)!=r['size_bytes'] or hashlib.sha256(raw).hexdigest()!=r['sha256']:errors.append('SOURCE_CHANGED:'+r['relative_path'])
  count+=1
 if receipt:
  outer=json.loads(receipt.read_text(encoding='utf-8'))
  if hashlib.sha256(manifest.read_bytes()).hexdigest()!=outer['manifest']['sha256']:errors.append('EXTERNAL_MANIFEST_BINDING_MISMATCH')
 return {'status':'FAIL' if errors else 'PASS','scope':'EXACT_DELIVERY_BYTES_ONLY','listed_files_verified':len(rows),'source_files_verified':count,'errors':errors,'manifest_self_hash':'Bound by external P12_delivery_receipt.json and archive hash, excluded to avoid circular hashing.','independent_functional_review':'NOT_RUN'}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--receipt',type=Path);a=p.parse_args();r=verify(a.root,a.receipt);print(json.dumps(r,ensure_ascii=False,indent=2));return 0 if r['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())

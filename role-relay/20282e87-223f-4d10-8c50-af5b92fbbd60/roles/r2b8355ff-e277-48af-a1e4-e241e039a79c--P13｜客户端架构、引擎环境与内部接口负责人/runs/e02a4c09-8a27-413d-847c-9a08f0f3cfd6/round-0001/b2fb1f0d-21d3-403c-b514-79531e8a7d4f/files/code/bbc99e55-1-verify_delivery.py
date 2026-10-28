"""Exact offline package verification; never substitutes for runtime acceptance."""
from pathlib import Path, PurePosixPath
import argparse
import ast
import csv
import hashlib
import json

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def verify(root,receipt=None):
    errors=[];manifest=root/'delivery_manifest.sha256.tsv'
    with manifest.open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f,delimiter='\t'))
    names=set()
    for r in rows:
        rel=PurePosixPath(r['relative_path'])
        if rel.is_absolute() or '..' in rel.parts or '\\' in str(rel):errors.append('UNSAFE_PATH:'+str(rel));continue
        if str(rel) in names:errors.append('DUPLICATE_MANIFEST_PATH:'+str(rel));continue
        names.add(str(rel));p=root.joinpath(*rel.parts)
        if not p.is_file() or p.is_symlink():errors.append('MISSING_OR_SYMLINK:'+str(rel));continue
        if p.stat().st_size!=int(r['size_bytes']) or sha(p)!=r['sha256']:errors.append('SIZE_OR_HASH_MISMATCH:'+str(rel))
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p!=manifest and '__pycache__' not in p.parts and p.suffix!='.pyc'}
    errors+=['UNLISTED_FILE:'+n for n in sorted(actual-names)]
    errors+=['LISTED_BUT_MISSING:'+n for n in sorted(names-actual)]
    src=json.loads((root/'architecture/source_input_receipt.json').read_text())
    for s in src['sources']:
        p=root/s['retained_relative_path']
        if p.stat().st_size!=s['size_bytes'] or sha(p)!=s['sha256']:errors.append('UPSTREAM_SOURCE_CHANGED:'+s['source_id'])
    syntax_count=0
    for sub in ['runtime/framework','architecture/tools']:
        for p in (root/sub).rglob('*.py'):
            try:ast.parse(p.read_text(encoding='utf-8'),filename=str(p));syntax_count+=1
            except SyntaxError as exc:errors.append('PYTHON_SYNTAX:'+str(exc))
    binding=json.loads((root/'architecture/evidence/final_source_binding.json').read_text())
    for r in binding['files']:
        p=root/r['relative_path']
        if sha(p)!=r['sha256']:errors.append('EXECUTED_SOURCE_CHANGED:'+r['relative_path'])
    optional={}
    if receipt:
        outer=json.loads(receipt.read_text())
        if sha(manifest)!=outer['manifest']['sha256']:errors.append('OUTER_MANIFEST_MISMATCH')
        for e in outer['exports']:
            p=root/e['package_relative_path']
            if sha(p)!=e['sha256'] or p.stat().st_size!=e['size_bytes']:errors.append('EXPORT_PACKAGE_MISMATCH:'+e['filename'])
            sibling=receipt.parent/e['filename']
            if sibling.is_file():
                optional[e['filename']]='CHECKED'
                if sha(sibling)!=e['sha256'] or sibling.stat().st_size!=e['size_bytes']:errors.append('EXPORT_BYTES_MISMATCH:'+e['filename'])
            else:optional[e['filename']]='NOT_PRESENT_NOT_CHECKED'
        z=receipt.parent/outer['archive']['filename']
        if z.exists() and (sha(z)!=outer['archive']['sha256'] or z.stat().st_size!=outer['archive']['size_bytes']):errors.append('ARCHIVE_MISMATCH')
    return {'status':'FAIL' if errors else 'PASS','scope':'EXACT_PACKAGE_BYTES_AND_PYTHON_SYNTAX_ONLY','manifest_records':len(rows),'upstream_files_verified':len(src['sources']),'executed_source_files_bound':len(binding['files']),'python_files_parsed':syntax_count,'optional_sibling_exports':optional,'errors':errors,'game_engine_runtime':'NOT_RUN','independent_acceptance':'NOT_RUN','manifest_self_hash':'Excluded from own rows; bound by outer delivery_receipt.json'}

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--receipt',type=Path);a=p.parse_args()
    r=verify(a.root.resolve(),a.receipt);print(json.dumps(r,ensure_ascii=False,indent=2));return 1 if r['status']=='FAIL' else 0

if __name__=='__main__':raise SystemExit(main())

"""Recheck supplied source bytes, recursive ZIPs, manifest entries and Git blobs."""
import csv
import hashlib
import io
import json
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parents[3]
def sha(b):return hashlib.sha256(b).hexdigest()

def verify():
    receipt=json.loads((ROOT/'design/linguistic/source_input_receipt.json').read_text())
    a=receipt['primary_archive'];raw=(ROOT/a['package_path']).read_bytes()
    assert sha(raw)==a['sha256'] and len(raw)==a['actual_bytes'],'primary archive mismatch'
    seen=set();counts={'unique_zip_archives':0,'zip_occurrences':0,'relay_manifest_entries':0,'tsv_manifest_entries':0,'loose_manifests_not_applicable':0,'source_snapshots':0,'git_blob_bindings':0}
    blobs={};details=[]
    def walk(raw):
        counts['zip_occurrences']+=1
        h=sha(raw)
        if h in seen:return
        seen.add(h);counts['unique_zip_archives']+=1
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names=z.namelist()
            assert len(names)==len(set(names)),'duplicate ZIP member'
            assert sum(i.file_size for i in z.infolist())<=100_000_000,'ZIP size limit'
            for i in z.infolist():
                q=PurePosixPath(i.filename)
                assert not q.is_absolute() and '..' not in q.parts and '\\' not in i.filename and not stat.S_ISLNK(i.external_attr>>16),'unsafe ZIP member'
            assert z.testzip() is None,'ZIP CRC'
            files={n:z.read(n) for n in names if not n.endswith('/')}
            for n,b in files.items():blobs[sha(b)]=b
            for n,b in files.items():
                if n.endswith('manifest.json'):
                    m=json.loads(b)
                    if isinstance(m,dict) and isinstance(m.get('files'),list):
                        for r in m['files']:
                            if not all(k in r for k in ('path','sha256')):continue
                            path=str(PurePosixPath(n).parent/r['path'])
                            data=files[path]
                            assert sha(data)==r['sha256'] and len(data)==r.get('size',r.get('bytes',len(data))),'relay manifest mismatch'
                            counts['relay_manifest_entries']+=1
                if 'manifest' in PurePosixPath(n).name and n.endswith('.tsv'):
                    rows=list(csv.DictReader(io.StringIO(b.decode('utf-8')),delimiter='\t'))
                    if not rows or not {'relative_path','sha256','actual_bytes'}<=set(rows[0]):continue
                    bases=[PurePosixPath('.'),*PurePosixPath(n).parents]
                    base=next((p for p in bases if all(str(p/r['relative_path']) in files for r in rows)),None)
                    if base is None:
                        counts['loose_manifests_not_applicable']+=1
                        continue
                    for r in rows:
                        data=files[str(base/r['relative_path'])]
                        assert sha(data)==r['sha256'] and len(data)==int(r['actual_bytes']),'TSV manifest mismatch'
                        counts['tsv_manifest_entries']+=1
            details.append({'archive_sha256':h,'members':len(names),'status':'PASS_BYTE_INTEGRITY_ONLY'})
            for n,b in files.items():
                if n.lower().endswith('.zip'):walk(b)
    walk(raw)
    for s in receipt['consumed_sources']:
        data=raw
        for name in s['member_chain']:
            with zipfile.ZipFile(io.BytesIO(data)) as z:data=z.read(name)
        local=(ROOT/s['package_path']).read_bytes()
        assert data==local and sha(local)==s['sha256'] and len(local)==s['actual_bytes'],'source chain mismatch'
        counts['source_snapshots']+=1
    for g in json.loads((ROOT/'design/linguistic/evidence/intake/git_blob_bindings.json').read_text()):
        data=blobs[g['sha256']]
        assert len(data)==g['size'] and hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==g['git_blob_sha1'],'Git blob mismatch'
        file='v6_github_tree.json' if 'juesedemo-' in g['repository'] else 'p08_github_tree.json'
        tree=json.loads((ROOT/'design/linguistic/evidence/intake'/file).read_text())
        assert not tree.get('truncated'),'truncated pinned tree'
        assert any(x['path']==g['repository_path'] and x['sha']==g['git_blob_sha1'] and x.get('size')==g['size'] for x in tree['tree']),'tree binding mismatch'
        counts['git_blob_bindings']+=1
    return {'status':'PASS','scope':'SOURCE_BYTE_INTEGRITY_AUTHOR_CHECK','counts':counts,'archives':details}

if __name__=='__main__':
    try:print(json.dumps(verify(),ensure_ascii=False,indent=2))
    except Exception as e:
        print(json.dumps({'status':'FAIL','error':str(e)},ensure_ascii=False));sys.exit(1)

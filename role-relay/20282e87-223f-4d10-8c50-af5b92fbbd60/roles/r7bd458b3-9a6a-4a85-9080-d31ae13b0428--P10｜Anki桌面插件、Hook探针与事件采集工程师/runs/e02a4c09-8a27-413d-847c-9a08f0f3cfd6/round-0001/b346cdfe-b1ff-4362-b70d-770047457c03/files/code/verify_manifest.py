import csv,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def verify(root=ROOT):
    m=root/'delivery_manifest.sha256.tsv'
    rows=list(csv.DictReader(m.open(encoding='utf-8'),delimiter='\t'))
    paths=[r['relative_path'] for r in rows]
    assert len(paths)==len(set(paths)),'duplicate path'
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and p!=m and '__pycache__' not in p.parts}
    assert actual==set(paths),'missing or extra manifest entry'
    for r in rows:
        p=root/r['relative_path'];assert p.resolve().is_relative_to(root.resolve()),'path traversal'
        b=p.read_bytes();assert len(b)==int(r['actual_bytes']) and hashlib.sha256(b).hexdigest()==r['sha256'],r['relative_path']
        assert r['source_input_hashes_json'] and r['receivers'] and r['modify_whitelist'],'missing metadata'
    return {'status':'PASS','scope':'DELIVERY_BYTE_INTEGRITY_ONLY','entries':len(rows),'manifest_self_hash':'BOUND_BY_EXTERNAL_RECEIPT'}
if __name__=='__main__':
    try:print(json.dumps(verify(),ensure_ascii=False))
    except Exception as e:print(json.dumps({'status':'FAIL','error':str(e)},ensure_ascii=False));sys.exit(1)

#!/usr/bin/env python3
"""Verify every packaged file against the non-self-referential manifest."""
import json,sys
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,str(Path(__file__).resolve().parent))
from p22_content.io import safe_path,sha256,ContentError

def verify(root):
    manifest_path=root/'delivery_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'));errors=[]
    expected={r['relative_path'] for r in manifest['files']}
    if len(expected)!=len(manifest['files']):errors.append('duplicate manifest path')
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}-{'delivery_manifest.json'}
    if actual!=expected:errors.append({'missing':sorted(expected-actual),'unexpected':sorted(actual-expected)})
    for row in manifest['files']:
        try:
            raw=safe_path(root,row['relative_path']).read_bytes()
            if len(raw)!=row['size_bytes'] or sha256(raw)!=row['sha256']:errors.append({'path':row['relative_path'],'code':'HASH_OR_SIZE_MISMATCH'})
        except (ContentError,OSError) as e:errors.append({'path':row['relative_path'],'code':str(e)})
    receipt=json.loads((root/'evidence/intake/source_input_receipt.json').read_text(encoding='utf-8'))
    unchanged=0
    for row in receipt['selected_sources']:
        raw=safe_path(root,row['path']).read_bytes()
        if len(raw)==row['size_bytes'] and sha256(raw)==row['sha256']:unchanged+=1
        else:errors.append({'path':row['path'],'code':'UPSTREAM_CHANGED'})
    return {'status':'PASS' if not errors else 'FAIL','manifest_entries':len(expected),'package_files_including_manifest':len(expected)+1,'selected_upstream_files_unchanged':unchanged,'selected_upstream_file_count':len(receipt['selected_sources']),'errors':errors,'manifest_self_hash_binding':'EXTERNAL_P22_DELIVERY_RECEIPT'}

if __name__=='__main__':
    try:
        result=verify(Path(__file__).resolve().parents[2]);print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(0 if result['status']=='PASS' else 2)
    except (OSError,ValueError,KeyError,ContentError) as e:print(json.dumps({'status':'FAIL','error':str(e)},ensure_ascii=False));raise SystemExit(2)

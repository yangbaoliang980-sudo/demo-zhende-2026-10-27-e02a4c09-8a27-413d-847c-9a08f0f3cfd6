"""Check the exact delivered file inventory; not a functionality/approval test."""
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


def verify(root):
    manifest = root/'delivery_manifest.sha256.tsv'
    rows = list(csv.DictReader(manifest.open(encoding='utf-8'),delimiter='\t'))
    names = set()
    errors = []
    for row in rows:
        rel = PurePosixPath(row['relative_path'])
        if rel.is_absolute() or '..' in rel.parts or '\\' in row['relative_path']:
            errors.append('UNSAFE_PATH:'+row['relative_path']);continue
        if str(rel) in names:
            errors.append('DUPLICATE_MANIFEST_ENTRY:'+str(rel));continue
        names.add(str(rel))
        path = root/str(rel)
        if not path.is_file() or path.is_symlink():
            errors.append('MISSING_OR_LINK:'+str(rel));continue
        raw = path.read_bytes()
        if len(raw) != int(row['actual_bytes']) or hashlib.sha256(raw).hexdigest() != row['sha256']:
            errors.append('SIZE_OR_HASH_MISMATCH:'+str(rel))
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()
              and p!=manifest and '__pycache__' not in p.parts and not p.name.endswith('.pyc')}
    for name in sorted(actual-names):errors.append('UNLISTED_FILE:'+name)
    for name in sorted(names-actual):errors.append('LISTED_BUT_MISSING:'+name)
    source = json.loads((root/'source_input_receipt.json').read_text(encoding='utf-8'))
    source_checks = 0
    for record in source['consumed_files']:
        raw = (root/record['relative_path']).read_bytes()
        if len(raw) != record['size_bytes'] or hashlib.sha256(raw).hexdigest() != record['sha256']:
            errors.append('UPSTREAM_SOURCE_CHANGED:'+record['relative_path'])
        source_checks += 1
    return {'status':'FAIL' if errors else 'PASS','scope':'DELIVERY_BYTES_ONLY',
            'files_verified':len(rows),'source_snapshots_verified':source_checks,'errors':errors,
            'manifest_self_hash':'See external P11_delivery_receipt.json; self-reference deliberately excluded.',
            'independent_functional_acceptance':'NOT_RUN'}


if __name__ == '__main__':
    result = verify(Path(__file__).resolve().parents[1])
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['status']=='PASS' else 1)

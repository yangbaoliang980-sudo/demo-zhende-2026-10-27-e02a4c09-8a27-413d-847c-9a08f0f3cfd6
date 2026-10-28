"""Read-only input tree fingerprint matching run_engine_probe.py."""
import argparse
import hashlib
import json
from pathlib import Path

def main():
    p=argparse.ArgumentParser();p.add_argument('--project',type=Path,required=True);a=p.parse_args()
    root=a.project.resolve()
    if not root.is_dir():p.error('Project directory does not exist.')
    files=[]
    for f in sorted(root.rglob('*')):
        if f.is_symlink():p.error('Materialize and review symlinked inputs before probing.')
        if f.is_file():files.append({'path':f.relative_to(root).as_posix(),'size_bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    raw=json.dumps(files,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    print(json.dumps({'root':str(root),'tree_sha256':hashlib.sha256(raw).hexdigest(),'files':files},ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())

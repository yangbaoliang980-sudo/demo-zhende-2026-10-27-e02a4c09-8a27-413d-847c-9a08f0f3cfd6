"""Record actual commands, bytes, exits and raw logs, including failed attempts."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,subprocess,sys,zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('command',nargs=argparse.REMAINDER)
    args=p.parse_args();command=args.command
    if command and command[0]=='--':command=command[1:]
    if not command:raise SystemExit('command required')
    runs=ROOT/'evidence/runs';runs.mkdir(parents=True,exist_ok=True)
    target=runs/args.label
    target.mkdir(exist_ok=False)
    paths=[]
    for folder in ['battle_core','resolution_replay_tests','examples','tools','upstream']:
        for f in sorted((ROOT/folder).rglob('*')):
            if f.is_file() and '__pycache__' not in f.parts:
                paths.append(f)
    hashes=[]
    with zipfile.ZipFile(target/'executed_sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in paths:
            b=f.read_bytes();rel=f.relative_to(ROOT).as_posix();z.writestr(rel,b)
            hashes.append({'path':rel,'size_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1'
    result=subprocess.run(command,cwd=ROOT,env=env,capture_output=True)
    (target/'stdout.log').write_bytes(result.stdout);(target/'stderr.log').write_bytes(result.stderr)
    record={'label':args.label,'started_utc':start,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'cwd':str(ROOT),'command':command,'exit_code':result.returncode,'author_role':'P14',
        'independent_P32_P35':False,'executed_files':hashes}
    (target/'run.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    sys.stdout.buffer.write(result.stdout);sys.stderr.buffer.write(result.stderr)
    print(json.dumps({'record':str(target/'run.json'),'exit_code':result.returncode}))
    raise SystemExit(result.returncode)


if __name__=='__main__':main()

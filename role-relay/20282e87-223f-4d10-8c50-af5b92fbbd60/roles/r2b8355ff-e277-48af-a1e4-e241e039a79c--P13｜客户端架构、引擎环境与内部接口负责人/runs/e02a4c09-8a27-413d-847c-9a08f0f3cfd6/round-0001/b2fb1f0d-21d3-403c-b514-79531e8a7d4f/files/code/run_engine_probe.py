"""Future engine process probe on a fresh copy. Source input is never launched in place.

This script has NOT been run against an engine in this delivery. A zero process
exit is deliberately not reported as a game runtime PASS: inspect logs, expected
scene handshake, target graphics and independent tests separately.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--engine',choices=['godot','unity'],required=True)
    p.add_argument('--executable',type=Path,required=True);p.add_argument('--project',type=Path,required=True)
    p.add_argument('--source-commit',required=True);p.add_argument('--expected-tree-sha256',required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout',type=int,default=45)
    a=p.parse_args();source=a.project.resolve();binary=a.executable.resolve();out=a.output.resolve()
    if not source.is_dir() or not binary.is_file():p.error('Explicit source directory and engine executable are required.')
    if out.is_relative_to(source):p.error('Output must be outside original project.')
    if not 1<=a.timeout<=60:p.error('Timeout must be 1..60 seconds.')
    files=[]
    for f in sorted(source.rglob('*')):
        if f.is_symlink():p.error('Symlinked source must be reviewed and materialized separately.')
        if f.is_file():files.append({'path':f.relative_to(source).as_posix(),'size_bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
    tree_raw=json.dumps(files,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
    tree_sha=hashlib.sha256(tree_raw).hexdigest()
    if tree_sha!=a.expected_tree_sha256:p.error('Source tree SHA-256 differs; do not overwrite or launch.')
    if a.engine=='godot' and not (source/'project.godot').is_file():p.error('project.godot is missing.')
    if a.engine=='unity' and not (source/'ProjectSettings/ProjectVersion.txt').is_file():p.error('Unity ProjectVersion.txt is missing.')
    out.mkdir(parents=True,exist_ok=False);copy=out/'project_copy';shutil.copytree(source,copy)
    env=os.environ.copy();env.update(XDG_DATA_HOME=str(out/'user_data'),XDG_CONFIG_HOME=str(out/'user_config'),XDG_CACHE_HOME=str(out/'cache'))
    if a.engine=='godot':argv=[str(binary),'--headless','--path',str(copy),'--editor','--quit','--log-file',str(out/'engine.log')]
    else:argv=[str(binary),'-batchmode','-nographics','-projectPath',str(copy),'-quit','-logFile',str(out/'engine.log')]
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        r=subprocess.run(argv,cwd=copy,env=env,capture_output=True,timeout=a.timeout);code=r.returncode;stdout=r.stdout;stderr=r.stderr;status='PROCESS_EXITED_ZERO_REVIEW_LOG_REQUIRED' if code==0 else 'FAIL'
    except subprocess.TimeoutExpired as exc:
        code=None;stdout=exc.stdout or b'';stderr=exc.stderr or b'';status='FAIL_TIMEOUT'
    except OSError as exc:
        code=None;stdout=b'';stderr=str(exc).encode();status='FAIL_SPAWN'
    (out/'stdout.log').write_bytes(stdout);(out/'stderr.log').write_bytes(stderr)
    record={'status':status,'scope':'ENGINE_EDITOR_IMPORT_PROBE_ONLY','game_main_scene':'NOT_RUN','target_gpu_rendering':'NOT_RUN','source_commit_asserted_by_operator':a.source_commit,'source_tree_sha256':tree_sha,'source_files':files,'engine_binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'command_argv':argv,'cwd':str(copy),'started_at_utc':started,'ended_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':code,'stdout_sha256':hashlib.sha256(stdout).hexdigest(),'stderr_sha256':hashlib.sha256(stderr).hexdigest()}
    (out/'probe_receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(record,ensure_ascii=False,indent=2));return 0 if code==0 else 1

if __name__=='__main__':raise SystemExit(main())

"""Read-only discovery; never treats PATH absence as proof about another machine."""
import argparse
import datetime
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

MARKERS={'project.godot','ProjectVersion.txt','manifest.json','package.json','Cargo.toml','CMakeLists.txt','pyproject.toml'}
def run(argv):
    start=datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        r=subprocess.run(argv,capture_output=True,timeout=15)
        return {'command_argv':argv,'started_at_utc':start,'exit_code':r.returncode,'stdout':r.stdout.decode('utf-8',errors='replace'),'stderr':r.stderr.decode('utf-8',errors='replace')}
    except (OSError,subprocess.TimeoutExpired) as exc:
        return {'command_argv':argv,'started_at_utc':start,'exit_code':None,'status':'NOT_COMPLETED','error':type(exc).__name__+':'+str(exc)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--scan-root',action='append',default=[]);a=ap.parse_args()
    probes=[];availability={}
    for name in ['godot','godot4','Godot','Unity','unity','dotnet','anki','python','node','npm','git']:
        argv=[sys.executable,'-B','-c','import shutil,sys; p=shutil.which(sys.argv[1]); print(p if p else "NOT_FOUND_ON_PATH"); sys.exit(0 if p else 1)',name]
        r=run(argv);probes.append(r);availability[name]=shutil.which(name)
    for name in ['python','node','npm','git','dotnet','godot','godot4']:
        if availability[name]:probes.append(run([availability[name],'--version']))
    markers=[];counts={}
    for root_text in a.scan_root:
        root=Path(root_text).resolve();count=0
        if not root.is_dir():counts[str(root)]='MISSING';continue
        for p in sorted(root.rglob('*')):
            if not p.is_file() or p.is_symlink():continue
            count+=1
            # Generic manifest.json is not itself an engine entry. Include only
            # Unity's Packages/manifest.json, never relay attachment manifests.
            if (p.name in MARKERS-{'manifest.json'} or (p.name=='manifest.json' and p.parent.name=='Packages') or p.suffix in {'.sln','.csproj','.uproject'}):
                b=p.read_bytes();markers.append({'root':str(root),'relative_path':str(p.relative_to(root)),'size_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
        counts[str(root)]=count
    result={'schema_version':'P13-ENVIRONMENT-PROBE/0.1.0','timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Current execution host and explicitly passed source roots only','environment':{'system':platform.system(),'release':platform.release(),'machine':platform.machine(),'python':sys.version,'python_executable':sys.executable,'display_available':bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))},'availability':availability,'discovery_commands':probes,'source_file_counts':counts,'project_markers':markers,'actual_game_source_commit':None,'user_target_os':None,'user_target_hardware':None,'engine_launch_status':'NOT_RUN','target_runtime_gate':'BLOCKED','reason':'No verified target engine project or P34 device receipt was supplied. Discovery exit 1 means unavailable on current PATH; no engine process was attempted.'}
    print(json.dumps(result,ensure_ascii=False,indent=2));return 3

if __name__=='__main__':raise SystemExit(main())

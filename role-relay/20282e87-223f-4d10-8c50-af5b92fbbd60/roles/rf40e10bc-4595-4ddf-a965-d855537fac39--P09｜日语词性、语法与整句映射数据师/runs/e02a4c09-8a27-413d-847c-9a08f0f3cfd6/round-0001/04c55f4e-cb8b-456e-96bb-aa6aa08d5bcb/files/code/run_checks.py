"""Capture reproducible author checks. Destination must not already exist."""
import argparse,datetime,hashlib,json,platform,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    dest=Path(args.output).resolve();dest.mkdir(parents=True,exist_ok=False)
    env={'python':sys.version,'executable':sys.executable,'os':platform.platform(),'machine':platform.machine(),
         'scope':'AUTHOR_SYNTHETIC_REFERENCE_ONLY','target_game_engine':None,'target_anki_version':None,
         'captured_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (dest/'environment.json').write_text(json.dumps(env,ensure_ascii=False,indent=2)+'\n')
    input_paths=[]
    for folder in ('content/linguistic','design/linguistic/reference','design/linguistic/verification','design/linguistic/evidence/readonly_sources','design/linguistic/evidence/intake'):
        input_paths.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    input_paths.extend(ROOT/p for p in ('design/linguistic/source_input_receipt.json','design/linguistic/formal_prerequisites.json'))
    bindings=[{'relative_path':str(p.relative_to(ROOT)),'actual_bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(set(input_paths))]
    (dest/'input_bindings.json').write_text(json.dumps({'captured_before_execution':True,'inputs':bindings},ensure_ascii=False,indent=2)+'\n')
    runs=[('sources',[sys.executable,'-B','design/linguistic/verification/verify_source_inputs.py'],0),
          ('mapping_cases',[sys.executable,'-B','design/linguistic/verification/verify_delivery.py'],0),
          ('author_unit',[sys.executable,'-B','-m','unittest','discover','-s','design/linguistic/verification','-p','test_*.py','-v'],0),
          ('formal_preflight',[sys.executable,'-B','design/linguistic/verification/verify_delivery.py','--formal'],3)]
    records=[]
    for name,command,expected in runs:
        start=datetime.datetime.now(datetime.timezone.utc).isoformat()
        proc=subprocess.run(command,cwd=ROOT,capture_output=True)
        for stream,data in [('stdout',proc.stdout),('stderr',proc.stderr)]:(dest/f'{name}.{stream}.log').write_bytes(data)
        status='BLOCKED' if name=='formal_preflight' and proc.returncode==3 else ('PASS' if proc.returncode==expected else 'FAIL')
        records.append({'name':name,'command':command,'cwd':str(ROOT),'started_at_utc':start,
            'exit_code':proc.returncode,'expected_exit_code':expected,'status':status,
            'stdout_sha256':hashlib.sha256(proc.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(proc.stderr).hexdigest()})
    (dest/'run_results.json').write_text(json.dumps({'scope':'AUTHOR_CHECK_NOT_P32_OR_P35','runs':records},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'runs':[{k:r[k] for k in ('name','exit_code','status')} for r in records],'output':str(dest)},ensure_ascii=False))
    return int(any(r['status']=='FAIL' for r in records))
if __name__=='__main__':sys.exit(main())

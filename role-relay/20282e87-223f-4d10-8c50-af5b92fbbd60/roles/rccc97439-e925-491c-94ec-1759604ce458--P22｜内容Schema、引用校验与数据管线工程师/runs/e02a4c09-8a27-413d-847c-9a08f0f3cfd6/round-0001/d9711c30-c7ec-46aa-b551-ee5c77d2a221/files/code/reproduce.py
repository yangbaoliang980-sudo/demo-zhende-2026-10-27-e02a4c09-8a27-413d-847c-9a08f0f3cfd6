#!/usr/bin/env python3
"""Run verification, author tests, read-only linting and metadata migration.

Output must be a new directory outside this package. No network calls are made.
"""
import argparse,datetime,hashlib,json,os,platform,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]

def hash_file(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot():return {p.relative_to(ROOT).as_posix():hash_file(p) for p in ROOT.rglob('*') if p.is_file()}
def main():
    a=argparse.ArgumentParser();a.add_argument('--output',required=True,type=Path);args=a.parse_args();out=args.output.absolute()
    if out.exists() or out.resolve().is_relative_to(ROOT.resolve()):a.error('output must be a new directory outside the package')
    out.mkdir();before=snapshot();env=dict(os.environ);env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONHASHSEED']='17'
    runs=[]
    commands=[
      ('verify_delivery',[str(HERE/'verify_delivery.py')],0),
      ('author_tests',[str(HERE/'run_tests.py'),'--json-out',str(out/'test_results.json')],0),
      ('lint_a',[str(HERE/'schema_linter.py'),'lint','--output',str(out/'lint_a')],0),
      ('lint_b',[str(HERE/'schema_linter.py'),'lint','--output',str(out/'lint_b')],0),
      ('formal_preflight',[str(HERE/'schema_linter.py'),'preflight','--output',str(out/'preflight')],3),
      ('negative_samples',[str(HERE/'schema_linter.py'),'negative-samples','--output',str(out/'negative_samples')],0),
      ('manifest_migration',[str(HERE/'schema_linter.py'),'migrate-manifest','--input','tools/content_validation/fixtures/manifest_v1.synthetic.json','--output',str(out/'metadata_migration')],0),
      ('real_id_map',[str(HERE/'schema_linter.py'),'id-map','--output',str(out/'id_map')],0)]
    for name,parts,expected in commands:
        command=[sys.executable,'-B',*parts];started=datetime.datetime.now(datetime.timezone.utc).isoformat()
        if name=='lint_b':env['PYTHONHASHSEED']='987'
        try:
            p=subprocess.run(command,cwd=ROOT,env=env,capture_output=True,timeout=120)
            stdout,stderr,rc=p.stdout,p.stderr,p.returncode
        except subprocess.TimeoutExpired as e:stdout=e.stdout or b'';stderr=(e.stderr or b'')+b'\nPROCESS_TIMEOUT\n';rc=-999
        so=out/(name+'.stdout.txt');se=out/(name+'.stderr.txt');so.write_bytes(stdout);se.write_bytes(stderr)
        runs.append({'name':name,'command':command,'cwd':str(ROOT),'started_utc':started,'exit_code':rc,'expected_exit_code':expected,'expectation_met':rc==expected,'stdout':so.name,'stdout_sha256':hash_file(so),'stderr':se.name,'stderr_sha256':hash_file(se)})
        print(name,rc,'expected',expected,flush=True)
    after=snapshot();deterministic=False
    if (out/'lint_a').is_dir() and (out/'lint_b').is_dir():
        left={p.relative_to(out/'lint_a').as_posix():hash_file(p) for p in (out/'lint_a').rglob('*') if p.is_file()};right={p.relative_to(out/'lint_b').as_posix():hash_file(p) for p in (out/'lint_b').rglob('*') if p.is_file()};deterministic=left==right
    status='PASS' if all(r['expectation_met'] for r in runs) and before==after and deterministic else 'FAIL'
    receipt={'scope':'P22_AUTHOR_REPRODUCTION_NOT_P32_OR_P35','status':status,'environment':{'python':sys.version,'platform':platform.platform()},'runs':runs,'package_unchanged':before==after,'package_files_checked':len(before),'deterministic_reports':deterministic,'formal_gate':'BLOCKED','independent_tests':'NOT_RUN','target_engine_windows_anki_e2e':'NOT_RUN'}
    (out/'reproduction_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['runs','environment']},ensure_ascii=False,indent=2));return 0 if status=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())

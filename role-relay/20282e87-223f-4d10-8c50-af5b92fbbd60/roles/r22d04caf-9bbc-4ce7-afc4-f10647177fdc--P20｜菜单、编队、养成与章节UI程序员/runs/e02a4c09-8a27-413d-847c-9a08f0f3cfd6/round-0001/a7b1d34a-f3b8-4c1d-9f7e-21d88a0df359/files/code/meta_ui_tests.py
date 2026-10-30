"""Run real author tests. Does not claim P32/P33/P35 or production integration."""
from pathlib import Path
import argparse,json,re,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent
def main():
    p=argparse.ArgumentParser();p.add_argument('--layer',choices=['all','js','contract'],default='all');a=p.parse_args();summary=[]
    commands=[]
    if a.layer in {'all','js'}:
        if not shutil.which('node'):print('BLOCKED: Node runtime not found');return 3
        commands.append(('AUTHOR_JS_UNIT',['node','--test','--test-isolation=none','tests/meta_ui_unit/model_controller.test.mjs']))
    if a.layer in {'all','contract'}:commands.append(('AUTHOR_NATIVE_CONTRACT',[sys.executable,'-B','-m','unittest','discover','-s','tests/meta_ui_unit','-p','test_domain_contracts.py','-v']))
    for layer,cmd in commands:
        result=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr)
        log=result.stdout+'\n'+result.stderr
        match=re.search(r'(?:ℹ|#) tests (\d+)',log) if layer.endswith('UNIT') else re.search(r'Ran (\d+) tests',log)
        count=int(match.group(1)) if match else 0
        admitted=result.returncode==0 and count>1
        summary.append({'layer':layer,'executed_tests':count,'exit_code':result.returncode,'status':'PASS' if admitted else 'FAIL'})
        if not admitted:print(json.dumps(summary));return result.returncode or 1
    print(json.dumps({'scope':'AUTHOR_ONLY','results':summary},ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())

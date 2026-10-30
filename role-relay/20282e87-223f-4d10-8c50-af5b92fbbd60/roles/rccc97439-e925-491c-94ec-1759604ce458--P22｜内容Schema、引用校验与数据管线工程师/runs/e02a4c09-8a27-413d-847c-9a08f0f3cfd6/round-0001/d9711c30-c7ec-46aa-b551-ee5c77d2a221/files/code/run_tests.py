#!/usr/bin/env python3
"""Author tests. Running this file does not constitute a P32/P35 acceptance."""
import argparse,json,platform,sys,time,unittest
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))

class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.events=[]
    def addSuccess(self,test):super().addSuccess(test);self.events.append({'test':test.id(),'status':'PASS'})
    def addFailure(self,test,err):super().addFailure(test,err);self.events.append({'test':test.id(),'status':'FAIL'})
    def addError(self,test,err):super().addError(test,err);self.events.append({'test':test.id(),'status':'ERROR'})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.events.append({'test':test.id(),'status':'NOT_RUN','reason':reason})

def main():
    p=argparse.ArgumentParser();p.add_argument('--json-out',type=Path);args=p.parse_args()
    suite=unittest.defaultTestLoader.discover(str(HERE/'tests'),pattern='test_*.py')
    result=unittest.TextTestRunner(verbosity=2,resultclass=RecordedResult).run(suite)
    record={'scope':'P22_AUTHOR_TESTS_ONLY','tests_run':result.testsRun,'passed':sum(e['status']=='PASS' for e in result.events),'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'status':'PASS' if result.wasSuccessful() and not result.skipped else 'FAIL' if not result.wasSuccessful() else 'PASS_WITH_NOT_RUN','p32_independent':'NOT_RUN','p35_review':'NOT_RUN','environment':{'python':sys.version,'platform':platform.platform()},'cases':result.events}
    if args.json_out:
        with args.json_out.open('x',encoding='utf-8') as f:json.dump(record,f,ensure_ascii=False,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:v for k,v in record.items() if k!='cases'},ensure_ascii=False,indent=2))
    return 0 if result.wasSuccessful() else 1

if __name__=='__main__':raise SystemExit(main())

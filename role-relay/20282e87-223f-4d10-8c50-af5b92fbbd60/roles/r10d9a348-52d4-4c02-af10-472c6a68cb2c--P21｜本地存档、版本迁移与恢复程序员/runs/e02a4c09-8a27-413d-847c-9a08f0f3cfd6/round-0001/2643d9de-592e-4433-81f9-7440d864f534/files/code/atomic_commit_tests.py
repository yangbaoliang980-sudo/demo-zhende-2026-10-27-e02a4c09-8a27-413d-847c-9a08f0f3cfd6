"""Reproducible P21 author tests. P32/P35 must independently accept this version."""
from pathlib import Path
import argparse
import datetime
import hashlib
import io
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import bootstrap  # noqa: E402,F401
sys.path.insert(0,str(ROOT/'tests/save_unit'))


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.rows=[]
    def addSuccess(self,test):super().addSuccess(test);self.rows.append({'id':test.id(),'status':'PASS'})
    def addFailure(self,test,err):super().addFailure(test,err);self.rows.append({'id':test.id(),'status':'FAIL','detail':self._exc_info_to_string(err,test)})
    def addError(self,test,err):super().addError(test,err);self.rows.append({'id':test.id(),'status':'ERROR','detail':self._exc_info_to_string(err,test)})
    def addSkip(self,test,reason):super().addSkip(test,reason);self.rows.append({'id':test.id(),'status':'NOT_RUN','reason':reason})


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output');parser.add_argument('--pattern',default='test_*.py');parser.add_argument('--worker',action='store_true')
    args=parser.parse_args()
    out=Path(args.output).resolve() if args.output else Path(tempfile.mkdtemp(prefix='p21-evidence-'))
    if args.worker:
        os.environ['P21_EVIDENCE_DIR']=str(out)
        suite=unittest.defaultTestLoader.discover(str(ROOT/'tests/save_unit'),pattern=args.pattern)
        result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
        report={'test_scope':'AUTHOR_ISOLATED_EXECUTION','tests_run':result.testsRun,
                'passed':sum(x['status']=='PASS' for x in result.rows),'failures':len(result.failures),
                'errors':len(result.errors),'not_run':len(result.skipped),'cases':result.rows,
                'P32':'NOT_RUN','P35':'NOT_RUN','Windows':'NOT_RUN','Anki_E2E':'NOT_RUN'}
        (out/'test_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        return 0 if result.wasSuccessful() else 1
    out.mkdir(parents=True,exist_ok=True)
    if (out/'run_receipt.json').exists():parser.error('output already contains a run; choose a new directory')
    selected=[]
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and (p.suffix in ('.py','.sql') or str(p.relative_to(ROOT)).startswith(('schema/save/','sources/'))):
            if any(x in p.parts for x in ['recovery_logs','__pycache__']):continue
            b=p.read_bytes();selected.append({'path':str(p.relative_to(ROOT)),'size_bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
    with zipfile.ZipFile(out/'executed_sources.zip','w',zipfile.ZIP_DEFLATED) as z:
        for x in selected:z.write(ROOT/x['path'],x['path'])
    (out/'source_hashes.json').write_text(json.dumps(selected,indent=2)+'\n')
    cmd=[sys.executable,'-B',str(Path(__file__).resolve()),'--worker','--output',str(out),'--pattern',args.pattern]
    started=now()
    process=subprocess.run(cmd,cwd=ROOT,capture_output=True)
    ended=now()
    (out/'stdout.log').write_bytes(process.stdout);(out/'stderr.log').write_bytes(process.stderr)
    receipt={'argv':cmd,'cwd':str(ROOT),'started_utc':started,'ended_utc':ended,'exit_code':process.returncode,
             'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'platform':platform.platform(),
             'source_file_count':len(selected),'source_snapshot_sha256':hashlib.sha256((out/'executed_sources.zip').read_bytes()).hexdigest(),
             'stdout_sha256':hashlib.sha256(process.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(process.stderr).hexdigest(),
             'status':'PASS' if process.returncode==0 else 'FAIL'}
    (out/'run_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    sys.stdout.buffer.write(process.stdout);sys.stderr.buffer.write(process.stderr)
    print(json.dumps({'evidence_directory':str(out),'exit_code':process.returncode},ensure_ascii=False))
    return process.returncode


if __name__=='__main__':raise SystemExit(main())

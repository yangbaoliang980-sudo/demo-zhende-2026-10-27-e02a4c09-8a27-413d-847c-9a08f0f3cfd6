"""Append-only author execution evidence. Never labels independent acceptance."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,platform,re,subprocess,sys,zipfile
ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser();p.add_argument('--group',choices=['core','all','process','oracle'],default='all');p.add_argument('--output',type=Path)
 a=p.parse_args();base=a.output or ROOT/'evidence'
 base.mkdir(parents=True,exist_ok=True)
 i=1
 while (base/f'author_run_{i:03}').exists():i+=1
 out=base/f'author_run_{i:03}';out.mkdir()
 files=[]
 for directory in ['runtime','mocks','contracts','verification','sources/P11']:
  for f in sorted((ROOT/directory).rglob('*')):
   if f.is_file() and '__pycache__' not in f.parts:
    raw=f.read_bytes();files.append({'path':f.relative_to(ROOT).as_posix(),'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
 (out/'input_hashes.json').write_text(json.dumps(files,indent=2)+'\n')
 with zipfile.ZipFile(out/'executed_sources.zip','w',zipfile.ZIP_DEFLATED) as z:
  for row in files:z.write(ROOT/row['path'],row['path'])
 if a.group=='core':cmd=[sys.executable,'-B','-m','unittest','mocks.anki_transport.parser_contract_tests','mocks.anki_transport.ack_replay_tests','-v']
 elif a.group=='process':cmd=[sys.executable,'-B','-m','mocks.anki_transport.process_replay','--output',str(out/'process_replay')]
 elif a.group=='oracle':cmd=[sys.executable,'-B','-m','mocks.anki_transport.schema_oracle','--output',str(out/'oracle.json')]
 else:cmd=[sys.executable,'-B','-m','unittest','discover','-s','mocks/anki_transport','-p','*_tests.py','-v']
 start=datetime.datetime.now(datetime.timezone.utc)
 result=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=120)
 end=datetime.datetime.now(datetime.timezone.utc)
 (out/(a.group+'.stdout.log')).write_bytes(result.stdout);(out/(a.group+'.stderr.log')).write_bytes(result.stderr)
 count=re.search(rb'Ran (\d+) tests',result.stderr)
 report={'schema_version':'P12-AUTHOR-RUN/0.1.0','group':a.group,'command':cmd,'cwd':str(ROOT),'started_utc':start.isoformat(),'ended_utc':end.isoformat(),'duration_seconds':(end-start).total_seconds(),'exit_code':result.returncode,'status':'PASS' if result.returncode==0 else 'FAIL','test_count':int(count[1]) if count else None,'environment':{'platform':platform.platform(),'python':sys.version,'executable':sys.executable},'evidence_scope':'AUTHOR_ISOLATED_SYNTHETIC_ONLY','independent_p32_p35':'NOT_RUN','real_anki_game_e2e':'NOT_RUN','output_files':[{'path':x.name,'sha256':hashlib.sha256(x.read_bytes()).hexdigest(),'size_bytes':x.stat().st_size} for x in sorted(out.glob('*')) if x.is_file()]}
 (out/'run_receipt.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({'directory':str(out),'status':report['status'],'exit_code':result.returncode,'test_count':report['test_count']},indent=2))
 if result.returncode:print(result.stderr.decode(errors='replace')[-10000:])
 return result.returncode
if __name__=='__main__':raise SystemExit(main())

"""Actual two-process IPC + hard-exit recovery. Synthetic P11/P21 stores only."""
from pathlib import Path
import argparse,datetime,json,os,selectors,subprocess,sys,tempfile
from mocks.anki_transport.support import ROOT,Harness,Q
from runtime.anki.transport.ipc_server_client.local import create_key


def start_game(directory,fault,log):
 cmd=[sys.executable,'-B','-m','mocks.anki_transport.process_peer','game','--directory',str(directory)]
 if fault:cmd+=['--fault',fault]
 p=subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 sel=selectors.DefaultSelector();sel.register(p.stdout,selectors.EVENT_READ)
 ready=sel.select(5);sel.close()
 if not ready:
  p.kill();out,err=p.communicate(timeout=5);raise RuntimeError('GAME_START_TIMEOUT '+err)
 line=p.stdout.readline();meta=json.loads(line)
 if meta['host']!='127.0.0.1':p.kill();raise AssertionError('NONLOCAL_LISTENER')
 log.append({'command':cmd,'ready_stdout':line.rstrip(),'pid':p.pid})
 return p,meta['port']


def plugin(directory,port,now,crash,log):
 cmd=[sys.executable,'-B','-m','mocks.anki_transport.process_peer','plugin','--directory',str(directory),'--port',str(port),'--now-ms',str(now)]
 if crash:cmd+=['--die-after-response']
 r=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True,timeout=10)
 log.append({'command':cmd,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
 return r,json.loads(r.stdout) if r.stdout else None


def finish(p,log):
 if p.poll() is None:p.terminate()
 out,err=p.communicate(timeout=5);log.append({'pid':p.pid,'exit_code':p.returncode,'stdout':out,'stderr':err})


def scenario(name,fault,client_crash,output):
 log=[];p=None;started=datetime.datetime.now(datetime.timezone.utc).isoformat()
 with tempfile.TemporaryDirectory(prefix='p12-process-') as temp:
  directory=Path(temp);os.chmod(directory,0o700);create_key(directory)
  try:
   p,port=start_game(directory,fault,log)
   r,first=plugin(directory,port,0,client_crash,log)
   if client_crash:
    assert r.returncode==72
   else:
    assert r.returncode==0 and first['row_state']=='RETRY_WAIT'
    p.wait(timeout=5);assert p.returncode==71;finish(p,log);p=None
    p,port=start_game(directory,None,log)
   r,second=plugin(directory,port,100000,False,log);assert r.returncode==0
   if fault=='after_wallet_before_commit':
    assert second['row_state']=='RETRY_WAIT' and second['action']=='SUBMIT'
    r,second=plugin(directory,port,200000,False,log);assert r.returncode==0
   assert second['row_state']=='SETTLED'
   with Harness(directory) as h:
    snap=h.store.snapshot();assert h.balance==Q;assert snap.wallet['version']==1
    audit={'balance':h.balance,'wallet_version':snap.wallet['version'],'ledger_rows':len(snap.ledger['inbox']),'transaction_watermark':snap.high_watermark,'receipt_count':len(h.store.export_receipts())}
   status='PASS'
  except BaseException:
   output.write_text(json.dumps({'scenario':name,'status':'FAIL','logs':log},indent=2)+'\n')
   raise
  finally:
   if p is not None:finish(p,log)
 report={'scenario':name,'status':status,'started_utc':started,'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evidence_scope':'ACTUAL_LINUX_PROCESSES_WITH_SYNTHETIC_P11_P21','real_anki':'NOT_RUN','real_game_engine':'NOT_RUN','logs':log,'final_verification':audit,'keys_or_databases_exported':False}
 output.write_text(json.dumps(report,indent=2)+'\n');return report


def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
 scenarios=[('server_exit_before_commit','after_wallet_before_commit',False),('server_exit_after_commit_before_ack','after_commit_before_reply',False),('plugin_exit_after_ack_before_outbox_commit',None,True)]
 reports=[]
 for name,fault,crash in scenarios:reports.append(scenario(name,fault,crash,a.output/(name+'.json')))
 summary={'status':'PASS','executed':len(reports),'scenarios':[{'name':r['scenario'],'status':r['status']} for r in reports],'not_proven':['real Anki','production P21','Windows','power loss','disk failure','independent review']}
 (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2));return 0
if __name__=='__main__':raise SystemExit(main())

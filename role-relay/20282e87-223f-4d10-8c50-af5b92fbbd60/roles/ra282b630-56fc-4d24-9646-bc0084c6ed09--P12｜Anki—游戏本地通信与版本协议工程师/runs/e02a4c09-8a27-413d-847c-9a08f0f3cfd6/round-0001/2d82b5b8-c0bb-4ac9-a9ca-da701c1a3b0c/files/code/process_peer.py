"""Executable game/plugin mocks. Never install this module into an Anki add-on."""
import argparse,json,os,signal
from threading import Event
from mocks.anki_transport.support import Harness,submit,pairing
from runtime.anki.transport.ipc_server_client.local import read_key
from runtime.anki.transport.ipc_server_client.outbox import Outbox,ClientPump
from runtime.anki.transport.ipc_server_client.wire import LoopbackServer,LoopbackClient,LoopbackAddress

def main():
 p=argparse.ArgumentParser();p.add_argument('role',choices=['game','plugin']);p.add_argument('--directory',required=True);p.add_argument('--port',type=int,default=0);p.add_argument('--fault');p.add_argument('--message-id',default='1'*32);p.add_argument('--now-ms',type=int,default=0);p.add_argument('--die-after-response',action='store_true');a=p.parse_args()
 secret=read_key(a.directory)
 if a.role=='game':
  h=Harness(a.directory,fault=a.fault,hard_exit=bool(a.fault),secret=secret);server=LoopbackServer(h.ingress,LoopbackAddress(a.port));stop=Event()
  def finish(*_):stop.set();server.close()
  signal.signal(signal.SIGTERM,finish)
  print(json.dumps({'type':'READY','pid':os.getpid(),'host':server.address.host,'port':server.address.port,'scope':'SYNTHETIC_ONLY'}),flush=True)
  try:server.serve(stop)
  finally:server.close()
 else:
  from pathlib import Path
  pair=pairing(secret);box=Outbox(Path(a.directory)/'plugin.p12-outbox.sqlite',pair)
  mid=box.enqueue(submit(mid=a.message_id));client=LoopbackClient(LoopbackAddress(a.port),pair)
  if a.die_after_response:
   real=client
   class CrashClient:
    def exchange(self,raw):
     real.exchange(raw)
     os._exit(72)  # Reply received; outbox confirmation has NOT been committed.
   client=CrashClient()
  result=ClientPump(box,client).step(mid,a.now_ms);row=box.get(mid)
  print(json.dumps({'state':result,'row_state':row['state'],'message_id':mid,'inbox_id':row['inbox_id'],'raw_sha256':row['raw_sha'],'action':row['action'],'attempts':row['attempts'],'receipt_sequence':row['receipt_seq']}),flush=True)
 return 0
if __name__=='__main__':raise SystemExit(main())

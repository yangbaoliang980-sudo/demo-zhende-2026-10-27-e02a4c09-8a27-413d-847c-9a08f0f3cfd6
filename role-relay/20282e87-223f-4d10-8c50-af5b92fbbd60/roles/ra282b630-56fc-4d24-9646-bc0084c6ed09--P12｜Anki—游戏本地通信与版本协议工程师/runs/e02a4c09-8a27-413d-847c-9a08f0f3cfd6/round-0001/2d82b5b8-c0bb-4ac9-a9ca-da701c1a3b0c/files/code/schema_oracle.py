"""Cross-check the closed runtime validator against jsonschema Draft 2020-12.

Optional author-tool dependency only. It is not used by either IPC peer.
"""
import argparse,copy,hashlib,importlib.metadata,json
from pathlib import Path
from mocks.anki_transport.support import Harness,submit,query,event,control,SCOPE
from runtime.anki.transport.ipc_server_client.protocol import SCHEMA,ProtocolError,validate,canonical,VERSION,request

def mutations(value):
 yield value
 def paths(obj,prefix=()):
  if isinstance(obj,dict):
   for k,v in obj.items():
    yield prefix+(k,)
    yield from paths(v,prefix+(k,))
  elif isinstance(obj,list):
   for i,v in enumerate(obj):
    yield prefix+(i,)
    yield from paths(v,prefix+(i,))
 for path in paths(value):
  for new in [None,True,False,-1,0,9007199254740992,'unexpected','x\n','../private',{},[]]:
   obj=copy.deepcopy(value);parent=obj
   for k in path[:-1]:parent=parent[k]
   parent[path[-1]]=new;yield obj
  obj=copy.deepcopy(value);parent=obj
  for k in path[:-1]:parent=parent[k]
  if isinstance(parent,dict):del parent[path[-1]];yield obj
 obj=copy.deepcopy(value);obj['unknown']='x';yield obj

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 import jsonschema
 jsonschema.Draft202012Validator.check_schema(SCHEMA)
 reqs=[submit(mid='1'*32),submit(control('UNDO','undo-1','review-1',1),mid='2'*32),query(),request('HELLO',{'supported_versions':[VERSION]},message_id='3'*32,producer_id='fixture:plugin',scope=SCOPE)]
 with Harness() as h:
  replies=[h.send(reqs[0]),h.send(reqs[1]),h.send(reqs[3]),h.send(query(inbox='0'*64))]
 with Harness(closed=True) as h:replies.append(h.send(reqs[0]))
 mismatch=[];count=accepted=0;corpus=hashlib.sha256()
 for definition,seeds in [('request',reqs),('response',replies)]:
  standard=jsonschema.Draft202012Validator({'$schema':SCHEMA['$schema'],'$ref':'#/$defs/'+definition,'$defs':SCHEMA['$defs']})
  for seed in seeds:
   for value in mutations(seed):
    count+=1;corpus.update(canonical(value));external=standard.is_valid(value)
    try:validate(value,definition);internal=True
    except ProtocolError:internal=False
    accepted+=external
    if internal!=external:mismatch.append({'definition':definition,'value':value,'runtime':internal,'external':external})
 report={'status':'FAIL' if mismatch else 'PASS','validator':'jsonschema','validator_version':importlib.metadata.version('jsonschema'),'dialect':'2020-12','schema_valid':True,'instances_compared':count,'valid_instances':accepted,'invalid_instances':count-accepted,'corpus_sha256':corpus.hexdigest(),'mismatches':mismatch,'scope':'AUTHOR_SCHEMA_ALGORITHM_CROSSCHECK_NOT_P32_REVIEW'}
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='mismatches'},indent=2));return 1 if mismatch else 0
if __name__=='__main__':raise SystemExit(main())

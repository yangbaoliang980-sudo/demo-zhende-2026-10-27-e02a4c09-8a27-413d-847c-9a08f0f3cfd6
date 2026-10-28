"""Generate and validate real bytes for synthetic examples using original P11."""
import json
from mocks.anki_transport.support import Harness,submit,event,control,SCOPE,ROOT
from runtime.anki.transport.ipc_server_client.protocol import canonical,decode_response,VERSION,request,byte_hash,digest

def main():
 target=ROOT/'mocks/anki_transport/fixtures';records=[]
 def save(name,req,h):
  raw=canonical(req);reply=h.ingress.handle(raw);decode_response(reply)
  for suffix,data in [('request',raw),('response',reply)]:
   p=target/(name+'.'+suffix+'.json');p.write_bytes(data+b'\n')
   records.append({'path':p.relative_to(ROOT).as_posix(),'wire_bytes':len(data),'wire_sha256':byte_hash(data),'file_bytes':p.stat().st_size,'file_sha256':byte_hash(p.read_bytes()),'scope':'SYNTHETIC_ONLY'})
 with Harness() as h:
  save('01_hello',request('HELLO',{'supported_versions':[VERSION]},message_id='0'*32,producer_id='fixture:plugin',scope=SCOPE),h)
  save('02_review',submit(mid='1'*32),h)
  save('03_review_replay',submit(mid='1'*32),h)
  save('04_query_applied',request('QUERY_STATUS',{'inbox_id':digest(event())},message_id='2'*32,producer_id='fixture:plugin',scope=SCOPE),h)
  save('05_undo',submit(control('UNDO','undo-1','review-1',1),mid='3'*32),h)
  save('06_restore',submit(control('RESTORE','restore-1','undo-1',2),mid='4'*32),h)
  wrong=submit(mid='5'*32);wrong['protocol_version']='9.0.0';save('07_wrong_version',wrong,h)
 with Harness(closed=True) as h:save('08_quarantine',submit(mid='6'*32),h)
 with Harness() as h:save('09_causal_gap',submit(control('RESTORE','restore-1','undo-1',2),mid='7'*32),h)
 (target/'vector_manifest.json').write_text(json.dumps({'schema_version':'P12-WIRE-VECTORS/0.1.0','evidence_scope':'SYNTHETIC_P11_P21_ONLY','newline_note':'Files end in LF. Wire hashes exclude the final LF. HMAC/length use actual transmitted bytes.','records':records},indent=2)+'\n')
 print(json.dumps({'vector_pairs':len(records)//2,'validated_responses':len(records)//2,'status':'PASS'}))
if __name__=='__main__':main()

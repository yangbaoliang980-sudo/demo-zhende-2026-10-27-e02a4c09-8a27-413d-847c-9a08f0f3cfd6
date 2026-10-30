#!/usr/bin/env python3
"""Local P20 UI host. Default unbound; --fixture enables explicit author tests."""
from __future__ import annotations
import argparse,json,mimetypes,sys
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,unquote
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tests/meta_ui_unit/support'))
from fixture_host import Host,canonical

def serve(port=8766,fixture=False,scenario='demo'):
    model=Host(fixture,scenario)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,fmt,*args):print('P20_HTTP',fmt%args,flush=True)
        def headers_for(self,status,content_type,length):
            self.send_response(status);self.send_header('Content-Type',content_type);self.send_header('Content-Length',str(length))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
        def output(self,obj,status=200):
            data=json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode();self.headers_for(status,'application/json; charset=utf-8',len(data));self.wfile.write(data)
        def valid_host(self):return self.headers.get('Host') in {f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        def do_GET(self):
            if not self.valid_host():return self.output({'error':'E_HOST'},403)
            path=unquote(urlparse(self.path).path)
            if path=='/api/view':
                try:return self.output(model.view())
                except ConnectionError as exc:return self.output({'error':str(exc)},503)
            if path=='/api/fixture/trace' and fixture:return self.output({'trace':model.trace,'intent_count':len(model.intents),'receipt_count':len(model.responses)})
            if path=='/':file=ROOT/'ui/meta/index.html'
            elif path=='/lab' and fixture:file=ROOT/'tests/meta_ui_unit/lab.html'
            elif path.startswith('/ui/meta/') or (fixture and path=='/tests/meta_ui_unit/lab.mjs'):file=(ROOT/path.lstrip('/')).resolve()
            else:return self.output({'error':'E_NOT_FOUND'},404)
            if not file.is_relative_to(ROOT) or not file.is_file():return self.output({'error':'E_NOT_FOUND'},404)
            # No serving arbitrary upstream, tests, evidence, game, or Anki files.
            if not (file.is_relative_to(ROOT/'ui/meta') or (fixture and file.name in {'lab.html','lab.mjs'})):
                return self.output({'error':'E_NOT_FOUND'},404)
            data=file.read_bytes();kind={'.mjs':'text/javascript; charset=utf-8','.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8'}.get(file.suffix,mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
            self.headers_for(200,kind,len(data));self.wfile.write(data)
        def do_POST(self):
            origin=self.headers.get('Origin')
            allowed={f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'}
            if not self.valid_host() or self.headers.get('X-P20-UI')!='1' or (origin is not None and origin not in allowed):return self.output({'error':'E_ORIGIN'},403)
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.output({'error':'E_CONTENT_TYPE'},415)
            try:length=int(self.headers.get('Content-Length','0'))
            except ValueError:return self.output({'error':'E_LENGTH'},400)
            if not 0<length<=65536:return self.output({'error':'E_BODY_LIMIT'},413)
            path=urlparse(self.path).path
            try:
                from yltt_framework.codec import loads
                data=loads(self.rfile.read(length))
                if path=='/api/command':return self.output(model.submit(data))
                if path=='/api/lookup':return self.output(model.lookup(data))
                if path=='/api/fixture' and fixture:return self.output(model.control(data))
                return self.output({'error':'E_NOT_FOUND'},404)
            except ConnectionError as exc:return self.output({'error':str(exc)},503)
            except (ValueError,KeyError,TypeError) as exc:return self.output({'error':str(exc)},400)
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}','fixture':fixture,'durable':False,'production_integration':'BLOCKED'},ensure_ascii=False),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close();model.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',type=int,default=8766);p.add_argument('--fixture',action='store_true');p.add_argument('--scenario',choices=['demo','empty','equipment','unbound'],default='demo');a=p.parse_args()
    serve(a.port,a.fixture,a.scenario)

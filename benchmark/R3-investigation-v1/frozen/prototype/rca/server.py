"""Loopback-only evidence inbox. No remote exposure or third-party messaging."""
import json,base64,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from . import engine
from .storage import read

def serve(case,port):
 case=Path(case).resolve()
 if not engine.statepath(case).exists():raise ValueError('Initialize the case first.')
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,status,body,kind='application/json'):
   raw=body.encode();self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
  def valid_host(self):return self.headers.get('Host') in [f'127.0.0.1:{port}',f'localhost:{port}']
  def do_GET(self):
   if not self.valid_host():return self.send(403,'{"error":"Invalid host"}')
   if self.path=='/':return self.send(200,(Path(__file__).with_name('ui.html')).read_text(),'text/html')
   if self.path=='/state':return self.send(200,json.dumps(read(engine.statepath(case)),ensure_ascii=False))
   self.send(404,'{"error":"Not found"}')
  def do_POST(self):
   if not self.valid_host() or self.headers.get('Origin') not in [f'http://127.0.0.1:{port}',f'http://localhost:{port}']:return self.send(403,'{"error":"Same-origin local requests only"}')
   try:
    n=int(self.headers.get('Content-Length','0'))
    if n<1 or n>30_000_000:raise ValueError('Request size is invalid (30 MB maximum).')
    data=json.loads(self.rfile.read(n))
    if self.path=='/submit':
     if data.get('file'):
      name=Path(data['filename']).name
      with tempfile.TemporaryDirectory() as tmp:
       p=Path(tmp)/name;p.write_bytes(base64.b64decode(data['file'],validate=True));sid,changed=engine.submit(case,path=p,request_id=data.get('request_id'),corrects=data.get('corrects'))
     else:sid,changed=engine.submit(case,request_id=data.get('request_id'),answer=data.get('answer'),corrects=data.get('corrects'))
     return self.send(200,json.dumps(dict(source_id=sid,changed=changed)))
    if self.path=='/run':
     budget=int(data.get('max_calls',12))
     if not 1<=budget<=100:raise ValueError('Choose 1–100 calls for this invocation; resume later if needed.')
     def work():
      try:engine.run(case,budget)
      except Exception as e:print('Run stopped:',str(e),flush=True)
     threading.Thread(target=work,daemon=True).start();return self.send(202,'{"started":true}')
    if self.path=='/review':
     engine.review(case,data['id'],int(data['version']),data['decision'],data['note']);return self.send(200,'{"saved":true}')
    self.send(404,'{"error":"Not found"}')
   except Exception as e:self.send(400,json.dumps({'error':str(e)}))
 print(f'RCA inbox: http://127.0.0.1:{port}',flush=True)
 ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()

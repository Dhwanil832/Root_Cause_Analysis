"""Loopback evidence inbox; atomic submissions and visible run/recovery outcomes."""
import json,base64,tempfile,threading
from pathlib import Path
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from . import engine,provider


def make_server(case,port=8765):
 case=Path(case).resolve()
 if not engine.statepath(case).exists():raise ValueError('Initialize the case first.')
 guard=threading.Lock();running=False;run_error=None
 class Handler(BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def send(self,status,body,kind='application/json'):
   raw=body.encode();self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(raw)
  def hosts(self):return [f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}']
  def do_GET(self):
   if self.headers.get('Host') not in self.hosts():return self.send(403,'{"error":"Invalid host"}')
   if self.path=='/':return self.send(200,Path(__file__).with_name('ui.html').read_text(),'text/html')
   if self.path in ['/ui.js','/ui_state.js']:return self.send(200,Path(__file__).with_name(self.path[1:]).read_text(),'application/javascript')
   if self.path=='/state':
    state=engine.view_state(case);state['run_active']=state['run_active'] or running
    if run_error:state['diagnostics']['server_error']=run_error
    return self.send(200,json.dumps(state,ensure_ascii=False))
   self.send(404,'{"error":"Not found"}')
  def do_POST(self):
   nonlocal running,run_error
   if self.headers.get('Host') not in self.hosts() or self.headers.get('Origin') not in ['http://'+h for h in self.hosts()]:return self.send(403,'{"error":"Same-origin local requests only"}')
   try:
    n=int(self.headers.get('Content-Length','0'))
    if n<1 or n>30_000_000:raise ValueError('Request size is invalid (30 MB maximum). Nothing submitted.')
    data=json.loads(self.rfile.read(n))
    if self.path=='/submit':
     with tempfile.TemporaryDirectory() as tmp:
      entries=[];request=data.get('request_id')
      if data.get('answer','').strip():entries.append(dict(answer=data['answer'],request_id=request,corrects=data.get('corrects') if not data.get('file') else None))
      if data.get('file'):
       name=Path(data['filename']).name;p=Path(tmp)/name;raw=base64.b64decode(data['file'],validate=True)
       if len(raw)>20_000_000:raise ValueError('Upload must be at most 20 MB. Nothing submitted.')
       p.write_bytes(raw);entries.append(dict(path=p,request_id=request,corrects=data.get('corrects')))
      if not entries:raise ValueError('An answer or document is required.')
      outcomes=engine.submit_bundle(case,entries)
     return self.send(200,json.dumps(dict(saved=outcomes,atomic=True)))
    if self.path=='/run':
     budget=data.get('max_calls')
     if budget is not None and (type(budget) is not int or budget<1):raise ValueError('Optional checkpoint must be a positive integer; omit it for no call-count cap.')
     with guard:
      if running:raise ValueError('This case is already running; wait for it to pause.')
      running=True;run_error=None
     started=threading.Event();outcome={}
     def acquired():outcome['acquired']=True;started.set()
     def work():
      nonlocal running,run_error
      try:engine.run(case,budget,_on_started=acquired)
      except Exception as exc:
       run_error=provider.diagnostic(exc);outcome['error']=run_error
      finally:
       with guard:running=False
       started.set()
     threading.Thread(target=work,daemon=True).start()
     if not started.wait(5):return self.send(202,'{"starting":true,"message":"Waiting for startup validation; inspect current status."}')
     if 'error' in outcome and not outcome.get('acquired'):return self.send(409,json.dumps(dict(error=outcome['error']['detail'],diagnostic=outcome['error'])))
     return self.send(202,'{"started":true,"message":"Run acquired the case. Follow status for completion or failure."}')
    if self.path=='/retry':
     result=engine.retry_failed(case,data.get('reason',''));run_error=None;return self.send(200,json.dumps(result))
    if self.path=='/review':
     engine.review(case,data['id'],int(data['version']),data['decision'],data['note']);return self.send(200,'{"saved":true}')
    self.send(404,'{"error":"Not found"}')
   except Exception as exc:self.send(400,json.dumps({'error':provider.sanitize(str(exc)),'submitted':False if self.path=='/submit' else None}))
 return ThreadingHTTPServer(('127.0.0.1',port),Handler)


def serve(case,port):
 server=make_server(case,port)
 print(f'RCA inbox: http://127.0.0.1:{server.server_port}',flush=True)
 server.serve_forever()

import { setTimeout } from 'node:timers/promises';
import { request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
const base = process.env.RCA_APP_URL || `http://127.0.0.1:${process.env.RCA_PORT || 3017}`;
const token = process.env.RCA_WORKER_TOKEN;
if (!token) throw new Error('RCA_WORKER_TOKEN is required; normally npm run dev supplies it to both processes.');
let stopping = false;
process.on('SIGTERM', () => { stopping = true; });
process.on('SIGINT', () => { stopping = true; });
console.log(`Try 7 investigation worker polling ${base}; one model task at a time.`);
let lastError = '';
// Node fetch has a default headers timeout that can abandon a still-running
// local inference. Explicit cancellation, not a second HTTP timer, owns this call.
function tick() {
  return new Promise((resolve,reject)=>{
    const url=new URL('/api/engine/tick',base), request=url.protocol==='https:'?httpsRequest:httpRequest;
    const req=request(url,{method:'POST',headers:{'x-rca-worker-token':token}},res=>{
      let data='';res.setEncoding('utf8');res.on('data',chunk=>{data+=chunk;});res.on('error',reject);
      res.on('end',()=>{try{const body=JSON.parse(data);if((res.statusCode||500)>=400)throw Object.assign(Error(body.error||'Worker endpoint: '+res.statusCode),{fatal:true});resolve(body);}catch(e){reject(Object.assign(e,{fatal:true}));}});
    });req.on('error',reject);req.end();
  });
}
while (!stopping) {
  try {
    // No application task or whole-investigation timeout. Native provider limits
    // still apply; leases recover interruptions without resetting the run.
    const body = await tick();
    lastError = '';
    if (!body.idle) console.log(JSON.stringify(body));
    if (body.idle) await setTimeout(2500);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message !== lastError) console.error(`Worker waiting: ${message}`);
    lastError = message;
    if(error?.fatal){console.error('Worker stopped after an unhandled server failure. Inspect the saved run before restarting.');process.exitCode=1;break;}
    await setTimeout(5000);
  }
}

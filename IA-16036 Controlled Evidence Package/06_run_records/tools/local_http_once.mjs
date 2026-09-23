import http from 'node:http';

// No implicit five-minute headers deadline, retries, redirects or remote hosts.
// The caller's explicit wall-clock deadline is the only timeout.
export function localHttpOnce(url, {method='GET', headers={}, body, timeoutMs=30000}={}) {
  const target=new URL(url);
  if(target.protocol!=='http:'||!['127.0.0.1','localhost','[::1]'].includes(target.hostname))throw Error('Local HTTP only');
  if(!Number.isFinite(timeoutMs)||timeoutMs<=0)throw Error('Explicit positive timeout required');
  return new Promise((resolve,reject)=>{
    const request=http.request(target,{method,headers},response=>{
      const chunks=[];
      response.on('data',chunk=>chunks.push(chunk));
      response.on('end',()=>{clearTimeout(timer);resolve({status:response.statusCode,body:Buffer.concat(chunks).toString('utf8')});});
      response.on('error',error=>{clearTimeout(timer);reject(error);});
    });
    const timer=setTimeout(()=>request.destroy(new Error(`Explicit local HTTP deadline exceeded (${timeoutMs} ms)`)),timeoutMs);
    request.on('error',error=>{clearTimeout(timer);reject(error);});
    request.end(body);
  });
}

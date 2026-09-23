import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const dir=path.resolve(process.argv[2]||'');
const root=path.join(dir,'frozen-app/prompts');
const sha=text=>createHash('sha256').update(text).digest('hex');
const shared=fs.readFileSync(path.join(root,'shared/system.md'),'utf8');
const prompts={};
function walk(at){for(const entry of fs.readdirSync(at,{withFileTypes:true})){const full=path.join(at,entry.name);if(entry.isDirectory())walk(full);else if(entry.name==='system.md')prompts[sha(shared+'\n\n'+fs.readFileSync(full,'utf8'))]=path.relative(root,path.dirname(full));}}
walk(root);
const files=fs.readdirSync(path.join(dir,'model-capture')).filter(n=>n.endsWith('-request.json')).sort();
const all=process.argv.includes('--all');
const detailed=process.argv.includes('--details');
for(const name of all?files:files.slice(-3)){
  const request=JSON.parse(fs.readFileSync(path.join(dir,'model-capture',name)));
  const input=request.messages[1].content;
  const packed=input.split('--- BEGIN EVIDENCE PACKET ---')[1]?.split('--- END EVIDENCE PACKET ---')[0]?.trim();
  let packet={};try{packet=JSON.parse(packed);}catch{}
  const responseName=name.replace('-request','-response'),responsePath=path.join(dir,'model-capture',responseName);
  let response,output;try{response=JSON.parse(fs.readFileSync(responsePath));output=JSON.parse(response.message?.content);}catch{}
  console.log(JSON.stringify({id:name.slice(0,4),stage:prompts[sha(request.messages[0].content)]||'unknown',inputKeys:Object.keys(packet),inputChars:input.length,repair:input.includes('previous output failed validation'),finished:fs.existsSync(responsePath),durationSeconds:response?.total_duration/1e9,outputTokens:response?.eval_count,outputKeys:output?Object.keys(output):[],summary:output?.decision?.summary,...(detailed?{packet,output}:{})}));
}

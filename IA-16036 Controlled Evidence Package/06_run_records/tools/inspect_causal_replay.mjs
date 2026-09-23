// Read-only status for the causal-only replay, including reused-call lineage.
import fs from 'node:fs';
import path from 'node:path';
const directory=path.resolve(process.argv[2]||'');
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const manifest=read(path.join(directory,'manifest.json'));
const unique=new Map(),visited=new Set();
function load(folder){
  if(visited.has(folder))throw Error('Lineage cycle');visited.add(folder);
  const m=read(path.join(folder,'manifest.json'));
  if(m.checkpointReuseSource)load(m.checkpointReuseSource);
  for(const name of fs.readdirSync(path.join(folder,'checkpoints')).sort()){
    const row=read(path.join(folder,'checkpoints',name));
    if(row.kind==='model-call')unique.set(row.key,row);
  }
}
load(directory);
const current=fs.readdirSync(path.join(directory,'checkpoints')).sort().map(name=>read(path.join(directory,'checkpoints',name)));
const counts={discovery:0,linking:0,revisions:0,verification:0};
const seenClaims=new Set(),proposals=[],tokens=[];
for(const row of unique.values()){
  const properties=row.requestIdentity.schema.properties;
  const stage=properties.nodes?'discovery':properties.edges?'linking':properties.updates?'revisions':'verification';
  counts[stage]++;
  if(stage==='discovery'){
    for(const claim of row.requestIdentity.packet.evidenceClaims||[])seenClaims.add(claim.id);
    proposals.push(...row.response.output.nodes);
  }
  if(row.response.usage?.inputTokens)tokens.push(row.response.usage.inputTokens);
}
const resultPath=path.join(directory,'result.json'),failurePath=path.join(directory,'failure.json');
const result=fs.existsSync(resultPath)?read(resultPath):null;
const failure=fs.existsSync(failurePath)?read(failurePath):null;
let processAlive=false;try{if(manifest.runnerPid){process.kill(manifest.runnerPid,0);processAlive=true;}}catch{}
const captures=fs.readdirSync(path.join(directory,'model-capture'));
console.log(JSON.stringify({directory,status:result?'completed':failure?'failed':processAlive?'running':'no-live-process-detected',
  startedAt:manifest.createdAt,processAlive,model:manifest.model,upstreamRerun:manifest.upstreamRerun,
  completeCalls:counts,currentRunNewCalls:current.filter(c=>c.kind==='model-call').length,
  reusedCalls:current.filter(c=>c.kind==='model-call-reused').length,
  requestsDispatched:captures.filter(f=>f.endsWith('-request.json')).length,
  responsesReceived:captures.filter(f=>f.endsWith('-response.json')).length,
  discoveryClaimCoverage:{presented:seenClaims.size,total:manifest.claims},
  draftPropositions:proposals.length,byteDistinctPropositions:new Set(proposals.map(p=>JSON.stringify(p))).size,
  inputTokens:tokens.length?{minimum:Math.min(...tokens),maximum:Math.max(...tokens)}:null,
  result,failure:failure?.error,appVersionCommitted:false,
  caution:'Proposal counts and successful execution do not establish causal correctness. Read verification and source passages.'},null,2));

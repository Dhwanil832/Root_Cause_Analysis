import { CLAIM_INTERPRETATION_POLICY, interpretationSchema, type ClaimInterpretation } from './contract';
import type { EngineState, Finding } from '../types';

const normalize=(s:string)=>s.replace(/\s+/gu,' ').trim();
export function interpretClaim(statement:string,raw:unknown):ClaimInterpretation {
  const out=interpretationSchema.parse(raw);
  if(out.targetStatement!==statement)throw new Error('Interpretation target differs from the saved proposition.');
  const target=normalize(statement),covered=new Uint8Array(target.length);
  const parts=out.parts.map((part,index)=>{
    const fragment=normalize(part.claimText);
    let start=target.indexOf(fragment);
    while(start>=0&&Array.from({length:fragment.length},(_,i)=>covered[start+i]).every(Boolean))start=target.indexOf(fragment,start+1);
    if(start<0)throw new Error('Interpretation part is not a verbatim target fragment.');
    for(let i=start;i<start+fragment.length;i++)covered[i]=1;
    return {...part,partId:'P'+(index+1)};
  });
  if([...target.matchAll(/[\p{L}\p{N}]+/gu)].some(m=>Array.from({length:m[0].length},(_,i)=>m.index+i).some(i=>!covered[i])))
    throw new Error('Interpretation omits target wording, including a possible qualifier or negation.');
  return {policy:CLAIM_INTERPRETATION_POLICY,targetStatement:statement,parts};
}
export function currentInterpretation(finding:Finding) {
  const meaning=finding.interpretation;
  return meaning?.policy===CLAIM_INTERPRETATION_POLICY&&meaning.targetStatement===finding.statement?meaning:undefined;
}
export function invalidateReview(finding:Finding,execution:'unreviewed'|'incomplete',reason:string,state?:EngineState) {
  finding.status='proposed';finding.reviewExecution=execution;finding.reviewReason=reason;finding.opposedBy=[];
  delete finding.reviewAssessment;delete finding.causalRole;delete finding.causalRelevance;
  // Retain the branch and its identity, but not a stale approval based on this premise.
  const nodes=state?.propositions.filter(p=>p.findingId===finding.id)||[];
  for(const node of nodes) {
    delete node.roleAssessment;
    node.status='proposed';node.reviewReason='Underlying claim review is '+execution+'.';
    if(node.humanStatus==='accepted')node.humanStatus='reopened';
  }
  for(const edge of state?.relationships.filter(e=>e.findingIds.includes(finding.id)||nodes.some(n=>e.from===n.id||e.to===n.id))||[]) {
    edge.status='proposed';edge.reviewReason='Underlying claim review is '+execution+'.';
  }
  for(const action of state?.actions.filter(a=>a.causalTargetIds.some(id=>nodes.some(n=>n.id===id)))||[]) {
    if(action.status==='accepted') {
      action.status='proposed';
      state?.changes.push({targetId:action.id,kind:'rechecked',reason:'Underlying premise changed; the corrective action needs fresh human approval.'});
    }
  }
}

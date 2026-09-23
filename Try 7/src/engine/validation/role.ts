import {z} from 'zod';
import type {EngineState,EngineTask} from '../types';
import {resolve,type References} from '../records';
export const roleSchema=z.object({status:z.enum(['valid','invalid','unknown']),reason:z.string().min(1),
  protectiveFunction:z.string(),references:z.array(z.string()),decision:z.object({summary:z.string()})});
export function applyRole(state:EngineState,task:EngineTask,raw:unknown,refs:References) {
  const out=roleSchema.parse(raw),p=state.propositions.find(p=>p.findingId===task.targetIds[0]);
  const f=state.findings.find(f=>f.id===p?.findingId);
  if(!p||!f)throw Error('Role target is missing.');
  const spans=resolve(out.references,refs.sources);
  if(out.status==='valid'&&(!spans.length||f.status!=='supported'))throw Error('A valid causal role requires original evidence and a supported observation.');
  if(out.status==='valid'&&p.type==='barrier'&&!out.protectiveFunction.trim())throw Error('A barrier requires an evidenced protective function.');
  p.roleAssessment={status:out.status,role:p.type,reason:out.reason,protectiveFunction:out.protectiveFunction,spanIds:spans,findingRevision:f.revision,version:state.version};
  if(p.humanStatus==='accepted'&&out.status!=='valid')p.humanStatus='reopened';
}

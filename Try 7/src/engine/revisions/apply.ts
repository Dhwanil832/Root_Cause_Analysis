import type {z} from 'zod';
import {revisionSchema} from '../investigation/contracts';
import type {EngineState,EngineTask} from '../types';
import {ingestFinding,resolve,quarantine,type References} from '../records';

/** Each correction is validated before mutation. Independent valid corrections
 * survive a malformed sibling; no verdict is inferred from a replacement. */
export function applyCorrections(state:EngineState,task:EngineTask,out:z.infer<typeof revisionSchema>,refs:References) {
  const applied=new Set<string>();
  for(const row of out.corrections)try {
    const id=resolve([row.finding],refs.findings)[0],f=state.findings.find(f=>f.id===id);
    if(!f||f.revision!==row.expectedRevision)throw Error('Stale correction: the saved finding revision differs.');
    if(!row.statement.trim()||!resolve(row.references,refs.sources).length)throw Error('A correction requires original source evidence.');
    const before=f.statement;
    ingestFinding(state,task,{...row,kind:f.kind,tags:f.tags,replaces:row.finding},refs);
    for(const p of state.propositions.filter(p=>p.findingId===id)) {delete p.roleAssessment;if(p.humanStatus==='accepted')p.humanStatus='reopened';}
    state.changes.push({targetId:id,kind:'revised',reason:row.reason,before,after:f.statement,evidenceIds:resolve(row.references,refs.sources)});
    applied.add(id);
  }catch(error){quarantine(state,task,row,error);}
  return applied;
}
export function applyImpacts(state:EngineState,task:EngineTask,out:z.infer<typeof revisionSchema>,refs:References,corrected=new Set<string>()) {
  const expected=new Set(task.targetIds),seen=new Set<string>();
  for(const row of out.impacts)try {
    const id=refs.findings.get(row.target)||row.target;
    if(!expected.has(id)||seen.has(id))throw Error('Impact must name an assigned target exactly once.');
    const findingIds=resolve(row.findings,refs.findings);
    if(['correct','strengthen','weaken'].includes(row.action)&&!findingIds.length)throw Error('A substantive impact requires attributed evidence.');
    if(row.action==='correct'&&state.findings.some(f=>f.id===id)&&!corrected.has(id))throw Error('A correction impact cannot be marked applied without a valid correction operation.');
    const branch=state.investigation!.branches.find(b=>b.id===id);
    if(row.action==='withdraw'&&branch&&branch.status!=='withdrawn')throw Error('A branch withdrawal needs an applied withdrawn branch revision.');
    if(['split','combine'].includes(row.action)&&branch) {
      const successors=state.investigation!.branches.filter(b=>b.replaces?.includes(id));
      if(branch.status!=='superseded'||!successors.length||(row.action==='split'&&successors.length<2))throw Error('Split/combine requires explicit successor branches and retained lineage.');
    }
    (state.investigation!.impacts ||= []).push({targetId:id,action:row.action,reason:row.reason,findingIds,version:state.version,taskId:task.id});
    seen.add(id);
  }catch(error){quarantine(state,task,row,error);}
  state.investigation!.pendingImpacts=[...expected].filter(id=>!seen.has(id));
  for(const id of state.investigation!.pendingImpacts)quarantine(state,task,{targetId:id},'Model omitted the required evidence-impact disposition; target remains unresolved.');
}

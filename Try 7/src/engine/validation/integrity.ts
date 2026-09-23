import type { EngineState, Relationship } from '../types';

/** Only strict precedence is acyclic. Physical/process feedback is not banned. */
export function temporalIssues(state:EngineState,edge:Relationship) {
  if(edge.type!=='preceded')return [];
  const visited=new Set<string>();
  const reaches=(id:string):boolean=>{
    if(id===edge.from)return true;if(visited.has(id))return false;visited.add(id);
    return state.relationships.some(e=>e.id!==edge.id&&e.type==='preceded'&&e.proposedBy?.length&&e.from===id&&reaches(e.to));
  };
  return reaches(edge.to)?['Strict precedence cycle between the same event nodes; withdraw or disambiguate event instances.']:[];
}
export function refreshIntegrity(state:EngineState) {
  for(const edge of state.relationships.filter(e=>e.proposedBy?.length)) {
    edge.integrityIssues=temporalIssues(state,edge);
    if(edge.integrityIssues.length){edge.status='unknown';edge.reviewReason=edge.integrityIssues.join(' ');}
    if(edge.type==='failed-to-prevent') {
      const barrier=state.propositions.find(p=>p.id===edge.from);
      if(barrier?.type!=='barrier'||barrier.roleAssessment?.status!=='valid'||!barrier.roleAssessment.protectiveFunction.trim()) {
        edge.integrityIssues.push('Protective function at the prevention-link source is not established.');
        edge.status='unknown';edge.reviewReason=edge.integrityIssues.join(' ');
      }
    }
  }
}

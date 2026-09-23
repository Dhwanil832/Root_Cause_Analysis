import { claimReviewSchema, CLAIM_REVIEW_POLICY, type ClaimReviewOutput, type ClaimInterpretation } from './contract';
import { currentInterpretation } from './interpretation';
import type { EngineState, EpistemicStatus, Finding } from '../types';
import type { References } from '../records';
import type { ReviewFormattingNormalization } from './formatting';

type Quote={source:string;line:number;quote:string;claimText?:string;label?:string;revision?:string;localRef?:string};
type Part=ClaimReviewOutput['parts'][number];
export interface ReviewedPart extends Omit<Part,'relation'|'counterexample'> {
  // The legacy relation remains readable in immutable earlier snapshots.
  relation:Part['relation']|'conflicting'|'partially-established';
  claimText:string;claimType:ClaimInterpretation['parts'][number]['claimType']|'mixed';
  counterexample?:Part['counterexample'];
  assertion?:string;truthConditions?:string;
  status:Exclude<EpistemicStatus,'proposed'>;
  spanIds:string[];issues:string[];quotes:Quote[];
}
type Conflict=ClaimReviewOutput['evidenceConflicts'][number];
export interface ReviewedConflict extends Conflict {
  status:'open';
  impact?:'claim-truth'|'underlying-event-only';
  sideA:ClaimReviewOutput['evidenceConflicts'][number]['sideA'] & {spanIds:string[];quotes:Quote[]};
  sideB:ClaimReviewOutput['evidenceConflicts'][number]['sideB'] & {spanIds:string[];quotes:Quote[]};
}
export interface ClaimReviewAssessment {
  policy:string;status:Exclude<EpistemicStatus,'proposed'>;
  parts:ReviewedPart[];uncoveredText:string[];issues:string[];
  evidenceConflicts?:ReviewedConflict[];
  formattingNormalization?:ReviewFormattingNormalization;
}

/** Structural/provenance checks cannot prove natural-language entailment.
 * Meaning and evidence judgments are separately retained and separately evaluated. */
export function assessClaim(state:EngineState,finding:Finding,raw:unknown,refs:References) {
  const out=claimReviewSchema.parse(raw),meaning=currentInterpretation(finding);
  if(out.targetStatement!==finding.statement)throw new Error('Review target differs from the saved proposition.');
  if(!meaning)throw new Error('No current evidence-blind interpretation exists for this claim.');
  if(out.interpretationIssue.trim())throw new Error('Review incomplete: fixed interpretation needs clarification. '+out.interpretationIssue);
  if(out.parts.length!==meaning.parts.length||new Set(out.parts.map(p=>p.partId)).size!==meaning.parts.length
    ||out.parts.some(p=>!meaning.parts.some(m=>m.partId===p.partId)))throw new Error('Review must judge every fixed part exactly once.');
  const spans=new Map(state.sources.flatMap(s=>s.spans).map(s=>[s.id,s]));
  function quotations(evidence:Part['evidence']) {
    const spanIds:string[]=[],quotes:Quote[]=[];
    for(const selection of evidence) {
      const id=refs.sources.get(selection.source),source=id?spans.get(id):undefined;
      for(const number of selection.lines) {
        const quote=source?.text.split('\n')[number-1];
        if(!source||source.modality||!quote?.trim())throw new Error('Review incomplete: no original text at '+selection.source+' line '+number+'.');
        spanIds.push(id!);quotes.push({source:selection.source,line:number,quote});
      }
    }
    return {spanIds:[...new Set(spanIds)],quotes};
  }
  const evidenceConflicts:ReviewedConflict[]=out.evidenceConflicts.map(conflict=>{
    if(conflict.affectsParts.some(id=>!meaning.parts.some(p=>p.partId===id)))throw new Error('Conflict refers to an unknown fixed part.');
    const sideA={...conflict.sideA,...quotations(conflict.sideA.evidence)},sideB={...conflict.sideB,...quotations(conflict.sideB.evidence)};
    const key=(quotes:Quote[])=>[...new Set(quotes.map(q=>q.source+':'+q.line))].sort().join('|');
    if(key(sideA.quotes)===key(sideB.quotes)&&sideA.assertion===sideB.assertion)throw new Error('A duplicated assertion is not two opposing evidence accounts.');
    return {...conflict,status:'open',sideA,sideB};
  });
  const blocks=new Set<number>();
  for(const q of out.questions)for(const number of q.requiredForParts) {
    if(number>meaning.parts.length)throw new Error('Question refers to a nonexistent fixed part.');
    blocks.add(number);
  }
  const parts:ReviewedPart[]=meaning.parts.map((fixed,index)=>{
    const part=out.parts.find(p=>p.partId===fixed.partId)!,quoted=quotations(part.evidence),issues:string[]=[];
    if(part.counterexample.possible&&!part.counterexample.scenario.trim())throw new Error('Review incomplete: counterexample scenario missing.');
    if(part.missingPremises.some(p=>p.trim()))issues.push('A necessary premise remains unproved.');
    if(part.counterexample.possible)issues.push('The supplied evidence permits this exact assertion to be false.');
    if(blocks.has(index+1))issues.push('An unanswered question is required to establish this part.');
    if(fixed.ambiguities.length)issues.push('The fixed meaning contains an unresolved material ambiguity.');
    const disputed=evidenceConflicts.some(c=>c.affectsParts.includes(fixed.partId))
      && !['record-observation','general-requirement'].includes(fixed.claimType);
    if(disputed)issues.push('Conflicting accounts leave the actual incident state unresolved.');
    const status:ReviewedPart['status']=disputed||fixed.ambiguities.length?'unknown'
      :part.relation==='entailed'?issues.length?'unknown':'supported'
      :part.relation==='contradicted'?'contradicted':'unknown';
    return {...fixed,...part,...quoted,status,issues};
  });
  const status:ClaimReviewAssessment['status']=parts.some(p=>p.status==='contradicted')?'contradicted'
    :parts.every(p=>p.status==='supported')?'supported':parts.some(p=>p.status==='supported')?'partial':'unknown';
  const assessment:ClaimReviewAssessment={policy:CLAIM_REVIEW_POLICY,status,parts,uncoveredText:[],issues:[],evidenceConflicts};
  const types=new Set(parts.map(p=>p.claimType));
  const contextOnly=[...types].every(t=>t==='record-observation'||t==='general-requirement');
  const causalRole:Finding['causalRole']=contextOnly?'context':status!=='supported'||types.has('hypothesis')?'hypothesis':types.has('actual-event')?'event':'condition';
  const reason=[status+': '+parts.filter(p=>p.status==='supported').length+'/'+parts.length+' necessary parts supported.',
    ...parts.map(p=>p.partId+' ('+p.status+'): '+p.reason+(p.issues.length?' '+p.issues.join(' '):'')),
    ...evidenceConflicts.map(c=>'Open source conflict: '+c.reason)].join(' ');
  return {out,assessment,causalRole,reason,
    causalRelevance:contextOnly?'Record content or a general requirement, not an established incident mechanism.':status==='supported'
      ?'The stated event/condition is supported; causal contribution still requires separate analysis.'
      :'Unproved proposition; may be explored as a hypothesis, not an established cause.',
    supporting:[...new Set(parts.filter(p=>p.status==='supported').flatMap(p=>p.spanIds))],
    opposing:[...new Set([...parts.filter(p=>p.status==='contradicted').flatMap(p=>p.spanIds),...evidenceConflicts.flatMap(c=>[...c.sideA.spanIds,...c.sideB.spanIds])])]};
}

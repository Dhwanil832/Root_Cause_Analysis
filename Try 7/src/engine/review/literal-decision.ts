import { literalReviewSchema, literalReviewShape, CLAIM_REVIEW_POLICY } from './literal-contract';
import type { ClaimReviewAssessment, ReviewedConflict, ReviewedPart } from './decision';
import type { EngineState, Finding } from '../types';
import { ingestQuestion, type References } from '../records';
import type { EngineTask } from '../types';
import { normalizeReviewFormatting } from './formatting';

type Selection={source:string;lines:number[]};
export function originalQuotations(state:EngineState,refs:References,selections:Selection[]) {
  const spans=new Map(state.sources.flatMap(s=>s.spans).map(s=>[s.id,s]));
  const spanIds:string[]=[],quotes:ReviewedPart['quotes']=[];
  for(const selection of selections) {
    const id=refs.sources.get(selection.source),span=id?spans.get(id):undefined;
    for(const line of selection.lines) {
      const quote=span?.text.split('\n')[line-1];
      if(!span||span.modality||!quote?.trim())throw new Error(`Review incomplete: no original text at ${selection.source} line ${line}.`);
      spanIds.push(id!);quotes.push({source:span.id,label:span.label,revision:span.revision,localRef:selection.source,line,quote});
    }
  }
  return {spanIds:[...new Set(spanIds)],quotes};
}

/** Recover questions only, never facts or a repaired verdict. A structurally
 * malformed, wrong-target or forged-citation response cannot supply gaps. */
export function preserveReviewGaps(state:EngineState,task:EngineTask,finding:Finding,raw:unknown,refs:References,incomplete:boolean) {
  const parsed=literalReviewShape.safeParse(raw);
  if(!parsed.success||parsed.data.targetStatement!==finding.statement)return [];
  const {output:out}=normalizeReviewFormatting(parsed.data,state.reviewFormattingPolicy);
  try {
    originalQuotations(state,refs,out.evidence);
    for(const c of out.evidenceConflicts)for(const side of [c.sideA,c.sideB])originalQuotations(state,refs,side.evidence);
  } catch {return [];}
  const ids:string[]=[];
  for(const premise of [...new Set(out.missingPremises.map(p=>p.trim()).filter(Boolean))]) {
    const id=ingestQuestion(state,task,{
      text:`What evidence, if any, can resolve this stated gap: “${premise}”?`,
      intent:'Resolve a proposed evidence gap; the question is not an established fact.',
      decision:`Determine whether the complete claim is supported: ${finding.statement}`,
      subject:finding.subject,location:finding.location,time:finding.time,
      references:[...new Set(out.evidence.map(e=>e.source))],
    },refs);
    const q=state.questions.find(q=>q.id===id)!;
    q.reviewTargets=[...new Set([...(q.reviewTargets||[]),finding.id])];
    q.owners=[...new Set([...q.owners,...finding.owners])];
    if(!q.answer)q.reason=incomplete?'Proposed gap recovered from an inconsistent review. The review remains incomplete; no factual verdict was accepted.':'Evidence needed to resolve an unestablished part of the original claim.';
    ids.push(id);
  }
  return ids;
}

/** Review the saved literal assertion. No generated interpretation, coverage
 * repair, term-definition veto, or fraction-of-sentence scoring is involved. */
export function assessLiteralClaim(state:EngineState,finding:Finding,raw:unknown,refs:References) {
  // Preserve the raw response. Normalize only exact empty-list markers, then
  // run every existing consistency, target and original-citation check.
  const formatted=normalizeReviewFormatting(literalReviewShape.parse(raw),state.reviewFormattingPolicy);
  const out=literalReviewSchema.parse(formatted.output);
  if(out.targetStatement!==finding.statement)throw new Error('Review target differs from the saved proposition.');
  const quotations=(selections:Selection[])=>originalQuotations(state,refs,selections);
  const evidenceConflicts:ReviewedConflict[]=out.evidenceConflicts.map(c=>{
    const sideA={...c.sideA,...quotations(c.sideA.evidence)},sideB={...c.sideB,...quotations(c.sideB.evidence)};
    const key=(q:ReviewedPart['quotes'])=>[...new Set(q.map(x=>`${x.source}:${x.line}`))].sort().join('|');
    if(key(sideA.quotes)===key(sideB.quotes)&&sideA.assertion===sideB.assertion)throw new Error('A duplicated assertion is not a source conflict.');
    return {...c,affectsParts:['P1'],sideA,sideB,status:'open'};
  });
  // A disagreement about reality does not erase a verified report-content claim.
  // Conversely a disputed actual value must not be marked false merely because
  // another account gives a different value.
  const disputed=evidenceConflicts.some(c=>c.impact==='claim-truth');
  const status:ClaimReviewAssessment['status']=disputed?'unknown':out.relation==='entailed'?'supported'
    :out.relation==='partially-established'?'partial':out.relation==='contradicted'?'contradicted':'unknown';
  const issues=disputed?['Unresolved source disagreement affects the truth of this complete assertion.']:[];
  const quoted=quotations(out.evidence);
  const part:ReviewedPart={partId:'P1',claimText:finding.statement,claimType:out.claimType,
    establishes:out.establishes,relation:out.relation,evidence:out.evidence,missingPremises:out.missingPremises,
    reason:out.reason,status,issues,...quoted};
  const assessment:ClaimReviewAssessment={policy:CLAIM_REVIEW_POLICY,status,parts:[part],uncoveredText:[],issues,evidenceConflicts,
    ...(formatted.normalization?{formattingNormalization:formatted.normalization}:{})};
  const contextOnly=out.claimType==='record-observation'||out.claimType==='general-requirement';
  const causalRole:Finding['causalRole']=contextOnly?'context':status!=='supported'||out.claimType==='hypothesis'?'hypothesis':out.claimType==='actual-event'?'event':'condition';
  const reason=[`${status}: ${out.reason}`,...issues,...out.missingPremises.map(p=>`Unresolved: ${p}`),...evidenceConflicts.map(c=>`Source conflict: ${c.reason}`),
    ...(formatted.normalization?['Formatting only: explicit no-missing-premise marker(s) removed from the list; genuine gaps and original response preserved.']:[])].join(' ');
  return {out,assessment,reason,causalRole,
    causalRelevance:contextOnly?'Established record content or rule text is not by itself an incident mechanism.':status==='supported'
      ?'The complete assertion is supported; causal contribution requires separate analysis.':'The complete assertion is not established as an incident cause.',
    supporting:status==='supported'||status==='partial'?quoted.spanIds:[],
    opposing:[...new Set([...(status==='contradicted'?quoted.spanIds:[]),...evidenceConflicts.flatMap(c=>[...c.sideA.spanIds,...c.sideB.spanIds])])]};
}

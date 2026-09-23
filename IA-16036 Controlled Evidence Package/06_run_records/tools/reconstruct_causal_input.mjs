// Read-only deterministic reconstruction of the pre-causal B0 boundary. No new model answers.
import fs from 'node:fs';
import path from 'node:path';
import {buildEvidenceSegments} from '../../../Try 4/src/knowledge/evidence-segments.ts';
import {documentObservationClaims} from '../../../Try 4/src/stages/document-intelligence/run.ts';
export function reconstructCausalInput(directory) {
  const dir=path.resolve(directory);
  const input=JSON.parse(fs.readFileSync(path.join(dir,'frozen-rca-input.json')));
  const state=JSON.parse(fs.readFileSync(path.join(dir,'failure-snapshot.json')));
  const track=state.incident.tracks.find(t=>t.id===input.trackId);
  if(input.answers.length || input.previousVersion || track.versions.length) throw Error('Only this initial B0 boundary is supported');
  const checkpoints=track.checkpoints.filter(c=>c.status==='completed');
  const at=stage=>{
    const matches=checkpoints.filter(c=>c.stage===stage);
    if(matches.length!==1)throw Error(`Ambiguous/missing checkpoint ${stage}`);
    return structuredClone(matches[0].payload);
  };
  const source=at('evidence-adjudication');
  const processed=at('evidence-processing');
  const fetched=at('answer-fetching');
  const claims=new Map([...processed.claims,...fetched.fetchedClaims,...documentObservationClaims(at('document-intelligence').records)].map(c=>[c.id,c]));
  const evidenceClaims=[...claims.values()];
  const knowledgeBases=at('tagging').map(tag=>at(tag.id).knowledgeBase);
  for(const kb of knowledgeBases) for(const claim of evidenceClaims.filter(c=>c.routedTo.includes(kb.tagId))) {
    if(kb.findings.some(f=>f.id===claim.id))continue;
    kb.findings.push({id:claim.id,statement:claim.text,type:claim.kind==='inference'?'hypothesis':'finding',status:claim.status,sourceIds:claim.sourceIds});
  }
  const byQuestion=new Map(fetched.answerFetches.map(f=>[f.questionId,f]));
  const questions=at('question-broker').questions.map(q=>{
    const f=byQuestion.get(q.id);
    return !f?q:{...q,status:f.status==='answered'?'answered':f.status==='partial'?'partially-answered':f.status==='conflicting'?'contradicted':'awaiting-user'};
  });
  return {originalIncident:{sourceId:'incident-description',text:input.description},answers:input.answers,
    evidenceSegments:buildEvidenceSegments(input.documents),structuredIncident:at('incident-structuring'),
    specialistKnowledgeBases:knowledgeBases,evidenceClaims,conflicts:processed.conflicts,
    sourceAssessments:source.sourceAssessments,adjudicationConflicts:source.adjudicationConflicts,
    questions,previousBoard:null};
}

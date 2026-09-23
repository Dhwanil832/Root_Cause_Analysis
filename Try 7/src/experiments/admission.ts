import type {DocumentRecord,InvestigationAnswer} from '@/src/domain/types';
import type {EngineInput} from '@/src/engine/types';
import {digest} from '@/src/engine/identity';

/** Controller objects are never downgraded to released evidence by a prompt. */
export function admitDocuments(documents:DocumentRecord[],trackId?:string,version?:number) {
  const seen=new Set<string>();
  for(const doc of documents) {
    if(seen.has(doc.id))throw Error('A release contains duplicate source IDs.');
    seen.add(doc.id);
    if(doc.visibility&&doc.visibility!=='released')throw Error('Controller-only or future evidence is not admitted to an investigator.');
    if(doc.trackId&&doc.trackId!==trackId)throw Error('Document belongs to a different model track.');
    if(version!==undefined&&doc.introducedVersion!==undefined&&doc.introducedVersion>version)throw Error('Document belongs to a future evidence release.');
  }
}
export function validateReleasedInput(input:EngineInput) {
  admitDocuments(input.documents,input.release?.trackId,input.release?input.release.parentVersion+1:undefined);
  if(input.release) {
    const actual=[...input.documents.map(d=>d.id),...input.answers.map(a=>a.sourceId||`answer:${a.questionId}`),'incident-description'].sort();
    if(new Set(actual).size!==actual.length)throw Error('Two released records cannot share a source identity.');
    if(JSON.stringify(actual)!==JSON.stringify([...input.release.sourceIds].sort()))throw Error('Input sources do not match the frozen release manifest.');
  }
}
export async function releaseHash(incident:string,documents:DocumentRecord[],answers:InvestigationAnswer[],extra:unknown) {
  return digest([incident,documents.map(d=>[d.id,d.revision,d.sha256,d.extractedText,d.scope,d.questionId,d.visibility||'released']).sort((a,b)=>String(a[0]).localeCompare(String(b[0]))),
    answers.map(a=>[a.questionId,a.text,a.responseStatus,a.sourceId]).sort((a,b)=>String(a[0]).localeCompare(String(b[0]))),extra]);
}

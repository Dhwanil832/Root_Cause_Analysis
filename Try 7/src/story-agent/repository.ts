import { database, addTrackAnswers, stageQuestionDocument } from '@/src/server/repository';
import type { AnalysisSnapshot } from '@/src/domain/types';
import { latestInput } from '@/src/server/engine-repository';
import { readJSON } from '@/src/engine/tasks/artifacts';
import { pendingStoryQuestions, scenarioSchema, releasedAnswerText, restrictStorySources, selectStoryRelease, type StoryScenario, type StoryOutput } from './contracts';

interface ScenarioRow {id:string;track_id:string;title:string;model_id:string;scenario_json:string;created_at:string}
interface RoundRow {id:string;scenario_id:string;base_version:number;status:string;questions_json:string;output_json:string;error:string;result_version:number|null;created_at:string;updated_at:string}
async function latest(trackId:string) {
  const track=await database().prepare('SELECT * FROM model_tracks WHERE id = ?').bind(trackId).first<{id:string;incident_id:string;model_id:string;model_name:string}>();
  if(!track) throw new Error('Model track not found.');
  const row=await database().prepare('SELECT number, analysis_json FROM versions WHERE track_id = ? ORDER BY number DESC LIMIT 1').bind(trackId).first<{number:number;analysis_json:string}>();
  if(!row) throw new Error('Complete the initial RCA version first.');
  return {track,version:row.number,analysis:await readJSON<AnalysisSnapshot>(database(),row.analysis_json)};
}
async function scenarioFor(trackId:string) {
  return database().prepare('SELECT * FROM story_scenarios WHERE track_id = ?').bind(trackId).first<ScenarioRow>();
}
async function roundsFor(scenarioId:string) {
  return (await database().prepare('SELECT * FROM story_rounds WHERE scenario_id = ? ORDER BY created_at').bind(scenarioId).all<RoundRow>()).results;
}
// Only the separate simulator endpoint calls this. RCA endpoints never load scenarios.
export async function getStoryWorkspace(trackId:string) {
  const current=await latest(trackId);
  const scenario=await scenarioFor(trackId);
  const rounds=scenario ? await roundsFor(scenario.id):[];
  return {track:current.track,version:current.version,questions:pendingStoryQuestions(current.analysis),
    scenario:scenario ? {...scenario,definition:JSON.parse(scenario.scenario_json),scenario_json:undefined}:null,
    rounds:rounds.map(r=>({...r,questions:JSON.parse(r.questions_json),output:JSON.parse(r.output_json),questions_json:undefined,output_json:undefined}))};
}
export async function createStoryScenario(trackId:string, definition:unknown) {
  const current=await latest(trackId);
  if(!current.track.model_id.startsWith('ollama:')) throw new Error('Select an Ollama RCA track for this local story workflow.');
  const scenario=scenarioSchema.parse(definition);
  if(await scenarioFor(trackId)) throw new Error('This track already has a locked scenario. Use another incident track for another world.');
  const id=crypto.randomUUID();
  await database().prepare('INSERT INTO story_scenarios (id,track_id,title,model_id,scenario_json,created_at) VALUES (?,?,?,?,?,?)')
    .bind(id,trackId,scenario.title,current.track.model_id,JSON.stringify(scenario),new Date().toISOString()).run();
  return {id};
}
export async function generateStoryRound(trackId:string, questionIds?:string[], sourceIds?:string[]) {
  const scenario=await scenarioFor(trackId);
  if(!scenario) throw new Error('Lock a scenario first.');
  restrictStorySources(JSON.parse(scenario.scenario_json) as StoryScenario, sourceIds);
  const current=await latest(trackId), latestRun=await latestInput(database(),trackId);
  if(latestRun && ['queued','running'].includes(latestRun.row.status)) throw new Error('Wait for the queued RCA revision before selecting its questions.');
  const history=await roundsFor(scenario.id), existing=history.find(r=>r.base_version===current.version);
  if(existing && !['failed','partial','paused'].includes(existing.status)) return {id:existing.id,status:existing.status};
  if(history.some(r=>['generating','applying'].includes(r.status))) throw new Error('A story round is already running.');
  const all=pendingStoryQuestions(current.analysis);
  if(questionIds?.some(id=>!all.some(q=>q.id===id))) throw new Error('The selection contains stale or unknown question IDs.');
  const questions=existing ? JSON.parse(existing.questions_json) as Array<{id:string;text:string;sourceIds?:string[]}>
    : (questionIds ? all.filter(q=>questionIds.includes(q.id)) : all).map(q=>({...q,...(sourceIds ? {sourceIds} : {})}));
  if(!questions.length) throw new Error('Select at least one unanswered question.');
  const id=existing?.id || crypto.randomUUID(), now=new Date().toISOString(), db=database();
  if(existing) {
    await db.batch([
      db.prepare("UPDATE story_rounds SET status='generating',error='',updated_at=? WHERE id=? AND status IN ('failed','partial','paused')").bind(now,id),
      db.prepare("UPDATE story_jobs SET status='queued',error='',lease=NULL,lease_until=0,updated_at=? WHERE round_id=? AND status='failed'").bind(now,id),
    ]);
  } else {
    await db.batch([
      db.prepare('INSERT INTO story_rounds (id,scenario_id,base_version,status,questions_json,output_json,error,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)')
        .bind(id,scenario.id,current.version,'generating',JSON.stringify(questions),'{}','',now,now),
      ...questions.map(q=>db.prepare("INSERT INTO story_jobs (id,round_id,question_id,question_json,created_at,updated_at) VALUES (?,?,?,?,?,?)")
        .bind(crypto.randomUUID(),id,q.id,JSON.stringify(q),now,now)),
    ]);
  }
  return {id,status:'generating'};
}
export async function applyStoryRound(trackId:string, roundId:string, strictCausal = false, documents: {sourceId:string;questionId:string}[] = [], approvedQuestionIds?:string[]) {
  const scenario=await scenarioFor(trackId);
  if(!scenario) throw new Error('Scenario not found.');
  const round=await database().prepare('SELECT * FROM story_rounds WHERE id=? AND scenario_id=?').bind(roundId,scenario.id).first<RoundRow>();
  if(!round) throw new Error('Round not found for this track.');
  if(round.status==='applied') return {version:round.result_version};
  const queued=await latestInput(database(),trackId);
  if(queued?.input.storyRoundId===roundId) return {version:queued.row.number,queued:true};
  const current=await latest(trackId);
  if(current.version!==round.base_version || (queued && queued.row.number!==round.base_version)) throw new Error('This batch belongs to an older RCA version. Generate a new batch.');
  const claim=await database().prepare("UPDATE story_rounds SET status='applying',error='',updated_at=? WHERE id=? AND status IN ('ready','partial')")
    .bind(new Date().toISOString(),roundId).run();
  if(!claim.meta.changes) throw new Error('This round is not ready or is already being applied.');
  try {
    const definition=JSON.parse(scenario.scenario_json) as StoryScenario;
    const candidate=JSON.parse(round.output_json) as {output:StoryOutput};
    const output=selectStoryRelease(candidate.output,approvedQuestionIds);
    const questions=JSON.parse(round.questions_json) as Array<{id:string;sourceIds?:string[]}>;
    if (new Set(documents.map(d=>d.sourceId)).size !== documents.length) throw new Error('Duplicate release document.');
    const selectedDocuments=documents.map(d=>{
      const q=questions.find(q=>q.id===d.questionId);
      const source=definition.sources.find(s=>s.id===d.sourceId && s.available);
      if(!q || !source || (q.sourceIds && !q.sourceIds.includes(source.id))) throw new Error('Document is outside this question batch release scope.');
      return {source,questionId:q.id};
    });
    // All records and unchanged model answers are staged before ONE revision is
    // queued. A repeat reuses matching staged originals; it cannot create V3.
    for(const {source,questionId} of selectedDocuments) await stageQuestionDocument(trackId,questionId,
      new File([source.text], `${source.id}.md`, {type:'text/markdown'}),round.base_version);
    await database().prepare("UPDATE story_rounds SET output_json=? WHERE id=? AND status='applying'")
      .bind(JSON.stringify({...candidate,releasedOutput:output,releaseDocuments:documents,
        withheldQuestionIds:candidate.output.answers.filter(a=>!output.answers.some(b=>a.questionId===b.questionId)).map(a=>a.questionId)}),roundId).run();
    const answers=output.answers.map(a=>({questionId:a.questionId,text:releasedAnswerText(a,definition),responseStatus:a.status,
      sourceId:`story-release:${roundId}:${a.questionId}`,answeredAt:new Date().toISOString()}));
    const result=await addTrackAnswers(trackId,answers,round.base_version,round.id,strictCausal);
    if(!result) throw new Error('Track disappeared before application.');
    return result;
  } catch(error) {
    await database().prepare("UPDATE story_rounds SET status='ready',error=?,updated_at=? WHERE id=? AND status='applying'")
      .bind(error instanceof Error?error.message:String(error),new Date().toISOString(),roundId).run();
    throw error;
  }
}

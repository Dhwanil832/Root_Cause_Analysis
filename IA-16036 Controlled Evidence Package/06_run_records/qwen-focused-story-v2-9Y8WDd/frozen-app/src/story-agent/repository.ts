import { database, modelFromId, addTrackAnswers } from '@/src/server/repository';
import type { AnalysisSnapshot } from '@/src/domain/types';
import { answerStoryBatch, StoryValidationError } from './run';
import { pendingStoryQuestions, scenarioSchema, releasedAnswerText, type StoryScenario, type StoryOutput } from './contracts';

interface ScenarioRow {id:string;track_id:string;title:string;model_id:string;scenario_json:string;created_at:string}
interface RoundRow {id:string;scenario_id:string;base_version:number;status:string;questions_json:string;output_json:string;error:string;result_version:number|null;created_at:string;updated_at:string}
async function latest(trackId:string) {
  const track=await database().prepare('SELECT * FROM model_tracks WHERE id = ?').bind(trackId).first<{id:string;incident_id:string;model_id:string;model_name:string}>();
  if(!track) throw new Error('Model track not found.');
  const row=await database().prepare('SELECT number, analysis_json FROM versions WHERE track_id = ? ORDER BY number DESC LIMIT 1').bind(trackId).first<{number:number;analysis_json:string}>();
  if(!row) throw new Error('Complete the initial RCA version first.');
  return {track,version:row.number,analysis:JSON.parse(row.analysis_json) as AnalysisSnapshot};
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
export async function generateStoryRound(trackId:string, requestedQuestionIds?:unknown) {
  const scenario=await scenarioFor(trackId);
  if(!scenario) throw new Error('Lock a scenario first.');
  const current=await latest(trackId);
  const pending=pendingStoryQuestions(current.analysis);
  if(requestedQuestionIds!==undefined && (!Array.isArray(requestedQuestionIds) || !requestedQuestionIds.length ||
    requestedQuestionIds.some(id=>typeof id!=='string') || new Set(requestedQuestionIds).size!==requestedQuestionIds.length)) {
    throw new Error('Select distinct, nonempty pending question IDs.');
  }
  const selected=requestedQuestionIds as string[]|undefined;
  if(selected?.some(id=>!pending.some(q=>q.id===id))) throw new Error('A selected question is not pending in this version.');
  const questions=selected ? selected.map(id=>pending.find(q=>q.id===id)!):pending;
  if(!questions.length) throw new Error('No unanswered questions remain in this version.');
  const history=await roundsFor(scenario.id);
  const existing=history.find(r=>r.base_version===current.version);
  if(existing && JSON.stringify(JSON.parse(existing.questions_json))!==JSON.stringify(questions)) {
    throw new Error('This round has a different frozen question selection. Use a separate experiment.');
  }
  if(existing && existing.status!=='failed') return {id:existing.id,status:existing.status};
  // Generation and application are serialized per track; duplicate requests reuse the round.
  if(history.some(r=>['generating','applying'].includes(r.status))) throw new Error('A story round is already running.');
  const id=existing?.id || crypto.randomUUID(), now=new Date().toISOString();
  if(existing) {
    const claim=await database().prepare("UPDATE story_rounds SET status='generating', error='', updated_at=? WHERE id=? AND status='failed'").bind(now,id).run();
    if(!claim.meta.changes) throw new Error('Another request already restarted this round.');
  } else {
    await database().prepare('INSERT INTO story_rounds (id,scenario_id,base_version,status,questions_json,output_json,error,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)')
      .bind(id,scenario.id,current.version,'generating',JSON.stringify(questions),'{}','',now,now).run();
  }
  try {
    const result=await answerStoryBatch(await modelFromId(scenario.model_id),JSON.parse(scenario.scenario_json),questions,
      history.filter(r=>r.status==='applied').map(r=>JSON.parse(r.output_json).output as StoryOutput),
      current.analysis.answers.map(a=>({questionId:a.questionId,text:a.text})));
    await database().prepare("UPDATE story_rounds SET status='ready', output_json=?, updated_at=? WHERE id=?")
      .bind(JSON.stringify({...result,priorGeneration:existing ? JSON.parse(existing.output_json):undefined}),new Date().toISOString(),id).run();
    return {id,status:'ready'};
  } catch(error) {
    await database().prepare("UPDATE story_rounds SET status='failed',error=?,output_json=?,updated_at=? WHERE id=?")
      .bind(error instanceof Error?error.message:String(error),JSON.stringify({attempts:error instanceof StoryValidationError?error.attempts:[],priorGeneration:existing ? JSON.parse(existing.output_json):undefined}),new Date().toISOString(),id).run();
    throw error;
  }
}
export async function applyStoryRound(trackId:string, roundId:string, strictCausal = false) {
  const scenario=await scenarioFor(trackId);
  if(!scenario) throw new Error('Scenario not found.');
  const round=await database().prepare('SELECT * FROM story_rounds WHERE id=? AND scenario_id=?').bind(roundId,scenario.id).first<RoundRow>();
  if(!round) throw new Error('Round not found for this track.');
  if(round.status==='applied') return {version:round.result_version};
  const current=await latest(trackId);
  if(current.version!==round.base_version) throw new Error('This batch belongs to an older RCA version. Generate a new batch.');
  const claim=await database().prepare("UPDATE story_rounds SET status='applying',error='',updated_at=? WHERE id=? AND status='ready'")
    .bind(new Date().toISOString(),roundId).run();
  if(!claim.meta.changes) throw new Error('This round is not ready or is already being applied.');
  try {
    const definition=JSON.parse(scenario.scenario_json) as StoryScenario;
    const output=JSON.parse(round.output_json).output as StoryOutput;
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

import { answerStoryBatch } from './run';
import type { StoryScenario, StoryOutput } from './contracts';
import type { ModelDescriptor } from '@/src/domain/types';
import { readJSON } from '@/src/engine/tasks/artifacts';
import type { EngineInput } from '@/src/engine/types';
import { restrictStorySources } from './contracts';

interface Job { id:string;round_id:string;question_json:string;lease:string; }
/** One durable question per tick, independent of the RCA job queue. */
export async function storyWorkerStep(db:D1Database, resolveModel:(id:string)=>Promise<ModelDescriptor>, answer=answerStoryBatch, roundId?:string) {
  const lease=crypto.randomUUID(), now=Date.now();
  const job=await db.prepare(`UPDATE story_jobs SET status='running',lease=?,lease_until=?,attempts=attempts+1,updated_at=?
    WHERE id=(SELECT j.id FROM story_jobs j JOIN story_rounds r ON r.id=j.round_id
      WHERE r.status='generating' AND (j.status='queued' OR (j.status='running' AND j.lease_until<?))
      AND (? IS NULL OR r.id=?)
      AND NOT EXISTS (SELECT 1 FROM story_jobs busy WHERE busy.round_id=j.round_id AND busy.status='running' AND busy.lease_until>=?)
      ORDER BY j.created_at,j.id LIMIT 1) RETURNING *`).bind(lease,now+90000,new Date().toISOString(),now,roundId||null,roundId||null,now).first<Job>();
  if(!job) return {idle:true};
  let lost=false;
  const controller = new AbortController();
  const loseLease = () => { lost=true; controller.abort(new Error('Story job paused or lease lost.')); };
  const timer=setInterval(()=>{void db.prepare('UPDATE story_jobs SET lease_until=? WHERE id=? AND lease=? AND status=\'running\'')
    .bind(Date.now()+90000,job.id,lease).run().then(r=>{if(!r.meta.changes)loseLease();}).catch(loseLease);},20000);
  try {
    const row=await db.prepare(`SELECT s.scenario_json,s.model_id,s.track_id,s.id AS scenario_id FROM story_scenarios s
      JOIN story_rounds r ON r.scenario_id=s.id WHERE r.id=?`).bind(job.round_id).first<{scenario_json:string;model_id:string;scenario_id:string;track_id:string}>();
    if(!row) throw new Error('Story scenario disappeared.');
    const history=await db.prepare(`SELECT output_json FROM story_rounds WHERE scenario_id=? AND status='applied' ORDER BY created_at`)
      .bind(row.scenario_id).all<{output_json:string}>();
    const siblings=await db.prepare("SELECT output_json FROM story_jobs WHERE round_id=? AND status='completed' ORDER BY created_at,id")
      .bind(job.round_id).all<{output_json:string}>();
    const memory=[...history.results,...siblings.results].map(r=>{
      const saved=JSON.parse(r.output_json);return (saved.releasedOutput??saved.output) as StoryOutput;
    }).filter(Boolean);
    const model=await resolveModel(row.model_id);
    const original=await db.prepare('SELECT input_json FROM engine_runs WHERE track_id=? ORDER BY number LIMIT 1').bind(row.track_id).first<{input_json:string}>();
    const frozen=original?(await readJSON<EngineInput>(db,original.input_json)).model:null;
    if(frozen?.digest&&frozen.digest!==model.digest)throw new Error('Installed model digest changed; keep simulator identity fixed.');
    const question = JSON.parse(job.question_json) as {id:string;text:string;sourceIds?:string[]};
    const definition = restrictStorySources(JSON.parse(row.scenario_json) as StoryScenario, question.sourceIds);
    const result=await answer(model,definition,[{id:question.id,text:question.text}],memory,[],controller.signal);
    if(lost)return {leaseLost:true};
    await db.prepare("UPDATE story_jobs SET status='completed',output_json=?,error='',lease_until=0,updated_at=? WHERE id=? AND lease=?")
      .bind(JSON.stringify(result),new Date().toISOString(),job.id,lease).run();
  } catch(error) {
    const message=error instanceof Error?error.message:String(error);
    if(!lost&&/fetch failed|ECONNREFUSED|ECONNRESET|unreachable|(?:HTTP|returned) (401|403|429|50[234])|digest changed/i.test(message)) {
      await db.batch([
        db.prepare("UPDATE story_jobs SET status='queued',error=?,lease_until=0 WHERE id=? AND lease=?").bind(message,job.id,lease),
        db.prepare("UPDATE story_rounds SET status='paused',error=?,updated_at=? WHERE id=? AND status='generating'").bind(message,new Date().toISOString(),job.round_id),
      ]);
      return {idle:false,storyRoundId:job.round_id,status:'paused',error:message};
    }
    if(!lost)await db.prepare("UPDATE story_jobs SET status='failed',error=?,lease_until=0,updated_at=? WHERE id=? AND lease=?")
      .bind(error instanceof Error?error.message:String(error),new Date().toISOString(),job.id,lease).run();
  } finally {clearInterval(timer);}
  const jobs=(await db.prepare('SELECT status,output_json,error,question_id FROM story_jobs WHERE round_id=? ORDER BY created_at,id')
    .bind(job.round_id).all<{status:string;output_json:string;error:string;question_id:string}>()).results;
  const pending=jobs.some(j=>['queued','running'].includes(j.status));
  const complete=jobs.filter(j=>j.status==='completed').map(j=>JSON.parse(j.output_json));
  const failures=jobs.filter(j=>j.status==='failed').map(j=>({questionId:j.question_id,error:j.error}));
  const status=pending?'generating':failures.length?(complete.length?'partial':'failed'):'ready';
  await db.prepare("UPDATE story_rounds SET status=?,output_json=?,error=?,updated_at=? WHERE id=? AND status='generating'")
    .bind(status,JSON.stringify({output:{answers:complete.flatMap(r=>r.output.answers)},jobs:jobs.map(j=>({questionId:j.question_id,status:j.status,error:j.error})),failures}),
      failures.map(f=>f.questionId+': '+f.error).join('\n'),new Date().toISOString(),job.round_id).run();
  return {idle:false,storyRoundId:job.round_id,taskId:job.id,status};
}

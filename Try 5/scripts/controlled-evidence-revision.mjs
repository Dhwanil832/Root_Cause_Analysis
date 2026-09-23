// Operator-authorized scoped continuation. Uses the app's real D1/R2 store,
// production executor, frozen model, and evidence gates; never edits verdicts.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {getPlatformProxy} from 'wrangler';
import {readJSON,readState,putJSON,putState} from '../src/engine/tasks/artifacts.ts';
import {initializeState} from '../src/engine/tasks/planner.ts';
import {project} from '../src/engine/board/projection.ts';
import {workerStep} from '../src/engine/tasks/worker.ts';
import {D1EngineStore} from '../src/engine/tasks/d1-store.ts';
import {ENGINE_VERSION} from '../src/engine/types.ts';

const [mode,releasePath]=process.argv.slice(2);
if(!['prepare','run','refresh','watch'].includes(mode)||!releasePath)throw Error('Usage: controlled-evidence-revision.mjs prepare|run|refresh|watch RELEASE_JSON');
const release=JSON.parse(fs.readFileSync(releasePath,'utf8'));
const directory=path.dirname(path.resolve(releasePath));
const digest=value=>createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');
const write=(name,value)=>fs.writeFileSync(path.join(directory,name),JSON.stringify(value,null,2)+'\n');
const exclusive=(name,value)=>fs.writeFileSync(path.join(directory,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
process.env.WRANGLER_WRITE_LOGS='false';
process.env.WRANGLER_LOG_PATH='.wrangler/logs';
const platform=await getPlatformProxy({configPath:'wrangler.local.json',persist:{path:'.wrangler/state/v3'},remoteBindings:false,envFiles:[]});
const db=platform.env.DB;
let activeRunId;
try {
  async function modelIdentity(model) {
    const response=await fetch((process.env.OLLAMA_BASE_URL||'http://127.0.0.1:11434')+'/api/tags');
    if(!response.ok)throw Error('Ollama model list unavailable');
    const tags=await response.json();
    const installed=tags.models?.find(m=>(m.name===model.name||m.name===model.id.replace(/^ollama:/,''))&&m.digest===model.digest);
    if(!installed)throw Error('Original model digest unavailable; no model substitution allowed.');
    return {...model,digest:installed.digest};
  }
  async function row(id) {const value=await db.prepare('SELECT * FROM engine_runs WHERE id=?').bind(id).first();if(!value)throw Error('Run not found');return value;}
  async function refresh(manifest) {
    const v1=JSON.parse(fs.readFileSync(path.join(directory,'v1-frozen.json'),'utf8'));
    const parent=await row(manifest.parentRunId),current=await row(manifest.runId);
    const originalSnapshot=await readJSON(db,parent.snapshot_json);
    if(digest(originalSnapshot.causalBoard)!==manifest.parentBoardHash||digest(parent.state_json)!==manifest.parentStatePointerHash||digest(parent.input_json)!==manifest.parentInputPointerHash)throw Error('Frozen V1 changed. Stop and inspect.');
    const analysis=await readJSON(db,current.snapshot_json);
    const v2={id:current.id,number:current.number,trigger:current.trigger,createdAt:current.created_at,executionStatus:current.status,analysis};
    write('v2-latest.json',v2);
    const finished=['partial','completed'].includes(current.status);
    if(finished&&!fs.existsSync(path.join(directory,'v2-published.json')))exclusive('v2-published.json',v2);
    if(finished&&digest(JSON.parse(fs.readFileSync(path.join(directory,'v2-published.json'),'utf8')))!==digest(v2))throw Error('Published V2 changed. Stop and inspect.');
    const v2File=finished?'v2-published.json':'v2-latest.json';
    const incident=await db.prepare('SELECT * FROM incidents WHERE id=?').bind(release.incidentId).first();
    const boardVersion=(v,file,label)=>({number:v.number,label,subtitle:v.trigger,createdAt:v.createdAt,status:v.executionStatus,
      sourcePath:path.relative(path.resolve('..'),path.join(directory,file)),sourceSha256:digest(fs.readFileSync(path.join(directory,file),'utf8')),
      sourceRecordId:v.id,board:v.analysis.causalBoard});
    const versions=[boardVersion(v1,'v1-frozen.json','V1 · Frozen partial checkpoint'),boardVersion(v2,v2File,`V2 · ${finished?'Controlled partial revision':current.status}`)];
    const metadata={app:'Try 5',title:incident.title,description:incident.description,modelName:manifest.model.name,
      originalIncidentId:release.incidentId,originalTrackId:release.trackId,kind:'controlled-revision',
      note:`V1 is the operator-frozen partial checkpoint, not a completed original investigation. V2 is a real same-track evidence revision using four source-grounded answers and three B2 documents with the selected-answers-v1 scheduling policy. V2 execution: ${current.status}. The original unrestricted queue was not resumed.`,
      href:finished?'/history/causal-comparison':'/incident/'+release.incidentId,dataUrl:'/history/featured-causal-boards.json',
      versions:versions.map(({board,...v})=>({...v,nodes:board.nodes.length,edges:board.edges.length}))};
    fs.writeFileSync('src/history/featured-comparison.json',JSON.stringify(metadata,null,2)+'\n');
    fs.writeFileSync('public/history/featured-causal-boards.json',JSON.stringify({metadata,versions},null,2)+'\n');
    const summary={runId:current.id,status:current.status,version:current.number,v1Unchanged:true,nodes:analysis.causalBoard.nodes.length,
      edges:analysis.causalBoard.edges.length,verifiedEdges:analysis.causalBoard.edges.filter(e=>e.verified).length,
      tasks:analysis.engineProgress?.tasks.reduce((out,t)=>(out[t.status]=(out[t.status]||0)+1,out),{}),updatedAt:current.updated_at};
    write('status.json',summary);
    return summary;
  }
  if(mode==='prepare') {
    if(fs.existsSync(path.join(directory,'manifest.json')))throw Error('This release is already prepared; use run or refresh.');
    const parent=await row(release.parentRunId);
    if(parent.status!=='paused'||parent.track_id!==release.trackId||parent.number!==release.expectedParentVersion)throw Error('Expected exact paused parent version.');
    if(await db.prepare('SELECT id FROM engine_runs WHERE track_id=? AND number>?').bind(release.trackId,parent.number).first())throw Error('A later revision already exists.');
    if(await db.prepare("SELECT id FROM engine_runs WHERE status IN ('queued','running') LIMIT 1").first())throw Error('Pause other app work before preparing this controlled continuation.');
    const input=await readJSON(db,parent.input_json),previous=await readState(db,parent.state_json),before=await readJSON(db,parent.snapshot_json);
    if(input.engineVersion!==ENGINE_VERSION||!previous||input.model.provider!=='ollama')throw Error('Parent engine/model is not compatible.');
    await modelIdentity(input.model);
    const now=new Date().toISOString();
    const answers=release.answers.map(a=>({...a,answeredAt:now}));
    if(new Set(answers.map(a=>a.questionId)).size!==answers.length||answers.some(a=>!previous.questions.some(q=>q.id===a.questionId&&!q.coveredBy)))throw Error('Answers must target distinct parent questions.');
    exclusive('parent-row-before-freeze.json',parent);exclusive('parent-input.json',input);exclusive('parent-state.json',previous);exclusive('parent-snapshot-before-freeze.json',before);
    exclusive('previous-pinned-metadata.json',JSON.parse(fs.readFileSync('src/history/featured-comparison.json','utf8')));
    exclusive('previous-pinned-boards.json',JSON.parse(fs.readFileSync('public/history/featured-causal-boards.json','utf8')));
    const frozen=structuredClone(before);
    if(frozen.engineProgress){frozen.engineProgress.status='partial';frozen.engineProgress.scopeNote='Operator-frozen partial V1. The existing board is preserved exactly; unfinished tasks were not completed or discarded. V2 has an independently recorded controlled evidence scope.';}
    const frozenPointer=await putJSON(db,frozen);
    const documents=[];
    for(const sourcePath of release.documentPaths) {
      const text=fs.readFileSync(sourcePath,'utf8'),id=crypto.randomUUID(),fileName=path.basename(sourcePath),fileKey=`question/${release.trackId}/${id}-${fileName}`;
      await platform.env.FILES.put(fileKey,text,{httpMetadata:{contentType:'text/markdown'}});
      documents.push({id,scope:'question',title:fileName,plant:'IA-16036 controlled case',incidentId:release.incidentId,trackId:release.trackId,introducedVersion:parent.number+1,
        fileKey,fileName,contentType:'text/markdown',size:Buffer.byteLength(text),sha256:digest(text),revision:'1',extractionStatus:'ready',extractionNotes:'Unmodified fixed B2 record; copied from the clean-input evidence package.',extractedText:text,createdAt:now});
    }
    const nextInput={...input,documents:[...input.documents,...documents],answers:[...input.answers,...answers],
      answerQuestions:{...input.answerQuestions,...Object.fromEntries(previous.questions.map(q=>[q.id,q.text]))},
      controlledUpdate:{policy:'selected-answers-v1',questionIds:answers.map(a=>a.questionId),reason:release.reason},reviewAfterReading:false};
    const state=await initializeState(nextInput,parent.number+1,previous),snapshot=project(state,nextInput,'queued');
    const runId=crypto.randomUUID(),trigger='Controlled evidence release: four answers + IA-P04 / IA-P05 / IA-P06; scoped partial continuation';
    const inputPointer=await putJSON(db,nextInput),statePointer=await putState(db,state),snapshotPointer=await putJSON(db,snapshot);
    const manifest={parentRunId:parent.id,runId,incidentId:release.incidentId,trackId:release.trackId,createdAt:now,model:input.model,
      engineVersion:ENGINE_VERSION,schedulingPolicy:'selected-answers-v1',parentBoardHash:digest(before.causalBoard),parentStatePointerHash:digest(parent.state_json),
      parentInputPointerHash:digest(parent.input_json),releaseHash:digest(release),inputHash:digest(nextInput),documents:documents.map(d=>({id:d.id,title:d.title,sha256:d.sha256})),
      selectedQuestions:answers.map(a=>({id:a.questionId,text:previous.questions.find(q=>q.id===a.questionId).text})),baseline:{nodes:before.causalBoard.nodes.length,edges:before.causalBoard.edges.length,findings:previous.findings.length,questions:previous.questions.length}};
    exclusive('manifest.json',manifest);exclusive('v2-input.json',nextInput);
    const guard="EXISTS (SELECT 1 FROM engine_runs WHERE id=? AND status='paused' AND generation=?)";
    const statements=[db.prepare(`INSERT INTO versions (id,track_id,number,trigger,analysis_json,created_at) SELECT ?,?,?,?,?,? WHERE ${guard}`)
      .bind(parent.id,parent.track_id,parent.number,'Operator-frozen partial checkpoint; original investigation unfinished',frozenPointer,now,parent.id,parent.generation)];
    for(const d of documents){
      statements.push(db.prepare(`INSERT INTO documents (id,scope,title,plant,incident_id,track_id,question_id,introduced_version,file_key,file_name,content_type,size,sha256,revision,extraction_status,extraction_notes,extracted_text,created_at) SELECT ?,?,?,?,?,?,NULL,?,?,?,?,?,?,?,?,?,?,? WHERE ${guard}`)
        .bind(d.id,d.scope,d.title,d.plant,d.incidentId,d.trackId,d.introducedVersion,d.fileKey,d.fileName,d.contentType,d.size,d.sha256,d.revision,d.extractionStatus,d.extractionNotes,d.extractedText,d.createdAt,parent.id,parent.generation));
      statements.push(db.prepare(`INSERT INTO track_documents (id,track_id,document_id,source_scope,introduced_version,created_at) SELECT ?,?,?,?,?,? WHERE ${guard}`).bind(crypto.randomUUID(),release.trackId,d.id,d.scope,parent.number+1,now,parent.id,parent.generation));
    }
    statements.push(db.prepare(`INSERT INTO engine_runs (id,track_id,number,parent_number,status,trigger,input_json,state_json,snapshot_json,created_at,updated_at) SELECT ?,?,?,?,'queued',?,?,?,?,?,? WHERE ${guard}`)
      .bind(runId,release.trackId,parent.number+1,parent.number,trigger,inputPointer,statePointer,snapshotPointer,now,now,parent.id,parent.generation));
    statements.push(db.prepare("UPDATE engine_runs SET status='partial',snapshot_json=?,pause_reason='Operator-frozen partial V1; unfinished queue preserved, not resumed.',lease=NULL,lease_until=0,generation=generation+1,updated_at=? WHERE id=? AND status='paused' AND generation=?")
      .bind(frozenPointer,now,parent.id,parent.generation));
    const result=await db.batch(statements);
    if(!result.at(-1).meta.changes)throw Error('Parent changed before commit; nothing was committed by the guarded transaction.');
    exclusive('v1-frozen.json',{id:parent.id,number:parent.number,trigger:'Operator-frozen partial checkpoint; original investigation unfinished',createdAt:parent.created_at,executionStatus:'partial',analysis:frozen});
    console.log(JSON.stringify({event:'prepared',...await refresh(manifest)}));
  }else{
    const manifest=JSON.parse(fs.readFileSync(path.join(directory,'manifest.json'),'utf8'));
    if(manifest.releaseHash!==digest(release))throw Error('The prepared release has changed.');
    if(mode==='refresh'){console.log(JSON.stringify(await refresh(manifest)));}
    else if(mode==='watch') {
      // The app's existing worker may claim the queued run before this CLI.
      // In that case observe/publish only; never start a competing worker.
      let lastGeneration;
      while(true) {
        const current=await row(manifest.runId);
        if(current.generation!==lastGeneration) {
          console.log(JSON.stringify(await refresh(manifest)));
          lastGeneration=current.generation;
        }
        if(!['queued','running'].includes(current.status)) break;
        await new Promise(resolve=>setTimeout(resolve,15000));
      }
    }
    else {
      activeRunId=manifest.runId;
      const store=new D1EngineStore(db,activeRunId);
      const stop=async()=>{await store.pause(activeRunId,'Controlled revision runner explicitly interrupted; durable task state retained.');};
      process.once('SIGINT',()=>void stop());process.once('SIGTERM',()=>void stop());
      await modelIdentity(manifest.model);
      console.log(JSON.stringify({event:'started',runId:activeRunId,trackId:manifest.trackId,model:manifest.model.id,policy:manifest.schedulingPolicy}));
      while(true){
        const current=await row(activeRunId);
        if(!['queued','running'].includes(current.status)){console.log(JSON.stringify({event:'stopped',...await refresh(manifest)}));break;}
        const result=await workerStep(store,async()=>modelIdentity(manifest.model));
        console.log(JSON.stringify({at:new Date().toISOString(),...result}));
        if(result.idle){console.log(JSON.stringify({event:'not-claimed',reason:'Another worker owns the lease or a predecessor blocks the run.'}));break;}
        const fresh=await row(activeRunId);
        const summary=await readJSON(db,fresh.snapshot_json);
        write('status.json',{runId:activeRunId,status:fresh.status,updatedAt:fresh.updated_at,nodes:summary.causalBoard.nodes.length,edges:summary.causalBoard.edges.length,
          tasks:summary.engineProgress?.tasks.reduce((out,t)=>(out[t.status]=(out[t.status]||0)+1,out),{}),lastTask:result.taskId});
      }
    }
  }
}catch(error){
  if(activeRunId)await new D1EngineStore(db,activeRunId).pause(activeRunId,`Controlled runner stopped: ${error.message}`);
  throw error;
}finally{await platform.dispose();}

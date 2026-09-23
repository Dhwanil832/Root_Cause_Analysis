'use client';
import {useCallback,useEffect,useState} from 'react';
import Link from 'next/link';
import type {StoryScenario,StoryOutput} from '@/src/story-agent/contracts';
import './story.css';

interface Workspace {
  track:{incident_id:string;model_id:string;model_name:string};version:number;questions:{id:string;text:string}[];
  scenario:null|{title:string;definition:StoryScenario};
  rounds:{id:string;base_version:number;status:string;result_version:number|null;error:string;questions:{id:string;text:string}[];output:{output?:StoryOutput}}[];
}
export function StoryWorkspace({trackId}:{trackId:string}) {
  const [data,setData]=useState<Workspace|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState('');
  const [title,setTitle]=useState(''),[truth,setTruth]=useState(''),[sources,setSources]=useState('[]');
  const endpoint=`/api/tracks/${trackId}/story`;
  const refresh=useCallback(async()=>{const r=await fetch(endpoint);const body=await r.json() as Workspace & {error?:string};if(!r.ok)throw Error(body.error);setData(body);},[endpoint]);
  useEffect(()=>{void refresh().catch(e=>setError(String(e)));},[refresh]);
  const active=!!busy||!!data?.rounds.some(r=>['generating','applying'].includes(r.status));
  useEffect(()=>{if(!active)return;const timer=setInterval(()=>void refresh().catch(()=>{}),5000);return()=>clearInterval(timer);},[active,refresh]);
  async function action(name:string,extra:Record<string,unknown>={}) {
    setBusy(name);setError('');
    try{const r=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:name,...extra})});const body=await r.json() as {error?:string};if(!r.ok)throw Error(body.error);await refresh();}
    catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy('');}
  }
  function loadScenario(s:StoryScenario){setTitle(s.title);setTruth(s.hiddenTruth);setSources(JSON.stringify(s.sources,null,2));}
  const current=data?.rounds.find(r=>r.base_version===data.version);
  return <main className="story-workspace">
    <header><p className="story-eyebrow">TRY 4 · EXTERNAL BENCHMARK SIMULATOR</p><h1>One model. Two separate roles.</h1><p>The story role holds a fixed scenario. The RCA role receives only the answers you release—not the hidden scenario or its private memory.</p>
      {data&&<Link href={`/incident/${data.track.incident_id}`}>← Return to RCA board · V{data.version}</Link>}</header>
    {error&&<p role="alert" className="story-error">{error}</p>}
    {!data?<p>Loading simulator…</p>:<>
      <div className="story-stats"><span>Model <strong>{data.track.model_name||data.track.model_id}</strong></span><span>RCA version <strong>V{data.version}</strong></span><span>Unanswered questions <strong>{data.questions.length}</strong></span></div>
      <p className="story-notice">Synthetic benchmark only. Separate requests and memory use the same Ollama model; they are not independent-model validation. This local evaluator page reveals private scenario data to you, not to the RCA model.</p>
      {!data.scenario?<section><h2>1. Define and lock the world</h2><p>Define facts before the model answers. Sources may include conflicting reports, but their reliability must be labeled. Once locked, this track’s scenario cannot be edited.</p>
        <div className="story-actions"><button onClick={async()=>{try{const r=await fetch('/api/story-template');if(!r.ok)throw Error('Unable to load template');loadScenario(await r.json());}catch(e){setError(String(e));}}}>Load R3 benchmark starter</button>
          <label>Import scenario JSON <input type="file" accept=".json,application/json" onChange={async e=>{try{const f=e.target.files?.[0];if(f)loadScenario(JSON.parse(await f.text()));}catch{setError('Invalid scenario JSON.');}}}/></label></div>
        <label>Scenario title<input value={title} onChange={e=>setTitle(e.target.value)}/></label>
        <label>Private scenario facts<textarea rows={6} value={truth} onChange={e=>setTruth(e.target.value)}/></label>
        <label>Available evidence sources (JSON)<textarea rows={12} value={sources} onChange={e=>setSources(e.target.value)} spellCheck={false}/></label>
        <p>Each source requires id, title, sourceClass, text, and available (true or false). Use document excerpts; original file ingestion is not part of this simulator yet.</p>
        <button disabled={active} onClick={()=>{try{void action('create',{scenario:{title,hiddenTruth:truth,sources:JSON.parse(sources)}});}catch{setError('Sources must be valid JSON.');}}}>Lock scenario</button>
      </section>:<section><h2>1. Locked scenario: {data.scenario.title}</h2><details><summary>Evaluator-only scenario and evidence</summary><p>{data.scenario.definition.hiddenTruth}</p>{data.scenario.definition.sources.map(s=><article key={s.id}><h3>{s.id} · {s.title}</h3><p>{s.sourceClass} · {s.available?'Available':'Unavailable'}</p><pre>{s.text}</pre></article>)}</details></section>}
      <section><h2>2. Generate answers</h2><p>All pending questions go to a separate story request with its own scenario and previously released answers. No RCA causal board is sent.</p>
        <details><summary>View {data.questions.length} pending questions</summary><ol>{data.questions.map(q=><li key={q.id}>{q.text}</li>)}</ol></details>
        <button disabled={!data.scenario||active||!data.questions.length||!!current&&current.status!=='failed'} onClick={()=>void action('generate')}>{busy==='generate'?'Story model is answering…':'Generate answer batch'}</button>
        {active&&<p role="status">Working locally. This can take several minutes; completed rounds are preserved here.</p>}
      </section>
      <section><h2>3. Review and release</h2><p>Review source support before release. Applying a batch runs one RCA cycle and saves one new version. Unknown and partial responses are not automatically marked resolved.</p>
        {!data.rounds.length&&<p>No answer batches yet.</p>}
        {[...data.rounds].reverse().map(round=><article key={round.id} className="story-round"><h3>From V{round.base_version} · {round.status}{round.result_version?` → V${round.result_version}`:''}</h3>
          {round.error&&<p className="story-error">{round.error}</p>}
          {round.output.output?.answers.map(a=><details key={a.questionId}><summary>{round.questions.find(q=>q.id===a.questionId)?.text||a.questionId} <small>— {a.status}</small></summary><p>{a.answer}</p>{a.citations.map((c,i)=><blockquote key={i}>{c.quote}<footer>Source: {c.sourceId}</footer></blockquote>)}<p>Limit: {a.limitation||'Synthetic benchmark evidence.'}</p></details>)}
          {round.status==='ready'&&<button disabled={active||round.base_version!==data.version} onClick={()=>{if(window.confirm('Release this entire synthetic answer batch and create the next RCA version?'))void action('apply',{roundId:round.id});}}>Release batch → create V{round.base_version+1}</button>}
        </article>)}
      </section>
    </>}
  </main>;
}

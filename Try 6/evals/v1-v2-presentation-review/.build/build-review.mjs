import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {Presentation,PresentationFile,FileBlob} from '@oai/artifact-tool';
process.on('uncaughtException',e=>{console.error('BUILD ERROR:',e.message);console.error(String(e.stack).split('\n').slice(-8).join('\n'));process.exit(1);});

const ROOT='/Users/dhwanilchauhan/Desktop/RCA Try 1';
const WORK=path.join(ROOT,'Try 6/evals/v1-v2-presentation-review');
const SKILL='/Users/dhwanilchauhan/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations';
const REF='/Users/dhwanilchauhan/.codex/plugins/cache/openai-curated-remote/openai-templates/0.1.1/skills/artifact-template-simple-light-mode/assets/reference.pptx';
const PY='/Users/dhwanilchauhan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
process.env.RUNTIME_NODE_MODULES='/Users/dhwanilchauhan/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const evidencePath=path.join(ROOT,'Try 6/evals/ia16036-v2-controlled/failure-report-evidence.json');
const evidence=JSON.parse(await fs.readFile(evidencePath,'utf8'));
const template=JSON.parse(await fs.readFile(path.join(WORK,'.build/template-model.json'),'utf8'));
// Imported reference slide 1 (cover) and slide 5 (plain two-column body).
// Retain the imported theme, layouts, white background, typography and header/footer rhythm.
template.slides=[template.slides[0],template.slides[4]];
// The JSON inspection snapshot cannot carry embedded-font bytes. The imported
// template's text uses Helvetica Neue; its unused OpenAI Sans embed is omitted.
template.fonts=[];
let p=Presentation.load(template);
const coverTemplate=p.slides.items[0], bodyTemplate=p.slides.items[1];
const selected=[], nativeTables=[], nativeCharts=[];
const FONT='Helvetica Neue';
const E='Local evidence: '+evidencePath;
const SRC=path.join(ROOT,'IA-16036 Controlled Evidence Package/07_case_content_inputs/02_model_visible');
const CODE=path.join(ROOT,'Try 6/src');
const research={
 sufficient:'https://research.google/pubs/sufficient-context-a-new-lens-on-retrieval-augmented-generation-systems-2/',
 chain:'https://aclanthology.org/2025.acl-long.1089/',
 graph:'https://proceedings.mlr.press/v267/luo25t.html',
 prog:'https://aclanthology.org/2025.acl-short.73/',
 trace:'https://aclanthology.org/2026.acl-long.912/',
 delta:'https://arxiv.org/abs/2604.02733'
};
function style(shape,size=26,bold=false,color='#141414'){
 shape.text.style={typeface:FONT,fontSize:size,bold,color,autoFit:'none',verticalAlignment:'top'};
}
function box(s,text,x,y,w,h,size=26,bold=false,color='#141414'){
 const a=s.shapes.add({name:'Review text',geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 a.text=text;style(a,size,bold,color);return a;
}
function base(title,sub='',notes=''){
 const s=bodyTemplate.duplicate();selected.push(s.id);
 const shapes=[...s.shapes.items];
 for(const sh of shapes){
   if(sh.position.top>170 && sh.position.top<650) sh.delete();
   else if(sh.position.top<150){sh.text=title;sh.position={left:42,top:35,width:1196,height:100};style(sh,40);}
   else if(sh.position.left>1000){sh.text=String(selected.length);sh.position={left:1184,top:676,width:54,height:22};style(sh,14,false,'#666666');}
   else {sh.text='TRY 6 / EVIDENCE REVIEW / 20 SEPTEMBER 2026';sh.position={left:42,top:676,width:950,height:22};style(sh,13,false,'#777777');}
 }
 if(sub)box(s,sub,42,137,1196,70,24,false,'#555555');
 s.speakerNotes.textFrame.setText(notes+'\n\n'+E+'\nReport: '+path.join(WORK,'output/Try6_V1_V2_Evidence_Review.md'));
 return s;
}
function cols(title,sub,columns,notes=''){
 const s=base(title,sub,notes);const gap=48,n=columns.length,w=(1196-gap*(n-1))/n;
 columns.forEach((c,i)=>{const x=42+i*(w+gap);box(s,c[0],x,230,w,70,30,true);box(s,c[1],x,310,w,315,27);});return s;
}
function tableSlide(title,sub,headers,rows,widths,notes='',size=23){
 const s=base(title,sub,notes);const vals=[headers,...rows];
 const t=s.tables.add({rows:vals.length,columns:headers.length,left:42,top:205,width:1196,height:440,columnWidths:widths,values:vals});
 t.styleOptions={headerRow:true,bandedRows:false};
 t.borders.assign({fill:'#D3D3D3',width:0.6,style:'solid'});
 t.cells.block({row:0,column:0,rowCount:vals.length,columnCount:headers.length}).assign({
   fill:'#FFFFFF',textStyle:{typeface:FONT,fontSize:size,color:'#171717',autoFit:'none'},
   margins:{left:10,right:12,top:5,bottom:5},anchor:'top'
 });
 t.cells.block({row:0,column:0,rowCount:1,columnCount:headers.length}).assign({fill:'#F1F1F1',textStyle:{typeface:FONT,fontSize:size,bold:true,color:'#111111'}});
 t.rows[0].height=44;
 for(let i=1;i<vals.length;i++)t.rows[i].height=396/rows.length;
 nativeTables.push(selected.length);return s;
}

// 01: reference cover, minimal and evidence-led.
{
 const s=coverTemplate.duplicate();selected.push(s.id);
 const sh=[...s.shapes.items].sort((a,b)=>a.position.top-b.position.top);
 sh[0].text='TRY 6  /  IA-16036  /  20 SEPTEMBER 2026';style(sh[0],22);
 sh[1].text='RCA evidence review\nV1 → V2';sh[1].position={left:42,top:184,width:1180,height:285};style(sh[1],82);
 sh[2].text='What we expected. What happened.\nWhat is proven—and what must change.';sh[2].position={left:42,top:516,width:1110,height:120};style(sh[2],29);
 s.speakerNotes.textFrame.setText('One incident and one Qwen configuration. This is a review of saved runs, not a new run or a production change. V1 evaluated without V2-only evidence. V2 evaluated against prewritten controlled expectations. Research checked online 20 September 2026.\n'+E);
}
cols('Two versions finished; causal progress remains insufficient',
 'Completion, statement support and causal validity are different outcomes.',[
 ['What worked','Both snapshots preserved.\n\nNew records read; relevant facts extracted.\n\nMore individual statements supported in V2.'],
 ['What did not','The expected route-and-valve mechanism was not assembled.\n\nOld errors and evidence gaps survived.\n\nNo connection became verified.'],
 ['What we can prove','Specific contract, review and handoff defects.\n\nSource/output mismatches.\n\nNot the model’s internal reason for every mistake.']
 ],'Source: runs[0/1].counts, board, position and findings. Do not infer that zero verified edges alone proves a failure or that V1 had to solve the incident.');

tableSlide('What was actually tested','Same model digest; V2 adds two records and one reviewed answer. V1 required mid-run engineering recovery.',
 ['Measure','V1','V2'],[
 ['Uploaded documents / storyteller answers','10 / 0','12 / 1'],
 ['Notebook findings','100','154'],
 ['Board nodes / active connections','5 / 4','9 / 6'],
 ['Supported non-focal nodes','1','5'],
 ['Verified connections','0','0'],
 ['Published questions, including baseline','9','11']
 ],[650,273,273],'Sources: saved counts. V1 partial/finished and V2 partial/finished. One model: ollama:qwen3.5:latest. V1 elapsed includes pauses and sampling-profile change; do not present a causal runtime improvement. Documents exclude the incident description; questions include baseline.');

cols('V1 was expected to be provisional—not complete','V1 assessment uses only the documents available to V1.',[
 ['What it should establish','Accurate pressure/alarm chronology.\n\nRUN indication ≠ measured flow.\n\nAL-44 is a P-R low-pressure signal, despite its legacy label.\n\nAn internally consistent preliminary board.'],
 ['What should remain open','Actual piping connectivity.\n\nIncident-time valve actions.\n\nActual briefing content.\n\nPhysical and organizational causes not yet established.']
 ],'V1 source inventory: incident, D01–D03, S01–S03, P01–P03 and C01. P04/P05 withheld until V2. Detailed V1 rubric is retrospective; V2 expectations were prewritten. P02 mapping distinguishes legacy COMP FAULT label from the actual input.\n'+SRC);

tableSlide('V1: all five nodes reviewed','A supported observation does not automatically have a valid causal role.',
 ['Node','V1 status / role','Assessment'],[
 ['Pressure-loss focal event','Proposed / focal','Useful incident anchor; not a root cause.'],
 ['Reported event around 10:00','Partial / event','Directly reported; extra Turn-2 corroboration is a different question.'],
 ['AL-44 timestamps','Proposed / event','Present in P01; reviewer output was internally inconsistent.'],
 ['Return to normal band','Supported / condition','Grounded; numerical recovery is also in P01.'],
 ['C-11 RUN = 1 at samples','Proposed / barrier','Sampled fact is grounded; protective function is not established.']
 ],[370,265,561],'Sources: V1 board.nodes. Invalid alarm review f7db8787-5ba9-431d-9129-1f83bed4d96f; invalid RUN review cc9428a7-f9e7-41b4-bb8f-b4c7eefdb736. Both combined entailment with necessary missing premises. The guard correctly rejected the contradictory output.',22);

tableSlide('V1: all four connections reviewed','Unknown status is permissible. Wrong direction and unsupported roles are not useful uncertainty.',
 ['Connection','Assessment','Why'],[
 ['Loss → alarm: caused','Plausible; not verified','Mapping exists in P02, but the saved gap says it is missing.'],
 ['Recovery → loss: preceded','Wrong direction','Its own explanation says recovery happened after the interruption.'],
 ['Loss → recovery: preceded','Reasonable ordering','Not proof of a cause; coexists with the opposite arrow.'],
 ['Loss → RUN: failed-to-prevent','Unsupported relation','Neither the pressure-loss event nor the RUN indication is an established barrier.']
 ],[405,265,526],'All V1 edges shown in saved board. No verification calls completed in V1. Review gates unresolved premises. The loss-to-recovery direction is a reasonable temporal statement, not evidence of the recovery mechanism.',23);

tableSlide('V1 already contained factual and evidence-use errors','These failures predate V2; they are not regressions caused by adding P04/P05.',
 ['Saved output','Source evidence','Consequence'],[
 ['P-R reaches 2.1 bar by 10:03','P01: 2.6 at 10:03:10; 2.1 at 10:05:50','Wrong timeline enters the notebook and summary.'],
 ['Numerical recovery confirmation missing','P01: 6.0 at 10:06:20; 6.8 at 10:06:50','An already-answerable gap remains open.'],
 ['Alarm input mapping unavailable','P02: AL-44 input is P-R; legacy display wording','Unverified compressor speculation receives too much framing weight.']
 ],[390,410,396],'Finding 22dc870b-4cb9-4384-8d38-f5b2e59bffa5 and V1 summary contain timing error. See P01/P02. The compressor branch remained a hypothesis, not a supported trip conclusion. A rejected V1 review also misread 10:00:11 as a below-threshold time: recorded P-R was 5.8, while low threshold was <4.5.',25);

cols('V1 questions: useful directions mixed with redundant parts','A missing source format is not the same as missing information.',[
 ['Legitimate next requests','Physical routes between headers.\n\nValve-by-valve field actions.\n\nWhat the briefing actually covered.\n\nA genuine compressor-trip log, if available.'],
 ['Already supplied or over-scoped','AL-44 input identity: P02.\n\nMeasurement-point mapping: P02.\n\nNumerical recovery samples: P01.\n\nSeparate corroboration from the literal claim “the report says Turn 2.”']
 ],'V1 position.directions and resolver outputs. Keep genuine gaps; narrow compound requests into known and unknown parts. Do not grade V1 down for not having P04/P05.');

tableSlide('V2 evidence should narrow the physical mechanism','P04: normal route through M-101/D-101/M-102; auxiliary route through V-201/B-17/V-202.',
 ['Record / time','Observation','What it contributes'],[
 ['P04: connection schedule','V-201 and V-202 are in series','Physical meaning of both valve positions.'],
 ['P05: 10:00:03 ±5 s','M-101 closes','An action near the start of the pressure fall.'],
 ['P05: 10:05:40 ±5 s','V-202 observed closed','Auxiliary-path state late in the event.'],
 ['P05: 10:06:18 ±5 s','V-202 opens; M-101 stays closed','Action associated with recovery.'],
 ['P01: 10:06:20 / 10:06:50','P-R rises to 6.0 / 6.8 bar','Measured recovery sequence.']
 ],[320,430,446],'Expected inference: distribution-path interruption becomes a stronger physical hypothesis. Not final proof: a late observation does not establish continuous prior closure; handle position does not establish internal condition; timing uncertain. P05 also records V-201 open about 09:56. Prewritten expectations: '+path.join(ROOT,'Try 6/evals/ia16036-v2-expectations.md'),22);

tableSlide('V1 → V2: more support, little mechanism revision','The three branch titles, mechanisms and gap texts are unchanged; only version markers advance.',
 ['Dimension','V1 → V2','Finding'],[
 ['Statement support','1 → 5 supported non-focal nodes','Real improvement'],
 ['C-11 prevention edge','Present → withdrawn','Real correction'],
 ['C-11 barrier role','Barrier → still barrier','Persistent role error'],
 ['Recovery direction','Opposite arrows → both retained','Persistent graph error'],
 ['Wrong 2.1-bar timing','Notebook/summary → also on board','Error propagated'],
 ['Piping and valve gaps','Missing → supplied but still requested','Missed evidence integration']
 ],[345,510,341],'V2 adds four nodes, retains all five V1 node identities, withdraws one edge and adds three. No verified edges in either version. Compare board/position rather than mere node counts.',22);

cols('The useful facts were extracted—but not assembled','Confirmed location of failure: selection and synthesis after successful ingestion.',[
 ['Available in the notebook','Four connection segments.\n\nInline V-201 / V-202 relationship.\n\nM-101 closure.\n\nV-202 closed observation and later opening.'],
 ['Missing from the selected mechanism','Topology segments and V-202 observations were not selected as premises.\n\nOld field-operation and routing gaps survived.\n\nWhy the model overlooked these facts is not isolated.']
 ],'V2 runs[1].findings vs position.selectedFindingIds. Frame trace b0053b1c-3674-425f-86a7-5df44258e742 saw all 154 notebook findings but not original P04. Refine 7f1777d6-e056-4bae-9da9-792e08aadbe9 saw notebook but neither original P04/P05. Resolvers and connection calls did have the originals. Do not say upload failed or context capacity caused the omission.');

tableSlide('Review itself introduced errors and misleading statuses','Review is another fallible model output, not an independent source of truth.',
 ['Observed review behavior','What the evidence/code establishes','Published effect'],[
 ['“Not a contradiction” + claim-truth conflict flag','Approximate and precise times not shown incompatible; flag forces unknown','AL-44 claim unknown; 3 dependent edges gated.'],
 ['V-201 “opened and later closed”','P05 says V-201 opened and M-101 closed','Wrong entity/action pairing in verifier output.'],
 ['Partial verdict → conflicting → unknown','Status application uses both reference lists; UI flattens conflict','Distinct reasons for uncertainty become indistinguishable.']
 ],[390,460,346],'AL-44 review 60b7aea1-8d44-45bd-8700-68055befdfdb. Entity error da20381b-14ca-490d-80a1-0207ca1dfe94. Both verifiers partial; neither supported. Code: literal-decision.ts, board/changes.ts, board/projection.ts.',23);

tableSlide('The feedback loop does not reliably reach the next round','A saved review finding is not enough: it must change the board or receive an explicit disposition.',
 ['Expected','Observed','Confirmed mechanism'],[
 ['Correct an identified factual error','2.1-bar timing remains after review flags it','Final refinement precedes review; no post-review claim/map reconciliation.'],
 ['Route new causal questions','All 4 verifier questions saved; none published','They lack links required by the projection filter.'],
 ['Retire or narrow obsolete questions','Turn-2 and RUN questions remain after parent support','Question state not fully reconciled with revised findings.']
 ],[315,460,421],'Question flags in diagnostic export. Projection requires direction or selected reviewTargets. Story selector consumes published analysis questions. Some verifier questions are themselves wrong, so routing must allow correction/rejection, not automatically publish every question. Code: investigation/planner.ts, apply.ts, board/projection.ts, records.ts, story-agent/contracts.ts.',23);

tableSlide('Software causes we can identify without speculation','These explain specific failures—not every model reasoning error.',
 ['Boundary','Confirmed mismatch','Required change'],[
 ['Resolver assignment','Schema allows all visible IDs; runtime accepts assigned IDs only','One assignment object drives both.'],
 ['Graph acceptance','Valid references do not check temporal direction or barrier role','Separate semantic relation/role checks.'],
 ['Review interpretation','Flags and reference-list presence override distinct meanings','Consistent partial/conflict/unknown states.'],
 ['Publication','Statuses update after last map refinement','Explicit claim amendment and reconciliation.'],
 ['Question handoff','Saved questions can fail visibility predicate silently','Canonical registry; every item has a disposition.']
 ],[280,520,396],'Code anchors: tasks/executor.ts, investigation/contracts.ts, investigation/apply.ts, review/literal-contract.ts, review/literal-decision.ts, board/changes.ts, board/projection.ts, investigation/planner.ts. Each confirmed against raw outputs and applied state. Proposed changes are not yet implemented.',22);

tableSlide('Storyteller: operational, but not yet unattended','Two jobs completed once. Human review released one and withheld one.',
 ['Question','Candidate behavior','Outcome / boundary'],[
 ['Actual briefing content','Grounded excerpts, but missing actual checklist; marked “answered”','Released unchanged. Should be partial; repeats existing sources.'],
 ['Physical connectivity','P04 was in input, but answer treated routing as unavailable','Withheld by human reviewer. Never fed into V2.']
 ],[300,440,456],'Both P04/P05 included in actual story input catalogs. Story round c5bdbc70-37bd-42f3-9acc-00912637f096. Job times approx 24.895s and 22.986s, no retries. P04/P05 were preselected by operator. This tests transport and reviewed partial release, not autonomous discovery or multi-round memory consistency. story-candidate.json and story-review.json.',27);

{
 const s=base('Most V2 time was spent reviewing premises','78 min 39 s elapsed; 60.25 min in premise review. No infinite specialist queue in this run.',
 'Recorded stage durations from runs[1].stageTiming. Premise review 3,614,997 ms / elapsed 4,719,243 ms = 76.6%. Sum task durations approx 78m31s. Global changed-source invalidation is in planner.ts; dependency-sensitive savings have not been measured. Native context 262144, generation -1. 154 findings are not 154 agents. V1 elapsed is not a fair speed baseline.');
 const r=evidence.runs[1].stageTiming;
 const values=[r.read.durationMs,r.frame.durationMs+r.refine.durationMs,r.connect.durationMs,r.resolve.durationMs,r.review.durationMs,r.verify.durationMs].map(x=>Number((x/60000).toFixed(2)));
 const chart=s.charts.add('bar',{position:{left:42,top:218,width:770,height:420},title:'Recorded V2 task time (minutes)',titleTextStyle:{typeface:FONT,fontSize:23},categories:['Read','Frame + refine','Connect','Resolve','Review premises','Verify links'],series:[{name:'Minutes',values,valuesFormatCode:'0.00',fill:'#222222'}],barOptions:{direction:'bar',grouping:'clustered'},hasLegend:false,dataLabels:{showValue:true,position:'outEnd',numberFormatCode:'0.00'},xAxis:{numberFormatCode:'0'},yAxis:{numberFormatCode:'0'},chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF'});
 applyPresentationChartFont(chart,{fontFamily:FONT});nativeCharts.push(selected.length);
 chart.dataLabels={showValue:true,position:'outEnd',textStyle:{typeface:FONT,fontSize:19,fill:'#222222'}};
 chart.xAxis={numberFormatCode:'0',textStyle:{typeface:FONT,fontSize:18},majorGridlines:null};
 chart.yAxis={numberFormatCode:'0',textStyle:{typeface:FONT,fontSize:18},majorGridlines:null};
 values.forEach((value,i)=>{const label=chart.series.getItemAt(0).dataLabelOverrides.add(i);label.text=value.toFixed(2);label.showValue=false;label.position='outEnd';label.textStyle.fontSize=19;label.textStyle.typeface=FONT;});
 box(s,'76.6%',860,258,340,105,76);box(s,'of elapsed time\nspent reviewing premises',860,370,340,110,28);
 box(s,'Optimize affected dependencies;\ndo not remove factual checks.',860,530,340,110,25);
}

cols('Proposed repair: make evidence revision a complete loop','Architectural correction—not a prompt that hard-codes this incident’s answer.',[
 ['Before proposing a mechanism','Source-linked observations:\nentity, state/action, time, value, uncertainty.\n\nJoint evidence bundles preserve identities across documents.\n\nEvery affected branch gets an explicit delta decision.'],
 ['Before publishing a version','Review can create a corrected claim—not merely a lower status.\n\nRecheck affected links and reconcile summary, gaps and questions.\n\nReuse reviews only with a visible dependency rationale.']
 ],'Recommendations based on local F01–F10. Not implemented or demonstrated by this report. No fine-tuning or multi-model fallback is needed for the first implementation. Preserve superseded claims historically; do not silently rewrite V1. Related research on the following two slides.');

tableSlide('Research supports targeted evidence and constraint checks','Primary research, 2025. Transfer to this RCA system remains to be tested.',
 ['Research','Relevant principle','Local adaptation / limitation'],[
 ['Sufficient Context\nICLR 2025','Separate context sufficiency from successful use','Audit packet coverage; adequate context can still be misused. QA ≠ industrial RCA.'],
 ['ChainRAG\nACL 2025','Preserve entities across multi-hop retrieval','Bundle topology + state + time. Reported tests are multi-hop QA.'],
 ['Graph-constrained Reasoning\nICML 2025','Constrain reasoning paths to a graph','Validate typed relationships. Graph faithfulness alone is not causal truth.']
 ],[340,390,466],'Sources: '+research.sufficient+'\n'+research.chain+'\n'+research.graph+'\nThese are adaptations, not measured fixes. GCR full approach uses a KG-specialized model; we borrow the constraint principle without proposing its full training architecture.',24);

tableSlide('Research also supports correction and controlled revision tests','2025–2026 evidence; preprint status is explicitly distinguished.',
 ['Research','Relevant principle','Local adaptation / limitation'],[
 ['ProgCo\nACL 2025','Program-driven verification and refinement','Executable ID/time/value checks plus claim repair; not universal proof of self-correction.'],
 ['TraceElephant\nACL 2026','Full execution inputs and outputs for attribution','Replay packet → output → applied state → view; not output-only diagnosis.'],
 ['DeltaLogic\nApril 2026 preprint','Controlled premise edits test revision behavior','Support / defeat / remove / irrelevant deltas. Small logic study, not an RCA solution.']
 ],[340,390,466],'Sources: '+research.prog+'\n'+research.trace+'\n'+research.delta+'\nResearch checked 20 September 2026. No published effect size is claimed as a local gain. DeltaLogic does not establish that anchoring caused this Qwen run. ProgCo evaluated instruction following and math.',24);

tableSlide('Acceptance must measure correction—not board size','Use these frozen failures as regression cases; then test unseen incidents and evidence changes.',
 ['Area','Observable pass condition'],[
 ['Source fidelity','Correct time/value pairs and valve identities; observations distinct from inference.'],
 ['Graph meaning','Correct event ordering; a protective function is required for a barrier role.'],
 ['Evidence revision','New routes and valve states narrow the mechanism; uncertainty remains explicit.'],
 ['Feedback','Corrected claims reach publication; every question has an explicit disposition.'],
 ['Storyteller','Relevant records used; partial answers labelled; source ancestry retained.'],
 ['Generality','Fixed-config latency and accuracy comparisons, followed by unseen-case tests.']
 ],[290,906],'These are proposed acceptance tests, not a report that they already pass. V2 target follows prewritten expectations. Do not force a supported edge; permit a justified qualified hypothesis or evidence-based explanation of why it remains unsupported.',22);

cols('The defensible conclusion','We have an inspectable two-version investigation—not yet reliable evidence-driven causal revision.',[
 ['Established by this review','V1 had source and graph errors before V2.\n\nV2 improved extraction and statement support.\n\nSpecific software paths explain propagation and handoff failures.'],
 ['Not established','A universal Qwen limitation.\n\nContext overload or anchoring as the internal cause.\n\nA guaranteed fix from more agents, larger context or fine-tuning.\n\nA final organizational root cause.']
 ],'One case/model configuration. V1 recovered under changed execution behavior. Suggestions not implemented. All app data and prior versions remain unchanged. Detailed trace index and source links in accompanying report.');

cols('Evidence and reproducibility','The full report contains the failure register, exact trace IDs, source links and acceptance tests.',[
 ['Local audit material','Frozen V1/V2 export.\n\nEvery node and edge reviewed.\n\nReleased documents, raw public outputs, task metrics and projection flags.\n\nCode paths linked for each confirmed harness defect.'],
 ['How to present this fairly','Separate “observed” from “cause proven.”\n\nKeep a blank where the internal cause is unknown.\n\nLabel research-inspired repairs as proposals.\n\nDo not equate a finished run with a validated RCA.']
 ],'Incident 9660f4f2-5fc0-4d0a-917e-8e48641956e3; V1 a20904da-8710-40df-8d58-fec78f451f2a; V2 3d44374c-888e-465a-8870-99d11eaa8c12. Digest 6488c96fa5faab64bb65cbd30d4289e20e6130ef535a93ef9a49f42eda893ea7. Live dashboard if app running: http://127.0.0.1:3016/incident/9660f4f2-5fc0-4d0a-917e-8e48641956e3. No model run or application mutation during this review.');

// Keep only authored duplicates, in intended order; imported theme/layouts remain intact.
const proto=p.toProto();const byId=new Map(proto.slides.map(s=>[s.id,s]));
proto.slides=selected.map((id,i)=>({...byId.get(id),index:i}));p=Presentation.load(proto);
await fs.mkdir(path.join(WORK,'.build/rendered'),{recursive:true});
const candidate=path.join(WORK,'.build/candidate.pptx');
await (await PresentationFile.exportPptx(p)).save(candidate);
const finalPath=path.join(WORK,'output/Try6_V1_V2_Review.pptx');
const result=await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath,pythonExecutable:PY,
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...nativeTables.flatMap(n=>['--require-native-table-slide',String(n)])],
 requiredNativeTableOwnerSlides:nativeTables,requiredNativeChartOwnerSlides:nativeCharts,
 materializeLiteralChartWorkbooks:true,
 fontPolicy:{basis:'reference',families:[FONT],referencePath:REF,referenceSha256:crypto.createHash('sha256').update(await fs.readFile(REF)).digest('hex')},
 verifyArtifactToolImport:true,receiptPath:path.join(WORK,'.build/validation-r4.json')});
console.log('FINALIZED',JSON.stringify({path:result.finalPath,layout:result.presentationLayout,chart:result.nativeChartValidation}));
await fs.writeFile(path.join(WORK,'.build/authored-model.json'),JSON.stringify(p.toProto(),null,2));
p=await PresentationFile.importPptx(await FileBlob.load(finalPath));
for(let i=0;i<p.slides.items.length;i++){
 const b=await p.slides.items[i].export({format:'png',scale:1});
 await fs.writeFile(path.join(WORK,'.build/rendered',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await b.arrayBuffer()));
}
console.log('SLIDES',p.slides.items.length,'TABLES',nativeTables,'CHARTS',nativeCharts);

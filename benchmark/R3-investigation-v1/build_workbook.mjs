import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=import.meta.dirname, out=`${root}/outputs/01a0cef3-83d5-7bc1-a0a5-45c70c3255a3`;
await fs.mkdir(out,{recursive:true});await fs.mkdir(`${root}/verification/previews`,{recursive:true});
const criteria=JSON.parse(await fs.readFile(`${root}/private/evaluator/criteria.json`,'utf8'));
const stages=JSON.parse(await fs.readFile(`${root}/private/evaluator/stages.json`,'utf8'));
const records=JSON.parse(await fs.readFile(`${root}/public/inventory.json`,'utf8'));
const arms=['gpt_clean','gpt_connected','qwen_clean','qwen_connected'];
const wb=Workbook.create();
const sheets=Object.fromEntries(['Comparison','Stage scores','Criteria','Grades','Records'].map(n=>[n,wb.worksheets.add(n)]));
function base(s,last,col){s.showGridLines=false;s.getRange(`A1:${col}${last}`).format.font={name:'Arial',size:11,color:'#233247'};s.getRange(`A1:${col}${last}`).format.rowHeight=24;s.getRange(`A1:${col}${last}`).format.verticalAlignment='center';}
function header(s,row,labels){const range=s.getRangeByIndexes(row-1,0,1,labels.length);range.values=[labels];range.format={fill:'#243A55',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,verticalAlignment:'center',horizontalAlignment:'center',rowHeight:36};}
function title(s,t,lastcol){s.getRange('A2').values=[[t]];s.getRange(`A2:${lastcol}2`).format.rowHeight=30;s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:'#243A55'};}
function widths(s,values){for(const [i,w] of values.entries())s.getRangeByIndexes(0,i,1,1).format.columnWidth=w;}
const gr=sheets.Grades,N=criteria.length*arms.length*3,end=N+5;
base(gr,end,'M');title(gr,'R3 scoring entries','M');gr.getRange('A3').values=[['Enter outcome, exposure, reference, rationale, contradiction and failure origin. Blank means unscored.']];
header(gr,5,['Criterion','Stage','Arm','Run','Outcome','Exposure','Output reference','Excerpt or absence reason','Contradiction','Failure origin','Presence point','Consistent point','Reviewed flag']);
const rows=[];for(const arm of arms)for(let rep=1;rep<=3;rep++)for(const c of criteria)rows.push([c.id,c.stage,arm,rep,null,null,null,null,null,null,null,null]);
gr.getRange(`A6:L${end}`).values=rows;
widths(gr,[14,10,22,8,22,20,34,65,17,19,16,18,17]);gr.getRange(`E6:J${end}`).format.fill='#FFF7DF';gr.getRange(`G6:H${end}`).format.wrapText=true;
gr.getRange(`E6:E${end}`).dataValidation={rule:{type:'list',values:['Present','Missing','Not reached','Harness blocked']}};
gr.getRange(`F6:F${end}`).dataValidation={rule:{type:'list',values:['Supplied','Not obtained','Harness blocked']}};
gr.getRange(`I6:I${end}`).dataValidation={rule:{type:'list',values:['No','Yes']}};
gr.getRange(`J6:J${end}`).dataValidation={rule:{type:'list',values:['None','Interpretation','Acquisition','Composition','Retention','Routing','Harness','Transport','Resource','Unknown']}};
const k=[],l=[];
for(let r=6;r<=end;r++){
 k.push([`=IF(OR(E${r}="",F${r}="",G${r}="",H${r}="",I${r}="",J${r}=""),"",IF(E${r}="Harness blocked","BLOCKED",IF(AND(E${r}="Present",F${r}="Supplied"),1,IF(OR(E${r}="Missing",E${r}="Not reached"),0,"CHECK"))))`]);
 l.push([`=IF(ISNUMBER(K${r}),IF(AND(K${r}=1,I${r}="No"),1,0),K${r})`]);
}
gr.getRange(`K6:K${end}`).formulas=k;gr.getRange(`L6:L${end}`).formulas=l;gr.freezePanes.freezeRows(5);gr.freezePanes.freezeColumns(2);
gr.getRange(`M6:M${end}`).formulas=rows.map((_,i)=>[`=IF(ISNUMBER(K${i+6}),1,0)`]);
gr.getRange(`K6:L${end}`).conditionalFormats.add('containsText',{text:'BLOCKED',format:{fill:'#FBE5E5',font:{color:'#9C2020'}}});
gr.tables.add(`A5:M${end}`,true,'ScoringEntries');
const cr=sheets.Criteria;base(cr,101,'G');title(cr,'Frozen expected-output criteria','G');cr.getRange('A3').values=[['96 binary checks. Equivalent supported meaning earns credit. Contradictions are recorded separately.']];
header(cr,5,['Criterion','Stage','Expected output','Evidence / contract','Do not credit','Clean packet','Maximum']);
cr.getRange('A6:G101').values=criteria.map(c=>[c.id,c.stage_name,c.expected,c.source_refs.join('; '),c.not_credit,c.clean_packet,1]);
widths(cr,[14,27,72,38,65,16,12]);cr.getRange('B6:F101').format.wrapText=true;
for(let i=0;i<criteria.length;i++){const c=criteria[i];const lines=Math.max(Math.ceil(c.expected.length/67),Math.ceil(c.not_credit.length/60),Math.ceil(c.source_refs.join('; ').length/35),Math.ceil(c.stage_name.length/24));cr.getRange(`A${i+6}:G${i+6}`).format.rowHeight=Math.max(44,lines*17+10);}
cr.freezePanes.freezeRows(5);cr.freezePanes.freezeColumns(1);cr.tables.add('A5:G101',true,'FrozenCriteria');
const ss=sheets['Stage scores'];base(ss,149,'I');title(ss,'Stage scores by model, mode and run','I');ss.getRange('A3').values=[['A score appears only after all eight criteria have complete review fields. Harness blocks remain unavailable.']];
header(ss,5,['Stage','Arm','Run','Reviewed / 8','Earned / 8','Coverage','Consistent / 8','Consistent rate','Harness blocks']);
const stageRows=[];for(const arm of arms)for(let rep=1;rep<=3;rep++)for(const st of stages)stageRows.push([st.id,arm,rep,null,null,null,null,null,null]);
ss.getRange('A6:I149').values=stageRows;widths(ss,[13,24,9,17,16,16,20,19,18]);
for(let r=6;r<=149;r++){
 const filt=`'Grades'!$B$6:$B$${end},A${r},'Grades'!$C$6:$C$${end},B${r},'Grades'!$D$6:$D$${end},C${r}`;
 ss.getRange(`D${r}:I${r}`).formulas=[[
  `=SUMIFS('Grades'!$M$6:$M$${end},${filt})`,
  `=IF(D${r}=8,SUMIFS('Grades'!$K$6:$K$${end},${filt}),"")`,
  `=IF(ISNUMBER(E${r}),E${r}/8,"")`,
  `=IF(D${r}=8,SUMIFS('Grades'!$L$6:$L$${end},${filt}),"")`,
  `=IF(ISNUMBER(G${r}),G${r}/8,"")`,
  `=COUNTIFS(${filt},'Grades'!$K$6:$K$${end},"BLOCKED")`
 ]];
}
ss.getRange('F6:F149').setNumberFormat('0.0%');ss.getRange('H6:H149').setNumberFormat('0.0%');ss.freezePanes.freezeRows(5);ss.tables.add('A5:I149',true,'StageResults');
const co=sheets.Comparison;base(co,38,'F');title(co,'R3 investigation evaluation','F');widths(co,[13,45,23,23,23,23]);co.tabColor='#243A55';
co.getRange('A4').values=[['Evaluation v1 frozen. Model runs not started. Runtime and adapter qualification remains open.']];
header(co,6,['Stage','Investigation step','GPT clean','GPT connected','Qwen clean','Qwen connected']);
for(let i=0;i<stages.length;i++){
 const r=7+i;co.getRange(`A${r}:B${r}`).values=[[stages[i].id,stages[i].name]];
 for(let a=0;a<4;a++){
  const col=String.fromCharCode(67+a),arm=arms[a];const filt=`'Stage scores'!$A$6:$A$149,A${r},'Stage scores'!$B$6:$B$149,"${arm}"`;
  co.getRange(`${col}${r}`).formulas=[[`=IF(COUNTIFS(${filt},'Stage scores'!$D$6:$D$149,8)=3,SUMIFS('Stage scores'!$E$6:$E$149,${filt})/24,"Pending")`]];
 }
}
co.getRange('C7:F18').setNumberFormat('0.0%');co.getRange('A20').values=[['Stage rates pool 3 runs: earned points / 24. Each run also has an individual 0–8 score on Stage scores.']];
header(co,23,['Model','Input mode','Reviewed checks','Coverage','Consistent rate','Planned checks']);
for(let a=0;a<4;a++){
 const r=24+a,arm=arms[a];co.getRange(`A${r}:B${r}`).values=[[a<2?'GPT-5.5':'Qwen',a%2?'Previous outputs':'Clean inputs']];
 co.getRange(`C${r}:F${r}`).formulas=[[
  `=SUMIFS('Stage scores'!$D$6:$D$149,'Stage scores'!$B$6:$B$149,"${arm}")`,
  `=IF(C${r}=F${r},SUMIFS('Stage scores'!$E$6:$E$149,'Stage scores'!$B$6:$B$149,"${arm}")/F${r},"Pending")`,
  `=IF(C${r}=F${r},SUMIFS('Stage scores'!$G$6:$G$149,'Stage scores'!$B$6:$B$149,"${arm}")/F${r},"Pending")`,
  '=96*3'
 ]];
}
co.getRange('D24:E27').setNumberFormat('0.0%');
co.getRange('A30').values=[['Grades: amber cells require reviewer input. No grade is inferred from a blank cell.']];
co.getRange('A32').values=[['Presence earns 1 even if contradicted elsewhere; consistent coverage also requires no material contradiction.']];
co.getRange('A34').values=[['Model-caused unvisited stages score 0. Harness-blocked stages prevent a completed comparable score.']];
co.getRange('A36').values=[['See PROTOCOL.md for stage boundaries, custody, repetition policy and failure attribution.']];
const re=sheets.Records;base(re,22,'E');title(re,'R3 evidence package','E');re.getRange('A3').values=[['17 unchanged synthetic surrounding records. Original chart and evaluator keys stay outside model inputs.']];
header(re,5,['ID','Document','Initial input','Sections','SHA-256']);
re.getRange('A6:E22').values=records.map(r=>[r.id,r.title,r.initial?'Yes':'Custodian-held',r.sections.join('; '),r.sha256]);widths(re,[12,68,22,65,72]);re.getRange('B6:D22').format.wrapText=true;re.getRange('A6:E22').format.rowHeight=48;re.freezePanes.freezeRows(5);re.tables.add('A5:E22',true,'EvidenceRecords');
// Meaningful checks of blank, zero, incomplete, complete and harness-blocked behavior.
const tests=[];
wb.recalculate();tests.push({name:'blank_not_zero',ok:co.getRange('C7').values[0][0]==='Pending'});
gr.getRange('E6:J13').values=Array.from({length:8},()=>['Present','Supplied','test-only reference','test-only excerpt','No','None']);wb.recalculate();
tests.push({name:'one_stage_eight_points',ok:ss.getRange('E6').values[0][0]===8});tests.push({name:'other_repetitions_still_pending',ok:co.getRange('C7').values[0][0]==='Pending'});
gr.getRange('E6').values=[['Harness blocked']];wb.recalculate();tests.push({name:'harness_block_not_scored_zero',ok:ss.getRange('E6').values[0][0]===''&&ss.getRange('I6').values[0][0]===1});
gr.getRange('E6:J293').values=Array.from({length:288},()=>['Missing','Supplied','test-only reference','test-only absence rationale','No','Interpretation']);wb.recalculate();tests.push({name:'real_zero_preserved',ok:co.getRange('D24').values[0][0]===0});
gr.getRange(`E6:J${end}`).clear({applyTo:'contents'});wb.recalculate();tests.push({name:'restored_blank',ok:co.getRange('D24').values[0][0]==='Pending'});
if(tests.some(t=>!t.ok))throw new Error(JSON.stringify(tests));
const inspect=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:20},summary:'Formula error scan'});
await fs.writeFile(`${root}/verification/workbook-checks.json`,JSON.stringify({tests,errorScan:inspect.ndjson,nativeExcelTested:false},null,2));
const previews={Comparison:'A1:F36','Stage scores':'A1:I13',Criteria:'A1:G10',Grades:'A1:L10',Records:'A1:E10'};
for(const [name,range] of Object.entries(previews)){
 const blob=await wb.render({sheetName:name,range,scale:1,format:'png'});await fs.writeFile(`${root}/verification/previews/${name.replaceAll(' ','-')}.png`,new Uint8Array(await blob.arrayBuffer()));
}
await (await SpreadsheetFile.exportXlsx(wb)).save(`${out}/R3_Evaluation.xlsx`);
console.log(JSON.stringify({output:`${out}/R3_Evaluation.xlsx`,criteria:criteria.length,gradeRows:N,tests,formulaScan:inspect.ndjson}));

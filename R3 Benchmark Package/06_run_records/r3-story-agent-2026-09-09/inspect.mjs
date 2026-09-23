import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const dir=path.dirname(fileURLToPath(import.meta.url));
const files=fs.readdirSync(dir).filter(f=>/^version-\d+\.json$/.test(f)).sort((a,b)=>Number(a.match(/\d+/)[0])-Number(b.match(/\d+/)[0]));
if(!files.length){const snapshots=fs.readdirSync(path.join(dir,'snapshots')).sort();const s=JSON.parse(fs.readFileSync(path.join(dir,'snapshots',snapshots.at(-1))));console.log(JSON.stringify(s.incident.tracks[0].checkpoints.map(c=>({stage:c.stage,status:c.status,sequence:c.sequence})),null,2));process.exit();}
const version=JSON.parse(fs.readFileSync(path.join(dir,process.argv[2]||files.at(-1))));const a=version.analysis;
if(process.argv[3]==='questions')console.log(JSON.stringify({version:version.number,baseline:a.baselineQuestions,canonical:a.questions,skipped:a.skippedQuestions,fetches:a.answerFetches,verification:a.causalBoard.verificationFindings,answers:a.answers},null,2));
else if(process.argv[3]==='board')console.log(JSON.stringify({version:version.number,status:a.status,board:a.causalBoard,actions:a.correctiveActions,errors:a.stageErrors,revision:a.revision},null,2));
else console.log(JSON.stringify({version:version.number,status:a.status,facts:a.facts,questions:a.questions.map(q=>({id:q.id,owner:q.tagId,proposedBy:q.proposedBy,routes:q.routedTo,text:q.text,needed:q.evidenceNeeded,status:q.status,fetch:a.answerFetches.find(f=>f.questionId===q.id)})),verification:a.causalBoard.verificationFindings,board:a.causalBoard.nodes.map(n=>({id:n.id,label:n.label,status:n.status})),errors:a.stageErrors},null,2));

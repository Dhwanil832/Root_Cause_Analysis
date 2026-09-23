// Explicit evaluation-package preparation, NOT a production evidence filter.
// Originals remain labeled and unchanged. Only the listed simulation metadata
// is removed from derived model inputs; substantive uncertainty is retained.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';

const originalRoot=path.resolve(import.meta.dirname,'../../IA-16036 Controlled Evidence Package');
const output=path.join(originalRoot,'07_case_content_inputs');
const manifest=JSON.parse(await fs.readFile(path.join(originalRoot,'package_manifest.json'),'utf8'));
const sha=value=>createHash('sha256').update(value).digest('hex');
const replacements={
  'IA-I01':[
    ['Synthetic evaluation record derived from a historical incident. Not an actual company record or operating instruction.',''],
    ['No injury is reported in this evaluation case.','No injury is reported.'],
  ],
  'IA-D01':[['Synthetic evaluation record. All equipment identifiers and layout details are fictional and are not operating instructions.','']],
  'IA-D02':[['Synthetic evaluation record. Conventions apply to this fictional case only.','']],
  'IA-D03':[['Synthetic evaluation record. Fictional administrative requirements, not the partner\'s actual policy or a safe-work procedure.','']],
  'IA-S01':[['Synthetic evaluation record. Times and entries are reconstructed for the exercise.','']],
  'IA-S02':[['Synthetic evaluation record. This is an administrative excerpt, not an executable isolation procedure.','This is an administrative excerpt, not an executable isolation procedure.']],
  'IA-S03':[['Synthetic evaluation record. Personnel codes are fictional; no actual employee records are reproduced.','']],
  'IA-P01':[['Synthetic evaluation record. Numeric values and timestamped rows are fictional measurements for this exercise.','']],
  'IA-P02':[['Synthetic evaluation record. Applies only to the fictional instrumentation in this case.','']],
  'IA-P03':[['Synthetic evaluation record. Only equipment scope and document metadata are reproduced. Safety-critical execution steps are intentionally not supplied as operating instructions.','Only equipment scope and document metadata are reproduced. Safety-critical execution steps are intentionally not supplied as operating instructions.']],
  'IA-C01':[['Synthetic evaluation record. The note is an unverified contemporaneous account within the fictional case.','The note is an unverified contemporaneous account.']],
  'IA-P04':[['Synthetic evaluation record. The piping arrangement, identifiers and completion records are fictional. This is not a plant drawing or operating procedure.','']],
  'IA-P05':[
    ['Synthetic evaluation record. Entries, observation details and times are reconstructed for testing; no original photographs are supplied.','No original photographs are supplied.'],
    ['The field photo description is a text surrogate for the evaluation, not an image that has been independently inspected.','The field photo description is a text surrogate, not an image that has been independently inspected.'],
  ],
  'IA-P06':[['Synthetic evaluation record. Inspection observations and scope are fictional.','']],
  'IA-C02':[['Synthetic evaluation record. Fictional reference sheet reproduced as found in a mixed service folder.','Reference sheet reproduced as found in a mixed service folder.']],
  'IA-P07':[['Synthetic evaluation record. This administrative history is an invented controlled-case detail, not an actual company finding.','']],
  'IA-P08':[['Synthetic evaluation record. Revision dates, draft content and distribution records are reconstructed.','']],
  'IA-P09':[['Synthetic evaluation record. Journal results and interview are fictional case evidence.','']],
};

// Validate the entire transformation before creating any derived files.
const prepared=[];
for(const r of manifest.records){
  const original=await fs.readFile(path.join(originalRoot,r.path),'utf8');
  if(!replacements[r.id])throw Error('Unreviewed record: '+r.id);
  let content=original;
  for(const [before,after] of replacements[r.id]){
    if(content.split(before).length!==2)throw Error('Source changed; inspect before removal: '+r.id);
    content=content.replace(before,after);
  }
  content=content.replace(/\n{3,}/g,'\n\n');
  if(/synthetic|fictional|evaluation|reconstructed|for the exercise/i.test(content))throw Error('Unreviewed simulation metadata remains: '+r.id);
  // No table value, timestamp, equipment identifier or table qualification moves.
  const tables=text=>text.split('\n').filter(line=>line.trimStart().startsWith('|')).join('\n');
  if(tables(content)!==tables(original))throw Error('A table changed: '+r.id);
  prepared.push({...r,originalSha256:sha(original),sha256:sha(content),content});
}
await fs.mkdir(output); // Never overwrite a previous prepared input package.
for(const r of prepared){
  const target=path.join(output,r.path);
  await fs.mkdir(path.dirname(target),{recursive:true});
  await fs.writeFile(target,r.content,{flag:'wx'});
}
const audit={createdAt:new Date().toISOString(),originalRoot,
  provenance:'Historically anchored synthetic evaluation records, not actual company records or operating instructions.',
  purpose:'Remove simulation metadata from model input, not evidence limitations or incident facts.',
  originalsUnchanged:true,tableRowsUnchanged:true,
  changes:prepared.map(r=>({id:r.id,path:r.path,originalSha256:r.originalSha256,sha256:r.sha256,replacements:replacements[r.id]}))};
await fs.writeFile(path.join(output,'provenance.operator-only.json'),JSON.stringify(audit,null,2)+'\n',{flag:'wx'});
await fs.writeFile(path.join(output,'package_manifest.json'),JSON.stringify({...manifest,package_version:'1.1-case-content-only',
  status:'prepared_not_run',records:prepared.map(({content,...r})=>r),
  never_upload:[...manifest.never_upload,'provenance.operator-only.json'],
  note:'Operator only. Model inputs are individual record contents only, released by batch. Never upload this manifest, provenance, folder names, future releases, or evaluation material.'},null,2)+'\n',{flag:'wx'});
await fs.writeFile(path.join(output,'README.md'),`# Case-content-only input view — operator only

These remain **synthetic evaluation records**, not real company records or operating instructions.
The user authorized removal of simulation disclaimers from model-facing text.
Original labeled documents remain unchanged in the parent package.

Upload only individual documents at their planned release: B0 then B1, B2, B3.
For the current cumulative V1, use B0+B1 only (incident plus ten documents).
Never upload this README, the manifest, provenance audit, private truth, or future-release plan.

Unverified testimony, sample coverage, unavailable photographs, administrative scope,
missing records and all other substantive limitations are preserved. No causal answer
was added. Every table row is byte-identical to its original.

The operator-only provenance JSON records exact before/after text and document hashes.
An existing run cannot be cleaned retroactively; start a new track without importing
its old findings, answers, questions or cache.
`,{flag:'wx'});
for(const r of prepared)if(sha(await fs.readFile(path.join(originalRoot,r.path)))!==r.originalSha256)throw Error('Original unexpectedly changed.');
console.log(JSON.stringify({output,records:prepared.length,initialRecords:prepared.filter(r=>['B0','B1'].includes(r.release)).length,
  originalFilesUnchanged:true,tablesUnchanged:true},null,2));

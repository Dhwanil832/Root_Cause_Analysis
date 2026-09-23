// Read-only audit of the exact Ollama request bodies, not the database previews.
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
const dir = path.resolve(process.argv[2] || '');
const frozen = JSON.parse(fs.readFileSync(path.join(dir, 'frozen-rca-input.json')));
const root = path.join(dir, 'frozen-app/prompts');
const shared = fs.readFileSync(path.join(root, 'shared/system.md'), 'utf8');
const sha = text => createHash('sha256').update(text).digest('hex');
const roles = new Map();
function walk(folder) {
  for (const entry of fs.readdirSync(folder, {withFileTypes:true})) {
    const file = path.join(folder, entry.name);
    if (entry.isDirectory()) walk(file);
    else if (entry.name === 'system.md') roles.set(sha(shared + '\n\n' + fs.readFileSync(file, 'utf8')), path.relative(root, folder));
  }
}
walk(root);
const required = new Set(['incident-understanding','incident-structuring','tagging','evidence-adjudication','evidence-processing','causal-analysis','causal-verification']);
const requests = [];
for (const name of fs.readdirSync(path.join(dir, 'model-capture')).filter(n => n.endsWith('-request.json')).sort()) {
  const request = JSON.parse(fs.readFileSync(path.join(dir, 'model-capture', name)));
  const stage = roles.get(sha(request.messages[0].content)) || 'unknown';
  if (!required.has(stage) && !stage.startsWith('specialists/')) continue;
  const packed = request.messages[1].content.split('--- BEGIN EVIDENCE PACKET ---')[1]?.split('--- END EVIDENCE PACKET ---')[0]?.trim();
  const packet = JSON.parse(packed);
  const segments = [];
  function collect(value) {
    if (!value || typeof value !== 'object') return;
    for (const [key, child] of Object.entries(value)) {
      if (key === 'evidenceSegments' && Array.isArray(child)) segments.push(...child);
      else if (typeof child === 'object') collect(child);
    }
  }
  collect(packet);
  const documents = frozen.documents.map(doc => {
    const supplied = segments.filter(s => s.documentId === doc.id).sort((a,b) => a.start - b.start);
    let offset = 0;
    const contiguous = supplied.every(s => {
      const valid = s.start === offset && s.end - s.start === s.excerpt.length;
      offset = s.end;
      return valid;
    });
    const text = supplied.map(s => s.excerpt).join('');
    return {id:doc.id, fileName:doc.fileName, expectedCharacters:doc.extractedText.length,
      suppliedCharacters:text.length, complete:contiguous && text === doc.extractedText};
  });
  requests.push({request:name.slice(0,4), stage, packetCharacters:packed.length,
    complete:documents.every(d => d.complete), documents});
}
const report = {requests, allCapturedRequiredRequestsComplete:requests.length > 0 && requests.every(r => r.complete)};
if (process.argv.includes('--save')) fs.writeFileSync(path.join(dir, 'document-delivery-audit.json'), JSON.stringify(report, null, 2), {flag:'wx'});
console.log(JSON.stringify(process.argv.includes('--summary')
  ? {...report, requests:requests.map(({documents, ...request}) => ({...request, documentCount:documents.length}))}
  : report, null, 2));

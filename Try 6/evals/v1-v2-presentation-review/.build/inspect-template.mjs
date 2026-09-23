import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const source='/Users/dhwanilchauhan/.codex/plugins/cache/openai-curated-remote/openai-templates/0.1.1/skills/artifact-template-simple-light-mode/assets/reference.pptx';
const p=await PresentationFile.importPptx(await FileBlob.load(source));
const out=new URL('./',import.meta.url);
const snapshot=await p.inspect({kind:'slide,textbox,layout,chart,table',maxChars:100000});
await fs.writeFile(new URL('template-inspection.ndjson',out),snapshot.ndjson);
await fs.writeFile(new URL('template-model.json',out),JSON.stringify(p.toProto(),null,2));
console.log(JSON.stringify({slides:p.slides.items.length,masters:p.masters.items.map(m=>({id:m.id,name:m.name})),layouts:p.layouts.items.map(l=>({id:l.id,name:l.name}))}));
for(let i=0;i<p.slides.items.length;i++){
 const s=p.slides.items[i];
 await fs.writeFile(new URL(`template-${i+1}.png`,out),new Uint8Array(await(await s.export({format:'png',scale:1})).arrayBuffer()));
}

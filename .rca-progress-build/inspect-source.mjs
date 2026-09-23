import fs from 'node:fs/promises';
import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('/Users/dhwanilchauhan/Downloads/S&T_PTC_July2026Presentation.pptx'));
await fs.writeFile('.rca-progress-build/source-inspect.json',(await p.inspect({kind:'slide,layout,textbox',maxChars:100000})).ndjson);
for(let i=0;i<p.slides.items.length;i++){const b=await p.export({slide:p.slides.items[i],format:'png',scale:0.7});await fs.writeFile(`.rca-progress-build/source-${i+1}.png`,new Uint8Array(await b.arrayBuffer()));}
console.log('done');

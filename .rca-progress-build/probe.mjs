import {FileBlob,PresentationFile} from '@oai/artifact-tool';
const p=await PresentationFile.importPptx(await FileBlob.load('/Users/dhwanilchauhan/Downloads/S&T_PTC_July2026Presentation.pptx'));
for(const [n,o] of [['slides',p.slides],['slide',p.slides.items[0]],['shapes',p.slides.items[0].shapes]])console.log(n,Object.getOwnPropertyNames(Object.getPrototypeOf(o)));
console.log('layouts',p.layouts.items.map(l=>({id:l.id,name:l.name})));

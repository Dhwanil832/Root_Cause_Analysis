import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const p = await PresentationFile.importPptx(
  await FileBlob.load("/Users/dhwanilchauhan/Desktop/RCA Try 1/.pptx-goals-slide.GkJ6uO/template-starter.pptx"),
);
const slide = p.slides.items[0];
const table = slide.tables.items[0];
console.log("slide keys", Object.keys(slide));
console.log("tables keys", Object.keys(slide.tables));
console.log("table keys", Object.keys(table));
console.log("slide proto", Object.getOwnPropertyNames(Object.getPrototypeOf(slide)));
console.log("tables proto", Object.getOwnPropertyNames(Object.getPrototypeOf(slide.tables)));
console.log("table proto", Object.getOwnPropertyNames(Object.getPrototypeOf(table)));
console.log((await p.help("remove table", { search: "remove delete table collection", include: ["index", "notes"], maxChars: 6000 })).ndjson);

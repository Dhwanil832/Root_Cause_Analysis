import fs from "node:fs/promises";
import { FileBlob, PresentationFile } from "@oai/artifact-tool";

const input = "/Users/dhwanilchauhan/Desktop/RCA Try 1/.pptx-goals-slide.GkJ6uO/template-starter.pptx";
const output = "/Users/dhwanilchauhan/Desktop/RCA Try 1/agent_kickoff_question_maps_with_goals.pptx";
const qaDir = "/Users/dhwanilchauhan/Desktop/RCA Try 1/.pptx-goals-slide.GkJ6uO/final-qa";

const values = [
  ["Category", "Core facts to establish", "Tangential links to explore"],
  ["Human involvement", "Roles, exposure, actions, task intent, competence", "Information, workload, PPE, supervision, system constraints"],
  ["Electrical incident", "Asset or circuit, energy state, work, abnormal evidence, protection", "Exposure path, temporary setup, environment, isolation"],
  ["Equipment or tool", "Function, expected state, actual condition, changes, failure behavior", "Maintenance, guards, interfaces, human contact, stored energy"],
  ["Mobile equipment / vehicle", "Vehicle, task, motion, route, controls, operating status", "Visibility, separation, ground conditions, communication"],
  ["Crane / lifting / suspended load", "Load, lift method, rigging, support, position, control", "Exclusion zone, signals, inspection, weather, gravity energy"],
  ["Rail / locomotive", "Movement, equipment, route, authority, switching, braking", "Track condition, signals, visibility, communication, interfaces"],
  ["Stored / released / gravity energy", "Energy source, magnitude, state, restraint, release path", "Isolation, pressure, balance, position, line of fire"],
  ["Isolation / LOTO", "Energy sources, boundaries, steps, verification, actual status", "Stored energy, shared systems, handoffs, changes, deviations"],
  ["Maintenance / outage / non-routine work", "Scope, sequence, non-normal configuration, changes, work status", "Simultaneous work, temporary states, handoffs, restoration"],
  ["Process or material", "Material, process state, parameters, containment, release", "Reaction, contamination, temperature, pressure, handling, exposure"],
  ["Work environment", "Location, access, layout, physical conditions, immediate hazards", "Lighting, weather, height, atmosphere, congestion, housekeeping"],
  ["Procedure / planning", "Required method, scope, hazards considered, planned versus actual work", "Document quality, feasibility, permits, change control, authorization"],
  ["Communication / supervision", "Who knew what, instructions, handoffs, decisions, oversight", "Language, conflicting cues, stop-work, contractor coordination"],
  ["Animal / wildlife / insect", "Species, presence, contact route, timing, immediate effect", "Attractants, habitat, barriers, season, reporting and response"],
  ["Other / novel condition", "Unclassified condition, observable facts, possible mechanism, impact", "Rare interactions, changed assumptions, external factors, expert needs"],
];

async function writeBlob(path, blob) {
  await fs.writeFile(path, new Uint8Array(await blob.arrayBuffer()));
}

const presentation = await PresentationFile.importPptx(await FileBlob.load(input));
const overview = presentation.slides.items[0];

const title = overview.shapes.items.find((shape) => shape.name === "Text 1");
const badge = overview.shapes.items.find((shape) => shape.name === "Text 3");
if (!title || !badge || overview.tables.items.length !== 1) {
  throw new Error("The copied source-slide structure did not match the expected template.");
}

title.text.replace("Human involvement", "What each category should establish");
badge.text.replace("Table 1/15", "Overview");

const oldTable = overview.tables.items[0];
overview.tables.deleteById(oldTable.id);

const table = overview.tables.add({
  rows: values.length,
  columns: 3,
  left: 43.2,
  top: 109.44,
  width: 1193.28,
  height: 571.2,
  columnWidths: [245, 466, 482.28],
  values,
});
table.styleOptions = {
  headerRow: false,
  totalRow: false,
  firstColumn: false,
  lastColumn: false,
  bandedRows: false,
  bandedColumns: false,
};
table.borders.assign({ style: "solid", fill: "#C9D6E4", width: 0.75 });
table.rows[0].height = 32;
for (let row = 1; row < values.length; row += 1) {
  table.rows[row].height = 35.95;
}

for (let row = 0; row < values.length; row += 1) {
  for (let column = 0; column < 3; column += 1) {
    const cell = table.getCell(row, column);
    if (row === 0) {
      cell.fill = "#12365D";
      cell.text.style = {
        fontSize: 11.2,
        typeface: "Aptos",
        color: "#FFFFFF",
        bold: true,
      };
    } else {
      cell.fill = row % 2 === 0 ? "#EEF6FB" : "#FFFFFF";
      cell.text.style = {
        fontSize: 9.8,
        typeface: "Aptos",
        color: "#1F2937",
        bold: column === 0,
      };
    }
  }
}

for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.items[index];
  const pageNumber = slide.shapes.items.find(
    (shape) => shape.name === "Slide Number Placeholder 0",
  );
  if (pageNumber) pageNumber.text = String(index + 1);
}

await fs.mkdir(qaDir, { recursive: true });
for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.items[index];
  const stem = `slide-${String(index + 1).padStart(2, "0")}`;
  await writeBlob(
    `${qaDir}/${stem}.png`,
    await presentation.export({ slide, format: "png", scale: 1 }),
  );
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(`${qaDir}/${stem}.layout.json`, await layout.text());
}

const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
await writeBlob(`${qaDir}/deck-montage.webp`, montage);

const snapshot = await presentation.inspect({
  kind: "slide,textbox,shape,table,notes,layout",
  maxChars: 30000,
});
await fs.writeFile(`${qaDir}/final-inspect.ndjson`, snapshot.ndjson);

const pptx = await PresentationFile.exportPptx(presentation);
await pptx.save(output);

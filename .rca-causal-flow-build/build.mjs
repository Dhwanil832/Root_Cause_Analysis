import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const SKILL_DIR = "/Users/dhwanilchauhan/.codex/plugins/cache/openai-primary-runtime/presentations/26.903.11726/skills/presentations";
const workspaceDir = "/Users/dhwanilchauhan/Desktop/RCA Try 1";
const buildDir = path.join(workspaceDir, ".rca-causal-flow-build");
const outputDir = path.join(workspaceDir, "RCA Presentation Outputs");
const FINAL_PPTX = path.join(outputDir, "RCA_investigation_system_flow_v4.pptx");
const FLOW_IMAGE = path.join(outputDir, "RCA_full_flow_v4.png");
const RUNTIME_PYTHON = "/Users/dhwanilchauhan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3";

const { finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href
);

const C = {
  bg: "#F7F9FC",
  navy: "#12365D",
  teal: "#0E7490",
  tealLight: "#E7F4F8",
  blueLight: "#EEF6FB",
  orange: "#F59E0B",
  orangeLight: "#FFF4D6",
  green: "#2F855A",
  greenLight: "#E7F6EC",
  red: "#B42318",
  redLight: "#FDECEC",
  purple: "#6941C6",
  purpleLight: "#F0EAFE",
  gray: "#607089",
  line: "#CBD8E6",
  text: "#1F2937",
  white: "#FFFFFF",
};

const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function addText(slide, text, position, style = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position,
    fill: "none",
    line: { fill: "none", width: 0 },
  });
  shape.text = text;
  shape.text.style = {
    typeface: style.typeface ?? "Aptos",
    fontSize: style.fontSize ?? 18,
    bold: style.bold ?? false,
    color: style.color ?? C.text,
    alignment: style.alignment ?? "left",
    verticalAlignment: style.verticalAlignment ?? "middle",
    autoFit: style.autoFit ?? "shrinkText",
  };
  return shape;
}

function addBox(slide, text, position, options = {}) {
  const shape = slide.shapes.add({
    geometry: options.geometry ?? "roundRect",
    position,
    fill: options.fill ?? C.white,
    line: {
      style: "solid",
      fill: options.line ?? C.line,
      width: options.lineWidth ?? 1.2,
    },
    borderRadius: options.radius ?? 12,
    shadow: options.shadow ?? "shadow-none",
  });
  shape.text = text;
  shape.text.style = {
    typeface: options.typeface ?? "Aptos",
    fontSize: options.fontSize ?? 17,
    bold: options.bold ?? true,
    color: options.color ?? C.navy,
    alignment: options.alignment ?? "center",
    verticalAlignment: "middle",
    autoFit: "shrinkText",
  };
  return shape;
}

function connect(slide, from, to, options = {}) {
  return slide.shapes.connect(from, to, {
    kind: options.kind ?? "elbow",
    fromSide: options.fromSide,
    toSide: options.toSide,
    line: {
      style: options.dashed ? "dashed" : "solid",
      fill: options.color ?? C.teal,
      width: options.width ?? 2.2,
    },
    tail: { type: "triangle", width: "sm", length: "sm" },
  });
}

function addChrome(slide, title, number, subtitle) {
  slide.background.fill = C.bg;
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 1280, height: 12 },
    fill: C.teal,
    line: { fill: C.teal, width: 0 },
  });
  addText(slide, title, { left: 48, top: 28, width: 1050, height: 48 }, {
    typeface: "Aptos Display",
    fontSize: 31,
    bold: true,
    color: C.navy,
  });
  if (subtitle) {
    addText(slide, subtitle, { left: 50, top: 82, width: 1090, height: 28 }, {
      fontSize: 16,
      color: C.gray,
    });
  }
  slide.shapes.add({
    geometry: "line",
    position: { left: 0, top: 690, width: 1280, height: 0 },
    fill: "none",
    line: { style: "solid", fill: "#D7DEE9", width: 1 },
  });
  addText(slide, "RCA investigation system", { left: 40, top: 694, width: 260, height: 20 }, {
    fontSize: 11,
    color: C.gray,
  });
  addText(slide, String(number), { left: 1175, top: 694, width: 60, height: 20 }, {
    fontSize: 11,
    color: C.gray,
    alignment: "right",
  });
}

function addBulletList(slide, items, position, options = {}) {
  const lineHeight = options.lineHeight ?? 42;
  items.forEach((item, index) => {
    slide.shapes.add({
      geometry: "ellipse",
      position: {
        left: position.left,
        top: position.top + index * lineHeight + 12,
        width: 8,
        height: 8,
      },
      fill: options.dotColor ?? C.orange,
      line: { fill: options.dotColor ?? C.orange, width: 0 },
    });
    addText(
      slide,
      item,
      {
        left: position.left + 20,
        top: position.top + index * lineHeight,
        width: position.width - 20,
        height: lineHeight - 4,
      },
      { fontSize: options.fontSize ?? 18, color: options.color ?? C.text },
    );
  });
}

// Slide 1: cover
{
  const slide = presentation.slides.add();
  slide.background.fill = C.bg;
  slide.shapes.add({
    geometry: "rect",
    position: { left: 0, top: 0, width: 1280, height: 18 },
    fill: C.teal,
    line: { fill: C.teal, width: 0 },
  });
  slide.shapes.add({
    geometry: "rect",
    position: { left: 72, top: 146, width: 7, height: 300 },
    fill: C.orange,
    line: { fill: C.orange, width: 0 },
  });
  addText(slide, "RCA Investigation System", { left: 112, top: 165, width: 900, height: 86 }, {
    typeface: "Aptos Display",
    fontSize: 50,
    bold: true,
    color: C.navy,
  });
  addText(
    slide,
    "From incident description to evidence-supported causal paths",
    { left: 116, top: 262, width: 820, height: 54 },
    { fontSize: 25, color: C.teal },
  );
  addText(
    slide,
    "Separate specialist knowledge bases, one question handler and an iterative causal-analysis loop",
    { left: 116, top: 337, width: 920, height: 72 },
    { fontSize: 19, color: C.gray },
  );
  addText(slide, "System concept", { left: 1090, top: 42, width: 140, height: 24 }, {
    fontSize: 13,
    bold: true,
    color: C.teal,
    alignment: "right",
  });
  addText(slide, "RCA investigation system", { left: 52, top: 676, width: 260, height: 22 }, {
    fontSize: 11,
    color: C.gray,
  });
}

// Slide 2: complete flow
{
  const slide = presentation.slides.add();
  addChrome(slide, "End-to-end investigation flow", 2, "Knowledge develops first. Causal analysis then tests possible explanations against evidence.");

  const y1 = 160;
  const y2 = 430;
  const w = 170;
  const h = 82;
  const x1 = [45, 247, 449, 651, 853, 1055];
  const topLabels = [
    "Incident\ndescription",
    "System\nunderstanding",
    "Tagging",
    "Selected specialist\nagents",
    "Candidate\nquestions",
    "Question\nBroker",
  ];
  const topColors = [C.tealLight, C.blueLight, C.orangeLight, C.purpleLight, C.blueLight, C.tealLight];
  const topNodes = topLabels.map((label, index) => addBox(slide, label, {
    left: x1[index], top: y1, width: w, height: h,
  }, { fill: topColors[index], line: index === 5 ? C.teal : C.line, fontSize: 17 }));
  for (let index = 0; index < topNodes.length - 1; index += 1) {
    connect(slide, topNodes[index], topNodes[index + 1], { fromSide: "right", toSide: "left" });
  }

  const x2 = [1055, 816, 577, 338, 99];
  const bottomLabels = [
    "Answer-Fetching\nAgent",
    "Question Broker\nreturns answer",
    "Specialist knowledge\nbases evolve",
    "Causal Analysis\nAgent",
    "Supported\ncausal board",
  ];
  const bottomColors = [C.orangeLight, C.tealLight, C.purpleLight, C.blueLight, C.greenLight];
  const bottomNodes = bottomLabels.map((label, index) => addBox(slide, label, {
    left: x2[index], top: y2, width: index === 4 ? 190 : 188, height: h,
  }, {
    fill: bottomColors[index],
    line: index === 4 ? C.green : C.line,
    fontSize: 17,
  }));
  connect(slide, topNodes[5], bottomNodes[0], { fromSide: "bottom", toSide: "top" });
  for (let index = 0; index < bottomNodes.length - 1; index += 1) {
    connect(slide, bottomNodes[index], bottomNodes[index + 1], { fromSide: "left", toSide: "right" });
  }

  addText(slide, "Knowledge-building round", { left: 46, top: 122, width: 500, height: 25 }, {
    fontSize: 15,
    bold: true,
    color: C.gray,
  });
  addText(slide, "Answer and causal-analysis round", { left: 700, top: 392, width: 365, height: 25 }, {
    fontSize: 15,
    bold: true,
    color: C.gray,
    alignment: "right",
  });

  const loop = slide.shapes.connect(bottomNodes[3], topNodes[5], {
    kind: "elbow",
    fromSide: "top",
    toSide: "bottom",
    line: { style: "dashed", fill: C.purple, width: 2 },
    tail: { type: "triangle", width: "sm", length: "sm" },
  });
  loop.sendToBack();
  addText(slide, "Missing facts create new questions", { left: 632, top: 318, width: 310, height: 30 }, {
    fontSize: 14,
    bold: true,
    color: C.purple,
    alignment: "center",
  });
  addText(slide, "Each model track runs this flow independently.", { left: 52, top: 615, width: 520, height: 32 }, {
    fontSize: 17,
    bold: true,
    color: C.navy,
  });
  addText(slide, "The human investigator can answer, correct or override at any stage.", { left: 620, top: 615, width: 610, height: 32 }, {
    fontSize: 17,
    color: C.gray,
    alignment: "right",
  });
}

// Slide 3: specialist knowledge separation
{
  const slide = presentation.slides.add();
  addChrome(slide, "Separate specialist knowledge bases", 3, "Specialists keep independent interpretations while the answer agent can search across all available knowledge.");

  addText(slide, "Separate domain views", { left: 55, top: 122, width: 330, height: 30 }, {
    fontSize: 18, bold: true, color: C.navy,
  });
  const kbLabels = [
    "Equipment knowledge base",
    "Stored-energy knowledge base",
    "Maintenance knowledge base",
    "Human knowledge base",
    "Other selected specialists",
  ];
  const kbs = kbLabels.map((label, index) => addBox(slide, label, {
    left: 55,
    top: 165 + index * 82,
    width: 340,
    height: 60,
  }, {
    fill: index % 2 === 0 ? C.blueLight : C.white,
    line: C.line,
    fontSize: 16,
    alignment: "left",
  }));

  const answerAgent = addBox(slide, "Answer-Fetching Agent", {
    left: 485, top: 248, width: 260, height: 86,
  }, { fill: C.orangeLight, line: C.orange, fontSize: 20 });
  const evidence = addBox(slide, "Documents, uploaded evidence\nand user answers", {
    left: 485, top: 410, width: 260, height: 86,
  }, { fill: C.white, line: C.gray, fontSize: 17 });
  const broker = addBox(slide, "Question Broker", {
    left: 855, top: 184, width: 290, height: 82,
  }, { fill: C.tealLight, line: C.teal, fontSize: 20 });
  const recipients = addBox(slide, "Relevant specialists and\nCausal Analysis Agent", {
    left: 855, top: 368, width: 290, height: 94,
  }, { fill: C.purpleLight, line: C.purple, fontSize: 18 });

  kbs.forEach((kb) => connect(slide, answerAgent, kb, {
    fromSide: "left", toSide: "right", color: C.gray, width: 1.4,
  }));
  connect(slide, answerAgent, evidence, { fromSide: "bottom", toSide: "top", color: C.orange });
  connect(slide, broker, answerAgent, { fromSide: "left", toSide: "right", color: C.teal });
  connect(slide, answerAgent, broker, { fromSide: "right", toSide: "bottom", color: C.teal });
  connect(slide, broker, recipients, { fromSide: "bottom", toSide: "top", color: C.purple });

  addText(slide, "The answer agent searches. It does not merge specialist knowledge bases.", {
    left: 460, top: 548, width: 720, height: 40,
  }, { fontSize: 18, bold: true, color: C.navy, alignment: "center" });
  addText(slide, "Redundancy remains visible so one specialist can catch what another missed.", {
    left: 460, top: 592, width: 720, height: 36,
  }, { fontSize: 17, color: C.gray, alignment: "center" });
}

// Slide 4: question handling
{
  const slide = presentation.slides.add();
  addChrome(slide, "Question handling", 4, "The same handler processes questions from specialist agents and from causal analysis.");

  const specialist = addBox(slide, "Specialist Agent\nproposes and justifies", {
    left: 60, top: 180, width: 245, height: 95,
  }, { fill: C.purpleLight, line: C.purple, fontSize: 18 });
  const causal = addBox(slide, "Causal Analysis Agent\nidentifies a missing fact", {
    left: 60, top: 400, width: 245, height: 95,
  }, { fill: C.blueLight, line: C.navy, fontSize: 18 });
  const broker = addBox(slide, "Question Broker", {
    left: 410, top: 287, width: 225, height: 95,
  }, { fill: C.tealLight, line: C.teal, fontSize: 22 });
  const answer = addBox(slide, "Answer-Fetching Agent", {
    left: 745, top: 287, width: 245, height: 95,
  }, { fill: C.orangeLight, line: C.orange, fontSize: 20 });
  const returnBroker = addBox(slide, "Question Broker\nreceives the answer", {
    left: 1060, top: 287, width: 170, height: 95,
  }, { fill: C.tealLight, line: C.teal, fontSize: 17 });

  connect(slide, specialist, broker, { fromSide: "right", toSide: "left", color: C.purple });
  connect(slide, causal, broker, { fromSide: "right", toSide: "left", color: C.navy });
  connect(slide, broker, answer, { fromSide: "right", toSide: "left", color: C.teal });
  connect(slide, answer, returnBroker, { fromSide: "right", toSide: "left", color: C.orange });

  const recipients = addBox(slide, "Broker distributes the answer to every contributing or relevant agent", {
    left: 655, top: 500, width: 575, height: 74,
  }, { fill: C.greenLight, line: C.green, fontSize: 18 });
  connect(slide, returnBroker, recipients, { fromSide: "bottom", toSide: "top", color: C.green });

  addText(slide, "Broker responsibilities", { left: 390, top: 445, width: 270, height: 28 }, {
    fontSize: 17, bold: true, color: C.teal,
  });
  addBulletList(slide, [
    "Merge overlapping questions",
    "Preserve contributors and purpose",
    "Return the answer to the right agents",
  ], { left: 390, top: 475, width: 245, height: 150 }, { fontSize: 15, lineHeight: 43, dotColor: C.teal });

  addText(slide, "Answer-agent responsibilities", { left: 715, top: 145, width: 310, height: 30 }, {
    fontSize: 17, bold: true, color: C.orange,
  });
  addBulletList(slide, [
    "Search specialist knowledge bases",
    "Search documents and evidence",
    "Ask the user when the answer remains unavailable",
  ], { left: 715, top: 178, width: 455, height: 120 }, { fontSize: 15, lineHeight: 39, dotColor: C.orange });
}

// Slide 5: first causal step
{
  const slide = presentation.slides.add();
  addChrome(slide, "The first causal step", 5, "Causal analysis starts with the immediate event and creates competing explanations for what directly allowed it.");

  const candidates = [
    "Required support\nwas lost",
    "A restraint was\nineffective",
    "The component moved\nout of position",
    "An external force\nacted on the beam",
  ].map((label, index) => addBox(slide, label, {
    left: 70,
    top: 150 + index * 112,
    width: 310,
    height: 76,
  }, {
    fill: index % 2 === 0 ? C.blueLight : C.white,
    line: C.line,
    fontSize: 18,
  }));

  const event = addBox(slide, "R3 Exit Carrier Beam\nfell from the yoke", {
    left: 840, top: 282, width: 340, height: 120,
  }, { fill: C.redLight, line: C.red, fontSize: 24 });
  candidates.forEach((candidate) => connect(slide, candidate, event, {
    fromSide: "right", toSide: "left", color: C.gray, width: 1.8,
  }));

  addText(slide, "Possible direct explanations", { left: 70, top: 112, width: 340, height: 28 }, {
    fontSize: 18, bold: true, color: C.navy,
  });
  addText(slide, "Event to explain", { left: 840, top: 238, width: 340, height: 30 }, {
    fontSize: 18, bold: true, color: C.red, alignment: "center",
  });

  const callout = addBox(slide, "A branch advances only when facts support a plausible mechanism.", {
    left: 470, top: 535, width: 710, height: 66,
  }, { fill: C.greenLight, line: C.green, fontSize: 20 });
  addText(slide, "At this stage, every explanation remains possible rather than proven.", {
    left: 475, top: 180, width: 630, height: 46,
  }, { fontSize: 19, color: C.gray, alignment: "center" });
  addText(slide, "The agent asks which fact would distinguish one explanation from the others.", {
    left: 475, top: 430, width: 630, height: 52,
  }, { fontSize: 19, color: C.navy, alignment: "center", bold: true });
}

// Slide 6: causal analysis loop
{
  const slide = presentation.slides.add();
  addChrome(slide, "Causal-analysis loop", 6, "The agent moves backward only along explanations that survive evidence checks.");

  const nodes = [
    addBox(slide, "1\nStart with the event", { left: 510, top: 125, width: 250, height: 74 }, { fill: C.redLight, line: C.red, fontSize: 18 }),
    addBox(slide, "2\nPropose direct explanations", { left: 865, top: 195, width: 280, height: 80 }, { fill: C.blueLight, line: C.navy, fontSize: 18 }),
    addBox(slide, "3\nConnect facts through a mechanism", { left: 900, top: 390, width: 280, height: 80 }, { fill: C.blueLight, line: C.navy, fontSize: 18 }),
    addBox(slide, "4\nIdentify the missing fact", { left: 510, top: 520, width: 250, height: 74 }, { fill: C.orangeLight, line: C.orange, fontSize: 18 }),
    addBox(slide, "5\nAsk through the Question Broker", { left: 105, top: 390, width: 290, height: 80 }, { fill: C.tealLight, line: C.teal, fontSize: 18 }),
    addBox(slide, "6\nReceive the answer and revise status", { left: 105, top: 195, width: 290, height: 80 }, { fill: C.purpleLight, line: C.purple, fontSize: 18 }),
  ];
  connect(slide, nodes[0], nodes[1], { fromSide: "right", toSide: "top", color: C.gray });
  connect(slide, nodes[1], nodes[2], { fromSide: "bottom", toSide: "top", color: C.gray });
  connect(slide, nodes[2], nodes[3], { fromSide: "left", toSide: "right", color: C.gray });
  connect(slide, nodes[3], nodes[4], { fromSide: "left", toSide: "right", color: C.gray });
  connect(slide, nodes[4], nodes[5], { fromSide: "top", toSide: "bottom", color: C.gray });
  connect(slide, nodes[5], nodes[0], { fromSide: "right", toSide: "left", color: C.gray });

  addBox(slide, "Supported path", { left: 470, top: 300, width: 155, height: 54 }, {
    fill: C.greenLight, line: C.green, fontSize: 16,
  });
  addBox(slide, "Possible path", { left: 650, top: 300, width: 155, height: 54 }, {
    fill: C.orangeLight, line: C.orange, fontSize: 16,
  });
  addBox(slide, "Rejected path", { left: 560, top: 375, width: 155, height: 54 }, {
    fill: C.redLight, line: C.red, fontSize: 16,
  });
  addText(slide, "When a direct link becomes supported, the agent asks what created that condition and moves one step further backward.", {
    left: 315, top: 620, width: 650, height: 44,
  }, { fontSize: 17, bold: true, color: C.navy, alignment: "center" });
}

// Slide 7: causal-link record
{
  const slide = presentation.slides.add();
  addChrome(slide, "Causal connection record", 7, "The causal board stores an explicit claim and the evidence needed to assess it.");

  const fields = [
    ["Condition", "What existed or happened before the event"],
    ["Effect", "What changed or occurred next"],
    ["Mechanism", "How the condition could have produced the effect"],
    ["Supporting facts", "Evidence that agrees with the proposed connection"],
    ["Contradicting facts", "Evidence that weakens or challenges the connection"],
    ["Missing evidence", "The specific fact that would distinguish the direction"],
    ["Status", "Supported, possible, disputed or rejected"],
  ];
  const table = slide.tables.add({
    rows: fields.length + 1,
    columns: 2,
    left: 70,
    top: 140,
    width: 1140,
    height: 430,
    columnWidths: [295, 845],
    values: [["Causal-link field", "What the agent records"], ...fields],
  });
  table.borders.assign({ style: "solid", fill: C.line, width: 0.8 });
  for (let row = 0; row < fields.length + 1; row += 1) {
    table.rows[row].height = row === 0 ? 43 : 55;
    for (let col = 0; col < 2; col += 1) {
      const cell = table.getCell(row, col);
      cell.fill = row === 0 ? C.navy : row % 2 === 0 ? C.blueLight : C.white;
      cell.text.style = {
        typeface: "Aptos",
        fontSize: row === 0 ? 17 : 16,
        bold: row === 0 || col === 0,
        color: row === 0 ? C.white : C.text,
      };
    }
  }
  addText(slide, "Questions remain outside the causal board until an answer produces a fact or changes a connection.", {
    left: 120, top: 600, width: 1040, height: 40,
  }, { fontSize: 19, bold: true, color: C.teal, alignment: "center" });
}

// Slide 8: investigation record and human control
{
  const slide = presentation.slides.add();
  addChrome(slide, "Investigation record", 8, "The system preserves how knowledge and causal explanations changed over time.");

  addText(slide, "The evolving record contains", { left: 70, top: 135, width: 480, height: 40 }, {
    fontSize: 24, bold: true, color: C.navy,
  });
  addBulletList(slide, [
    "Versioned knowledge base for every selected specialist",
    "Source and confidence attached to each fact",
    "Question history, merged wording and contributing agents",
    "Unresolved contradictions and missing documents",
    "Competing causal paths with current status",
    "Human corrections, approvals and overrides",
  ], { left: 80, top: 190, width: 580, height: 330 }, { fontSize: 18, lineHeight: 54 });

  const fact = addBox(slide, "Established facts", { left: 760, top: 150, width: 330, height: 72 }, {
    fill: C.blueLight, line: C.navy, fontSize: 21,
  });
  const paths = addBox(slide, "Competing causal paths", { left: 760, top: 285, width: 330, height: 72 }, {
    fill: C.orangeLight, line: C.orange, fontSize: 21,
  });
  const board = addBox(slide, "Evidence-supported\ncausal board", { left: 760, top: 430, width: 330, height: 94 }, {
    fill: C.greenLight, line: C.green, fontSize: 23,
  });
  connect(slide, fact, paths, { fromSide: "bottom", toSide: "top", color: C.gray });
  connect(slide, paths, board, { fromSide: "bottom", toSide: "top", color: C.gray });

  addText(slide, "Human approval remains the final gate", { left: 700, top: 575, width: 450, height: 44 }, {
    fontSize: 22, bold: true, color: C.teal, alignment: "center" });
}

for (const slide of presentation.slides.items) {
  slide.speakerNotes.textFrame.setText(
    "[Sources]\n- System design developed in the RCA application working session.\n[/Sources]"
  );
}

await fs.mkdir(buildDir, { recursive: true });
await fs.mkdir(outputDir, { recursive: true });

for (let index = 0; index < presentation.slides.items.length; index += 1) {
  const slide = presentation.slides.items[index];
  const png = await presentation.export({ slide, format: "png", scale: 1 });
  await fs.writeFile(
    path.join(buildDir, `preview-${String(index + 1).padStart(2, "0")}.png`),
    new Uint8Array(await png.arrayBuffer()),
  );
  const layout = await slide.export({ format: "layout" });
  await fs.writeFile(
    path.join(buildDir, `layout-${String(index + 1).padStart(2, "0")}.json`),
    await layout.text(),
  );
}

const flowPng = await presentation.export({ slide: presentation.slides.items[1], format: "png", scale: 2 });
await fs.writeFile(FLOW_IMAGE, new Uint8Array(await flowPng.arrayBuffer()));

const candidatePath = path.join(buildDir, "candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);

const requirements = {
  explicitTotalSlideCount: 8,
  requiredNativeTableOwnerSlides: [7],
  requiredNativeChartOwnerSlides: [],
};
const fontPolicy = {
  basis: "design",
  families: ["Aptos", "Aptos Display"],
};

const stagingDir = path.join(workspaceDir, ".codex-finalizer-rca-flow");
await fs.mkdir(stagingDir, { recursive: true });
await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: RUNTIME_PYTHON,
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "7",
  ],
  requiredNativeTableOwnerSlides: [7],
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(stagingDir, "RCA_investigation_system_flow_v4.validation.json"),
});

console.log(FINAL_PPTX);
console.log(FLOW_IMAGE);

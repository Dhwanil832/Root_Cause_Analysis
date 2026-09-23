import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile, fr } from "@oai/artifact-tool";

const SKILL_DIR = "/Users/dhwanilchauhan/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations";
const workspaceDir = "/Users/dhwanilchauhan/Desktop/RCA Try 1/Try 4";
const TMP_DIR = path.join(workspaceDir, ".codex-build/try3-try4-deck");
const FINAL_PPTX = path.join(workspaceDir, "output/presentations/RCA_Try_3_and_Try_4_Comparison_v3.pptx");
const FONT = "Helvetica Neue";
const W = 1280;
const H = 720;

const C = {
  navy: "#10263C",
  slate: "#425466",
  ink: "#17212B",
  muted: "#6B7B8C",
  paper: "#F6F3ED",
  white: "#FFFFFF",
  amber: "#E5A32D",
  amberLight: "#F7E5BE",
  teal: "#168B85",
  tealLight: "#D9EFEC",
  blue: "#3377B5",
  blueLight: "#DCE9F4",
  red: "#C9564D",
  redLight: "#F3DAD7",
  green: "#4F8B62",
  line: "#CCD3D9",
  gray: "#E8ECEF",
};

const p = Presentation.create({ slideSize: { width: W, height: H } });
const { applyPresentationChartFont, finalizePresentation } = await import(
  pathToFileURL(path.join(SKILL_DIR, "container_tools/artifact_tool_utils.mjs")).href,
);

function box(slide, x, y, w, h, fill = C.white, line = "none", radius = false) {
  return slide.shapes.add({
    geometry: radius ? "roundRect" : "rect",
    position: { left: x, top: y, width: w, height: h },
    fill,
    line: { style: "solid", fill: line, width: line === "none" ? 0 : 1 },
  });
}

function text(slide, value, x, y, w, h, opts = {}) {
  const shape = slide.shapes.add({
    geometry: "textbox",
    position: { left: x, top: y, width: w, height: h },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text = value;
  shape.text.style = {
    typeface: FONT,
    fontSize: opts.size ?? 22,
    bold: opts.bold ?? false,
    color: opts.color ?? C.ink,
    alignment: opts.align ?? "left",
    autoFit: "shrinkText",
  };
  return shape;
}

function addHeader(slide, title, subtitle = "") {
  text(slide, title, 64, 36, 1150, 54, { size: 38, bold: true, color: C.navy });
  if (subtitle) text(slide, subtitle, 66, 92, 1120, 34, { size: 19, color: C.muted });
  box(slide, 64, 132, 1152, 3, C.amber);
}

function addFooter(slide, number, source) {
  text(slide, source, 66, 682, 1040, 22, { size: 12, color: C.muted });
  text(slide, String(number).padStart(2, "0"), 1160, 680, 56, 24, { size: 14, bold: true, color: C.slate, align: "right" });
}

function baseSlide(title, subtitle, number, source) {
  const slide = p.slides.add();
  slide.background.fill = C.paper;
  addHeader(slide, title, subtitle);
  addFooter(slide, number, source);
  return slide;
}

function label(slide, value, x, y, w, color = C.amber) {
  box(slide, x, y + 4, 8, 22, color);
  text(slide, value.toUpperCase(), x + 18, y, w - 18, 30, { size: 15, bold: true, color: C.slate });
}

function flowNode(slide, value, x, y, w, h, fill, stroke = C.line, color = C.ink) {
  const node = box(slide, x, y, w, h, fill, stroke, true);
  node.text = value;
  node.text.style = { typeface: FONT, fontSize: 18, bold: true, color, alignment: "center", autoFit: "shrinkText" };
  return node;
}

function connect(slide, a, b, fromSide = "right", toSide = "left", color = C.slate, dashed = false) {
  return slide.shapes.connect(a, b, {
    kind: "elbow",
    fromSide,
    toSide,
    line: { style: dashed ? "dashed" : "solid", fill: color, width: 2 },
    tail: { type: "arrow", width: "med", length: "med" },
  });
}

function scoreRow(slide, y, model, score, strength, gap, accent = C.blue) {
  text(slide, model, 72, y, 205, 34, { size: 23, bold: true, color: C.navy });
  text(slide, String(score), 286, y - 4, 70, 44, { size: 34, bold: true, color: accent, align: "center" });
  box(slide, 370, y + 4, 3, 82, C.line);
  text(slide, strength, 394, y, 380, 78, { size: 18, color: C.ink });
  text(slide, gap, 806, y, 398, 78, { size: 18, color: C.slate });
  box(slide, 72, y + 91, 1132, 1, C.line);
}

// 1. Cover
{
  const s = p.slides.add();
  s.background.fill = C.navy;
  box(s, 0, 0, 20, 720, C.amber);
  text(s, "RCA Fieldwork", 82, 130, 930, 70, { size: 58, bold: true, color: C.white });
  text(s, "What Try 3 tested, what Try 4 changed, and why the investigation remains open", 86, 220, 1010, 108, { size: 31, color: "#D8E3EB" });
  box(s, 86, 364, 240, 4, C.amber);
  text(s, "R3 EXIT CARRIER BEAM CASE", 86, 393, 550, 34, { size: 17, bold: true, color: C.amber });
  text(s, "Model behavior benchmark and causal-analysis review", 86, 435, 690, 38, { size: 22, color: C.white });
  text(s, "September 2026", 86, 634, 300, 26, { size: 15, color: "#9FB2C1" });
  s.speakerNotes.textFrame.setText("Sources: Try 3 benchmark results and Try 4 qwen3.5 evaluation produced in the RCA Fieldwork workspace.");
}

// 2. Evolution overview
{
  const s = baseSlide("Two experiments with different purposes", "Try 3 compared models. Try 4 introduced a stronger, model-independent investigation harness.", 2, "Sources: Try 3 benchmark results; Try 4 evaluation report");
  label(s, "Try 3", 76, 166, 230, C.blue);
  text(s, "Model benchmark", 76, 205, 430, 52, { size: 34, bold: true, color: C.navy });
  text(s, "Ten installed Ollama models received independent R3 incidents and the same evidence framework.", 76, 268, 430, 90, { size: 22, color: C.slate });
  text(s, "Question tested", 76, 385, 180, 26, { size: 16, bold: true, color: C.blue });
  text(s, "Which local model behaves best inside the existing pipeline?", 76, 418, 430, 76, { size: 26, bold: true, color: C.ink });
  box(s, 590, 162, 2, 442, C.line);
  label(s, "Try 4", 658, 166, 230, C.teal);
  text(s, "Model-independent harness", 658, 205, 480, 52, { size: 34, bold: true, color: C.navy });
  text(s, "The architecture can run any supported model. Qwen3.5 supplied the first completed validation run.", 658, 268, 466, 104, { size: 22, color: C.slate });
  text(s, "Question tested", 658, 385, 180, 26, { size: 16, bold: true, color: C.teal });
  text(s, "Does the stronger harness produce a more defensible investigation? Initial test: qwen3.5", 658, 418, 460, 88, { size: 25, bold: true, color: C.ink });
  text(s, "64", 216, 532, 90, 54, { size: 46, bold: true, color: C.blue, align: "center" });
  text(s, "best Try 3 score", 312, 546, 180, 30, { size: 18, color: C.muted });
  text(s, "68", 804, 532, 90, 54, { size: 46, bold: true, color: C.teal, align: "center" });
  text(s, "first Try 4 run: qwen3.5", 900, 546, 235, 30, { size: 18, color: C.muted });
  s.speakerNotes.textFrame.setText("Try 3 score leader: qwen3.5 at 64/100. Try 4 is model-independent. Qwen3.5 was the first and only model evaluated in Try 4 at the time of this deck, scoring 68/100 using the same rubric.");
}

// 3. Try 3 flow
{
  const s = baseSlide("Try 3 investigation flow", "Each model owned a separate incident track and generated its own versioned investigation.", 3, "Source: Try 3 application design and evaluation protocol");
  const n1 = flowNode(s, "Incident description\n+ starter records", 64, 190, 185, 86, C.blueLight);
  const n2 = flowNode(s, "Baseline\nunderstanding", 286, 190, 164, 86, C.white);
  const n3 = flowNode(s, "Tag selection", 487, 190, 150, 86, C.white);
  const n4 = flowNode(s, "Selected\nspecialists", 674, 190, 160, 86, C.white);
  const n5 = flowNode(s, "Question\nbroker", 871, 190, 150, 86, C.white);
  const n6 = flowNode(s, "Answer\nfetchers", 1058, 190, 156, 86, C.amberLight);
  [ [n1,n2], [n2,n3], [n3,n4], [n4,n5], [n5,n6] ].forEach(([a,b]) => connect(s,a,b));
  const n7 = flowNode(s, "Evidence claims", 846, 390, 165, 82, C.white);
  const n8 = flowNode(s, "Causal board", 630, 390, 165, 82, C.white);
  const n9 = flowNode(s, "Verification", 414, 390, 165, 82, C.white);
  const n10 = flowNode(s, "Corrective actions", 170, 390, 190, 82, C.tealLight);
  connect(s,n6,n7,"bottom","right");
  connect(s,n7,n8,"left","right");
  connect(s,n8,n9,"left","right");
  connect(s,n9,n10,"left","right");
  text(s, "Evidence could create a new version inside the same model track", 166, 530, 850, 42, { size: 24, bold: true, color: C.navy, align: "center" });
  text(s, "The benchmark exposed failures in structured output, evidence reconciliation, causal direction, and premature actions.", 176, 582, 830, 54, { size: 19, color: C.slate, align: "center" });
  s.speakerNotes.textFrame.setText("Try 3 architecture summary. The flow is simplified for presentation and preserves the model-track separation described in the evaluation protocol.");
}

// 4. Rubric distribution
{
  const s = baseSlide("The 100-point evaluation rubric", "The scoring framework was defined before interpreting model performance.", 4, "Source: Try 3 R3 Ollama evaluation protocol");
  text(s, "100", 74, 172, 230, 110, { size: 82, bold: true, color: C.navy, align: "center" });
  text(s, "TOTAL POINTS", 74, 278, 230, 32, { size: 17, bold: true, color: C.amber, align: "center" });
  text(s, "Higher weight goes to evidence handling and causal reasoning because a fluent summary alone does not establish root cause.", 72, 348, 250, 150, { size: 22, color: C.slate, align: "center" });
  const chart = s.charts.add("bar", {
    position: { left: 350, top: 156, width: 842, height: 458 },
    categories: ["Causal reasoning", "Questions", "Evidence targeting", "Provenance", "Comprehension", "Tags", "Corrective actions", "Calibration"],
    series: [{ name: "Available points", values: [20, 15, 15, 15, 10, 10, 10, 5], fill: C.blue }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 45 },
    hasLegend: false,
    xAxis: { min: 0, max: 20, majorUnit: 5, textStyle: { fill: C.muted, fontSize: 13 }, majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    yAxis: { textStyle: { fill: C.ink, fontSize: 15 }, line: { style: "solid", fill: C.line, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fill: C.navy, fontSize: 14, bold: true } },
    chartFill: C.paper,
    plotAreaFill: C.paper,
  });
  applyPresentationChartFont(chart, { fontFamily: FONT });
  s.speakerNotes.textFrame.setText("Rubric weights: comprehension 10, tags 10, questions 15, evidence targeting 15, provenance and contradictions 15, causal reasoning 20, corrective actions 10, calibration and trace 5.");
}

// 5. Rubric details
{
  const s = baseSlide("What earns each point allocation", "Scores reflect investigative usefulness, evidence discipline, and causal validity.", 5, "Source: Try 3 R3 Ollama evaluation protocol");
  const rows = [
    ["Dimension", "Points", "What earns credit"],
    ["Incident comprehension", "10", "Correct entities, sequence, context, and explicit unknowns"],
    ["Tag selection", "10", "Relevant specialist routes without treating tags as causes"],
    ["Investigative questions", "15", "High-yield questions that open distinct causal directions"],
    ["Evidence targeting", "15", "Correct drawings, records, observations, and physical evidence"],
    ["Provenance and contradictions", "15", "Source separation, conflict detection, resistance to weak evidence"],
    ["Causal reasoning", "20", "Evidence-linked conditions, barriers, causes, and tested alternatives"],
    ["Corrective actions", "10", "Actions tied to verified conditions with owners and checks"],
    ["Calibration and trace", "5", "Visible limits, confidence, and useful decision records"],
  ];
  const table = s.tables.add({ rows: rows.length, columns: 3, left: 66, top: 156, width: 1148, height: 494, columnTracks: [fr(1.45), fr(0.42), fr(3.13)], values: rows });
  table.borders.assign({ style: "solid", fill: C.line, width: 1 });
  table.cells.block({ row: 0, column: 0, rowCount: 1, columnCount: 3 }).assign({ fill: C.navy, textStyle: { typeface: FONT, color: C.white, fontSize: 17, bold: true }, margins: { left: 10, right: 10, top: 7, bottom: 7 } });
  table.cells.block({ row: 1, column: 0, rowCount: 8, columnCount: 3 }).assign({ fill: C.white, textStyle: { typeface: FONT, color: C.ink, fontSize: 15 }, margins: { left: 10, right: 10, top: 6, bottom: 6 } });
  table.cells.block({ row: 1, column: 1, rowCount: 8, columnCount: 1 }).assign({ fill: C.amberLight, textStyle: { typeface: FONT, color: C.navy, fontSize: 17, bold: true } });
  s.speakerNotes.textFrame.setText("Full rubric wording from evaluation_protocol.md, shortened only for slide fit without changing the scoring meaning.");
}

// 6. Try 3 rankings
{
  const s = baseSlide("Try 3 model performance", "Qwen3.5 led the analytical benchmark. Two models produced no gradeable version within 30 minutes.", 6, "Source: Try 3 benchmark_results.md, September 8, 2026");
  const models = ["qwen3.5", "qwen2.5", "gemma3", "mistral", "llama3.1", "hermes3", "llama3.2", "phi4-mini", "deepseek-r1", "granite3.3"];
  const scores = [64, 38, 31, 29, 27, 18, 17, 13, 0, 0];
  const chart = s.charts.add("bar", {
    position: { left: 82, top: 150, width: 1110, height: 495 },
    categories: models,
    series: [{ name: "Score out of 100", values: scores, fill: C.blue, points: [{ idx: 0, fill: C.teal }, { idx: 8, fill: C.red }, { idx: 9, fill: C.red }] }],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 32 },
    hasLegend: false,
    xAxis: { min: 0, max: 70, majorUnit: 10, textStyle: { fill: C.muted, fontSize: 13 }, majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    yAxis: { textStyle: { fill: C.ink, fontSize: 15 }, line: { style: "solid", fill: C.line, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fill: C.navy, fontSize: 14, bold: true } },
    chartFill: C.paper,
    plotAreaFill: C.paper,
  });
  applyPresentationChartFont(chart, { fontFamily: FONT });
  s.speakerNotes.textFrame.setText("Try 3 scores: qwen3.5 64, qwen2.5 38, gemma3 31, mistral 29, llama3.1 27, hermes3 18, llama3.2 17, phi4-mini-reasoning 13, deepseek-r1 0, granite3.3 0.");
}

// 7. Top model explanations
{
  const s = baseSlide("Why the four highest Try 3 scores landed where they did", "Strengths earned credit. Missing evidence discipline and causal structure capped every score.", 7, "Source: Try 3 benchmark model-by-model findings");
  text(s, "MODEL", 72, 151, 200, 24, { size: 13, bold: true, color: C.muted });
  text(s, "SCORE", 286, 151, 70, 24, { size: 13, bold: true, color: C.muted, align: "center" });
  text(s, "WHAT WORKED", 394, 151, 340, 24, { size: 13, bold: true, color: C.muted });
  text(s, "WHY THE SCORE STOPPED", 806, 151, 360, 24, { size: 13, bold: true, color: C.muted });
  scoreRow(s, 188, "qwen3.5", 64, "Best questions and evidence requests. It framed the changed outage configuration correctly.", "Evidence processing failed. The board had one event node and no causal edges.", C.teal);
  scoreRow(s, 294, "qwen2.5", 38, "Useful tags and questions about restraint, turnover, and isolation boundaries.", "Six stage errors, repeated questions, missed conflicts, and reverse causal arrows.", C.blue);
  scoreRow(s, 400, "gemma3", 31, "Sound focal-event summary and useful requests for drawings and isolation records.", "Wrong rail and electrical tags, unsupported assertions, and failed causal analysis.", C.blue);
  scoreRow(s, 506, "mistral", 29, "Recognized gravity energy, planning, and communication context.", "Weak evidence targeting and only a shallow causal board. No planted conflict was found.", C.blue);
  s.speakerNotes.textFrame.setText("Explanations summarize the detailed findings in Try 3 benchmark_results.md.");
}

// 8. Remaining model explanations
{
  const s = baseSlide("Why the remaining Try 3 models scored below 30", "Completion alone did not earn a strong score when the investigation remained shallow or unreliable.", 8, "Source: Try 3 benchmark model-by-model findings");
  const items = [
    ["llama3.1", "27", "Clean structured-output run", "Only one tag and a shallow evidence-to-cause path"],
    ["hermes3", "18", "Produced a small causal graph", "Weak tag selection and little provenance discipline"],
    ["llama3.2", "17", "Completed two versions", "Low-value questions and weak causal development"],
    ["phi4-mini", "13", "Generated substantial text", "Nineteen stage errors and extensive fallback content"],
    ["deepseek-r1", "0", "No gradeable artifact", "Exceeded the 30-minute limit before committing a version"],
    ["granite3.3", "0", "No gradeable artifact", "Exceeded the 30-minute limit before committing a version"],
  ];
  text(s, "MODEL / SCORE", 72, 158, 240, 24, { size: 13, bold: true, color: C.muted });
  text(s, "CREDIT EARNED", 342, 158, 300, 24, { size: 13, bold: true, color: C.muted });
  text(s, "PRIMARY LIMIT", 710, 158, 450, 24, { size: 13, bold: true, color: C.muted });
  items.forEach((item, i) => {
    const y = 194 + i * 72;
    text(s, `${item[0]}   ${item[1]}`, 72, y, 246, 42, { size: 22, bold: true, color: Number(item[1]) === 0 ? C.red : C.navy });
    text(s, item[2], 342, y, 322, 48, { size: 18, color: C.ink });
    text(s, item[3], 710, y, 480, 48, { size: 18, color: C.slate });
    box(s, 72, y + 58, 1118, 1, C.line);
  });
  s.speakerNotes.textFrame.setText("Try 3 lower-ranked model findings. Zero scores reflect the absence of a committed artifact, not a claim that the models have no general capability.");
}

// 9. Try 3 system limitations
{
  const s = baseSlide("Try 3 exposed system failures as well as model failures", "Several weaknesses appeared across models, which means prompt quality alone could not solve them.", 9, "Source: Try 3 benchmark cross-model findings");
  const left = [
    ["Structured output", "Long JSON responses failed or truncated."],
    ["Evidence scope", "Large packets behaved like one source instead of separate records."],
    ["Question control", "Overlap survived and low-value questions consumed runtime."],
  ];
  const right = [
    ["Causal direction", "Some boards pointed from the event back to pre-event conditions."],
    ["Contradictions", "Every scored Try 3 output missed the three planted challenge records."],
    ["Corrective actions", "Some models proposed actions before verifying the causal mechanism."],
  ];
  [left, right].forEach((group, col) => group.forEach((item, i) => {
    const x = col === 0 ? 78 : 654;
    const y = 176 + i * 148;
    text(s, String(i + 1 + col * 3).padStart(2, "0"), x, y, 54, 38, { size: 28, bold: true, color: col === 0 ? C.blue : C.red });
    text(s, item[0], x + 70, y, 430, 34, { size: 25, bold: true, color: C.navy });
    text(s, item[1], x + 70, y + 44, 445, 72, { size: 20, color: C.slate });
    box(s, x + 70, y + 122, 445, 1, C.line);
  }));
  s.speakerNotes.textFrame.setText("Cross-model findings from Try 3: no scored output detected the seeded conflicts, several stages failed structured validation, and multiple boards contained weak or reversed causal links.");
}

// 10. Try 4 changes
{
  const s = baseSlide("Try 4 design changes apply to every supported model", "The initial validation used qwen3.5 alone so the effect of the harness changes remained observable.", 10, "Source: Try 4 implementation and initial qwen3.5 evaluation");
  text(s, "TRY 3", 78, 154, 250, 34, { size: 18, bold: true, color: C.blue });
  text(s, "TRY 4", 700, 154, 250, 34, { size: 18, bold: true, color: C.teal });
  const changes = [
    ["Documents supplied as broad packets", "Evidence split into individually identified segments"],
    ["Prompt asked for source discipline", "Dedicated source adjudication before specialists"],
    ["Broker mainly removed duplicates", "Questions need a causal branch and decision unlocked"],
    ["Causal links could remain weak", "Every link needs support, a counterfactual, an alternative, and a gap"],
    ["Actions could appear early", "Actions require a verified causal target"],
    ["Final output carried most audit detail", "Every stage persists a visible checkpoint"],
  ];
  changes.forEach((pair, i) => {
    const y = 198 + i * 72;
    text(s, pair[0], 78, y, 446, 48, { size: 19, color: C.slate });
    box(s, 570, y + 8, 22, 4, C.amber);
    text(s, pair[1], 700, y, 470, 48, { size: 19, bold: true, color: C.navy });
    box(s, 78, y + 58, 1092, 1, C.line);
  });
  s.speakerNotes.textFrame.setText("Try 4 changes implemented in the duplicated application. The harness is model-independent and can run supported Ollama or API models. No model combination or model fallback was used in the first scored qwen3.5 run.");
}

// 11. What is new in Try 4
{
  const s = baseSlide("What is new in Try 4", "One reusable investigation harness now adds evidence discipline, causal tests, and explicit decision gates around the selected model.", 11, "Source: Try 4 implementation design");

  text(s, "SUPPORTED MODEL", 70, 158, 190, 24, { size: 14, bold: true, color: C.muted });
  const m1 = flowNode(s, "Ollama model", 70, 195, 168, 62, C.blueLight, C.blue);
  const m2 = flowNode(s, "API model", 70, 279, 168, 62, C.blueLight, C.blue);
  text(s, "Qwen3.5 was the first test,\nnot a fixed dependency", 70, 373, 182, 78, { size: 18, bold: true, color: C.navy, align: "center" });

  const entry = flowNode(s, "Same Try 4 harness", 322, 237, 194, 78, C.tealLight, C.teal);
  connect(s, m1, entry, "right", "left", C.blue);
  connect(s, m2, entry, "right", "left", C.blue);

  const evidence = flowNode(s, "Evidence layer\nIndividual records\nSource adjudication", 594, 166, 208, 112, C.amberLight, C.amber);
  const reasoning = flowNode(s, "Reasoning layer\nQuestion value gate\nCausal-link tests", 594, 310, 208, 112, C.white, C.slate);
  const control = flowNode(s, "Control layer\nStage checkpoints\nAction verification", 594, 454, 208, 112, C.redLight, C.red);
  connect(s, entry, evidence, "right", "left", C.amber);
  connect(s, entry, reasoning, "right", "left", C.slate);
  connect(s, entry, control, "right", "left", C.red);

  const outcome = flowNode(s, "Traceable investigation\nwith supported, disputed,\nand missing evidence visible", 902, 280, 280, 140, C.tealLight, C.teal);
  connect(s, evidence, outcome, "right", "left", C.teal);
  connect(s, reasoning, outcome, "right", "left", C.teal);
  connect(s, control, outcome, "right", "left", C.teal);

  text(s, "The harness changes stay constant when the model changes", 320, 607, 870, 36, { size: 26, bold: true, color: C.navy, align: "center" });
  s.speakerNotes.textFrame.setText("Try 4 is not a qwen-specific application. Any supported Ollama or API model can enter the same evidence, reasoning, and control layers. Qwen3.5 was the first model evaluated after the Try 4 improvements.");
}

// 12. Try 4 flow
{
  const s = baseSlide("First Try 4 validation run: qwen3.5", "This initial run completed every reasoning stage and blocked corrective actions at the final gate.", 12, "Source: Try 4 stage checkpoints for incident e1325fa4-6198-4d26-a5eb-ae8d4a930ef8");
  const xs = [70, 250, 430, 610, 790, 970];
  const row1 = ["Understand", "Structure", "Tag", "Adjudicate\nsources", "Five\nspecialists", "Broker"];
  const nodes1 = row1.map((v,i) => flowNode(s,v,xs[i],184,142,72,i===3?C.amberLight:C.tealLight,C.teal));
  for (let i=0;i<nodes1.length-1;i++) connect(s,nodes1[i],nodes1[i+1],"right","left",C.teal);
  const row2 = ["11 answer\nfetches", "54 evidence\nclaims", "13 causal\nnodes", "7 causal\nlinks", "Verify", "Actions\nblocked"];
  const nodes2 = row2.map((v,i) => flowNode(s,v,xs[5-i],390,142,72,i===0?C.amberLight:(i===5?C.redLight:C.white),i===5?C.red:C.line));
  connect(s,nodes1[5],nodes2[0],"bottom","top",C.teal);
  for (let i=0;i<nodes2.length-1;i++) connect(s,nodes2[i],nodes2[i+1],"left","right",i===4?C.red:C.slate);
  text(s, "15", 176, 535, 80, 50, { size: 42, bold: true, color: C.teal, align: "center" });
  text(s, "successful checkpoints", 265, 546, 220, 28, { size: 18, color: C.slate });
  text(s, "0", 566, 535, 80, 50, { size: 42, bold: true, color: C.teal, align: "center" });
  text(s, "failed stages", 656, 546, 160, 28, { size: 18, color: C.slate });
  text(s, "23 min", 908, 535, 130, 50, { size: 36, bold: true, color: C.navy, align: "center" });
  text(s, "runtime", 1044, 546, 100, 28, { size: 18, color: C.slate });
  s.speakerNotes.textFrame.setText("The scored Try 4 run had 15 completed checkpoints, no failed reasoning stages, and one blocked corrective-action stage. Runtime was approximately 23 minutes.");
}

// 13. Qwen dimension comparison
{
  const s = baseSlide("Qwen3.5 improved most in causal reasoning", "The first Try 4 validation gained evidence and causal discipline but lost action points because the verifier blocked premature actions.", 13, "Sources: Try 3 qwen score 64; Try 4 qwen score 68");
  const cats = ["Comprehension", "Tags", "Questions", "Evidence targeting", "Provenance", "Causal reasoning", "Corrective actions", "Calibration"];
  const chart = s.charts.add("bar", {
    position: { left: 70, top: 154, width: 905, height: 484 },
    categories: cats,
    series: [
      { name: "Try 3", values: [9,8,13,13,4,6,7,4], fill: C.blue },
      { name: "Try 4", values: [9,9,13,14,6,12,0,5], fill: C.teal },
    ],
    barOptions: { direction: "bar", grouping: "clustered", gapWidth: 50 },
    hasLegend: true,
    legend: { position: "bottom", overlay: false, textStyle: { fill: C.ink, fontSize: 14 } },
    xAxis: { min: 0, max: 20, majorUnit: 5, textStyle: { fill: C.muted, fontSize: 12 }, majorGridlines: { style: "solid", fill: C.line, width: 1 } },
    yAxis: { textStyle: { fill: C.ink, fontSize: 14 }, line: { style: "solid", fill: C.line, width: 1 } },
    dataLabels: { showValue: true, position: "outEnd", textStyle: { fill: C.navy, fontSize: 12, bold: true } },
    chartFill: C.paper,
    plotAreaFill: C.paper,
  });
  applyPresentationChartFont(chart, { fontFamily: FONT });
  text(s, "64", 1010, 214, 150, 70, { size: 56, bold: true, color: C.blue, align: "center" });
  text(s, "TRY 3", 1010, 282, 150, 26, { size: 16, bold: true, color: C.muted, align: "center" });
  box(s, 1028, 332, 114, 2, C.line);
  text(s, "68", 1010, 368, 150, 70, { size: 56, bold: true, color: C.teal, align: "center" });
  text(s, "TRY 4", 1010, 436, 150, 26, { size: 16, bold: true, color: C.muted, align: "center" });
  text(s, "Safer restraint lowered the action score while improving the investigation's integrity.", 995, 508, 185, 90, { size: 18, color: C.slate, align: "center" });
  s.speakerNotes.textFrame.setText("Dimension scores. Try 3 qwen: 9, 8, 13, 13, 4, 6, 7, 4. Try 4 qwen: 9, 9, 13, 14, 6, 12, 0, 5. Totals are 64 and 68.");
}

// 14. Causal board result
{
  const s = baseSlide("The first Try 4 run produced a developing causal board", "Qwen3.5 proposed forward hypotheses. Verification kept the board at initial maturity.", 14, "Source: Try 4 qwen causal board and verification findings");
  const a = flowNode(s, "Balance left raised\nwith rolls removed", 62, 190, 202, 76, C.blueLight, C.blue);
  const b = flowNode(s, "B hydraulics\nisolated and bled", 62, 314, 202, 76, C.blueLight, C.blue);
  const c = flowNode(s, "Gravity-control field blank\nNo independent signature", 62, 438, 202, 86, C.amberLight, C.amber);
  const d = flowNode(s, "Suspected loss of positive\nmechanical restraint", 390, 280, 244, 94, C.amberLight, C.amber);
  const e = flowNode(s, "Carrier beam falls\ninto R3 mill pit", 758, 280, 224, 94, C.redLight, C.red);
  connect(s,a,d,"right","left",C.slate,true);
  connect(s,b,d,"right","left",C.slate,true);
  connect(s,c,d,"right","left",C.slate,true);
  connect(s,d,e,"right","left",C.red,true);
  text(s, "Six blocking findings", 1010, 180, 190, 34, { size: 21, bold: true, color: C.red });
  text(s, "Keeper function\n\nRequired restraint design\n\nTemporary supports\n\nPre-event configuration\n\nAnonymous note provenance\n\nR3 versus other stands", 1010, 228, 198, 302, { size: 18, color: C.slate });
  box(s, 390, 420, 592, 2, C.line);
  text(s, "Every displayed connection remains a hypothesis until the missing design and execution evidence discriminates it from alternatives.", 390, 446, 592, 100, { size: 22, bold: true, color: C.navy, align: "center" });
  text(s, "Corrective actions stayed blocked", 438, 578, 495, 40, { size: 26, bold: true, color: C.red, align: "center" });
  s.speakerNotes.textFrame.setText("Simplified rendering of the Try 4 qwen causal board. The actual board contains 13 nodes and 7 links. None were verified. Six blocking findings remained.");
}

// 15. Why the RCA remains open
{
  const s = baseSlide("The current test cannot establish a final root cause", "The method can find good questions and hypotheses, but the evidence package cannot prove the physical mechanism.", 15, "Sources: Try 4 qwen verification findings and post-run evaluation");
  label(s, "What the package establishes", 76, 168, 470, C.teal);
  text(s, "The beam fell with the keeper present.\n\nThe rolls had been removed.\n\nThe balance remained raised.\n\nB hydraulics had been isolated and bled.\n\nThe gravity-control record had gaps.", 82, 218, 460, 318, { size: 23, color: C.ink });
  box(s, 590, 166, 2, 448, C.line);
  label(s, "What the package does not prove", 654, 168, 490, C.red);
  text(s, "The keeper's load-bearing function.\n\nThe required support or stopper arrangement.\n\nWhether supports were installed, removed, or failed.\n\nThe exact release mechanism.\n\nWhich procedural gap caused the physical failure.", 660, 218, 500, 318, { size: 23, color: C.ink });
  text(s, "The test mixes model limitations with missing ground truth", 228, 580, 824, 48, { size: 30, bold: true, color: C.navy, align: "center" });
  s.speakerNotes.textFrame.setText("The current synthetic package contains useful records but lacks authoritative design and execution evidence required to verify the beam-release mechanism.");
}

// 16. Partner RCA next step
{
  const s = baseSlide("A partner RCA can create a valid ground-truth test", "The completed RCA provides the answer key. Its underlying evidence provides the fair model input.", 16, "Recommended validation design based on the current benchmark limitation");
  const n1 = flowNode(s, "Partner's completed RCA", 70, 202, 220, 82, C.amberLight, C.amber);
  const n2 = flowNode(s, "Identify accepted sequence,\nmechanism, barriers, and causes", 370, 202, 250, 82, C.white);
  const n3 = flowNode(s, "Assemble only the records\nused to reach those findings", 700, 202, 250, 82, C.white);
  const n4 = flowNode(s, "Run blind model tests", 1030, 202, 180, 82, C.tealLight, C.teal);
  connect(s,n1,n2);
  connect(s,n2,n3);
  connect(s,n3,n4);
  box(s, 160, 380, 960, 2, C.line);
  text(s, "Fair test", 170, 416, 200, 34, { size: 24, bold: true, color: C.teal });
  text(s, "Models receive the underlying documents without the completed RCA.", 170, 462, 360, 78, { size: 21, color: C.slate });
  text(s, "Ground truth", 580, 416, 200, 34, { size: 24, bold: true, color: C.amber });
  text(s, "Reviewers compare each model's causal chain with the partner's accepted findings.", 580, 462, 370, 78, { size: 21, color: C.slate });
  text(s, "What improves", 970, 416, 210, 34, { size: 24, bold: true, color: C.blue });
  text(s, "The test can separate missing data from failures in the method or model.", 970, 462, 220, 78, { size: 21, color: C.slate });
  text(s, "Best next input: the partner RCA plus every source record it relied on", 204, 592, 872, 42, { size: 28, bold: true, color: C.navy, align: "center" });
  s.speakerNotes.textFrame.setText("Recommended next validation step. Do not give the completed RCA to the model during the blind test. Use it as the scoring reference and supply the underlying evidence records as model inputs.");
}

await fs.mkdir(TMP_DIR, { recursive: true });
await fs.mkdir(path.dirname(FINAL_PPTX), { recursive: true });
const candidatePath = path.join(TMP_DIR, "candidate.pptx");
await (await PresentationFile.exportPptx(p)).save(candidatePath);

const montage = await p.export({ format: "png", montage: true, scale: 0.5 });
await fs.writeFile(path.join(TMP_DIR, "montage.png"), new Uint8Array(await montage.arrayBuffer()));
for (let i = 0; i < p.slides.length; i += 1) {
  const preview = await p.export({ slide: p.slides.getItemAt(i), format: "png", scale: 1 });
  await fs.writeFile(path.join(TMP_DIR, `slide-${String(i + 1).padStart(2, "0")}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const requirements = {
  explicitTotalSlideCount: 16,
  requiredNativeTableOwnerSlides: [5],
  requiredNativeChartOwnerSlides: [4, 6, 13],
  materializeLiteralChartWorkbooks: true,
};
const fontPolicy = { basis: "design", families: [FONT] };
await finalizePresentation({
  ...requirements,
  workspaceDir,
  candidatePath,
  finalPath: FINAL_PPTX,
  pythonExecutable: "/Users/dhwanilchauhan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
  integrityValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(SKILL_DIR, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: [
    "--expected-slide-size-emu", "12192000,6858000",
    "--validate-bullet-geometry",
    "--validate-heading-fit",
    "--require-native-table-slide", "5",
  ],
  requiredNativeTableOwnerSlides: [5],
  requiredNativeChartOwnerSlides: [4, 6, 13],
  materializeLiteralChartWorkbooks: true,
  fontPolicy,
  verifyArtifactToolImport: true,
  receiptPath: path.join(TMP_DIR, "RCA_Try_3_and_Try_4_Comparison_v3.validation.json"),
});

console.log(FINAL_PPTX);

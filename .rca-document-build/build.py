from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from pathlib import Path
root=Path('/Users/dhwanilchauhan/Desktop/RCA Try 1')
doc=Document();sec=doc.sections[0];sec.top_margin=Inches(.65);sec.bottom_margin=Inches(.65);sec.left_margin=Inches(.75);sec.right_margin=Inches(.75)
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
for name in ['Normal','Title','Subtitle','Heading 1','Heading 2','List Bullet']:
 st=doc.styles[name];st.font.name='Arial';st.font.color.rgb=RGBColor(0,0,0)
 st.paragraph_format.space_after=Pt(7)
doc.styles['Normal'].font.size=Pt(11);doc.styles['Normal'].paragraph_format.line_spacing=1.08
doc.styles['Title'].font.size=Pt(24);doc.styles['Heading 1'].font.size=Pt(17);doc.styles['Heading 2'].font.size=Pt(12)
for name in ['Heading 1','Heading 2']:
 doc.styles[name].paragraph_format.space_before=Pt(11);doc.styles[name].paragraph_format.keep_with_next=True
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
run=footer.add_run();fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');run._r.addnext(fld)
footer.style='Normal';footer.paragraph_format.space_after=Pt(0)
def p(t):doc.add_paragraph(t)
def h(t,l=1):doc.add_heading(t,l)
def bullet(label,body):
 q=doc.add_paragraph(style='List Bullet');q.add_run(label+' ').bold=True;q.add_run(body)
def page():doc.add_page_break()
def table(headers,rows,widths):
 t=doc.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
 for cell,w in zip(t.columns,widths):cell.width=Inches(w)
 for i,v in enumerate(headers):t.rows[0].cells[i].text=v
 for row in rows:
  cells=t.add_row().cells
  for i,v in enumerate(row):cells[i].text=str(v)
 for ri,row in enumerate(t.rows):
  for ci,c in enumerate(row.cells):
   c.width=Inches(widths[ci]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   pr=c._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
   for edge in ['top','left','bottom','right']:
    e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');b.append(e)
   pr.append(b);m=OxmlElement('w:tcMar')
   for edge in ['top','bottom','left','right']:
    e=OxmlElement('w:'+edge);e.set(qn('w:w'),'95');e.set(qn('w:type'),'dxa');m.append(e)
   pr.append(m)
   if ri==0:
    sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E8EDF0');pr.append(sh)
   for q in c.paragraphs:
    q.paragraph_format.space_after=Pt(2);q.paragraph_format.line_spacing=1.03
    for r in q.runs:r.font.size=Pt(10);r.bold=ri==0
    if ci>0 and len(headers)==3:q.alignment=WD_ALIGN_PARAGRAPH.CENTER
  trpr=row._tr.get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
 t.rows[0]._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
 doc.add_paragraph().paragraph_format.space_after=Pt(0)

# Page 1
h('Standalone RCA progress since July 2026',0)
p('Project 19  |  Progress through 22 September 2026')
p('Since the July presentation, we have developed the standalone root cause analysis system into an iterative investigation prototype, run Qwen development experiments, diagnosed failures in both execution and reasoning, and implemented changes to evidence handling and revision. We have also prepared two staged evidence packages for the next controlled evaluation.')
p('The main progress is a working, inspectable investigation process and a clearer way to test it. We have not yet demonstrated reliable autonomous RCA or a controlled improvement in causal accuracy. This report summarizes the work so it can be used to prepare the next project presentation.')
h('Where we were in July')
p('The July presentation described an RCA pipeline starting from sparse incident records. It organized the investigation around a neutral narrative, entity identification, document requests, a timeline, candidate causes, pruning, and corrective actions. A facilitator review step kept a person involved before finalization. The presentation also showed an early RCA interface and causal map.')
p('The limitations identified in July were unreliable expert knowledge, limited context retention, and attempts to perform RCA in one pass. The stated next steps were validation against actual incident RCA and testing open-source model viability. The work since then has concentrated on those problems. [1]')
h('Main work completed')
bullet('Iterative investigation prototype.', 'Built workflows that preserve the current explanation, source references, open questions and successive investigation versions.')
bullet('Model experiments.', 'Ran Qwen on development incidents, including the R3 beam case and the instrument-air interruption case, and retained outputs for review.')
bullet('System diagnosis and redesign.', 'Traced failures to evidence delivery, growing model context, question handling and incomplete application of corrections, alongside errors in model interpretation.')
bullet('Implementation and test infrastructure.', 'Added more explicit evidence, answer-delivery, revision and review records, with exportable experiment traces.')
bullet('Staged evaluation material.', 'Prepared two historically anchored synthetic investigation packages with three cumulative evidence releases. [2–5]')

# Process evolution
page();h('How the RCA process has changed')
p('The July proposal described a largely sequential pipeline. The current prototype organizes the work around a provisional explanation of the incident, targeted evidence questions, separate review judgments and saved revisions. It can publish an incomplete investigation and continue when more evidence becomes available. [1, 4, 8]')
h('The process described in the proposal',2)
p('Neutral incident narration → entity inventory → document set for each entity → source-bound timeline → candidate-cause and link analysis → pruning → facilitator review → corrective actions and verification.')
p('The entity inventory distinguished named entities from expected entities within the bounded harm pathway. Candidate causes were tested against evidence, systemic causes and recurrence. A facilitator could edit or upload the causal chart before action planning. [1]')
h('The current process',2)
p('Read available evidence → frame competing explanations → consult specialists on specific gaps → resolve questions and deliver answers → consolidate the explanation → review facts, roles and links → apply corrections and review again → publish a version with open requests → continue when new evidence arrives.')
table(['Aspect','Change from the proposal'],[
 ['Investigation structure','From a sequence of document and analysis phases to an explanation-led cycle that can retain alternatives and open questions.'],
 ['Use of specialists','Consultations address named uncertainties in an explanation; specialist output feeds back into the shared investigation.'],
 ['Evidence requests','Questions preserve their purpose, answer coverage and intended recipients. An answer must reach the owners who need it.'],
 ['Review','Factual support, causal role and the validity of a connection are assessed separately.'],
 ['New information','New evidence can revise statements, assumptions and connections in a later saved version, while preserving earlier versions.'],
 ['Completion and actions','A published version can remain partial. Action generation is gated by accepted, supported causal findings; publishing alone does not establish a root cause.']], [1.5,5.5])
p('The main change is that the system is expected to explain what the evidence currently supports, identify what would distinguish alternatives, and revise that position. Missing records identify an evidence gap; they do not by themselves prove a physical failure or root cause.')

# Current process, first half
page();h('Current RCA process: evidence to explanation')
p('The sequence below follows the current Try 7 investigation planner. It describes implemented workflow behavior, not a claim that every model run performs these judgments correctly. [4, 8]')
h('1. Receive and read the available evidence',2)
p('The investigation begins with the incident description and available records. Default references, incident starter records and later answer attachments have distinct scopes. The reader extracts findings tied to original source passages. New versions read material not already processed. If a prerequisite source cannot be read, the planner can pause rather than silently continue without it.')
h('2. Frame the incident and competing explanations',2)
p('Causal analysis considers the evidence collectively, identifies the focal event, selects relevant observations and proposes explanations of how it could have occurred. Explanations carry assumptions, required conditions and gaps. Initial board connections are proposals to review, not established causes. The framing also identifies evidence that would help distinguish the alternatives.')
h('3. Consult specialists on named gaps',2)
p('Relevant specialists receive a defined investigation purpose, such as interpreting equipment behavior or understanding an isolation arrangement. They contribute findings, challenge assumptions and ask focused questions. Consultations are tied to current explanation branches rather than an unrestricted exchange among specialists. Causal analysis and reviewers can also generate questions.')
h('4. Resolve questions and deliver the answers',2)
p('Question handling combines compatible requests while retaining their owners and purposes. Answer fetching uses the evidence available to that investigation track. Answers carry source references and can be complete, partial, conflicting or unavailable. Coverage is tracked by question subpart, and delivery records show whether the relevant owner has received the current answer revision.')
p('When available material does not answer a question, the request remains visible for later evidence or user input. Repeating the same document through several specialists does not provide independent corroboration.')
h('5. Consolidate the investigative position',2)
p('Causal analysis brings together the specialist findings and retrieved answers. It updates the selected observations, working explanations and proposed connections, retaining alternatives where the evidence does not distinguish them. The result is a current investigation position that is ready for review, rather than a final accepted RCA.')
h('What passes between these stages',2)
p('The working records include source passages, findings, explanation branches, questions, answer coverage, delivery receipts and a causal board. These records make it possible to inspect why a statement was proposed and whether later evidence actually reached the reasoning process.')

# Current process, second half
page();h('Current RCA process: review and revision')
h('6. Review facts, causal roles and connections separately',2)
p('Claim review checks whether the original evidence supports each selected statement. Role review asks whether a supported statement has the proposed function in the explanation. Connection review asks whether the evidence justifies the relationship between statements. A compressor running indication, for example, may be factual without establishing a protective barrier. Unresolved premises leave a connection provisional. [8]')
h('7. Apply feedback and validate the revised position',2)
p('Reviewer questions use the same answer path as earlier requests. A focused revision task addresses consequential evidence, unsupported premises, invalid roles and connection problems. Revisions retain source references and record history. The planner then delivers pending answers, updates connections and repeats the necessary fact, role and link checks. A proposed correction is not automatically accepted.')
h('8. Publish V1 with its limitations and open requests',2)
p('The saved version contains the current board, explanation and concrete evidence requests. Unresolved questions become requests awaiting user input. The position may remain partial or have no supported causal links. Evidence uncertainty, rejected model output and execution problems must remain distinguishable; task completion is not proof of a correct RCA.')
h('9. Continue as V2, V3 and later versions',2)
p('Later documents or answers trigger another evidence and revision cycle. The system should identify which explanations and premises are affected, correct or withdraw obsolete claims and preserve earlier versions for comparison. For example, a newly supplied valve-lineup record should be assessed against the competing explanations of an air interruption, not merely added as another node. Our Try 6 review showed that this expected revision did not happen reliably, motivating the Try 7 changes. [6]')
h('10. Gate corrective-action work on reviewed findings',2)
p('The current planner schedules corrective-action work only for selected findings that are supported, have a valid causal role, have been accepted by a human and participate in a supported non-temporal causal connection. This is a software gate for action proposals. It does not demonstrate that plant actions have been implemented or that their effectiveness has been verified. [8]')
h('How the application reached this workflow',2)
p('Try 4 explored specialist-led boards but exposed context growth and excessive link work. Try 5 added durable tasks and local recovery. Try 6 established an early investigation position and partial V1/V2 outputs, while revealing failures to revise explanations. Try 7 added clearer question coverage, answer delivery, sourced revisions and separate review judgments. [2, 4]')
p('Try 4–7 are application generations; V1–V3 are saved investigation versions. Development configurations changed between runs, so they do not establish a controlled ranking of application generations. Full Try 7 acceptance and comparative model validation remain incomplete.')

# Page 3
page();h('What the experiments showed')
h('Instrument air investigation with Try 6',2)
p('We preserved two partial Qwen investigations for IA-16036, an instrument-air interruption during maintenance preparation. V2 received routing and valve records plus one released answer. The comparison showed more observations and a larger board, but no verified causal connections. [6]')
table(['Recorded measure','V1','V2'],[
 ['Uploaded documents excluding the incident description','10','12'],['Released answers','0','1'],['Board nodes including the focal event','5','9'],['Active connections','4','6'],['Verified connections','0','0'],['Published status','Partial','Partial']], [4.6,1.2,1.2])
p('The important finding was not that V1 remained incomplete. The available records already supported facts that the system sometimes misrepresented, and later evidence did not consistently narrow its explanations.')
bullet('Chronology.', 'The board retained opposing “preceded” connections between pressure loss and recovery, even though recovery should follow the interruption.')
bullet('Factual correction.', 'A pressure timestamp error remained in the investigation. Review feedback did not reliably propagate into the wording of the current board.')
bullet('Causal interpretation.', 'The model treated a compressor running indication as a possible barrier without establishing a protective function.')
bullet('Evidence use.', 'Some requests still asked for information already supplied, while new routing and valve observations did not produce the expected mechanism revision.')
h('Latest Try 7 live Qwen smoke run',2)
p('The unscored pneumatic-carriage smoke run reached a preserved partial V1 on 20 September. It completed 21 scheduled tasks and published five selected observations plus the focal event, with zero causal links. The snapshot retained 20 rejected output items and one pending answer-delivery receipt.')
p('The run exposed additional question-identity, assignment and revision-handling defects. We implemented fixes and regression checks. However, configuration changes and a recorded checkpoint repair occurred during the run, and the post-run fixes still require a fresh run with a frozen configuration. Its assessment remains execution-inconclusive, not an RCA performance score. [4]')

# Page 4
page();h('Changes made after reviewing the runs')
p('The reviews showed that the application must reliably preserve, deliver and update evidence before a result can fairly assess model reasoning. We retained the investigation workflow and changed how its records and judgments move through the system. The Try 7 implementation receipt documents the following work. [3, 4]')
bullet('Preserved baselines and isolated development.', 'Created Try 7 with separate local storage and execution identity. The implementation record reports unchanged fingerprints for 268 baseline source, prompt, configuration and test files in Try 6.')
bullet('More explicit explanations.', 'Extended explanation records with assumptions, required conditions, alternatives and observations that could distinguish them. This makes an explanation easier to inspect and challenge.')
bullet('Question coverage and delivery.', 'Tracked answers by subpart, retained different subscriber purposes, and recorded delivery to relevant specialists and explanations. Reviewer-generated questions gained a visible answer path.')
bullet('Applied revisions.', 'Added a focused revision stage with source references, expected record revisions and retained history. A correction must pass review; proposing it does not make it supported.')
bullet('Separate review judgments.', 'Separated factual support, causal-role validity and connection validity. Added structural checks for issues such as inconsistent temporal direction and stale premises.')
bullet('Controlled releases and exports.', 'Added release receipts tied to a model track and parent version, along with experiment exports containing saved inputs, outputs, snapshots, task records and usage. These exports are unscored records.')
bullet('Clearer execution status.', 'Kept provider failures, application limitations and evidence uncertainty distinguishable. A completed software workflow does not automatically establish a correct root cause.')
h('Recorded software verification')
p('The implementation receipt reports 97 deterministic checks: 20 engine tests, 24 Try 7 tests, 37 regression tests and 16 capacity tests. TypeScript and application build checks also passed. Browser and HTTP checks exercised the local interface and export routes.')
p('These results support the implemented software contracts. They do not establish industrial RCA accuracy, remove every possible application defect, or replace a controlled live-model pilot. The smoke run found issues that scripted checks had missed, which is why the next frozen-configuration run remains necessary.')
h('What we learned')
p('Larger context limits, additional model calls and larger causal boards did not reliably solve the investigation problem. The system needs the right original evidence for each judgment, explicit uncertainty, and a revision path that changes the saved explanation when a correction is accepted. Execution reliability and causal quality must be evaluated separately.')

# Page 5
page();h('Evidence packages and the next milestone')
p('Historical incident rows anchor the event but often omit the records needed to justify a detailed causal reconstruction. We prepared two staged, historically anchored synthetic investigation packages on 22 September. They are constructed test material, not recovered company records. [5]')
bullet('R3 carrier-beam fall.', 'The package includes staged evidence for a beam-fall scenario. Its load-path and circuit reconstruction requires independent technical review before mechanical conclusions support scored claims.')
bullet('Instrument-air interruption.', 'The package combines configuration, pressure observations and operating chronology across separate records. It is prepared for a pilot, but has not received independent expert validation.')
p('Both packages use three cumulative releases. B0 provides the initial account and starter evidence for V1. B1 supplies information intended to distinguish explanations for V2. B2 adds deeper context or corrective evidence for V3. Private scenario records and expected changes are separated from investigator-facing material. These packages derive from previously used development incidents, so they are not independent held-out test cases. The package record reports no completed RCA runs on these new packages.')
h('Next steps')
p('The next milestone is one reproducible V1–V3 investigation. We need to freeze the model, prompts and evidence schedule, preserve each version, and inspect whether new evidence changes the explanation for justified reasons. A simpler baseline should receive the same evidence for comparison. Assessment should cover factual fidelity, supported causal mechanisms, uncertainty, useful questions and revision quality, with execution failures and resource use reported separately. Technical review should assess scenario realism and causal interpretation before broader evaluation. [7]')
h('Project summary')
p('Since July, we have built and exercised a more structured RCA investigation system. We can preserve successive versions, inspect evidence and questions, and trace where an investigation fails. Development experiments identified specific weaknesses, which informed the latest implementation changes. We now have staged evidence packages for a controlled pilot. The remaining research question is whether these changes improve evidence-supported causal explanations and their revision as new information arrives.')
h('Source records',2)
sources=[
 '[1] S&T PTC July 2026 Presentation, slides 7–13.',
 '[2] RCA Research Overview and Plan, 21 September 2026, sections 5 and 8.',
 '[3] RCA System Review, 18 September 2026, sections 2 and 3.',
 '[4] Try 7 Executive Plan, section 10 implementation receipt and observed smoke outcome.',
 '[5] Synthetic Evidence Packages 2026-09-22, operator overview and case status.',
 '[6] Try 6 V1 V2 Evidence Review, 20 September 2026, sections 1–3.',
 '[7] RCA Implementation and Paper Checklist, 20 September 2026, sections C–E.',
 '[8] Try 7/src/engine/investigation/planner.ts, current workflow inspected 22 September 2026.'
]
for t in sources:
 q=doc.add_paragraph(t);q.paragraph_format.space_after=Pt(3)
 for r in q.runs:r.font.size=Pt(9)

doc.core_properties.title='Standalone RCA progress since July 2026';doc.core_properties.subject='Project progress report';doc.core_properties.author='';doc.core_properties.keywords='RCA, project progress, July 2026'

for el in list(doc.styles.element.iter(qn('w:pBdr'))) + list(doc.element.iter(qn('w:pBdr'))):
 el.getparent().remove(el)
out=root/'RCA Progress Documents/RCA_Progress_Since_July_2026.docx';doc.save(out);print(out)

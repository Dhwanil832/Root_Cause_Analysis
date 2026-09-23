#!/usr/bin/env python3
"""Build a synthetic, staged evidence package for the R3 carrier beam incident."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable, Sequence

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "r3-beam-test-case"
DEFAULTS = OUT / "01_default_references"
STARTER = OUT / "02_starter_documents"
REQUESTED = OUT / "03_requested_evidence"
CHALLENGE = OUT / "04_challenge_evidence"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2C6E9B")
PALE_BLUE = colors.HexColor("#EAF2F8")
PALE_GRAY = colors.HexColor("#F3F5F7")
MID_GRAY = colors.HexColor("#667481")
GREEN = colors.HexColor("#DDEFE4")
AMBER = colors.HexColor("#FFF1CE")
RED = colors.HexColor("#B3261E")
PALE_RED = colors.HexColor("#FCE8E6")

styles = getSampleStyleSheet()
BODY = ParagraphStyle(
    "Body",
    parent=styles["BodyText"],
    fontName="Helvetica",
    fontSize=9.3,
    leading=12.2,
    textColor=colors.HexColor("#202A33"),
    spaceAfter=5,
)
SMALL = ParagraphStyle(
    "Small",
    parent=BODY,
    fontSize=7.7,
    leading=9.4,
    spaceAfter=2,
)
TITLE = ParagraphStyle(
    "Title",
    parent=styles["Title"],
    fontName="Helvetica-Bold",
    fontSize=20,
    leading=24,
    textColor=NAVY,
    alignment=TA_LEFT,
    spaceAfter=5,
)
SUBTITLE = ParagraphStyle(
    "Subtitle",
    parent=BODY,
    fontSize=10.5,
    leading=13,
    textColor=MID_GRAY,
    spaceAfter=10,
)
H1 = ParagraphStyle(
    "H1",
    parent=styles["Heading1"],
    fontName="Helvetica-Bold",
    fontSize=13,
    leading=16,
    textColor=NAVY,
    spaceBefore=8,
    spaceAfter=5,
)
H2 = ParagraphStyle(
    "H2",
    parent=styles["Heading2"],
    fontName="Helvetica-Bold",
    fontSize=10.5,
    leading=13,
    textColor=BLUE,
    spaceBefore=6,
    spaceAfter=4,
)
CELL = ParagraphStyle("Cell", parent=BODY, fontSize=8.2, leading=10.2, spaceAfter=0)
CELL_SMALL = ParagraphStyle("CellSmall", parent=SMALL, fontSize=7.1, leading=8.5, spaceAfter=0)
CELL_HEAD = ParagraphStyle(
    "CellHead",
    parent=CELL,
    fontName="Helvetica-Bold",
    textColor=colors.white,
)
CENTER_SMALL = ParagraphStyle("CenterSmall", parent=SMALL, alignment=TA_CENTER)


def p(text: object, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(html.escape(str(text)).replace("\n", "<br/>"), style)


def rich(text: str, style: ParagraphStyle = BODY) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: Iterable[str], level: int = 0) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item), leftIndent=9) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=17 + level * 10,
        bulletFontSize=6,
        spaceAfter=6,
    )


def table(
    rows: Sequence[Sequence[object]],
    widths: Sequence[float],
    header: bool = True,
    small: bool = False,
) -> Table:
    cell_style = CELL_SMALL if small else CELL
    data = []
    for r_idx, row in enumerate(rows):
        data.append(
            [
                item
                if isinstance(item, (Paragraph, Drawing))
                else p(item, CELL_HEAD if header and r_idx == 0 else cell_style)
                for item in row
            ]
        )
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#9AA7B2")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, PALE_GRAY]),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    return Table(data, colWidths=list(widths), repeatRows=1 if header else 0, style=TableStyle(commands))


def status_table(rows: Sequence[Sequence[object]], widths: Sequence[float], small: bool = False) -> Table:
    t = table(rows, widths, small=small)
    commands = []
    for idx, row in enumerate(rows[1:], start=1):
        status = str(row[-1]).lower()
        if "historical" in status or "confirmed" in status or "completed" in status:
            commands.append(("BACKGROUND", (-1, idx), (-1, idx), GREEN))
        elif "open" in status or "pending" in status or "not established" in status:
            commands.append(("BACKGROUND", (-1, idx), (-1, idx), AMBER))
        elif "gap" in status or "not completed" in status:
            commands.append(("BACKGROUND", (-1, idx), (-1, idx), PALE_RED))
    t.setStyle(TableStyle(commands))
    return t


def provenance_box() -> Table:
    return Table(
        [[rich("<b>SYNTHETIC TEST RECORD - NOT AN ACTUAL COMPANY RECORD</b>", CENTER_SMALL)]],
        colWidths=[7.15 * inch],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_RED),
                ("BOX", (0, 0), (-1, -1), 0.8, RED),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        ),
    )


def footer(canvas, doc):
    canvas.saveState()
    page_w, _ = doc.pagesize
    canvas.setStrokeColor(colors.HexColor("#CAD2D9"))
    canvas.line(doc.leftMargin, 0.47 * inch, page_w - doc.rightMargin, 0.47 * inch)
    canvas.setFont("Helvetica", 7.3)
    canvas.setFillColor(MID_GRAY)
    canvas.drawString(doc.leftMargin, 0.28 * inch, "R3 carrier beam RCA application test package")
    canvas.drawRightString(page_w - doc.rightMargin, 0.28 * inch, f"Page {doc.page}")
    canvas.setFont("Helvetica-Bold", 6.8)
    canvas.setFillColor(RED)
    canvas.drawCentredString(page_w / 2, 0.28 * inch, "SYNTHETIC - TEST USE ONLY")
    canvas.restoreState()


def header(title: str, document_id: str, purpose: str, include_provenance: bool = True):
    story = []
    if include_provenance:
        story.extend([provenance_box(), Spacer(1, 0.11 * inch)])
    story.extend(
        [
            p(title, TITLE),
            p(purpose, SUBTITLE),
            table(
                [
                    ["Document ID", "Incident", "Record type", "Status"],
                    [document_id, "R3 carrier beam - 10/14/2024", "Application test evidence", "Synthetic / controlled"],
                ],
                [1.45 * inch, 2.35 * inch, 1.95 * inch, 1.4 * inch],
                small=True,
            ),
            Spacer(1, 0.08 * inch),
        ]
    )
    return story


def section(title_text: str, body: object | None = None):
    parts = [p(title_text, H1)]
    if body is not None:
        parts.append(body if hasattr(body, "wrap") else p(body))
    return parts


def build_pdf(path: Path, story, pagesize=LETTER, title: str | None = None):
    path.parent.mkdir(parents=True, exist_ok=True)
    page_w, _ = pagesize
    margin = 0.55 * inch
    doc = SimpleDocTemplate(
        str(path),
        pagesize=pagesize,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=0.5 * inch,
        bottomMargin=0.62 * inch,
        title=title or path.stem,
        author="Synthetic RCA application test package",
        subject="R3 carrier beam investigation test evidence",
    )
    # Keep provenance bars aligned to the available width on landscape pages.
    if pagesize == landscape(LETTER):
        for flowable in story:
            if isinstance(flowable, Table) and getattr(flowable, "_colWidths", None) == [7.15 * inch]:
                flowable._argW = [page_w - 2 * margin]
                flowable._colWidths = [page_w - 2 * margin]
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def r3_area_drawing() -> Drawing:
    d = Drawing(700, 265)
    d.add(Rect(15, 18, 670, 225, strokeColor=NAVY, fillColor=colors.white, strokeWidth=1.2))
    d.add(String(28, 224, "Simplified cross-section - not to scale", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    d.add(Rect(220, 75, 260, 135, strokeColor=NAVY, fillColor=PALE_BLUE, strokeWidth=2))
    d.add(String(298, 188, "R3 ROUGHING MILL STAND", fontName="Helvetica-Bold", fontSize=11, fillColor=NAVY))
    d.add(Rect(300, 130, 100, 20, strokeColor=BLUE, fillColor=colors.HexColor("#BED8E8")))
    d.add(String(313, 136, "YOKE AREA", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    d.add(Line(350, 130, 350, 105, strokeColor=NAVY, strokeWidth=3))
    d.add(String(358, 112, "link", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    d.add(Rect(270, 92, 160, 14, strokeColor=NAVY, fillColor=colors.HexColor("#91B9CE")))
    d.add(String(291, 95, "exit carrier beam", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    d.add(Rect(210, 28, 280, 38, strokeColor=NAVY, fillColor=colors.HexColor("#E8ECEF")))
    d.add(String(325, 44, "R3 MILL PIT", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    d.add(Rect(240, 34, 68, 8, strokeColor=BLUE, fillColor=colors.HexColor("#C5D9E7")))
    d.add(String(253, 19, "sled", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    d.add(Rect(395, 35, 66, 18, strokeColor=colors.HexColor("#D97B29"), fillColor=colors.HexColor("#F9DEC5")))
    d.add(String(391, 19, "scaffold platform", fontName="Helvetica", fontSize=8, fillColor=NAVY))
    d.add(String(35, 142, "TOP OPERATOR SIDE", fontName="Helvetica-Bold", fontSize=9, fillColor=BLUE))
    d.add(Line(165, 145, 218, 145, strokeColor=BLUE, strokeWidth=1.5))
    d.add(Polygon([214, 149, 220, 145, 214, 141], strokeColor=BLUE, fillColor=BLUE))
    d.add(String(515, 142, "OPPOSITE SIDE", fontName="Helvetica-Bold", fontSize=9, fillColor=BLUE))
    d.add(Line(480, 145, 508, 145, strokeColor=BLUE, strokeWidth=1.5))
    d.add(Polygon([502, 149, 510, 145, 502, 141], strokeColor=BLUE, fillColor=BLUE))
    d.add(String(505, 77, "Walking route beside stand", fontName="Helvetica", fontSize=8, fillColor=MID_GRAY))
    d.add(Line(500, 70, 650, 70, strokeColor=MID_GRAY, strokeWidth=1.2))
    d.add(String(30, 53, "Red-flagged investigation boundary after event", fontName="Helvetica", fontSize=8, fillColor=RED))
    d.add(Line(28, 68, 185, 68, strokeColor=RED, strokeWidth=2))
    return d


def process_drawing() -> Drawing:
    d = Drawing(690, 150)
    xs = [20, 165, 310, 455, 600]
    labels = ["Rolls removed", "Balance left raised", "B hydraulics isolated", "Unobserved interval", "Beam falls"]
    for idx, (x, label) in enumerate(zip(xs, labels)):
        d.add(Rect(x, 68, 110, 44, fillColor=PALE_BLUE if idx < 3 else (AMBER if idx == 3 else PALE_RED), strokeColor=NAVY, rx=4, ry=4))
        words = label.split()
        if len(words) > 2:
            d.add(String(x + 55, 94, " ".join(words[:2]), textAnchor="middle", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
            d.add(String(x + 55, 81, " ".join(words[2:]), textAnchor="middle", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
        else:
            d.add(String(x + 55, 87, label, textAnchor="middle", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
        if idx < len(xs) - 1:
            d.add(Line(x + 112, 90, xs[idx + 1] - 5, 90, strokeColor=BLUE, strokeWidth=1.7))
            d.add(Polygon([xs[idx + 1] - 11, 94, xs[idx + 1] - 4, 90, xs[idx + 1] - 11, 86], fillColor=BLUE, strokeColor=BLUE))
    d.add(String(20, 133, "Known sequence from preliminary reporting; exact transition mechanism remains open", fontName="Helvetica-Bold", fontSize=10, fillColor=NAVY))
    return d


def evidence_photo_drawing() -> Drawing:
    d = Drawing(520, 260)
    items = [
        (5, 145, "P01", "Overall landing area", "Beam on sled / scaffold"),
        (180, 145, "P02", "Link and keeper", "Keeper visible as installed"),
        (355, 145, "P03", "Yoke pocket", "No gross fracture visible"),
        (5, 25, "P04", "Window liner", "Recovered with beam"),
        (180, 25, "P05", "Contact surfaces", "As-found marks recorded"),
        (355, 25, "P06", "Upper stand", "View partly obstructed"),
    ]
    for x, y, code, title_text, caption in items:
        d.add(Rect(x, y, 160, 100, fillColor=PALE_GRAY, strokeColor=NAVY))
        d.add(String(x + 10, y + 76, code, fontName="Helvetica-Bold", fontSize=18, fillColor=BLUE))
        d.add(String(x + 10, y + 55, title_text, fontName="Helvetica-Bold", fontSize=9, fillColor=NAVY))
        d.add(String(x + 10, y + 35, caption, fontName="Helvetica", fontSize=7.2, fillColor=MID_GRAY))
        d.add(String(x + 10, y + 14, "Synthetic image placeholder", fontName="Helvetica-Oblique", fontSize=6.8, fillColor=RED))
    return d


def build_default_documents():
    story = header(
        "80-inch Hot Strip Mill - R3 Area Orientation",
        "R3-DEF-001",
        "Baseline vocabulary and spatial context for model comprehension. This is a conceptual test aid, not a plant layout or engineering drawing.",
    )
    story += [r3_area_drawing()]
    story += section("Terms the model should be able to resolve")
    story.append(
        status_table(
            [
                ["Term", "Working meaning in this test case", "Boundary / caution", "Status"],
                ["R3 roughing mill stand", "The third stand in the roughing mill area referenced by the incident.", "Exact bay coordinates and elevations are not provided.", "Historical source fact"],
                ["Exit carrier beam", "The beam reported as falling from the yoke into the mill pit.", "Its detailed design and retention method require an equipment record.", "Historical source fact"],
                ["Yoke", "The upper support location on which the carrier-beam link was reported to rest.", "The drawing geometry and permitted link movement are not established here.", "Historical source fact"],
                ["R3 mill pit", "The below-floor work area into which the beam fell.", "Access controls and confined-space classification require separate records.", "Historical source fact"],
                ["Sled and scaffold platform", "Objects in the pit on which the beam landed.", "As-found locations and damage are evidence, not shown to scale here.", "Historical source fact"],
                ["Top operator side", "The side from which a small mill window liner was reported to fall.", "Compass direction is intentionally not assigned.", "Historical source fact"],
            ],
            [1.15 * inch, 2.35 * inch, 2.35 * inch, 1.3 * inch],
        )
    )
    story += section("What this document does not establish")
    story.append(bullets(["The mechanical retention design or required stopper arrangement.", "The exact pre-event position of the link inside the yoke.", "Whether the raised roll-balance condition was permitted by procedure.", "The sequence or physical mechanism that caused the beam to leave the yoke."]))
    build_pdf(DEFAULTS / "R3_Area_Orientation.pdf", story, pagesize=landscape(LETTER))

    story = header(
        "R3 Top Backup Roll Balance - System Primer",
        "R3-DEF-002",
        "A bounded component-and-energy primer based on the words used in the preliminary incident record. It avoids asserting unverified design details.",
    )
    story += section("Known relationship map")
    story.append(
        status_table(
            [
                ["Entity", "Relationship stated or implied by the preliminary record", "Why it matters", "Status"],
                ["Top backup roll balance", "Was left isolated in the raised position after roll removal.", "May define mechanical position and gravitational potential during outage work.", "Historical source fact"],
                ["B hydraulic system", "Was shut off and bled for work on that system.", "Pressure removal may alter support or restraint; the actual circuit boundary is separate evidence.", "Historical source fact"],
                ["Carrier beam and link", "Fell together; both were reported intact after the event.", "Fracture is not apparent, but seating, motion, wear, and retention still require examination.", "Historical source fact"],
                ["Keeper", "Was reported still installed on the recovered assembly.", "Presence does not by itself establish its design function, engagement, or load path.", "Historical source fact"],
                ["Yoke", "Was the location on which the link rested; no apparent damage was reported.", "Geometry, contact marks, clearances, and permitted movement remain relevant.", "Historical source fact"],
                ["Window liner", "A small liner fell from the top operator side with the carrier beam.", "Its timing, contact, and possible role are not established.", "Historical source fact"],
            ],
            [1.22 * inch, 2.55 * inch, 2.05 * inch, 1.33 * inch],
        )
    )
    story += section("Energy and configuration domains")
    story.append(table([["Domain", "Questions this primer should enable"], ["Gravity", "What mass was elevated, what normally supported it, and what positive restraint was required?"], ["Hydraulic", "Which circuit held or moved the balance, what was isolated, and how was zero pressure verified?"], ["Mechanical", "How were the beam, link, keeper, yoke, liner, and rolls positioned and retained?"], ["Outage configuration", "What changed when work and backup rolls were removed, and which temporary supports were required?"]], [1.25 * inch, 5.9 * inch]))
    story += section("Required source hierarchy")
    story.append(bullets(["Use controlled drawings and equipment-specific procedures for design intent.", "Use signed field records, photos, video, and measurements for as-found state.", "Treat witness recollection as attributed evidence with visibility limits.", "Keep design requirements separate from inferred causal explanations."]))
    build_pdf(DEFAULTS / "R3_Roll_Balance_System_Primer.pdf", story)

    story = header(
        "80HSM Outage Roles and Records Guide",
        "R3-DEF-003",
        "Default context for deciding who may know a fact and which record should be requested. Role names are generic for this synthetic test case.",
    )
    story += section("Role-to-evidence map")
    story.append(
        table(
            [
                ["Role", "Likely first-hand knowledge", "Records to request"],
                ["Area / shift manager", "Work status, stop-work actions, turnover expectations, area control.", "Shift log, turnover notes, incident notification, stand-down record."],
                ["Maintenance planner / supervisor", "Approved work scope, sequence, equipment configuration, deviations.", "Work order, maintenance practice, change authorization, completion log."],
                ["Energy-isolation lead", "Isolation boundary, locks, verification method, shift transfer.", "ECP/LOTO, group box sheet, zero-energy verification, lock audit."],
                ["Mechanical technician", "Removal sequence, observed component position, temporary supports.", "Task steps, field notes, measurements, inspection record."],
                ["Contractor supervisor", "Crew assignments, access times, pre-job brief, qualifications.", "Crew roster, JJHAC/JSHA, training cards, sign-in/out record."],
                ["Crane operator / lift coordinator", "Crane movement and lifts near R3.", "Crane activity log, radio log, lift plan, camera review."],
                ["Scaffold competent person", "Platform status, inspection time, occupancy restrictions.", "Scaffold tag, inspection sheet, access log, damage assessment."],
            ],
            [1.48 * inch, 2.72 * inch, 2.95 * inch],
        )
    )
    story += section("Preservation principle")
    story.append(p("Default documents remain shared reference material. Starter documents belong to this incident/model run at submission. Requested evidence is added later with its own provenance, version, and source. No record should silently replace an earlier version."))
    build_pdf(DEFAULTS / "R3_Outage_Roles_and_Records_Guide.pdf", story)


def build_starter_documents():
    story = header(
        "Preliminary Incident Notification - Record 16515",
        "R3-START-001",
        "A test-ready transcription of the historical preliminary record supplied to the application with the initial incident description.",
    )
    story.append(
        table(
            [
                ["Facility", "Area", "Location", "Event date / shift"],
                ["Indiana Harbor", "Hot Rolling and Finishing - 80-inch Hot Strip", "Roughing Mill R3", "10/14/2024 - Turn 2 - approximately 1:03 PM"],
                ["Classification", "Work type", "Category", "Potential severity"],
                ["Preliminary contractor case / SIFp", "Non-routine maintenance", "Falling object", "Death"],
            ],
            [1.35 * inch, 2.3 * inch, 1.75 * inch, 1.75 * inch],
            header=False,
        )
    )
    story += section("Incident description")
    story.append(p("At approximately 1:03 PM on October 14, 2024, the R3 exit carrier beam fell from the yoke into the R3 mill pit, landing on the sled and a scaffold platform. No team members were in the pit at the time. Several contractor employees had worked in the pit during the morning, and two contractor employees walking beside the mill stand witnessed the fall."))
    story.append(p("The area was red-flagged for investigation. The carrier beam and its link were found intact with the keeper still installed. No damage was apparent on the yoke where the link rests. A small mill window liner from the top operator side fell with the beam. No crane lifts involving this equipment were in progress or had occurred prior."))
    story.append(p("On the previous shift, the work rolls and the top and bottom backup rolls had been removed in preparation for outage work in the mill stand. The R3 top backup roll balance had been left isolated in the raised position. The B hydraulics had been shut off and bled for work on that system."))
    story += section("Immediate actions")
    story.append(p("Stopped work and red-flagged the area; inspected other mill stands; ensured top roll balances were lowered; verified link-arm keepers were present at other stands; and held a safety stand-down."))
    story += section("Evidence identified in the preliminary record")
    story.append(table([["Requested evidence", "Availability at starter stage"], ["Mechanical drawings", "Not attached - request from document control / engineering."], ["Energy Control Plan (ECP)", "Not attached - request incident-specific revision and execution record."], ["Lockout verification", "Not attached - request signed field record."], ["Video", "Not attached - request preserved clip and review log."], ["Pictures and measurements", "Not attached - request original files and measurement sheet."]], [2.15 * inch, 5 * inch]))
    story += section("Preliminary cause field")
    story.append(status_table([["Field", "Recorded value", "Status"], ["Cause category", "Work Environment - Other", "Historical source fact"], ["Investigation state", "Still investigating", "Open"]], [1.6 * inch, 3.9 * inch, 1.65 * inch]))
    build_pdf(STARTER / "Preliminary_Incident_Notification_16515.pdf", story)

    story = header(
        "Initial Scene Sketch and Event Timeline",
        "R3-START-002",
        "A starter-stage orientation record combining only the reported scene relationships and event sequence. Exact distances are not asserted.",
    )
    story.extend([r3_area_drawing(), process_drawing()])
    story += section("Time anchors")
    story.append(status_table([["Time / interval", "Reported event", "Precision", "Status"], ["Previous shift", "Work rolls and top and bottom backup rolls removed for outage work.", "Shift-level only", "Historical source fact"], ["Previous shift", "Top backup roll balance left isolated raised; B hydraulics shut off and bled.", "Sequence within shift not established", "Historical source fact"], ["Morning of 10/14", "Several contractor employees worked in the R3 pit.", "Names and exact times not in starter record", "Historical source fact"], ["Approx. 1:03 PM", "Carrier beam fell into pit; two nearby contractor employees witnessed the event.", "Narrative time", "Historical source fact"], ["Approx. 1:05 PM", "Structured event-time field in historical record.", "Two-minute difference from narrative", "Open / reconcile"], ["After event", "Work stopped and area red-flagged for investigation.", "Exact time not provided", "Historical source fact"]], [1.2 * inch, 3.4 * inch, 1.45 * inch, 1.1 * inch]))
    story += section("Scene limits")
    story.append(bullets(["The yoke and link seating surfaces are not visible in this sketch.", "The witnesses' exact sight lines are not established.", "No pre-event photograph is included.", "The fall path is reported, not reconstructed." ]))
    build_pdf(STARTER / "Initial_Scene_Sketch_and_Timeline.pdf", story, pagesize=landscape(LETTER))

    story = header(
        "Initial Evidence Register",
        "R3-START-003",
        "The starter inventory supplied at incident creation. It tells the app what exists, what is missing, and what requires preservation without providing the later evidence itself.",
    )
    story += section("Evidence status at submission")
    story.append(status_table([["Evidence ID", "Item", "Known holder / source", "Starter status"], ["EV-001", "Preliminary incident notification", "Safety reporting system", "Available"], ["EV-002", "Incident narrative and entity list", "Safety reporting system", "Available"], ["EV-003", "Mechanical assembly drawing", "Engineering / document control", "Request"], ["EV-004", "Energy Control Plan", "Maintenance / energy-isolation lead", "Request"], ["EV-005", "Executed lockout verification", "Group lockout records", "Request"], ["EV-006", "Shift turnover log", "Operations / maintenance", "Request"], ["EV-007", "Outage work scope and task sequence", "Planner / work management", "Request"], ["EV-008", "JJHAC / JSHA", "Contractor supervisor", "Request"], ["EV-009", "Witness statements", "Investigation team", "Request"], ["EV-010", "Crane activity log", "Crane operations", "Request"], ["EV-011", "Hydraulic status / bleed verification", "Maintenance", "Request"], ["EV-012", "Original scene photographs and measurements", "Investigation team", "Request"], ["EV-013", "Post-event mechanical inspection", "Reliability / engineering", "Request"], ["EV-014", "Other-stand comparison inspection", "Maintenance", "Request"], ["EV-015", "Scaffold inspection and occupancy", "Contractor / scaffold competent person", "Request"], ["EV-016", "Crew qualifications and training", "Contractor / site onboarding", "Request"], ["EV-017", "Preserved video and review notes", "Security / operations", "Request"], ["EV-018", "OEM design clarification", "Engineering / OEM", "Not yet available"]], [0.72 * inch, 2.55 * inch, 2.3 * inch, 1.2 * inch], small=True))
    story += section("Preservation notes")
    story.append(bullets(["Preserve original files and metadata; derived summaries do not replace originals.", "Record who supplied each later document and when it was added.", "If two records disagree, retain both and open a contradiction instead of overwriting either fact."]))
    build_pdf(STARTER / "Initial_Evidence_Register.pdf", story)


def requested_doc(path_name: str, title_text: str, doc_id: str, purpose: str, content):
    story = header(title_text, doc_id, purpose)
    story.extend(content)
    build_pdf(REQUESTED / path_name, story)


def build_requested_documents():
    requested_doc(
        "01_Mechanical_Assembly_and_Retention_Record.pdf",
        "Mechanical Assembly and Retention Record",
        "R3-EV-003",
        "A synthetic controlled-drawing extract for testing design-intent retrieval. It is not an actual engineering drawing and contains no fabrication dimensions.",
        section("Synthetic drawing notes") + [
            status_table([["Feature", "Test-scenario design statement", "Evidence role", "Status"], ["Carrier beam / link connection", "The carrier beam remains connected to the link by a pinned joint. The keeper retains that pin.", "Explains why beam, link, and keeper could be recovered together.", "Synthetic scenario fact"], ["Link / yoke interface", "The upper link surface rests in an open yoke pocket during the normal supported position.", "Defines a possible lift-out or unseating path that must be evaluated from geometry and marks.", "Synthetic scenario fact"], ["Keeper function", "The keeper is not a positive hold-down over the yoke pocket.", "Separates 'keeper present' from 'link positively retained in yoke.'", "Synthetic scenario fact"], ["Outage position", "When rolls are absent and the balance is raised, the carrier-beam assembly requires either the specified supported state or a rated temporary restraint before hydraulic pressure is removed.", "Creates a procedure/design requirement to compare with field execution.", "Synthetic scenario fact"], ["Permitted clearances", "No acceptance dimensions are included in this extract.", "Full drawing and OEM tolerances remain necessary for dimensional conclusions.", "Open / request full drawing"]], [1.3 * inch, 2.75 * inch, 2.05 * inch, 1.05 * inch])
        ] + section("Revision and authority") + [table([["Drawing reference", "Revision", "Approval", "Limitation"], ["R3-RB-ASM-SYN-001", "Test Rev A", "Synthetic evidence author", "For application evaluation only; not valid for field work."]], [2.1 * inch, 1.2 * inch, 1.7 * inch, 2.15 * inch])],
    )
    requested_doc(
        "02_Energy_Control_Plan.pdf",
        "Energy Control Plan - R3 Outage Configuration",
        "R3-EV-004",
        "A synthetic equipment-specific energy-control plan used to test source, boundary, verification, and configuration reasoning.",
        section("Energy-source boundary") + [
            status_table([["Source ID", "Energy / equipment", "Planned isolation", "Required verification", "Status in plan"], ["H-B", "B hydraulic system", "Shut supply, secure valve, open designated bleed / return path.", "Local gauge zero and functional try where applicable.", "Defined"], ["H-RB", "Top backup roll balance hydraulic branch", "Isolate branch before work within the stand.", "Confirm no commanded motion and document pressure state.", "Defined"], ["G-RB", "Gravity - raised roll-balance and attached components", "Lower to designated rest position or install rated mechanical blocking/restraint.", "Visual and physical verification of support; record block ID.", "Defined"], ["M-ROLL", "Mechanical support changed by removal of work and backup rolls", "Treat removal sequence as a configuration change; verify remaining parts are supported.", "Supervisor sign-off before removing hydraulic support.", "Defined"], ["E-AUX", "Auxiliary electrical controls", "Control-power isolation if work enters electrical or motion hazard zone.", "Meter test where electrical isolation is applied.", "Conditional"]], [0.65 * inch, 1.35 * inch, 2.25 * inch, 2.05 * inch, 0.85 * inch], small=True)
        ] + section("Required sequence") + [bullets(["Identify the as-found roll and balance configuration before isolation.", "Establish the safe supported position for gravity-loaded components.", "Apply hydraulic isolation and bleed pressure.", "Verify zero-energy state and positive mechanical support independently.", "Record any departure from the sequence and obtain authorization before work continues."])] + section("Execution evidence") + [p("This plan states what is required. It does not prove which steps were performed. Compare it with the signed lockout verification, shift log, work scope, photographs, and witness evidence.")],
    )

    requested_doc(
        "03_Lockout_Verification_Record.pdf",
        "Executed Lockout Verification - R3 Outage",
        "R3-EV-005",
        "A synthetic execution record that should be compared with the Energy Control Plan rather than treated as self-proving.",
        section("Recorded field entries") + [
            status_table([["Entry", "Recorded value", "Verification / signature", "Record status"], ["B hydraulic supply", "Isolation valve shut and equipment lock applied.", "Initialed - 10/13/2024, 11:58 PM", "Completed"], ["B hydraulic bleed", "Bleed path opened; local gauge read 0 psi.", "Initialed - 10/14/2024, 12:28 AM", "Completed"], ["Top backup roll balance position", "Raised.", "Position noted; no lowering entry", "Completed as observation"], ["Gravity control for raised balance / carrier assembly", "Mechanical block or rated restraint ID field is blank.", "No independent verifier signature", "Gap in record"], ["Functional try", "No motion on command after hydraulic isolation.", "Initialed - Turn 1", "Completed"], ["Shift transfer", "Open group isolation carried into Turn 2.", "Incoming-lead acceptance box unsigned on scanned copy", "Gap in record"]], [1.35 * inch, 2.55 * inch, 1.85 * inch, 1.4 * inch])
        ] + section("Record cautions") + [bullets(["A zero-pressure indication does not establish control of gravity energy.", "A blank field is evidence of a documentation gap; it is not proof that the physical control was absent.", "The original paper record and group-box log should be inspected for missing reverse-side or attachment pages."])],
    )

    requested_doc(
        "04_Shift_Turnover_Log.pdf",
        "Shift Turnover Log - Turn 1 to Turn 2",
        "R3-EV-006",
        "A synthetic contemporaneous log used to test sequence, handoff, and unresolved-condition analysis.",
        section("Turn 1 outgoing entry") + [
            table([["Time", "Entry", "Author role"], ["10/13 10:20 PM", "R3 work rolls removed; roll-change equipment clear.", "Maintenance shift lead"], ["10/13 11:45 PM", "Top and bottom backup rolls removed for outage scope.", "Maintenance shift lead"], ["10/14 12:25 AM", "Top backup roll balance remains up. B hydraulic system isolated and bled for B-system work.", "Energy-isolation lead"], ["10/14 12:40 AM", "Carrier-beam support / yoke seating not independently checked after roll removal.", "Maintenance shift lead"], ["10/14 12:55 AM", "Turnover note: keep personnel clear below upper balance components until day-turn confirms final supported condition.", "Maintenance shift lead"]], [1 * inch, 4.9 * inch, 1.25 * inch])
        ] + section("Turn 2 incoming entry") + [status_table([["Field", "Recorded value", "Status"], ["Outstanding condition acknowledged", "General red-zone restriction acknowledged in verbal handoff.", "Synthetic scenario fact"], ["Specific carrier-beam / yoke verification", "No entry found.", "Gap in record"], ["Formal re-brief before pit work", "Morning contractor brief references overhead hazards but not the carrier-beam condition by name.", "Synthetic scenario fact"]], [1.75 * inch, 4.2 * inch, 1.2 * inch])],
    )

    requested_doc(
        "05_Outage_Work_Scope_and_Sequence.pdf",
        "Outage Work Scope and Sequence - R3 Stand",
        "R3-EV-007",
        "A synthetic work-management record for testing planned-versus-actual configuration and change-control reasoning.",
        section("Approved scope") + [
            table([["Step", "Planned activity", "Interface / hold point"], ["1", "Remove work rolls.", "Confirm roll-change equipment clear."], ["2", "Remove top and bottom backup rolls.", "Confirm balance and associated components in approved supported state."], ["3", "Isolate and bleed B hydraulic system.", "Energy-isolation verification before B-system maintenance."], ["4", "Perform mill-stand and hydraulic outage work.", "Maintain exclusion zones and scaffold controls."], ["5", "Inspect and restore equipment.", "Engineering release before re-energization."]], [0.6 * inch, 3.7 * inch, 2.85 * inch])
        ] + section("Execution notes") + [status_table([["Question", "Record finding", "Status"], ["Was the listed sequence followed?", "Roll removal preceded B-system isolation and bleed.", "Synthetic scenario fact"], ["Was the supported-state hold point signed?", "No signature or attached checklist is present for Step 2.", "Gap in record"], ["Was the carrier beam listed as a separate protected component?", "No; it appears only within the general balance-system boundary.", "Synthetic scenario fact"], ["Was a field change approved?", "No change request is attached.", "Open / verify"]], [2.05 * inch, 3.85 * inch, 1.25 * inch])],
    )

    requested_doc(
        "06_JJHAC_JSHA_Record.pdf",
        "JJHAC / JSHA - R3 Mill Pit Outage Work",
        "R3-EV-008",
        "A synthetic pre-job hazard record modeled on the partner document family. It supports hazard-recognition and control-adequacy questions.",
        section("Task and crew") + [table([["Job / task", "Applicable roles", "Area", "Brief time"], ["R3 pit access and mill-stand outage support", "Contractor mechanical crew; site maintenance liaison", "R3 roughing mill / mill pit", "10/14/2024 - 6:35 AM"]], [2.6 * inch, 2.15 * inch, 1.45 * inch, 0.95 * inch])] + section("Job steps, hazards, and controls") + [
            status_table([["Step", "Potential hazard", "Recorded control", "Assessment"], ["Enter and work from pit / scaffold", "Access, fall exposure, dropped objects from above.", "Inspect scaffold; barricade work zone; hard hats; keep clear of overhead work.", "Addressed generally"], ["Work below mill stand", "Suspended or unsecured mill components.", "Verify no active crane lift; confirm equipment is under energy control.", "Addressed generally"], ["Hydraulic-system outage work", "Stored pressure or unexpected motion.", "Use ECP/LOTO; verify gauge zero; perform try.", "Addressed"], ["Changed roll configuration", "Change in support path after roll removal.", "No component-specific prompt for carrier beam / link / yoke seating.", "Gap in specificity"], ["Conditions change", "New task, equipment state, or personnel.", "Stop and revise brief before proceeding.", "Defined"]], [1.35 * inch, 2.05 * inch, 2.65 * inch, 1.1 * inch], small=True)
        ] + section("PPE and tools") + [p("Recorded: hard hat, safety glasses with side shields, safety footwear, gloves selected for task, hearing protection, fall protection where required by access condition. PPE does not replace control of falling-object or gravity-energy hazards.")],
    )

    requested_doc(
        "07_Witness_Statement_Packet.pdf",
        "Witness Statement Packet",
        "R3-EV-009",
        "Two synthetic attributed accounts. The statements preserve observation limits and should not be blended into a single voice.",
        section("Witness W-01 - contractor employee") + [table([["Prompt", "Statement"], ["Position", "Walking beside the R3 stand on the operator-side route; not inside the pit."], ["Observation", "Saw the lower beam move slightly at one end, rotate, and then drop into the pit. Did not see a crane hook, rigging, or a person touching it."], ["Sound", "Heard one metallic scrape followed by the impact."], ["Visibility limit", "Could see the beam but not the upper link-to-yoke contact point."], ["Time confidence", "Approximate; based on phone time checked after the event."]], [1.35 * inch, 5.8 * inch])] + section("Witness W-02 - contractor employee") + [table([["Prompt", "Statement"], ["Position", "Several feet behind W-01 on the same walking route."], ["Observation", "Looked toward the stand after hearing a scrape and saw the beam already moving downward. No crane motion was noticed."], ["Prior condition", "Did not inspect the carrier beam or yoke before the event."], ["Visibility limit", "Scaffold and stand structure partially blocked the lower landing area."], ["Uncertainty", "Cannot say whether the small liner moved before, with, or after the beam."]], [1.35 * inch, 5.8 * inch])] + section("Investigator note") + [p("Common points: falling beam, no observed person contact, no observed crane movement. Non-common points: W-01 reports seeing initial motion; W-02 begins observing after a sound. Preserve both accounts and their visibility limits.")],
    )

    requested_doc(
        "08_Crane_Activity_Log.pdf",
        "Crane Activity and Lift Check",
        "R3-EV-010",
        "A synthetic operational log used to test whether crane interaction is supported, contradicted, or merely unobserved.",
        section("Relevant interval") + [
            status_table([["Time window", "Logged activity", "Corroboration", "Status"], ["11:30 AM-12:10 PM", "Crane assigned to a different bay; no R3 lift ticket.", "Dispatch log and operator entry", "Synthetic scenario fact"], ["12:10 PM-1:10 PM", "No commanded crane travel or hoist movement in R3 bay.", "Controller event log", "Synthetic scenario fact"], ["Approx. 1:03 PM", "No active hook, rigging, or suspended crane load at R3.", "Witnesses and controller log", "Consistent"], ["Prior shift roll removal", "Crane-assisted roll-removal activities completed before the relevant interval.", "Work log; exact final-clear time recorded separately", "Historical source fact / detail synthetic"]], [1.35 * inch, 2.65 * inch, 2.05 * inch, 1.1 * inch])
        ] + section("Boundary") + [p("This log addresses crane movement and lifts. It does not exclude earlier contact, rigging interference, or a configuration change unless those possibilities are checked against the roll-removal records and physical evidence.")],
    )

    requested_doc(
        "09_Hydraulic_Status_and_Bleed_Verification.pdf",
        "Hydraulic Status and Bleed Verification",
        "R3-EV-011",
        "A synthetic field-data summary distinguishing recorded pressure state from mechanical support state.",
        section("Recorded readings") + [
            status_table([["Point / source", "Reading or state", "Time", "Limitation", "Status"], ["B-system supply gauge", "0 psi after bleed", "10/14 - 12:28 AM", "Local gauge accuracy not independently calibrated for investigation.", "Synthetic scenario fact"], ["B-system return / bleed", "Bleed path recorded open", "10/14 - 12:28 AM", "Exact trapped volumes not mapped in field record.", "Synthetic scenario fact"], ["Top balance position", "Raised", "Turnover entry", "Position does not establish the load path after pressure removal.", "Historical source fact"], ["Pressure trend", "No historian tag identified for isolated branch.", "Relevant interval", "Cannot reconstruct transient pressure from trend data.", "Not available"], ["Leak-down test", "Not performed before post-event disturbance.", "After event", "No direct rate measurement exists.", "Not completed"]], [1.35 * inch, 1.25 * inch, 1.05 * inch, 2.45 * inch, 1.05 * inch], small=True)
        ] + section("Interpretive boundary") + [p("The record supports that B hydraulics were intended to be at zero pressure. It does not establish how the raised balance and carrier assembly were mechanically supported, nor whether movement occurred during pressure decay.")],
    )

    requested_doc(
        "10_Scene_Photo_Index_and_Measurement_Log.pdf",
        "Scene Photograph Index and Measurement Log",
        "R3-EV-012",
        "A synthetic visual-evidence index. Graphic panels are placeholders, not recreations of actual photographs.",
        [evidence_photo_drawing()] + section("Measurement log") + [
            status_table([["Item", "As-found observation", "Measurement status", "Status"], ["Carrier beam", "No gross fracture visible; landed across sled and scaffold platform.", "Overall dimensions not re-measured before recovery.", "Historical source fact / measurement open"], ["Link", "Recovered with beam and described as intact.", "Critical wear and seating dimensions pending controlled inspection.", "Historical source fact / pending"], ["Keeper", "Present and installed on recovered assembly.", "Fit, deformation, and retained-pin clearance pending.", "Historical source fact / pending"], ["Yoke", "No apparent gross damage in initial view.", "Pocket geometry and contact-surface measurements pending.", "Historical source fact / pending"], ["Window liner", "Small top-operator-side liner recovered with beam.", "Pre-event location and attachment condition not documented in starter record.", "Historical source fact / open"]], [1.3 * inch, 2.65 * inch, 2.25 * inch, 0.95 * inch], small=True)
        ] + section("Original-file requirement") + [p("For a real investigation, upload the original image files with EXIF metadata and the scale/measurement method. This synthetic index is designed to prompt that request; it is not a substitute for imagery.")],
    )

    requested_doc(
        "11_Post_Event_Mechanical_Inspection.pdf",
        "Post-Event Mechanical Inspection",
        "R3-EV-013",
        "A synthetic condition report separating gross visual findings from dimensional and functional conclusions.",
        section("Inspection findings") + [
            status_table([["Component", "Visual finding", "What is not established", "Status"], ["Carrier beam", "No visible fracture or permanent gross bend in preliminary visual check.", "Load history, subtle distortion, and material condition.", "Synthetic scenario fact"], ["Link", "No visible fracture; one contact edge shows a polished witness area.", "When the mark formed and whether it indicates partial seating.", "Synthetic scenario fact / interpretation open"], ["Keeper and pin", "Keeper present; pin retained.", "Keeper engagement before the fall and dimensional condition.", "Historical source fact / details open"], ["Yoke pocket", "No gross crack or break; contact surfaces require cleaning and measurement.", "Wear, taper, clearance, and dynamic path.", "Historical source fact / pending"], ["Window liner", "Recovered displaced; attachment hardware condition not fully documented.", "Whether liner movement preceded or followed beam motion.", "Open"]], [1.2 * inch, 2.55 * inch, 2.45 * inch, 0.95 * inch], small=True)
        ] + section("Recommended follow-up tests") + [bullets(["Controlled dimensional inspection against the full drawing and tolerance stack.", "Material and non-destructive examination if engineering identifies critical areas.", "Fit-up demonstration using an exemplar or digital model without disturbing original evidence.", "Failure-mode review distinguishing fracture, pin release, link unseating, interference, and support loss."])],
    )

    requested_doc(
        "12_Similar_Stand_Inspection.pdf",
        "Similar-Stand Comparison - R1, R2, R4, and R5",
        "R3-EV-014",
        "A synthetic comparison record based on the immediate action to inspect other stands. It provides context, not proof of R3's pre-event state.",
        section("Comparison results") + [
            status_table([["Stand", "Keeper present", "Balance position at inspection", "Visual link seating", "Disposition"], ["R1", "Yes", "Lowered", "Centered in visible yoke pocket", "No gross anomaly"], ["R2", "Yes", "Lowered", "Centered; contact surfaces not measured", "No gross anomaly"], ["R4", "Yes", "Lowered", "Slight visual asymmetry; engineering measurement requested", "Follow-up"], ["R5", "Yes", "Lowered", "Centered in visible yoke pocket", "No gross anomaly"]], [0.75 * inch, 1.1 * inch, 1.65 * inch, 2.25 * inch, 1.4 * inch])
        ] + section("Comparison limits") + [bullets(["All other balances were lowered before or during the immediate safety response.", "The comparison does not reproduce R3's raised, roll-removed, hydraulically bled configuration.", "Visual similarity is not a tolerance check.", "The R4 observation is an inspection lead, not evidence that it shares the R3 event mechanism."])],
    )

    requested_doc(
        "13_Scaffold_and_Pit_Occupancy_Record.pdf",
        "Scaffold Inspection and Mill-Pit Occupancy Record",
        "R3-EV-015",
        "A synthetic access record used to establish exposure, last-known occupancy, and post-impact scaffold status.",
        section("Access and inspection log") + [
            status_table([["Time", "Entry", "Record source", "Status"], ["6:20 AM", "R3 scaffold inspected and tagged available for planned configuration.", "Competent-person scaffold tag", "Synthetic scenario fact"], ["6:45 AM-12:35 PM", "Contractor crew entries and exits recorded intermittently for pit work.", "Pit access sheet", "Synthetic scenario fact"], ["12:42 PM", "Last recorded contractor exit before event.", "Pit access sheet", "Synthetic scenario fact"], ["Approx. 1:03 PM", "No personnel in pit when carrier beam fell.", "Preliminary report and witnesses", "Historical source fact"], ["After event", "Platform quarantined; impact damage assessment required before reuse.", "Area-control log", "Synthetic scenario fact"]], [1.05 * inch, 3.45 * inch, 1.75 * inch, 0.9 * inch])
        ] + section("Exposure statement") + [p("The absence of personnel at the moment of impact prevented injury. Earlier occupancy beneath or near the potential fall path remains relevant to potential severity and control adequacy, but it does not show that worker action caused the fall.")],
    )

    requested_doc(
        "14_Contractor_Crew_Qualifications.pdf",
        "Contractor Crew Roster and Qualification Check",
        "R3-EV-016",
        "A synthetic anonymized qualification record. It supports competence and exposure checks without supplying personal data or implying misconduct.",
        section("Anonymized roster") + [
            status_table([["Worker ID", "Assigned role", "Relevant documented qualification", "Pit access on 10/14", "Status"], ["C-101", "Mechanical lead", "Site orientation; energy-control affected-person; task qualification current.", "Morning", "Current"], ["C-102", "Mechanical craft", "Site orientation; scaffold-user; task qualification current.", "Morning", "Current"], ["C-103", "Mechanical craft", "Site orientation; scaffold-user; task qualification current.", "Morning", "Current"], ["C-104", "Helper / spotter", "Site orientation; task-specific briefing documented.", "Morning", "Current"], ["C-201", "Witness / nearby crew", "Site orientation current.", "Not in pit at event", "Current"], ["C-202", "Witness / nearby crew", "Site orientation current.", "Not in pit at event", "Current"]], [0.75 * inch, 1.25 * inch, 2.9 * inch, 1.25 * inch, 1 * inch], small=True)
        ] + section("Record limits") + [bullets(["This check establishes only the listed training records; it does not prove task execution quality.", "No person is identified as having touched or altered the carrier assembly before the event.", "Authorization for energy-isolation leadership must be checked separately from affected-person training."])],
    )

    requested_doc(
        "15_Video_Review_Log.pdf",
        "Preserved Video Review Log",
        "R3-EV-017",
        "A synthetic review of a partial camera view. It tests temporal corroboration without pretending that hidden geometry is visible.",
        section("Camera and preservation") + [table([["Camera", "Coverage", "Preserved interval", "Limitation"], ["Roughing-bay fixed camera - synthetic", "Walking route, part of R3 stand, lower pit opening", "12:50 PM-1:10 PM", "Upper yoke/link interface obscured by stand structure; no useful audio"]], [1.65 * inch, 2.1 * inch, 1.45 * inch, 1.95 * inch])] + section("Observed sequence") + [
            status_table([["Timestamp", "Observation", "Confidence", "Status"], ["1:03:09 PM", "No person or crane hook visible within the immediate carrier-beam area.", "High within camera field", "Synthetic scenario fact"], ["1:03:11 PM", "Lower end of beam begins a small visible movement.", "Moderate; upper connection hidden", "Synthetic scenario fact"], ["1:03:12 PM", "Beam rotates and exits the visible support position.", "High", "Synthetic scenario fact"], ["1:03:13 PM", "Beam enters pit; dust / motion briefly obscures landing area.", "High", "Synthetic scenario fact"], ["1:03:20 PM", "Nearby personnel stop and move away from the stand.", "High", "Synthetic scenario fact"]], [1.05 * inch, 3.75 * inch, 1.45 * inch, 0.9 * inch])
        ] + section("What video cannot answer") + [bullets(["Whether the link was fully seated in the yoke before motion began.", "Whether hydraulic or mechanical movement occurred inside the obscured upper assembly.", "Whether the small liner moved first.", "Exact fall geometry or component clearances."])],
    )

    requested_doc(
        "16_OEM_Engineering_Information_Request.pdf",
        "OEM / Engineering Information Request",
        "R3-EV-018",
        "An intentionally unresolved evidence request. It tests whether the investigation can keep a causal branch open while awaiting authoritative design information.",
        section("Questions sent for authoritative response") + [
            status_table([["Request", "Why needed", "Current status"], ["Full carrier-beam, link, keeper, and yoke assembly drawing with revision history", "Establish design intent, geometry, and positive-retention features.", "Pending"], ["Permitted balance positions during roll removal and hydraulic bleed-down", "Determine whether the observed raised/isolation state was within approved configuration.", "Pending"], ["Required temporary blocking or restraint", "Compare field record with manufacturer-defined gravity control.", "Pending"], ["Inspection limits for yoke and link contact surfaces", "Evaluate wear and partial-seating hypotheses.", "Pending"], ["Known service bulletins or comparable events", "Assess whether a latent design or known-condition pattern exists.", "Pending"]], [3.05 * inch, 3.05 * inch, 1.05 * inch])
        ] + section("Investigation handling") + [p("Do not convert these requests into facts. Causes that depend on an OEM answer should remain provisional, with the missing evidence explicitly attached to the branch. Other supported branches may continue in parallel.")],
    )


def build_challenge_documents():
    """Build low-authority or conflicting evidence used to test model skepticism."""
    story = header(
        "Superseded Drawing Note - Similar Stand Variant",
        "R3-CH-001",
        "A synthetic, superseded engineering note found in an uncontrolled folder. It is deliberately easy to misuse if revision and equipment applicability are ignored.",
    )
    story += section("Document-control metadata")
    story.append(status_table([["Field", "Recorded value", "Status"], ["Title", "Roughing Mill Carrier Link Retention - Stand Variant", "Synthetic scenario fact"], ["Revision", "Rev D - superseded", "Warning"], ["Applies to", "R2 legacy configuration; R3 applicability not established", "Not established"], ["Controlled-copy status", "Uncontrolled scan; no current approval stamp", "Low authority"]], [1.55 * inch, 4.35 * inch, 1.25 * inch]))
    story += section("Excerpt")
    story.append(p("The legacy note depicts a cap plate above the yoke pocket and calls it a positive link hold-down. A handwritten margin annotation says, 'same all roughers,' but the author and date of the annotation are not identified."))
    story += section("Required handling")
    story.append(bullets(["Do not apply the cap-plate requirement to R3 without a current R3 drawing or engineering confirmation.", "Treat the handwritten annotation as an unattributed claim.", "Retain the record because it may identify a design-history question, not because it proves an R3 defect."]))
    build_pdf(CHALLENGE / "01_Superseded_Similar_Stand_Drawing_Note.pdf", story)

    story = header(
        "Anonymous Handwritten Turnover Note",
        "R3-CH-002",
        "A synthetic low-reliability note supplied without a verified author, time, or chain of custody.",
    )
    story += section("Transcribed note")
    story.append(Table([[rich("<font size='15'><i>Thought the keeper looked out last night - told somebody near the stand. Check before restart.</i></font>", BODY)]], colWidths=[7.15 * inch], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFFBEA")), ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#B4974A")), ("TOPPADDING", (0, 0), (-1, -1), 18), ("BOTTOMPADDING", (0, 0), (-1, -1), 18)])))
    story += section("Provenance check")
    story.append(status_table([["Question", "Finding", "Status"], ["Who wrote it?", "Unknown.", "Not established"], ["When was it written?", "Found after the event; no reliable creation time.", "Not established"], ["Which keeper?", "No stand, component, or side identifier appears in the note.", "Not established"], ["Was the statement first-hand?", "Unknown.", "Not established"], ["Does it conflict with other evidence?", "The recovered R3 keeper was documented as installed after the fall; pre-event state still requires direct evidence.", "Open / reconcile"]], [1.75 * inch, 4.2 * inch, 1.2 * inch]))
    build_pdf(CHALLENGE / "02_Anonymous_Turnover_Note.pdf", story)

    story = header(
        "Forwarded Email - Possible Crane Contact",
        "R3-CH-003",
        "A synthetic hearsay email with a confident subject line but no first-hand observation. It tests whether the model checks operational logs and source quality.",
    )
    story += section("Email metadata")
    story.append(table([["From", "To", "Sent", "Subject"], ["Outage distribution list member", "R3 investigation mailbox", "10/15/2024 - 8:12 AM", "Crane probably bumped the carrier beam"]], [1.65 * inch, 1.9 * inch, 1.5 * inch, 2.1 * inch]))
    story += section("Message body")
    story.append(p("Someone on nights said a crane may have been close to the stand during roll work. That would explain why the beam came loose. I was not in the bay and do not know which crane movement or time they meant."))
    story += section("Source-quality findings")
    story.append(status_table([["Factor", "Finding", "Status"], ["First-hand?", "No.", "Low authority"], ["Identified original speaker?", "No.", "Not established"], ["Specific time / lift / equipment?", "No.", "Not established"], ["Relevant evidence comparison", "The relevant-interval crane log, controller record, witnesses, and video report no crane activity at the event time.", "Contradicted for event interval"], ["Potential residual lead", "Earlier roll-removal interaction can be checked against the prior-shift lift records and physical marks.", "Open / bounded"]], [1.7 * inch, 4.1 * inch, 1.35 * inch]))
    build_pdf(CHALLENGE / "03_Unverified_Crane_Rumor_Email.pdf", story)


def build_manifest():
    story = header(
        "R3 Carrier Beam Test Document Set - User Index",
        "R3-INDEX-001",
        "USER GUIDE - do not upload this index as incident evidence when testing unguided model discovery.",
    )
    story += section("How to use the package")
    story.append(
        table(
            [
                ["Stage", "Folder", "When to supply", "What it tests"],
                ["Default library", "01_default_references", "Before incidents are created; shared across runs.", "Baseline standards, plant vocabulary, equipment orientation, source hierarchy."],
                ["Starter evidence", "02_starter_documents", "Attach with the initial incident description.", "Step-0 understanding, tagging, initial specialist fan-out, evidence-gap recognition."],
                ["Requested evidence", "03_requested_evidence", "Provide only when the app asks for the matching record.", "Retrieval, question handling, provenance, contradiction handling, knowledge-base growth, causal analysis."],
                ["Challenge evidence", "04_challenge_evidence", "Introduce only after a related branch exists.", "Revision control, source skepticism, hearsay resistance, and contradiction handling."],
            ],
            [1.2 * inch, 1.75 * inch, 2.25 * inch, 1.95 * inch],
        )
    )
    story += section("Default library contents")
    story.append(bullets(["Partner-provided Safety Handbook and relevant safety standards are copied unchanged into the default folder.", "R3_Area_Orientation.pdf supplies conceptual location vocabulary.", "R3_Roll_Balance_System_Primer.pdf supplies bounded component and energy context.", "R3_Outage_Roles_and_Records_Guide.pdf maps likely sources without answering the incident."]))
    story += section("Recommended starter upload")
    story.append(bullets(["Preliminary_Incident_Notification_16515.pdf", "Initial_Scene_Sketch_and_Timeline.pdf", "Initial_Evidence_Register.pdf"]))
    story += section("Requested-evidence catalog")
    rows = [["File", "Expected request trigger"]]
    catalog = [
        ("01_Mechanical_Assembly_and_Retention_Record.pdf", "Design, retention, stopper, keeper, yoke, or load-path question."),
        ("02_Energy_Control_Plan.pdf", "Required isolation boundary, gravity control, or verification question."),
        ("03_Lockout_Verification_Record.pdf", "What was actually isolated, verified, signed, or transferred."),
        ("04_Shift_Turnover_Log.pdf", "Previous-shift sequence, open conditions, or handoff."),
        ("05_Outage_Work_Scope_and_Sequence.pdf", "Planned task, sequence, hold point, or change control."),
        ("06_JJHAC_JSHA_Record.pdf", "Hazard recognition, controls, briefing, PPE, or task planning."),
        ("07_Witness_Statement_Packet.pdf", "Observed motion, personnel activity, sound, or visibility."),
        ("08_Crane_Activity_Log.pdf", "Crane lift, rigging, or equipment interaction."),
        ("09_Hydraulic_Status_and_Bleed_Verification.pdf", "Pressure state, bleed, decay, or hydraulic support."),
        ("10_Scene_Photo_Index_and_Measurement_Log.pdf", "As-found position, imagery, dimensions, or physical marks."),
        ("11_Post_Event_Mechanical_Inspection.pdf", "Damage, wear, seating, fracture, or failure mode."),
        ("12_Similar_Stand_Inspection.pdf", "Comparison, common mode, or abnormal configuration."),
        ("13_Scaffold_and_Pit_Occupancy_Record.pdf", "Exposure window, scaffold condition, access, or potential injury."),
        ("14_Contractor_Crew_Qualifications.pdf", "Who was involved, role, authorization, or competence."),
        ("15_Video_Review_Log.pdf", "Exact timing, visible interaction, or motion sequence."),
        ("16_OEM_Engineering_Information_Request.pdf", "Authoritative design requirement not established elsewhere."),
    ]
    rows.extend(catalog)
    story.append(table(rows, [3.55 * inch, 3.6 * inch], small=True))
    story += section("Ground-truth discipline")
    story.append(bullets(["Every incident-specific record is synthetic and labeled on every page.", "Historical-source facts are explicitly distinguished from added synthetic scenario facts.", "Open and pending fields must remain unresolved until evidence is supplied.", "The package provides evidence, not an answer key or a required root cause."]))
    build_pdf(OUT / "R3_Test_Document_Set_User_Index.pdf", story)


def build_readme():
    text = """# R3 carrier beam RCA app test documents

This package is organized by the three evidence channels supported by the app.

- `01_default_references/`: load once as shared default knowledge. It contains unchanged partner reference PDFs plus synthetic R3 orientation material.
- `02_starter_documents/`: attach when creating the R3 incident.
- `03_requested_evidence/`: hold back and provide only when the answer-fetching flow asks for the corresponding evidence.

Open `R3_Test_Document_Set_User_Index.pdf` for the complete stage-by-stage catalog. Do not upload the user index as incident evidence during an unguided test because it lists all available records.

All newly authored incident records are marked **SYNTHETIC TEST RECORD - NOT AN ACTUAL COMPANY RECORD**. Historical-source facts, synthetic scenario facts, and unresolved items are labeled separately inside the records.
"""
    (OUT / "README.md").write_text(text, encoding="utf-8")


def main():
    for folder in (DEFAULTS, STARTER, REQUESTED, CHALLENGE):
        folder.mkdir(parents=True, exist_ok=True)
    build_default_documents()
    build_starter_documents()
    build_requested_documents()
    build_challenge_documents()
    build_manifest()
    build_readme()
    print(f"Built synthetic R3 document package at: {OUT}")


if __name__ == "__main__":
    main()

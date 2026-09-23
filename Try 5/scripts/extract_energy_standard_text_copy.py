#!/usr/bin/env python3
from pathlib import Path

from pypdf import PdfReader


root = Path(__file__).resolve().parents[1]
source = root / "output/pdf/r3-beam-test-case/01_default_references/PARTNER_REFERENCE_Energy_Isolation_Standard.pdf"
output = source.with_name("PARTNER_REFERENCE_Energy_Isolation_Standard_text_copy.txt")
reader = PdfReader(str(source))
header = (
    "DERIVED TEXT-ONLY ACCESS COPY FOR THE LOCAL RCA TEST APP\n"
    "Source: Energy Isolation Safety Standard CCS HSS STD 001.0, effective 2022-09-01.\n"
    "Refer to the original controlled PDF for layout, approvals, figures, and current revision status.\n\n"
)
pages = []
for index, page in enumerate(reader.pages, start=1):
    text = page.extract_text() or "[No machine-readable text on this page]"
    pages.append(f"--- SOURCE PDF PAGE {index} ---\n{text}")
output.write_text(header + "\n\n".join(pages), encoding="utf-8")
print(f"Created {output} ({output.stat().st_size} bytes)")

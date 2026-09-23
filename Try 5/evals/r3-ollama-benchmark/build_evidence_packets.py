#!/usr/bin/env python3
from pathlib import Path

from pypdf import PdfReader, PdfWriter


benchmark = Path(__file__).resolve().parent
case_root = benchmark.parents[1] / "output/pdf/r3-beam-test-case"


def merge(source_folder: Path, destination: Path, title: str) -> None:
    writer = PdfWriter()
    for source in sorted(source_folder.glob("*.pdf")):
        reader = PdfReader(str(source))
        for page in reader.pages:
            writer.add_page(page)
    writer.add_metadata({"/Title": title, "/Subject": "Synthetic RCA application evaluation evidence"})
    with destination.open("wb") as handle:
        writer.write(handle)
    print(f"Created {destination.name}: {destination.stat().st_size} bytes, {len(writer.pages)} pages")


merge(
    case_root / "03_requested_evidence",
    benchmark / "R3_consolidated_requested_evidence.pdf",
    "R3 consolidated requested evidence - synthetic test packet",
)
merge(
    case_root / "04_challenge_evidence",
    benchmark / "R3_challenge_evidence.pdf",
    "R3 low-authority and conflicting evidence - synthetic test packet",
)

combined = PdfWriter()
for packet_name in ("R3_consolidated_requested_evidence.pdf", "R3_challenge_evidence.pdf"):
    for page in PdfReader(str(benchmark / packet_name)).pages:
        combined.add_page(page)
combined.add_metadata({
    "/Title": "R3 full evidence response with challenge records",
    "/Subject": "Synthetic RCA application evaluation evidence",
})
combined_path = benchmark / "R3_full_evidence_with_challenges.pdf"
with combined_path.open("wb") as handle:
    combined.write(handle)
print(f"Created {combined_path.name}: {combined_path.stat().st_size} bytes, {len(combined.pages)} pages")

"""Pure routing and aggregation rules for HERA1 outputs."""


def destination(task, payload: dict) -> tuple[str, str | None]:
    if task.task_kind == "request_review" and payload.get("disposition") == "revise":
        return "evidence_worker", task.sender_id
    # Evidence judgments and clarification answers go to the Lead. The Lead
    # decides board changes, question dispatch, and any Specialist rerouting.
    return "lead", None


def aggregate_relations(parts: list[dict]) -> str:
    labels = {part["relation"] for part in parts}
    if "mixed" in labels:
        return "mixed"
    if "supports" in labels and labels.intersection({"weakens", "contradicts"}):
        return "mixed"
    if "weakens" in labels and "contradicts" in labels:
        return "mixed"
    if "contradicts" in labels:
        return "contradictory"
    if "supports" in labels:
        return "supportive"
    if "weakens" in labels:
        return "weakening"
    return "insufficient"


def aggregate_part_findings(findings: list[dict]) -> str:
    """Summarize one claim's separate source findings without erasing conflict."""
    labels = {finding["relation"] for finding in findings}
    if "supports" in labels and labels.intersection({"weakens", "contradicts"}):
        return "mixed"
    if "weakens" in labels and "contradicts" in labels:
        return "mixed"
    if "contradicts" in labels:
        return "contradicts"
    if "supports" in labels:
        return "supports"
    if "weakens" in labels:
        return "weakens"
    if "does_not_address" in labels:
        return "does_not_address"
    return "insufficient_or_unclear"

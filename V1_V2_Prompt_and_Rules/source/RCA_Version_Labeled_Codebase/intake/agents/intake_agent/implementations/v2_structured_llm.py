"""Enhanced intake: scope/identity collision screening and modality audit."""
from intake.agents.intake_agent.components.normalization import normalize_extraction


def normalize(raw):
    return normalize_extraction(raw)

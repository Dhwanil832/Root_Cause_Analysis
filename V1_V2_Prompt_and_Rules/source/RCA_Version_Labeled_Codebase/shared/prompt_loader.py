"""Load only repo-local .md prompts and record hashes for reproducibility."""
from __future__ import annotations
import hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def load(role:str,implementation:str):
    paths={
        'intake':'intake/agents/intake_agent/prompts',
        'specialist':'reasoning/specialist/prompts',
        'lead':'reasoning/lead/prompts',
        'evidence_worker':'reasoning/evidence_worker/prompts',
        'assessor':'reasoning/assessor/prompts',
    }
    if role not in paths:raise ValueError(f'Unknown role {role}')
    # Restrict to known-safe identifiers, no path traversal from YAML.
    if not implementation.replace('_','').isalnum():raise ValueError('Invalid implementation ID')
    path=ROOT/paths[role]/(implementation+'.md')
    text=path.read_text(encoding='utf8')
    if not text.strip():raise ValueError(f'Empty prompt {path}')
    return text,hashlib.sha256(text.encode()).hexdigest()

"""Deep merge full default configuration with small experiment overrides."""
from __future__ import annotations
from pathlib import Path
import copy
import yaml
ROOT=Path(__file__).resolve().parents[1]

def merge(base:dict,overrides:dict)->dict:
    result=copy.deepcopy(base)
    for key,value in overrides.items():
        if isinstance(value,dict) and isinstance(result.get(key),dict):
            result[key]=merge(result[key],value)
        else:result[key]=copy.deepcopy(value)
    return result

def load_config(path=None):
    default=yaml.safe_load((ROOT/'config/default.yaml').read_text())
    if path is None:return default
    p=Path(path)
    if not p.exists():
        alternative=ROOT/path
        if not alternative.exists():raise FileNotFoundError(f'Unknown configuration: {path}')
        p=alternative
    override=yaml.safe_load(p.read_text()) or {}
    if not isinstance(override,dict):raise ValueError('Config file must contain a YAML object')
    return merge(default,override)

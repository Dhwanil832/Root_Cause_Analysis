"""Minimal local .env loader; never prints or overwrites existing environment secrets."""
from __future__ import annotations
from pathlib import Path
import os,re

def load_env_file(path):
    p=Path(path)
    if not p.is_file():return 0
    count=0
    for line in p.read_text(encoding='utf8').splitlines():
        line=line.strip()
        if not line or line.startswith('#') or '=' not in line:continue
        key,value=line.split('=',1)
        key=key.strip()
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',key):continue
        value=value.strip()
        if len(value)>=2 and value[0]==value[-1] and value[0] in {'"',"'"}:value=value[1:-1]
        if key not in os.environ and value:
            os.environ[key]=value;count+=1
    return count

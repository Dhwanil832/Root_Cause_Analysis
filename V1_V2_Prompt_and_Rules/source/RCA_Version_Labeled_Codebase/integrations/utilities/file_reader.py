"""Basic plain-text document adapter; do not silently parse opaque binary files."""
from pathlib import Path
import json

def read_document(path):
    path=Path(path)
    if path.suffix.lower() in {'.md','.txt','.text','.csv'}:
        return path.read_text(encoding='utf8')
    if path.suffix.lower()=='.json':
        obj=json.loads(path.read_text(encoding='utf8'))
        if isinstance(obj,str):return obj
        if isinstance(obj,dict) and isinstance(obj.get('text'),str):return obj['text']
        return json.dumps(obj,ensure_ascii=False,indent=2)
    raise ValueError(f'Unsupported input {path.suffix}; convert scans/PDF/DOCX to text first')

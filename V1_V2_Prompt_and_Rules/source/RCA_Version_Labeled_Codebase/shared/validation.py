"""Human-readable validation errors and stable scoped identifiers."""
from __future__ import annotations
import hashlib,re
class ProposalError(ValueError):pass

def short_id(prefix,text):return prefix+hashlib.sha256(text.encode('utf8')).hexdigest()[:12]

def safe_atom(value,limit=90):
    if not isinstance(value,str) or not value.strip():raise ProposalError('Expected nonempty atom')
    out=re.sub(r'[^a-zA-Z0-9_.:-]+','_',value.strip())[:limit].strip('_')
    if not out:raise ProposalError('Empty normalized atom')
    return out

def required_quote(quote,text):
    if not isinstance(quote,str) or len(quote.strip())<8 or quote not in text:
        raise ProposalError('Evidence quote must be a verbatim source substring of at least 8 characters')
    return quote

def bounded_str(value,limit=500):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise ProposalError('Missing, empty, or overlong text field')
    return value.strip()

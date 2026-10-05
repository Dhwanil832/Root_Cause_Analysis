import sys, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent
ARM = ROOT/'runtime'
PACKAGE = ROOT/'benchmark/R3-investigation-v1'
sys.path.insert(0, str(ARM/'prototype'))
from rca import engine, provider, schema
from rca.storage import read, save, digest, now

def verify():
    lock=read(ARM/'runtime-lock.json')
    for f,h in lock['files'].items():
        assert hashlib.sha256((ARM/f).read_bytes()).hexdigest()==h, f
    assert engine.fingerprint()==lock['runtime_fingerprint']
    for f,h in read(PACKAGE/'FREEZE.json')['files'].items():
        assert hashlib.sha256((PACKAGE/f).read_bytes()).hexdigest()==h, f

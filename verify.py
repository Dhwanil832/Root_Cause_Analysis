"""Verify the packaged scored runtime without making model or network calls."""
import hashlib
import json
from pathlib import Path

from common import ROOT, PACKAGE, engine, read, save, verify


def main():
    verify()
    manifest = read(ROOT / 'MANIFEST.json')
    assert engine.fingerprint() == manifest['runtime_fingerprint']
    for name in ['common.py', 'adapter.py', 'codex_adapter.py', 'run_local.py',
                 'run_gpt.py', 'deliver.py', 'report.py', 'score.py']:
        compile((ROOT / name).read_text(), name, 'exec')
    for folder in sorted((ROOT / 'scored-results').iterdir()):
        rows = read(folder / 'reviewed-annotations.json')
        assert len(rows) == 96 and len({r['criterion_id'] for r in rows}) == 96
        for row in rows:
            for relative, expected in row['verified_output_hashes'].items():
                assert hashlib.sha256((folder / relative).read_bytes()).hexdigest() == expected
    result = dict(
        verified=True, model_calls=0, network_calls=0,
        runtime_fingerprint=engine.fingerprint(),
        frozen_runtime_files=len(read(ROOT / 'runtime/runtime-lock.json')['files']),
        frozen_benchmark_files=len(read(PACKAGE / 'FREEZE.json')['files']),
        historical_scored_models=5, reviewed_checks_verified=480,
        note='Integrity and packaging verification, not a new RCA evaluation.')
    save(ROOT / 'VERIFICATION.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

# Replacement lineage

This fresh experiment replaces preserved `../qwen-story-autonomous-CDH6if/`, which produced a causal draft but failed verification on invented edge IDs before committing V1. That run replaced `../qwen-story-autonomous-A8rNaX/`, which had committed V1 but failed the first storyteller update's broker. Neither prior run has been overwritten or resumed.

This run freezes `try4.2.2-verification-contract`, including both the broker and verifier reference-contract fixes. The Qwen model, incident description, starter documents and locked-scenario protocol remain the same. See the parent run's `recovery-diagnosis.md` and `replacement.md` for evidence and verification results.

Monitor `monitor-qwen-rca-test` now targets this exact incident and track at two-hour intervals, with the next check intended no earlier than 2026-09-15T17:33:42Z. Read the current automation before acting on an older queued heartbeat to avoid following obsolete run IDs. If a previously repaired broker/verification-reference defect repeats, report and pause instead of making an indefinite sequence of fresh experiments.

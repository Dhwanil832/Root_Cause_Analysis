# Replacement lineage

This fresh experiment replaces the preserved failed run `../qwen-story-autonomous-A8rNaX/`. The parent committed V1 and generated 16 storyteller answers, but its V2 broker failed on incompatible disposition/owner fields. See the parent's `recovery-diagnosis.md` and `replacement.md` for the raw checkpoint references and verified fix.

This run freezes `try4.2.1-broker-contract`, keeping the same Qwen model, locked R3 scenario and evidence protocol. The repair does not alter the parent incident, its V1, its released answers or historical records. The original monitor `monitor-qwen-rca-test` now points here and is set to check at two-hour intervals, with the first follow-up intended no earlier than 2026-09-15T14:37:16Z.

Only this replacement was launched during this repair check. If it repeats the same contract failure, the monitor must report and pause rather than start an indefinite repair/restart loop.

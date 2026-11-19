# Notes for Claude working in this repo

Read `HANDOFF.md` first: it says where v0.5 work stopped and what is waiting on a decision.
Saved preferences and project facts are in `.claude/memory/` (start with `MEMORY.md`).

## Standing rules
- Never name the company or the exact plant anywhere in this public repo.
- No Claude attribution (no `Co-Authored-By` trailer) in commits or PR text.
- Commit or push only when asked.
- Do not install packages or pull models without asking.
- Do not change code until the user agrees with the direction. Propose first.
- Build and test the role components (Assessor `hera1`, Specialist `sahs`, Intake `piris`,
  Evidence Worker `ewv3`) first; change the Lead (`cferp`) last.
- The model under test (gpt-oss:20b via Ollama) should make the judgments. Code keeps the
  books: IDs, quotes, versions, scheduling, status counting. Do not add regex or word-list
  rules that decide what text means.

## Commands
- Python: `.venv/bin/python` (create a venv and install the requirements on a new machine).
- Tests:
  `PYTHONPATH=V3_Neurosymbolic_Inspired:V3_Neurosymbolic_Inspired/tests .venv/bin/python -m unittest discover -s V3_Neurosymbolic_Inspired/tests -t V3_Neurosymbolic_Inspired`
- Closed-loop run (Ollama must be running, `ollama serve`):
  `.venv/bin/python V3_Neurosymbolic_Inspired/scripts/run_v3_closed_loop.py --provider ollama_native --model gpt-oss:20b --num-ctx 32768 --answer-reserve 6000 --reasoning-effort low --max-jobs 256 --max-rounds 12 --max-job-failures 25 --custodian fixed --output outputs/<name>.json`

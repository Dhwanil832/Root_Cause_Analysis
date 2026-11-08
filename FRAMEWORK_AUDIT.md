# Framework audit — V3 closed loop (read-only; no code changed by this audit)

Evidence: the 17 saved runs in `outputs/`, the latest run
(`r3_gpt-oss-20b_ctx16k_containment.json`), and the code paths named below.
"Verified" means I checked it in the run output or the code. "Inferred" means it
follows from what I saw but I have not isolated it.

## 1. Run history: what ended each run

Of 17 saved runs, 16 ended on the first rejected model reply or harness error. Only
the last run reached the end of the case, and only because failures became
contained. Every fix below was found by one run dying on it.

| # | Run (file suffix) | Ended by | Fixed? |
|---|---|---|---|
| 1-4 | closed_loop, qwen, gpt-oss, structured_ctx4096 | Specialist reply had the wrong JSON shape, or empty output at Ollama's 4096-token default context | Yes: schema sent as `format`, bounded retry, `--num-ctx` |
| 5 | herafail | HERA reply used `exact_quote`/null `timing` | Yes: HERA schemas |
| 6 | hera_schema | `stale` result aborted the run (HERA compares global board version, Lead compares per-dependency) | Yes: pinned version reader, stale routing |
| 7 | stalefix_membershipfail | candidate membership named `R1`, links were `R1:source:N` | Yes: IDs expanded |
| 8 | memberfix_concurrency | `concurrency limit reached` | Yes: scheduler skips blocked jobs |
| 9 | schedfix_nameerror | missing `CandidateLink` import | Yes |
| 10 | importfix_requestreview | request-review reply broke a rule | Partly: retry added |
| 11 | heraretry | completed (61 jobs, 5 of 17 materials assessed) | n/a |
| 12 | jobs256_contextcap | HERA context over limit (24 links) | Yes: capped at 8 links |
| 13 | linkcap_citation | rationale cited link IDs without the `cl:` prefix | Yes: IDs in error message |
| 14 | idsinmsg_proportionality | empty `proportionality` | Yes: review schema |
| 15 | reviewschema_outsidepacket | `mat_` ID written where `cl:` ID belongs | Contained, not prevented |
| 16 | dedupe_bridge | empty `inference_bridge` | Yes: prompt wording |
| 17 | containment | completed with 1 contained failure (the `mat_` slip) | n/a |

Pattern (verified): a rule in a prompt and the rule in the validator drifted apart
each time, and a single violation killed the run. Containment fixes the second
half. The first half (a systematic audit of every prompt rule against its
validator) has not been done.

## 2. Findings in the framework

### Blocking: timing and settling
- **F1 Unprompted documents invalidate everything (verified).** `PIRIS` marks a
  document `provenance_complete` only if it is already tied to a need or claim, so
  every unrequested upload is incomplete. `CFERP.stale_dependents` then marks every
  active job stale, and `workflow.register_material` links the document to every
  open need. Latest run: 240 stale jobs.
- **F2 The budget counts jobs, not model calls (verified).** A job that reuses an
  earlier judgment costs no model call but still uses a slot. Latest run: 252 of
  256 jobs used, 226 of them assessor jobs.
- **F3 There is no settled state (verified).** A run ends at the budget or the end
  of the script. 36 jobs were still queued at the end of the latest run, so it never
  reached "nothing left to do with what is available".
- **F4 Late documents are starved (verified).** 7 of 16 documents were ever
  assessed. The valve work-pack (E03) and the workshop record (E16) were not.

### Evidence quality
- **F5 Retrieval is noisy (verified).** No stopword removal, no minimum overlap,
  top 8 per slot always returned. 188 of 214 assessments found nothing. Offline
  replay earlier showed stopwords plus 2 shared terms cut links 64 to 25 and kept
  the key sentences. No neighbouring-sentence window, so a sentence next to the
  match (for example the missing sealing test) is not seen.
- **F6 Judging is loose (verified).** "The contact surface and link-arm lateral
  offset are not resolved" was judged to contradict "keeper plate inspected"; "no
  gross fracture recorded" was judged to support it. Repeat assessments of the same
  sentence disagreed.
- **F7 Claims are duplicated (verified).** "Backup rolls were removed during the
  outage" exists four times (P8, P8a, P12, P19); "keeper plate contact surfaces were
  not inspected" three times (P11, P25, P4b). Revisits re-propose rather than reuse.
- **F8 The board does not yet ask the main question (verified).** The three
  candidate links concern keeper inspection and roll removal. None proposes the
  hydraulic isolation / bleed-through chain that the reference board treats as
  central. No measure of overlap with the reference board exists yet.

### Requests
- **F9 Requests are rejected for reasons the output does not record (verified
  gap).** 13 reviews: 9 raw `eligible`, 4 raw `not_eligible`. 8 requests ended
  `rejected`. So at least 4 raw-eligible requests were overridden by HERA's
  post-checks (`hera1/engine.py` lines 345-358: evidence status, proportionality,
  "rationale must engage retrieved links", "must not say irrelevant", sensitive
  scope). The final request does not store which check fired. Inferred: the
  "engage the links" check is keyword-based and penalises an honest "none of these
  links are relevant", which is the correct statement when retrieval is noisy.
- **F10 Absence of a record counts as the record (verified).** Two reviews marked
  the keeper-inspection request `resolved` because a statement said the observer
  "did not record an inspection". That is the absence of a record, not the record.
  The runbook itself warns a no-match is not proof.
- **F11 Duplicate requests (verified).** "What was the hydraulic pressure level
  during the outage?" was raised three times with near-identical wording, and the
  shift-handover request four times. No request dedupe.

### Simulator and measuring
- **F12 The simulated custodian is the model under test (verified).**
  `select_fixture_response(model, …)`. Two models would get different documents.
- **F13 Arrivals depend on the queue (verified).** Waves arrive after the queue
  drains; none arrives while work is running.
- **F14 No ground truth in the scorecard (verified).** `score_run.py` reports
  workflow signals only. No comparison against the reference RCA board.
- **F15 One run is not a measurement (inferred).** Results vary run to run; no
  repeated-run tooling exists.

### Hygiene
- **F16 The test environment is not reproducible (verified).** The Python
  environment used for every live run lived in a temporary folder that has been
  wiped. Under the system Python, 18 of 298 V3 tests error because `clingo` is not
  installed (the other 280 pass). `requirements-sahs.txt` exists; nothing records
  or checks the environment. **Resolved for now:** a project venv at `.venv`
  (clingo 5.8.2) was created; V3 suite 298/298 pass, `tests_ollama` 19/19 pass
  (it needs the `PYTHONPATH` from `OLLAMA_ADAPTER.md`). Nothing yet checks that
  the environment exists before a run.
- **F17 Output size (verified).** 50 MB per run, mostly raw model responses.
- **F18 Unexplained registrations (verified, not understood).** The heraretry run
  registered 17 materials from a 16-document packet; the latest run logged 3
  `duplicate_material_observed` events.
- **F19 The board viewer has no tests (verified).**

## 3. What is solid (verified by tests or runs)
Per-job failure containment, structured output with bounded retries, stale
handling by pinned version, split-link rule IDs, scheduling past blocked jobs,
revisit coalescing, judgment reuse (about 74% fewer extraction calls), request
link cap, and the scorecard.

## 4. Not yet checked
Prompt-versus-validator audit of every role (Phase 2). Intake extraction quality
(the parse of E01-E16 into sentences). Whether the Specialist's rule base is
adequate for hydraulic mechanisms. Determinism controls (temperature and seed) on
the model calls.

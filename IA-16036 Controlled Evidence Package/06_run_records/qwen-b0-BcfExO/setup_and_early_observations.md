# Setup and early observations

Evaluator notes. This file is not available to the model. No final score until the run stops.

## Preflight

The original Try 4 app automatically includes all reference-library documents when creating an incident. A frozen copy of the existing code and prompts was launched at localhost:3001 with a new local D1 database/R2 bucket. No original storage, secrets or history was copied. Installed dependencies are shared through a symlink; application source and prompts were copied and hashed.

Only IA-I01 and the six B0 documents were ingested. All six document byte hashes and complete extracted texts match the frozen input copies. Both the empty initial library/history and installed Qwen digest were saved. The capture proxy records raw Ollama requests/responses without changing their messages or generation settings.

The first dispatch wrapper stopped at preflight, before any model request or stage checkpoint, because multipart encoding normalized description LF to CRLF. This is preserved in `failure.json` and `before-initialize.json`. The comparison was corrected to permit only newline normalization; the actual stored description is frozen in `frozen-rca-input.json`. The `--initialize-prepared` path checks zero earlier model requests and zero checkpoints before its only initialize call. This was a setup correction, not a model-stage retry or evidence revision.

## Observed input boundaries

- Capture 0001 (incident-understanding) receives at most 1,200 characters per document. D01, D02, D03 and S01 are truncated; S02 and S03 arrive complete. No previous version or submitted answers are present.
- Capture 0004 (evidence-adjudication) receives one 900-character excerpt for each of all six documents. Several end mid-sentence/table. The later S02 qualification that an unsigned acceptance field is not a valve-position fact is absent from this excerpt.
- The implementation of `buildEvidenceSegments` recognizes only R3-specific markers; generic documents get one first-900-character segment, not coverage of the whole document. This is a harness coverage limitation independent of model ability. Later answer retrieval may have different coverage and must be inspected separately.

## Early model behavior to trace into the final result

- Capture 0001 keeps pressure-loss origin uncertain and asks useful pressure-location, configuration/change and recovery questions.
- It also says Maintenance receiver M-A was present. S03 assigns M-A as receiver but does not establish physical presence. This unsupported detail is repeated in tagging.
- Its structured entity list in capture 0002 includes only U-A; the timeline includes only the 07:00 assignment review, despite other supplied entities and event times.
- Capture 0003 selects human, equipment-tool, procedure-planning, communication-supervision, maintenance-outage and isolation-loto. It uses unestablished presence/lack of acceptance to suggest a communication breakdown, although work was still in preparation.
- These observations are provisional. Check whether source adjudication, evidence processing and causal verification correct or amplify them before evaluating the final board.

No prompts, model settings or evidence were changed in response to these outputs. No external answer agent or storyteller was invoked.

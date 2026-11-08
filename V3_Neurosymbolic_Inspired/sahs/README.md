# SAHS Specialist v0.3

SAHS is a bounded, stateful abductive hypothesis generator. It proposes
candidate mechanisms, validates provenance and structure in Python, composes
conditional paths with Clingo/ASP, and returns candidate/history deltas to the
Lead. It does not assess evidence, set incident truth, write to the shared
board, or contact a human.

## What is implemented

- Versioned assignment contracts for initial, revision, and advance runs.
- Strict structured proposal validation with Python-assigned statuses and
  exact source excerpt/version checks.
- One required LLM proposal call and at most one targeted expansion call.
- Clingo candidate search with AND antecedents, alternative rules, bounded
  depth/models/runtime, explicit assumptions, and cycle rejection.
- Generic `system_mechanism` nodes cannot be treated as incident assumptions;
  the model must express an incident condition separately.
- Targeted expansions must add a rule for the assigned open frontier.
- Candidate lifecycle deltas, affected-branch history, no-op detection, and
  information-need links.
- A typed `graph_delta` in the result, so the Lead receives proposition text,
  lifecycle status, rule structure, mechanism basis, and source provenance
  alongside the candidate IDs.
- A boundary adapter for the supplied archive's configured Specialist model,
  claims, documents, and Kernel snapshot. It does not mutate the archive board.

## Install and run

Python 3.11 or later is required. Install Clingo and run the tests from the
workspace root:

```bash
python -m pip install -r requirements-sahs.txt
python -m unittest discover -s tests -v
```

The test suite uses the real Clingo solver. The LLM transport is exercised with
scripted responses; no external provider call is made.

## Entry points

Use the independent engine with any compatible proposal generator:

```python
result = SpecialistEngine(proposer, ClingoCandidateSolver(), history_store).run(assignment)
```

For the supplied RCA archive, instantiate `ArchiveSpecialistAdapter` with its
`Investigator`, make an assignment snapshot, then call `run`:

```python
adapter = ArchiveSpecialistAdapter(investigator)
assignment = adapter.assignment_from_archive(
    investigator,
    assignment_id="case-123-specialist-run-4",
    operation_goal="develop_mechanism",
    lead_direction={"focal_proposition_id": "...", "direction": "..."},
    mode="advance",
    focal_proposition_id="...",
    history=prior_sahs_history,
)
result = adapter.run(assignment)
```

The adapter reuses `investigator._models["specialist"]` through its
`ask(task, system, payload)` interface and records model audit data when those
archive fields are present. The integration caller remains responsible for
persisting `result.updated_history`, resolving no-op result references, and
having the Lead decide whether/how to apply candidate deltas to the board.

## Epistemic rules

- New incident events and component states default to `hypothetical`.
- A source passage supports a candidate rule's provenance, not the occurrence
  of its antecedents or consequent in this incident.
- A reported claim remains reported; it is not independently verified here.
- An Assessor label is read-only annotation.
- Solver paths are conditional structures with assumptions, never causal
  findings or a complete RCA.
- A bounded or open search is reported as partial/open; failure to find a path
  under the supplied graph is not evidence that no cause exists.

## Remaining integration work

The adapter is a boundary implementation, not a production hook inside the
archive's registry. Production wiring still needs a durable atomic
`RunHistoryStore`, result-reference retrieval for no-op retries, a Lead-owned
commit path, and an explicit configuration switch that preserves V1/V2. Run
the archive's own regression suite after adding that hook. No live model call
or V1/V2 shadow evaluation has been performed in this workspace.

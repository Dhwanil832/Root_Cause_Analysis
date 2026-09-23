# Run records — currently empty of model results

The templates in this folder do not contain generated questions, answers or scores. Create a separate run directory when execution is authorized. Do not overwrite templates with results.

Preserve at least these artifacts per completed pass:

- Identity/configuration: run ID, app version/hash, prompt hash, exact model/digest, sampling/context settings, package seal.
- Frozen input: allowed document IDs, document hashes, actual text supplied, approved prior answers and previous-board identity.
- Raw outputs and errors: actual stage packets where available; missing capture must be declared.
- Board and questions: IDs, types/status, edges, source mappings, merge lineage and all specialist recipients.
- Separate candidate and approved answer payloads; explicit approval time and approver.
- Evidence-release ledger and exact-match review ledger.
- Point scores with the target IDs and attribution for each miss.

No job is scheduled by these files. A fresh run should start at B0 only and stop after V1 for inspection.

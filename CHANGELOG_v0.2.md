# Combined archive v0.2

- Added a combined OpenRouter runner for V1 prompt-only, V2 full, and V3 on the staged synthetic R3 fixture.
- Added a fail-fast preflight for API credentials, local fixture paths, Clingo, and runner files. `--check-only` validates without making model calls.
- Made the combined and V1/V2 runners return failure when a profile is partial or failed.
- Added a runner-only `case_id` option to the extracted V1/V2 evaluation harness so the fixture retains its own case identity. The V1/V2 role implementations remain unchanged.
- Updated run instructions and clarified that the R3 corpus is synthetic and the three runs are exploratory, not an apples-to-apples quality benchmark.
- Validation: 219 workspace tests and 257 V3 package tests passed; entrypoint help, Python compilation, and no-call preflight passed. No live OpenRouter request was made because this runtime has no configured API key.

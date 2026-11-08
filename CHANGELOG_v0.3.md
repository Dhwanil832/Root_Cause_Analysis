# Combined archive v0.3

- Fixed the V3 Evidence Worker to Assessor adapter for Lead needs linked to multiple hypothesis claims. The Lead's slot-to-target associations are preserved, and candidate passages create distinct claim–passage links for separate Assessor review.
- Added a standard-library native Ollama `/api/chat` model adapter and a shared model-client factory.
- Wired native Ollama selection into V1/V2 model construction, V3 archive configuration, the V3 standalone runtime, and the combined V1/V2/V3 launchers.
- Added local Ollama model discovery/preflight, JSON mode, bounded retries, request timing/token metadata, and documented setup commands.
- Added mock-server adapter tests. These verify the HTTP contract without requiring a local Ollama server.
- Validation for this update: 176 V1/V2 tests, 259 V3 tests, and 6 native-adapter tests passed; Python compilation and all three launcher help checks passed. Adapter tests use a mock HTTP server. An actual local Ollama inference was not run because no Ollama server/model was configured in this workspace.

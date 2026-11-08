# v0.4 — Closed-loop synthetic scenario replay

- Added a V3 closed-loop runner that handles Lead-approved outbound request
  dispatch, fixture-bounded simulated custodian replies, PIRIS re-ingestion,
  and continuation of Specialist/Evidence Worker/Assessor processing.
- The simulated custodian can select only fixture item and request-slot IDs
  provided in its call. Python rejects unknown IDs and extra response fields.
- Non-selected documents continue as unrequested arrivals. A final no-match
  reply is explicitly labeled as a search limitation, not proof of absence.
- Output records the simulated response trace and states that no human was
  contacted. This remains a synthetic workflow simulation, not an authenticated
  R3 incident replay or a claim that the investigation reached a final RCA.
- Added unit coverage for response ID bounds and malformed custodian output.

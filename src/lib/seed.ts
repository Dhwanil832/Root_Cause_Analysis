import type { Fact, Thing } from "./types";

export const indianaHarborIncident = `At approximately 1:03 PM on October 14, 2024 (Turn 2), the R3 Exit Carrier Beam at the Indiana Harbor 80\" Hot Strip roughing mill fell from the yoke into the R3 mill pit, landing on the sled and a scaffold platform. No team members were in the pit at the time, though several contractor employees had worked in the pit throughout the morning, and two contractor employees walking beside the mill stand witnessed the fall. The area was red-flagged for investigation. The beam and its link were found intact with the keeper still installed; no damage was apparent on the yoke on which the link rests. A small mill window liner from the top operator side fell with the beam. No crane lifts involving this equipment were in progress or had occurred prior. On the previous shift, the work rolls and top and bottom backup rolls had been removed in preparation for outage work in the mill stand; the R3 top backup roll balance had been left isolated in the raised position, and the B hydraulics had been shut off and bled for work on that system.`;

export const seedFacts: Fact[] = [
  { id: "F-001", statement: "The R3 Exit Carrier Beam fell from the yoke into the R3 mill pit at approximately 1:03 PM on October 14, 2024.", source: "Neutral framing", verified: true },
  { id: "F-002", statement: "The beam landed on the sled and a scaffold platform.", source: "Neutral framing", verified: true },
  { id: "F-003", statement: "No team members were in the pit at the time of the fall.", source: "Neutral framing", verified: true },
  { id: "F-004", statement: "The beam and its link were found intact and the keeper remained installed.", source: "Neutral framing", verified: true },
  { id: "F-005", statement: "No apparent damage was found on the yoke where the link rests.", source: "Neutral framing", verified: true },
  { id: "F-006", statement: "A small mill window liner from the top operator side fell with the beam.", source: "Neutral framing", verified: true },
  { id: "F-007", statement: "No crane lifts involving this equipment were in progress or had occurred prior to the fall.", source: "Neutral framing", verified: true },
  { id: "F-008", statement: "On the previous shift, work rolls and top and bottom backup rolls were removed for outage work in the mill stand.", source: "Neutral framing", verified: true },
  { id: "F-009", statement: "The R3 top backup roll balance was left isolated in the raised position.", source: "Neutral framing", verified: true },
  { id: "F-010", statement: "B hydraulics were shut off and bled for work on that system.", source: "Neutral framing", verified: true },
];

export const seedThings: Thing[] = [
  { id: "T-001", name: "R3 Exit Carrier Beam", category: "equipment", provenance: "explicit" },
  { id: "T-002", name: "yoke", category: "equipment", provenance: "explicit" },
  { id: "T-003", name: "beam link and keeper", category: "equipment", provenance: "explicit" },
  { id: "T-004", name: "R3 mill pit", category: "location", provenance: "explicit" },
  { id: "T-005", name: "R3 top backup roll balance", category: "equipment", provenance: "explicit" },
  { id: "T-006", name: "B hydraulics", category: "equipment", provenance: "explicit" },
  { id: "T-007", name: "outage work", category: "work process", provenance: "explicit" },
];

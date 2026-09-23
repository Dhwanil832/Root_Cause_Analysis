import type { TagId } from './types';

export const TAG_LABELS: Record<TagId, string> = {
  human: 'Human involvement',
  electrical: 'Electrical incident',
  'equipment-tool': 'Equipment or tool involvement',
  'mobile-equipment': 'Mobile equipment / vehicle involvement',
  'crane-lifting': 'Crane, lifting, or suspended-load involvement',
  'stored-energy': 'Stored, released, or gravity energy',
  'process-material': 'Process or material involvement',
  'work-environment': 'Work-environment involvement',
  'procedure-planning': 'Procedure / planning involvement',
  'communication-supervision': 'Communication / supervision involvement',
  'maintenance-outage': 'Maintenance, outage, or non-routine work',
  'isolation-loto': 'Isolation / LOTO involvement',
  'rail-locomotive': 'Rail / locomotive involvement',
  'animal-wildlife': 'Animal / wildlife / insect involvement',
  'other-novel': 'Other / novel condition',
};

export const TAG_KEYWORDS: Record<TagId, string[]> = {
  human: ['worker', 'employee', 'contractor', 'person', 'operator', 'witness', 'injury', 'team member', 'crew'],
  electrical: ['electrical', 'energized', 'voltage', 'arc flash', 'shock', 'panel', 'circuit', 'wiring', 'battery'],
  'equipment-tool': ['equipment', 'machine', 'beam', 'yoke', 'link', 'keeper', 'tool', 'component', 'roll', 'guard', 'sled'],
  'mobile-equipment': ['forklift', 'loader', 'truck', 'trailer', 'vehicle', 'cart', 'mobile equipment'],
  'crane-lifting': ['crane', 'hoist', 'rigging', 'sling', 'suspended', 'lift', 'hook', 'chainfall'],
  'stored-energy': ['fell', 'fall', 'dropped', 'pressure', 'hydraulic', 'pneumatic', 'gravity', 'raised', 'released', 'spring', 'tension'],
  'process-material': ['molten', 'slag', 'steel', 'chemical', 'gas', 'fume', 'steam', 'hot', 'fluid', 'material', 'weld'],
  'work-environment': ['pit', 'scaffold', 'ladder', 'platform', 'height', 'open hole', 'weather', 'lighting', 'ventilation', 'floor'],
  'procedure-planning': ['plan', 'procedure', 'permit', 'jsa', 'checklist', 'preparation', 'scope', 'planned'],
  'communication-supervision': ['shift', 'handover', 'supervisor', 'radio', 'contractor', 'coordination', 'witness'],
  'maintenance-outage': ['maintenance', 'outage', 'repair', 'removed', 'shutdown', 'startup', 'non-routine', 'work rolls'],
  'isolation-loto': ['isolated', 'lockout', 'tagout', 'loto', 'bled', 'de-energized', 'zero energy', 'shut off'],
  'rail-locomotive': ['rail', 'locomotive', 'rail car', 'trackmobile', 'switching', 'coupler', 'derail'],
  'animal-wildlife': ['animal', 'wildlife', 'bird', 'insect', 'bee', 'wasp', 'snake', 'nest', 'bite', 'sting'],
  'other-novel': [],
};

export const QUESTION_CATALOG: Record<TagId, Array<{
  intent: string;
  text: string;
  rationale: string;
  evidence: string[];
}>> = {
  human: [
    { intent: 'people-roles', text: 'Who was involved, exposed, or witnessing the work, and what was each person’s role?', rationale: 'Establishes actors without assuming human error.', evidence: ['crew list', 'contractor roster', 'witness statements'] },
    { intent: 'work-goal', text: 'What was each involved person trying to accomplish immediately before the event?', rationale: 'Connects actions to the work context.', evidence: ['interviews', 'job assignment', 'shift log'] },
    { intent: 'competence', text: 'What qualifications, task familiarity, authorization, and relevant training applied to the people involved?', rationale: 'Tests whether capability and authorization shaped exposure.', evidence: ['training records', 'qualification matrix', 'authorization record'] },
    { intent: 'human-conditions', text: 'Could workload, fatigue, time pressure, ergonomics, visibility, or PPE have affected what people could perceive or do?', rationale: 'Explores performance-shaping conditions.', evidence: ['shift schedule', 'PPE record', 'field observations'] },
  ],
  electrical: [
    { intent: 'asset-identity', text: 'What electrical asset, circuit, control, conductor, or power source could be involved?', rationale: 'Defines the possible electrical system boundary.', evidence: ['single-line diagram', 'asset record', 'photographs'] },
    { intent: 'energy-state', text: 'What was the confirmed electrical energy state immediately before and during the event?', rationale: 'Separates assumed from verified energy state.', evidence: ['switching record', 'meter readings', 'relay logs'] },
    { intent: 'electrical-signs', text: 'What evidence shows arcing, shock, overheating, a trip, damaged wiring, battery involvement, or another abnormal electrical condition?', rationale: 'Screens distinct electrical causal paths.', evidence: ['damage photographs', 'trip history', 'inspection results'] },
    { intent: 'electrical-work', text: 'Was work occurring on or near energized parts, panels, wiring, controls, or batteries?', rationale: 'Establishes interaction and exposure.', evidence: ['work order', 'energized-work permit', 'interviews'] },
  ],
  'equipment-tool': [
    { intent: 'asset-identity', text: 'What equipment, component, attachment, interface, or tool was involved, and what function did it serve?', rationale: 'Establishes the physical system under investigation.', evidence: ['drawings', 'manual', 'asset hierarchy'] },
    { intent: 'expected-actual', text: 'What was the equipment expected to do, and what did it actually do?', rationale: 'Defines the deviation to explain.', evidence: ['operating standard', 'event chronology', 'control data'] },
    { intent: 'physical-condition', text: 'What was its physical condition, alignment, support, guarding, and configuration before and after the event?', rationale: 'Tests condition and setup pathways.', evidence: ['photographs', 'inspection', 'measurements'] },
    { intent: 'maintenance-history', text: 'What inspection, maintenance, modification, defect, or previous abnormality history exists for the equipment?', rationale: 'Tests latent condition and recurrence.', evidence: ['CMMS history', 'inspection reports', 'defect log'] },
  ],
  'mobile-equipment': [
    { intent: 'movement-state', text: 'What mobile equipment was involved, and what were its position, direction, speed, load, and task?', rationale: 'Reconstructs movement.', evidence: ['telematics', 'CCTV', 'operator statement'] },
    { intent: 'route-visibility', text: 'What route, clearance, surface, traffic pattern, line of sight, and pedestrian exposure existed?', rationale: 'Tests environment and visibility.', evidence: ['site plan', 'photographs', 'measurements'] },
    { intent: 'vehicle-condition', text: 'What was the condition of brakes, steering, tires, alarms, restraints, lights, and attachments?', rationale: 'Screens equipment failure.', evidence: ['pre-use inspection', 'post-event inspection', 'maintenance record'] },
  ],
  'crane-lifting': [
    { intent: 'lift-system', text: 'What lifting equipment, rigging, attachments, and load were involved?', rationale: 'Defines the lifting system.', evidence: ['lift plan', 'rigging list', 'photographs'] },
    { intent: 'load-state', text: 'What stage of lifting, suspension, travel, landing, or release existed at the time?', rationale: 'Reconstructs load state.', evidence: ['witness statements', 'crane log', 'video'] },
    { intent: 'lift-capacity', text: 'How were weight, center of gravity, capacity, attachment points, and stability established?', rationale: 'Tests lift suitability.', evidence: ['capacity chart', 'engineering data', 'rigging calculation'] },
    { intent: 'exclusion-zone', text: 'What line-of-fire and exclusion-zone controls protected people near or beneath the load?', rationale: 'Tests exposure controls.', evidence: ['barricade plan', 'field photographs', 'briefing record'] },
  ],
  'stored-energy': [
    { intent: 'energy-state', text: 'What forms of stored, supported, pressurized, tensioned, thermal, or gravity energy were present?', rationale: 'Identifies credible energy paths.', evidence: ['energy-control assessment', 'system drawing', 'measurements'] },
    { intent: 'restraint', text: 'What supported or restrained the energy in normal conditions, and what was its observed state?', rationale: 'Locates the primary restraint.', evidence: ['component inspection', 'drawings', 'photographs'] },
    { intent: 'release-sequence', text: 'What changed immediately before the movement or release, and what physical evidence establishes the sequence?', rationale: 'Tests release mechanism.', evidence: ['event chronology', 'damage pattern', 'control logs'] },
    { intent: 'energy-path', text: 'What people, objects, structures, or work areas were within the potential energy path?', rationale: 'Defines actual and potential exposure.', evidence: ['scene map', 'crew locations', 'photographs'] },
  ],
  'process-material': [
    { intent: 'process-state', text: 'What process and material were involved, and what state or condition was expected?', rationale: 'Defines process baseline.', evidence: ['process log', 'material specification', 'operator record'] },
    { intent: 'material-properties', text: 'What were the actual temperature, pressure, composition, moisture, quantity, shape, and stability?', rationale: 'Tests material-driven pathways.', evidence: ['samples', 'sensor data', 'lab results'] },
    { intent: 'containment', text: 'What containment, separation, cooling, ventilation, or handling controls applied?', rationale: 'Tests process controls.', evidence: ['P&ID', 'inspection', 'alarm history'] },
  ],
  'work-environment': [
    { intent: 'area-layout', text: 'What physical features of the work area—including pits, platforms, access routes, openings, and clearances—were relevant?', rationale: 'Defines the exposure geography.', evidence: ['scene plan', 'photographs', 'measurements'] },
    { intent: 'environment-state', text: 'What were the lighting, visibility, surface, housekeeping, weather, noise, temperature, and ventilation conditions?', rationale: 'Screens environmental influences.', evidence: ['field observations', 'monitoring data', 'weather record'] },
    { intent: 'temporary-area', text: 'Had scaffolds, barriers, exclusion zones, temporary access, or outage work changed the normal area configuration?', rationale: 'Tests temporary conditions.', evidence: ['scaffold tag', 'barricade plan', 'outage map'] },
  ],
  'procedure-planning': [
    { intent: 'work-scope', text: 'What work was intended, and what procedure, plan, permit, risk assessment, or checklist governed it?', rationale: 'Defines planned work and controls.', evidence: ['job plan', 'permit', 'risk assessment'] },
    { intent: 'plan-fit', text: 'Did the plan match the actual equipment, hazards, sequence, staffing, and field conditions?', rationale: 'Tests work-as-imagined against work-as-done.', evidence: ['field walkdown', 'interviews', 'revision history'] },
    { intent: 'change-control', text: 'What changes, discoveries, or deviations occurred, and how were they evaluated and authorized?', rationale: 'Tests adaptation and change management.', evidence: ['change log', 'approvals', 'shift notes'] },
  ],
  'communication-supervision': [
    { intent: 'people-roles', text: 'Who owned, directed, performed, coordinated, and observed the work at each stage?', rationale: 'Clarifies authority and interfaces.', evidence: ['organization chart', 'work assignment', 'interviews'] },
    { intent: 'handoff', text: 'What shift, crew, contractor, or department handoffs occurred, and what information was transferred and confirmed?', rationale: 'Tests continuity across boundaries.', evidence: ['shift log', 'handover notes', 'radio records'] },
    { intent: 'escalation', text: 'Were abnormal conditions, concerns, or scope changes reported, understood, and resolved before work continued?', rationale: 'Tests feedback and stop-work paths.', evidence: ['issue log', 'supervisor notes', 'interviews'] },
  ],
  'maintenance-outage': [
    { intent: 'work-scope', text: 'What outage or maintenance work was planned, and what work had actually occurred by the event time?', rationale: 'Establishes work sequence.', evidence: ['outage schedule', 'work orders', 'shift log'] },
    { intent: 'abnormal-configuration', text: 'What equipment had been removed, bypassed, opened, raised, blocked, supported, or left in a non-normal configuration?', rationale: 'Identifies temporary system states.', evidence: ['configuration record', 'photographs', 'work package'] },
    { intent: 'handoff', text: 'What condition was the system expected to be left in between crews or shifts, and how was that condition communicated?', rationale: 'Tests state continuity.', evidence: ['turnover log', 'tags', 'crew interviews'] },
    { intent: 'return-to-service', text: 'What inspection, hold point, testing, and restoration steps were required before the next work stage?', rationale: 'Tests assurance barriers.', evidence: ['ITP', 'signoffs', 'test record'] },
  ],
  'isolation-loto': [
    { intent: 'isolation-boundary', text: 'What equipment and hazardous-energy boundary was intended to be isolated for the work?', rationale: 'Defines isolation scope.', evidence: ['LOTO sheet', 'energy-control diagram', 'work scope'] },
    { intent: 'energy-state', text: 'How was the intended safe or zero-energy state verified at the relevant times?', rationale: 'Tests verified rather than assumed state.', evidence: ['tryout record', 'meter reading', 'pressure gauge'] },
    { intent: 'isolation-points', text: 'What locks, tags, valves, disconnects, blocks, blanks, or restraints were applied, and by whom?', rationale: 'Reconstructs controls.', evidence: ['lockbox record', 'tag list', 'photographs'] },
    { intent: 'restoration', text: 'Were shift change, group LOTO, testing, temporary energization, or restoration conditions involved?', rationale: 'Tests transitions where state can change.', evidence: ['transfer record', 'restoration checklist', 'interviews'] },
  ],
  'rail-locomotive': [
    { intent: 'rail-movement', text: 'What locomotive, rail car, track, switch, or crossing was involved, and what movement was intended?', rationale: 'Defines rail operation.', evidence: ['switch list', 'movement authority', 'track diagram'] },
    { intent: 'rail-securement', text: 'What were the positions and securement states of the rolling stock before the event?', rationale: 'Tests unintended movement.', evidence: ['brake test', 'securement record', 'photographs'] },
    { intent: 'rail-condition', text: 'What was the condition of track, switches, derails, brakes, couplers, signals, and warning systems?', rationale: 'Screens equipment and infrastructure.', evidence: ['inspection', 'maintenance log', 'event recorder'] },
  ],
  'animal-wildlife': [
    { intent: 'biological-agent', text: 'What animal, wildlife, insect, nest, bite, sting, or biological condition was involved?', rationale: 'Identifies the exposure.', evidence: ['photographs', 'medical record', 'pest report'] },
    { intent: 'encounter-sequence', text: 'Where and when was it encountered, and what contact, startle, distraction, or secondary movement followed?', rationale: 'Reconstructs the event.', evidence: ['witness statement', 'scene inspection', 'camera footage'] },
    { intent: 'habitat-control', text: 'What inspection, warning, exclusion, pest-management, or habitat controls existed?', rationale: 'Tests preventive controls.', evidence: ['inspection log', 'pest-control record', 'work briefing'] },
  ],
  'other-novel': [
    { intent: 'novel-definition', text: 'What material condition is not represented by the existing tags, and what facts connect it to the event?', rationale: 'Prevents “other” from becoming an uncertainty bucket.', evidence: ['case facts', 'subject-matter review'] },
    { intent: 'taxonomy-fit', text: 'Which existing tag is closest, and why would using it hide or distort this investigation direction?', rationale: 'Tests whether a new category is actually needed.', evidence: ['tag comparison', 'historical cases'] },
  ],
};

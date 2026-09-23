import shared from '../../prompts/shared/system.md?raw';
import understanding from '../../prompts/incident-understanding/system.md?raw';
import structuring from '../../prompts/incident-structuring/system.md?raw';
import tagging from '../../prompts/tagging/system.md?raw';
import broker from '../../prompts/question-broker/system.md?raw';
import answerFetching from '../../prompts/answer-fetching/system.md?raw';
import evidenceProcessing from '../../prompts/evidence-processing/system.md?raw';
import evidenceAdjudication from '../../prompts/evidence-adjudication/system.md?raw';
import documentIntelligence from '../../prompts/document-intelligence/system.md?raw';
import causalAnalysis from '../../prompts/causal-analysis/system.md?raw';
import causalVerification from '../../prompts/causal-verification/system.md?raw';
import correctiveActions from '../../prompts/corrective-actions/system.md?raw';
import revision from '../../prompts/revision/system.md?raw';

import animalWildlife from '../../prompts/specialists/animal-wildlife/system.md?raw';
import communicationSupervision from '../../prompts/specialists/communication-supervision/system.md?raw';
import craneLifting from '../../prompts/specialists/crane-lifting/system.md?raw';
import electrical from '../../prompts/specialists/electrical/system.md?raw';
import equipmentTool from '../../prompts/specialists/equipment-tool/system.md?raw';
import human from '../../prompts/specialists/human/system.md?raw';
import isolationLoto from '../../prompts/specialists/isolation-loto/system.md?raw';
import maintenanceOutage from '../../prompts/specialists/maintenance-outage/system.md?raw';
import mobileEquipment from '../../prompts/specialists/mobile-equipment/system.md?raw';
import otherNovel from '../../prompts/specialists/other-novel/system.md?raw';
import procedurePlanning from '../../prompts/specialists/procedure-planning/system.md?raw';
import processMaterial from '../../prompts/specialists/process-material/system.md?raw';
import railLocomotive from '../../prompts/specialists/rail-locomotive/system.md?raw';
import storedEnergy from '../../prompts/specialists/stored-energy/system.md?raw';
import workEnvironment from '../../prompts/specialists/work-environment/system.md?raw';
import type { AgentId, TagId } from '@/src/domain/types';

export const PROMPT_VERSION = 'try4.2.4-evidence-coverage';

const stages: Partial<Record<AgentId, string>> = {
  'incident-understanding': understanding,
  'incident-structuring': structuring,
  tagging,
  'question-broker': broker,
  'answer-fetching': answerFetching,
  'evidence-processing': evidenceProcessing,
  'evidence-adjudication': evidenceAdjudication,
  'document-intelligence': documentIntelligence,
  'causal-analysis': causalAnalysis,
  'causal-verification': causalVerification,
  'corrective-actions': correctiveActions,
  revision,
};

export const specialistPrompts: Record<TagId, string> = {
  human,
  electrical,
  'equipment-tool': equipmentTool,
  'mobile-equipment': mobileEquipment,
  'crane-lifting': craneLifting,
  'stored-energy': storedEnergy,
  'process-material': processMaterial,
  'work-environment': workEnvironment,
  'procedure-planning': procedurePlanning,
  'communication-supervision': communicationSupervision,
  'maintenance-outage': maintenanceOutage,
  'isolation-loto': isolationLoto,
  'rail-locomotive': railLocomotive,
  'animal-wildlife': animalWildlife,
  'other-novel': otherNovel,
};

export function promptFor(stage: AgentId, specialist?: TagId) {
  const role = specialist ? specialistPrompts[specialist] : stages[stage];
  if (!role) throw new Error(`No prompt registered for ${stage}`);
  return `${shared}\n\n${role}`;
}

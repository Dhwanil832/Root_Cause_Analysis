import { z } from 'zod';
import { TAGS } from '@/src/domain/types';

const text = z.string();
const nonblank = z.string().trim().min(1);
const strings = z.array(z.string());
const decision = z.object({ summary: text });
export const directionSchema = z.object({ branch: nonblank, question: nonblank, decision: nonblank,
  evidenceNeeded: nonblank, ifPresent: nonblank, ifAbsent: nonblank,
  priority: z.enum(['discriminating', 'foundation']), findings: strings });
const node = z.object({ finding: nonblank, type: z.enum(['event','condition','barrier','change','human-decision-action']), reason: nonblank });
const edge = z.object({ from: nonblank, to: nonblank, type: z.enum(['caused','enabled','failed-to-prevent','preceded','combined-with']),
  rationale: nonblank, counterfactual: text, alternative: text, gap: text, findings: strings });
const branch = z.object({ id: nonblank, title: nonblank, mechanism: nonblank,
  status: z.enum(['open','disfavored','unresolved']), supporting: strings, opposing: strings, gap: nonblank, changeReason: nonblank });
const consultation = z.object({ branch: nonblank, domain: z.enum(TAGS), purpose: nonblank, findings: strings });
export const frameSchema = z.object({ summary: nonblank, focalEvent: nonblank, normalState: text, eventState: text,
  tags: z.array(z.object({ id: z.enum(TAGS), reason: nonblank, findings: strings })),
  nodes: z.array(node), edges: z.array(edge), branches: z.array(branch), consultations: z.array(consultation),
  directions: z.array(directionSchema),
  retiredNodes: z.array(z.object({ finding: nonblank, reason: nonblank })),
  withdrawnEdges: z.array(z.object({ id: nonblank, reason: nonblank })), decision });
export const consultSchema = z.object({ summary: nonblank, limitations: nonblank, findings: strings,
  directions: z.array(directionSchema), decision });
export const resolveSchema = z.object({ answers: z.array(z.object({ question: nonblank,
  status: z.enum(['answered','partial','conflicting','not-found','covered']), answer: text,
  findings: strings, references: strings, equivalentTo: z.string().nullable(), evidenceNeeded: text })), decision });
export const connectionSchema = z.object({ edges: z.array(edge),
  withdrawnEdges: z.array(z.object({ id: nonblank, reason: nonblank })),
  nodeRequests: z.array(z.object({ finding: nonblank, reason: nonblank })), decision });
export const investigationSchemas = { frame: frameSchema, consult: consultSchema, resolve: resolveSchema, refine: frameSchema, connect: connectionSchema };
export type InvestigationKind = keyof typeof investigationSchemas;
export function isInvestigationKind(kind: string): kind is InvestigationKind { return kind in investigationSchemas; }

/** Constrain source/fact/question identities without making the model repeat their text. */
export function investigationSchema(kind: InvestigationKind, findings: string[], sources: string[], questions: string[], nodeRefs: string[] = []) {
  const id = (values: string[]) => values.length ? z.enum(values as [string,...string[]]) : z.literal('__unavailable__');
  const list = (values: string[]) => values.length ? z.array(id(values)) : z.array(id(values)).max(0);
  const f = list(findings), d = directionSchema.extend({ findings: f });
  if (kind === 'resolve') return resolveSchema.extend({ answers: z.array(resolveSchema.shape.answers.element.extend({
    question: id(questions), findings: f, references: list(sources), equivalentTo: questions.length ? id(questions).nullable() : z.null(),
  })) });
  if (kind === 'consult') return consultSchema.extend({ findings: f, directions: z.array(d) });
  if (kind === 'connect') return connectionSchema.extend({
    edges: z.array(edge.extend({ from: id([...nodeRefs,'EVENT']), to: id([...nodeRefs,'EVENT']), findings: f })),
    nodeRequests: z.array(connectionSchema.shape.nodeRequests.element.extend({ finding: id(findings) })),
  });
  return frameSchema.extend({
    retiredNodes: z.array(frameSchema.shape.retiredNodes.element.extend({ finding: id(findings) })),
    nodes: z.array(node.extend({ finding: id(findings) })),
    // Node selection and connection generation are separate tasks. Supporting
    // notebook facts can never become arrow endpoints by accident.
    edges: z.array(edge).max(0).describe('Return []; connections are generated in a separate task using the committed node catalog.'),
    tags: z.array(frameSchema.shape.tags.element.extend({ findings: f })),
    branches: z.array(branch.extend({ supporting: f, opposing: f })),
    consultations: z.array(consultation.extend({ findings: f })), directions: z.array(d),
  });
}

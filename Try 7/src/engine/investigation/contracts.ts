import { z } from 'zod';
import { TAGS } from '@/src/domain/types';
import { explanationSchema } from '../explanations/contracts';

const text = z.string();
const nonblank = z.string().trim().min(1);
const strings = z.array(z.string());
const decision = z.object({ summary: text });
export const directionSchema = z.object({ branch: nonblank, question: nonblank, decision: nonblank,
  existingQuestion: z.string().nullable().default(null).describe('Existing Q reference when reusing a request; null for a genuinely new question. question contains readable wording, not an ID.'),
  subject:text.default(''),location:text.default(''),time:text.default(''),parts:z.array(nonblank).default([]),
  evidenceNeeded: nonblank, ifPresent: nonblank, ifAbsent: nonblank,
  priority: z.enum(['discriminating', 'foundation']), findings: strings });
const node = z.object({ finding: nonblank, type: z.enum(['event','condition','barrier','change','human-decision-action']), reason: nonblank });
const edge = z.object({ from: nonblank, to: nonblank, type: z.enum(['caused','enabled','failed-to-prevent','preceded','combined-with']),
  rationale: nonblank, counterfactual: text, alternative: text, gap: text, findings: strings,
  jointConditions:strings.default([]) });
const branch = explanationSchema;
const consultation = z.object({ branch: nonblank, domain: z.enum(TAGS), purpose: nonblank, findings: strings });
export const frameSchema = z.object({ summary: nonblank, focalEvent: nonblank, normalState: text, eventState: text,
  tags: z.array(z.object({ id: z.enum(TAGS), reason: nonblank, findings: strings })),
  nodes: z.array(node), edges: z.array(edge), branches: z.array(branch), consultations: z.array(consultation),
  directions: z.array(directionSchema),
  retiredNodes: z.array(z.object({ finding: nonblank, reason: nonblank })),
  withdrawnEdges: z.array(z.object({ id: nonblank, reason: nonblank })), decision });
export const consultSchema = z.object({ summary: nonblank, limitations: nonblank, findings: strings,
  directions: z.array(directionSchema), alternatives:z.array(branch).default([]), decision });
export const resolveSchema = z.object({ answers: z.array(z.object({ question: nonblank,
  status: z.enum(['answered','partial','conflicting','not-found','unavailable','covered']), answer: text,
  coverage:z.array(z.object({part:nonblank,status:z.enum(['answered','partial','conflicting','not-found','unavailable']),answer:text,references:strings,gap:text})).default([]),
  findings: strings, references: strings, equivalentTo: z.string().nullable(), evidenceNeeded: text })), decision });
export const connectionSchema = z.object({ edges: z.array(edge),
  withdrawnEdges: z.array(z.object({ id: nonblank, reason: nonblank })),
  nodeRequests: z.array(z.object({ finding: nonblank, reason: nonblank })), decision });
export const responseSchema=z.object({responses:z.array(z.object({question:nonblank,answerRevision:z.number().int().positive(),implication:nonblank})),directions:z.array(directionSchema),decision});
const correction=z.object({finding:nonblank,expectedRevision:z.number().int().positive(),statement:nonblank,
  subject:text,predicate:text,location:text,time:text,unit:text,qualifiers:text,references:strings,reason:nonblank});
export const revisionSchema=z.object({corrections:z.array(correction),branches:z.array(branch),
  impacts:z.array(z.object({target:nonblank,action:z.enum(['correct','strengthen','weaken','retain','withdraw','split','combine','not-applicable','unresolved']),reason:nonblank,findings:strings})),
  nodes:z.array(node),retiredNodes:z.array(z.object({finding:nonblank,reason:nonblank})),
  withdrawnEdges:z.array(z.object({id:nonblank,reason:nonblank})),directions:z.array(directionSchema),summary:text,decision});
export const investigationSchemas = { frame: frameSchema, consult: consultSchema, resolve: resolveSchema, refine: frameSchema, connect: connectionSchema,respond:responseSchema,revise:revisionSchema };
export type InvestigationKind = keyof typeof investigationSchemas;
export function isInvestigationKind(kind: string): kind is InvestigationKind { return kind in investigationSchemas; }

/** Constrain source/fact/question identities without making the model repeat their text. */
export function investigationSchema(kind: InvestigationKind, findings: string[], sources: string[], questions: string[], nodeRefs: string[] = [], assignedQuestions?:string[], findingRevisions?:Record<string,number>) {
  const id = (values: string[]) => values.length ? z.enum(values as [string,...string[]]) : z.literal('__unavailable__');
  const list = (values: string[]) => values.length ? z.array(id(values)) : z.array(id(values)).max(0);
  const f = list(findings), d = directionSchema.extend({ findings: f,
    existingQuestion:(questions.length?id(questions).nullable():z.null()).default(null) });
  const b=branch.extend({supporting:f,opposing:f,conditions:z.array(branch.shape.conditions.unwrap().element.extend({findings:f})).default([])});
  const assigned=assignedQuestions??questions;
  if(kind==='respond')return responseSchema.extend({responses:z.array(responseSchema.shape.responses.element.extend({question:id(assigned)}))
    .length(assigned.length).describe('One response per assigned question; other questions are context only.'),directions:z.array(d)});
  const correctionVariants=findings.filter(ref=>findingRevisions?.[ref]!==undefined).map(ref=>correction.extend({finding:z.literal(ref),
    expectedRevision:z.literal(findingRevisions![ref]).describe('Frozen current revision, not the proposed next revision.'),references:list(sources)}));
  const scopedCorrection=correctionVariants.length?z.discriminatedUnion('finding',correctionVariants as [typeof correctionVariants[number],...typeof correctionVariants]):correction.extend({finding:id(findings),references:list(sources)});
  if(kind==='revise')return revisionSchema.extend({corrections:z.array(scopedCorrection),
    branches:z.array(b),impacts:z.array(revisionSchema.shape.impacts.element.extend({findings:f})),nodes:z.array(node.extend({finding:id(findings)})),
    retiredNodes:z.array(revisionSchema.shape.retiredNodes.element.extend({finding:id(findings)})),directions:z.array(d)});
  if (kind === 'resolve') return resolveSchema.extend({ answers: z.array(resolveSchema.shape.answers.element.extend({
    question: id(assigned), findings: f, references: list(sources), equivalentTo: questions.length ? id(questions).nullable() : z.null(),
    coverage:z.array(resolveSchema.shape.answers.element.shape.coverage.unwrap().element.extend({references:list(sources)})).default([]),
  })).length(assigned.length).describe('One answer per assigned question. Other known questions may be equivalence targets, not additional answer assignments.') });
  if (kind === 'consult') return consultSchema.extend({ findings: f, directions: z.array(d),alternatives:z.array(b).default([]) });
  if (kind === 'connect') return connectionSchema.extend({
    edges: z.array(edge.extend({ from: id([...nodeRefs,'EVENT']), to: id([...nodeRefs,'EVENT']), findings: f,jointConditions:f.default([]) })),
    nodeRequests: z.array(connectionSchema.shape.nodeRequests.element.extend({ finding: id(findings) })),
  });
  return frameSchema.extend({
    retiredNodes: z.array(frameSchema.shape.retiredNodes.element.extend({ finding: id(findings) })),
    nodes: z.array(node.extend({ finding: id(findings) })),
    // Node selection and connection generation are separate tasks. Supporting
    // notebook facts can never become arrow endpoints by accident.
    edges: z.array(edge).max(0).describe('Return []; connections are generated in a separate task using the committed node catalog.'),
    tags: z.array(frameSchema.shape.tags.element.extend({ findings: f })),
    branches: z.array(b),
    consultations: z.array(consultation.extend({ findings: f })), directions: z.array(d),
  });
}

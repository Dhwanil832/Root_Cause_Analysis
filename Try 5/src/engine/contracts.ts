import { z } from 'zod';
import { TAGS } from '@/src/domain/types';
import { interpretationSchema } from './review/contract';
import { literalReviewSchema, literalReviewContract } from './review/literal-contract';

export const note = z.string();
export const refs = z.array(z.string().max(100));
export const questionSchema = z.object({ text: note, intent: note, decision: note, subject: note, location: note, time: note, references: refs });
export const findingSchema = z.object({
  statement: note, kind: z.enum(['observation','measurement','testimony','requirement','hypothesis','context']),
  subject: note, predicate: note, location: note, time: note, unit: note, qualifiers: note,
  references: refs, tags: z.array(z.enum(TAGS)), replaces: z.string().nullable(),
});
const decision = z.object({ summary: note });
export const readSchema = z.object({ findings: z.array(findingSchema), questions: z.array(questionSchema), decision });
export const understandSchema = z.object({ summary: note, focalEvent: note, normalState: note, eventState: note,
  entities: z.array(z.object({ name: note, description: note, references: refs })), questions: z.array(questionSchema), decision });
export const tagSchema = z.object({ tags: z.array(z.object({ id: z.enum(TAGS), reason: note, references: refs })), decision });
export const brokerSchema = z.object({ equivalentTo: z.string().nullable(), reason: note, decision });
export const answerSchema = z.object({ status: z.enum(['answered','partial','conflicting','not-found']), answer: note,
  references: refs, findings: z.array(findingSchema), evidenceRequest: note, decision });
export const reviewSchema = z.object({ status: z.enum(['supported','partial','unknown','contradicted','conflicting']),
  reason: note, supporting: refs, opposing: refs, questions: z.array(questionSchema), decision });
export const causalSchema = z.object({ disposition: z.enum(['node','context','question']),
  type: z.enum(['event','condition','barrier','change','human-decision-action']), label: note, detail: note,
  reason: note, references: refs,
  edges: z.array(z.object({ from: z.string(), to: z.string(), type: z.enum(['caused','enabled','failed-to-prevent','preceded','combined-with']),
    rationale: note, counterfactual: note, alternative: note, gap: note, references: refs })),
  questions: z.array(questionSchema), decision });
export const inquirySchema = z.object({
  observations: z.array(z.object({statement:note,references:refs,limitation:note})),
  explanations: z.array(z.object({id:z.string().min(1).max(100),title:note,mechanism:note,supporting:refs,opposing:refs,unresolved:note})),
  questions: z.array(questionSchema.extend({evidenceNeeded:note,contrasts:z.array(z.object({explanationId:z.string().max(100),expectedObservation:note,implication:note}))})),
  decision,
});
export const actionsSchema = z.object({ actions: z.array(z.object({ title: note, description: note,
  type: z.enum(['containment','elimination','substitution','engineering','administrative','ppe']), ownerRole: note,
  completionEvidence: note, effectivenessCheck: note })), decision });

export const schemas = { read: readSchema, understand: understandSchema, tag: tagSchema, specialist: readSchema,
  broker: brokerSchema, answer: answerSchema, interpret: interpretationSchema, review: literalReviewSchema, causal: causalSchema, inquiry:inquirySchema, verify: reviewSchema, actions: actionsSchema };

/** Actual call-local IDs constrain generation, not just validation afterwards. */
export function taskSchema(kind: keyof typeof schemas, sources: string[], findings: string[], questions: string[], targetStatement = '', sourceLines?:Record<string,number[]>): z.ZodType {
  const ids = (values:string[]) => values.length ? z.enum(values as [string,...string[]]) : z.literal('__no_reference_available__');
  const citations = (sources.length ? z.array(ids(sources)) : z.array(ids(sources)).max(0))
    .describe('Exact original-evidence S IDs only. No F IDs, commentary, punctuation, or invented IDs. Put explanation in reason/qualifiers.');
  const question = questionSchema.extend({references:citations});
  const finding = findingSchema.extend({references:citations,
    replaces:findings.length ? ids(findings).nullable().describe('Existing F ID only when correcting that finding; otherwise null.') : z.null()});
  if (kind==='read'||kind==='specialist') return readSchema.extend({findings:z.array(finding),questions:z.array(question)});
  if (kind==='understand') return understandSchema.extend({entities:z.array(z.object({name:note,description:note,references:citations})),questions:z.array(question)});
  if (kind==='tag') return tagSchema.extend({tags:z.array(z.object({id:z.enum(TAGS),reason:note,references:citations}))});
  if (kind==='broker') return brokerSchema.extend({equivalentTo:questions.length?ids(questions).nullable():z.null()});
  if (kind==='answer') return answerSchema.extend({references:citations,findings:z.array(finding)});
  if (kind==='interpret') return interpretationSchema.extend({targetStatement:z.literal(targetStatement)});
  if (kind==='review') return literalReviewContract(sources,targetStatement,sourceLines);
  if (kind==='verify') return reviewSchema.extend({supporting:citations,opposing:citations,questions:z.array(question)});
  if (kind==='inquiry') return inquirySchema.extend({
    observations:z.array(inquirySchema.shape.observations.element.extend({references:citations})),
    explanations:z.array(inquirySchema.shape.explanations.element.extend({supporting:citations,opposing:citations})),
    questions:z.array(inquirySchema.shape.questions.element.extend({references:citations})),
  });
  if (kind==='causal') return causalSchema.extend({references:citations,questions:z.array(question),edges:z.array(causalSchema.shape.edges.element.extend({
    from:ids([...findings,'EVENT']),to:ids([...findings,'EVENT']),references:citations,
  }))});
  return actionsSchema;
}

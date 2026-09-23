import { z } from 'zod';

export const CLAIM_REVIEW_POLICY = 'fixed-meaning-v4';
export const CLAIM_INTERPRETATION_POLICY = 'claim-meaning-v1';
const text = z.string();
export const meaningPartSchema = z.object({
  claimText: text.min(1).describe('Verbatim contiguous target fragment; preserve negation, alternatives and qualifications.'),
  claimType: z.enum(['record-observation','actual-state','actual-event','general-requirement','hypothesis']),
  assertion: text.min(1).describe('Equivalent explicit assertion, not a weaker statement that would be easier to support.'),
  scope: z.object({subject:text,location:text,time:text}),
  truthConditions: text.min(1).describe('What must be established for this exact assertion to be true; not an evidence verdict.'),
  ambiguities: z.array(text).describe('Material ambiguities in the wording alone; do not invent evidence gaps.'),
}).strict();
export const interpretationSchema = z.object({
  targetStatement: text, parts: z.array(meaningPartSchema).min(1), decision: z.object({summary:text}),
}).strict();
export interface ClaimInterpretation {
  policy: string; targetStatement: string;
  parts: Array<z.infer<typeof meaningPartSchema> & {partId:string}>;
}
export const evidenceSelectionSchema = z.object({source:z.string(),lines:z.array(z.number().int().min(1)).min(1)
  .describe('One-based original line numbers. The application copies quotations; do not generate them.')}).strict();
const judgmentFields = {
  partId: z.string(), establishes: text.min(1),
  counterexample: z.object({possible:z.boolean(),scenario:text}),
  missingPremises: z.array(text), reason: text.min(1),
};
// Required citations are part of the provider grammar, not merely a post-hoc warning.
export const claimPartSchema = z.discriminatedUnion('relation',[
  z.object({...judgmentFields,relation:z.literal('entailed'),evidence:z.array(evidenceSelectionSchema).min(1)}).strict(),
  z.object({...judgmentFields,relation:z.literal('contradicted'),evidence:z.array(evidenceSelectionSchema).min(1)}).strict(),
  z.object({...judgmentFields,relation:z.literal('not-established'),evidence:z.array(evidenceSelectionSchema)}).strict(),
]);
const conflictSideSchema=z.object({assertion:text.min(1),evidence:z.array(evidenceSelectionSchema).min(1)}).strict();
export const conflictSchema=z.object({
  affectsParts:z.array(z.string()).min(1),
  scope:z.object({subject:text.min(1),location:text,time:text}),
  sideA:conflictSideSchema,sideB:conflictSideSchema,
  reason:text.min(1),resolutionNeeded:text.min(1),
}).strict();
export const partQuestionSchema = z.object({
  text,intent:text,decision:text,subject:text,location:text,time:text,references:z.array(z.string()),
  requiredForParts:z.array(z.number().int().min(1)),
});
export const claimReviewSchema=z.object({
  targetStatement:text,
  interpretationIssue:text.describe('Empty if the fixed meaning is usable. Otherwise explain the mismatch; do not rewrite it.'),
  parts:z.array(claimPartSchema).min(1), evidenceConflicts:z.array(conflictSchema),
  questions:z.array(partQuestionSchema),decision:z.object({summary:text}),
}).strict();
export type ClaimReviewOutput=z.infer<typeof claimReviewSchema>;

export function claimReviewContract(sourceIds:string[],statement:string,sourceLines?:Record<string,number[]>,meaning?:ClaimInterpretation) {
  const id=sourceIds.length?z.enum(sourceIds as [string,...string[]]):z.literal('__no_reference_available__');
  const selections=sourceLines?sourceIds.flatMap(source=>{
    const lines=sourceLines[source]||[];
    return lines.length?[z.object({source:z.literal(source),lines:z.array(z.literal(lines as [number,...number[]])).min(1)}).strict()]:[];
  }):[];
  const selection=sourceLines&&selections.length?z.union([selections[0],...selections.slice(1)]):evidenceSelectionSchema.extend({source:id});
  const available=sourceLines?selections.length>0:sourceIds.length>0;
  const evidence=available?z.array(selection):z.array(selection).max(0);
  const partId=meaning?.parts.length?z.enum(meaning.parts.map(p=>p.partId) as [string,...string[]]):z.string();
  const fields={...judgmentFields,partId};
  const unknown=z.object({...fields,relation:z.literal('not-established'),evidence}).strict();
  const part=available?z.discriminatedUnion('relation',[
    z.object({...fields,relation:z.literal('entailed'),evidence:evidence.min(1)}).strict(),
    z.object({...fields,relation:z.literal('contradicted'),evidence:evidence.min(1)}).strict(),unknown,
  ]):unknown;
  const side=conflictSideSchema.extend({evidence:z.array(selection).min(1)});
  const conflict=conflictSchema.extend({affectsParts:z.array(partId).min(1),sideA:side,sideB:side});
  return claimReviewSchema.extend({
    targetStatement:z.literal(statement),parts:z.array(part).min(1),
    evidenceConflicts:available?z.array(conflict):z.array(conflict).max(0),
    questions:z.array(partQuestionSchema.extend({references:sourceIds.length?z.array(id):z.array(id).max(0)})),
  });
}

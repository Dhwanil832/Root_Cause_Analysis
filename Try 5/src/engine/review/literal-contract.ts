import { z } from 'zod';
import { evidenceSelectionSchema } from './contract';

export const CLAIM_REVIEW_POLICY='literal-claim-v5.5';
const text=z.string();
const side=z.object({assertion:text.min(1),evidence:z.array(evidenceSelectionSchema).min(1)}).strict();
export const sourceConflictSchema=z.object({
  impact:z.enum(['claim-truth','underlying-event-only']).describe('Does the disagreement prevent deciding this exact claim, or only the reality described by a record whose content is still known?'),
  scope:z.object({subject:text.min(1),location:text,time:text}),
  sideA:side,sideB:side,reason:text.min(1),resolutionNeeded:text.min(1),
}).strict();
const question=z.object({text,intent:text,decision:text,subject:text,location:text,time:text,references:z.array(z.string())});
const fields={
  targetStatement:text,
  claimType:z.enum(['record-observation','actual-state','actual-event','general-requirement','hypothesis','mixed']),
  establishes:text.min(1).describe('What the selected original evidence actually establishes, before judging the claim. Do not silently replace the target with this narrower observation.'),
  missingPremises:z.array(text).describe('Only information necessary to decide the asserted fact that the supplied evidence does not establish. Ordinary terminology already resolved by the records is not a gap.'),
  evidenceConflicts:z.array(sourceConflictSchema),
  reason:text.min(1).describe('Compare the complete original assertion with the evidence, including every qualification. Explain why it follows, fails, or remains unresolved.'),
  questions:z.array(question),decision:z.object({summary:text}),
};
const relation=z.enum(['entailed','partially-established','contradicted','not-established']);
function consistent(out:{relation:z.infer<typeof relation>;evidence:unknown[];missingPremises:string[]},ctx:z.RefinementCtx) {
  if(out.relation!=='not-established'&&!out.evidence.length)ctx.addIssue({code:'custom',path:['evidence'],message:'A definitive or partial judgment requires original evidence.'});
  if(out.relation==='entailed'&&out.missingPremises.length)ctx.addIssue({code:'custom',path:['missingPremises'],message:'An entailed claim cannot have an unresolved necessary premise.'});
  if(out.relation==='partially-established'&&!out.missingPremises.some(p=>p.trim()))ctx.addIssue({code:'custom',path:['missingPremises'],message:'Partial establishment requires a concrete missing premise.'});
}
// One shared shape, not four copies of every field and nested citation grammar.
// Cross-field checks still run before an answer can be committed.
export const literalReviewShape=z.object({...fields,relation,evidence:z.array(evidenceSelectionSchema)}).strict();
export const literalReviewSchema=literalReviewShape.superRefine(consistent);
export type LiteralReviewOutput=z.infer<typeof literalReviewSchema>;

export function literalReviewContract(sourceIds:string[],statement:string,sourceLines?:Record<string,number[]>) {
  const id=sourceIds.length?z.enum(sourceIds as [string,...string[]]):z.literal('__no_reference_available__');
  const selections=sourceLines?sourceIds.flatMap(source=>{
    const lines=sourceLines[source]||[];
    return lines.length?[z.object({source:z.literal(source),lines:z.array(z.literal(lines as [number,...number[]])).min(1)}).strict()]:[];
  }):[];
  const selection=sourceLines&&selections.length?z.union([selections[0],...selections.slice(1)]):evidenceSelectionSchema.extend({source:id});
  const available=sourceLines?selections.length>0:sourceIds.length>0;
  // With original passages available every result cites the relevant passage,
  // including when it establishes only the narrower known fact. With no text,
  // the only admissible result is not-established with no citations.
  const evidence=available?z.array(selection).min(1):z.array(selection).max(0);
  const boundSide=side.extend({evidence:z.array(selection).min(1)});
  const conflict=sourceConflictSchema.extend({sideA:boundSide,sideB:boundSide});
  const bound={...fields,targetStatement:z.literal(statement),
    evidenceConflicts:available?z.array(conflict):z.array(conflict).max(0),
    questions:z.array(question.extend({references:sourceIds.length?z.array(id):z.array(id).max(0)}))};
  // Parse structure/provenance here; apply-time consistency remains mandatory.
  // This lets a rejected judgment preserve its proposed evidence gap as a
  // question, without converting the verdict or accepting any of its facts.
  return z.object({...bound,relation:available?relation:z.literal('not-established'),evidence}).strict();
}

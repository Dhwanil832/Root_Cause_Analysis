import {z} from 'zod';
export const conditionSchema=z.object({id:z.string().min(1),statement:z.string().min(1),
  status:z.enum(['established','contradicted','unknown','conflicting']),findings:z.array(z.string()),
  expectedObservation:z.string(),scope:z.string()});
export const explanationSchema=z.object({id:z.string().min(1),title:z.string().min(1),mechanism:z.string().min(1),
  status:z.enum(['open','disfavored','unresolved','withdrawn','superseded']),supporting:z.array(z.string()),opposing:z.array(z.string()),
  gap:z.string().min(1),changeReason:z.string().min(1),
  applicability:z.string().default(''),assumptions:z.array(z.string()).default([]),
  conditions:z.array(conditionSchema).default([]),alternatives:z.array(z.string()).default([]),
  distinguishes:z.array(z.object({observation:z.string().min(1),ifEstablished:z.string(),ifRuledOut:z.string()})).default([]),
  replaces:z.array(z.string()).default([])});

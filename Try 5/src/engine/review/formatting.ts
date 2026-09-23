/** A formatting-only policy, frozen per input revision. Not a truth repair. */
export const REVIEW_FORMATTING_POLICY='explicit-no-missing-premises-v1';
export interface ReviewFormattingNormalization {
  policy:typeof REVIEW_FORMATTING_POLICY;
  field:'missingPremises';
  removed:string[];
}

const emptyMarkers=new Set([
  'none',
  'no missing premises',
  'no missing premises identified',
  'no unresolved necessary premises',
  'no missing premises for this claim',
]);
function emptyMarker(text:string,claimType:string) {
  const value=text.trim().toLowerCase().replace(/\s+/g,' ').replace(/\.$/,'');
  // Match the whole value, never a substring such as "none of the witnesses"
  // or "none, except that the timing remains unproved".
  return emptyMarkers.has(value)||(claimType==='record-observation'
    && value==='none for establishing the record observation itself');
}

export function normalizeReviewFormatting<T extends {claimType:string;missingPremises:string[]}>(out:T,policy?:string):
  {output:T;normalization?:ReviewFormattingNormalization} {
  if(policy!==REVIEW_FORMATTING_POLICY)return {output:out};
  const removed=out.missingPremises.filter(p=>emptyMarker(p,out.claimType));
  if(!removed.length)return {output:out};
  return {
    output:{...out,missingPremises:out.missingPremises.filter(p=>!emptyMarker(p,out.claimType))},
    normalization:{policy:REVIEW_FORMATTING_POLICY,field:'missingPremises',removed},
  };
}

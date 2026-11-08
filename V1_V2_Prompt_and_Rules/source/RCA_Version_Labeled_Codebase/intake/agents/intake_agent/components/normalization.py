"""Structured intake post-processing: detect identity/claim collisions and modality risks.

Raw text remains unchanged; this module does NOT pretend to extract facts from
text. It operates on model-proposed assertions and exposes uncertainty flags
for the Assessor rather than silently inventing a canonical interpretation.
"""
from __future__ import annotations
import re
from copy import deepcopy
from shared.validation import ProposalError


def normalize_extraction(raw):
    if not isinstance(raw,dict):raise ProposalError('Intake extraction must be a JSON object')
    if not isinstance(raw.get('assertions',[]),list):raise ProposalError('Expected an assertion list')
    result=deepcopy(raw)
    labels={};keys={};retained=[];warnings=[]
    for index,a in enumerate(result.get('assertions',[])):
        if not isinstance(a,dict):raise ProposalError('Intake assertion must be an object')
        try:
            label=a['semantic_label'];identity=(a['subject'],a['predicate'],a['scope'],a['configuration'])
        except KeyError as e:
            raise ProposalError(f'Incomplete assertion identity: {e}') from e
        if not isinstance(label,str) or not label.strip():
            raise ProposalError('Intake assertion label cannot be empty')
        if label in labels and labels[label]!=identity:
            raise ProposalError('Same semantic label applied to two distinct scoped assertions')
        labels[label]=identity
        polarity=bool(a.get('polarity',True))
        if identity in keys:
            other=keys[identity]
            if bool(other.get('polarity',True))!=polarity:
                raise ProposalError('Contradictory same-scope assertions in one document require distinct times or episode scopes')
            # Repeated same assertion adds no independent evidence. Keeping two
            # copies would inflate extractor output and provenance audit counts.
            warnings.append({'kind':'duplicate_assertion','index':index,'semantic_label':label})
            continue
        keys[identity]=a
        quote=a.get('quote','')
        basis=a.get('basis','assessed_source_assertion')
        if isinstance(quote,str):
            if basis=='documented_measurement' and not re.search(
                r'(?<![a-z-])\d+(?:[.,]\d+)?\s*(?:mm\b|cm\b|m\b|ml\b|liters?\b|kg\b|psi\b|bar\b|seconds?\b|minutes?\b|hours?\b|%)',
                quote,re.I):
                warnings.append({'kind':'measurement_without_numeric_quote','index':index,'semantic_label':label})
            if basis=='conditional_model' and not re.search(r'\b(if|may|might|can|could|would|under|when|provided|assuming|possible)\b',quote,re.I):
                warnings.append({'kind':'conditional_scope_not_explicit_in_quote','index':index,'semantic_label':label})
            if basis=='assessed_source_assertion' and re.search(r'\b(may|might|could|would|possibly|hypothesi[sz]ed)\b',quote,re.I):
                warnings.append({'kind':'possibly_conditional_claim','index':index,'semantic_label':label})
        retained.append(a)
    result['assertions']=retained
    result['_intake_audit']={
        'policy':'structured_llm','input_assertions':len(raw.get('assertions',[])),
        'retained_assertions':len(retained),'flags':warnings,
        'semantic_entailment_verified':False,
    }
    return result

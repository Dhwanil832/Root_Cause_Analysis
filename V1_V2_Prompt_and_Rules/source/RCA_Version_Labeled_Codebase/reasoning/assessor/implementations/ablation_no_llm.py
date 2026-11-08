"""Baseline assessor: structurally validate proposals without an extra model call.

This is an intentional ablation comparator, not a semantic verifier. Exact
source quotations are checked elsewhere before commit.
"""
from __future__ import annotations


def review(runtime, source, state, extraction, frontier, new_claims):
    return {
        'frontier': dict(frontier),
        'new_claims':list(new_claims),
        'assessment': {
            'policy': 'baseline',
            'model_review_performed': False,
            'excluded_inference_indices': [],
            'excluded_assertion_labels': [],
            'excluded_hypothesis_summaries': [],
            'flags': [],
            'limitation': 'No independent semantic entailment review',
        },
    }


def postcommit(runtime, corrections):
    return []

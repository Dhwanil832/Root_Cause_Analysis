"""Compile a *candidate* hypothesis/condition/question coverage matrix.

This is an IRIS-inspired open-world variable audit, not IRIS's learned/statistical
causal discovery. No row in this matrix counts as evidence, and missing conditions
never become supported findings. A matrix is useful even when the model has not
produced a single valid inference edge.
"""
from __future__ import annotations
from collections import defaultdict
from reasoning.specialist.components.frontier_policy import overlap, terms

# Ignore generic event vocabulary when relating a candidate *condition* to a
# question. Otherwise two unrelated mechanisms become conflated merely because
# both mention the accident outcome (e.g. "the package fell").
EVENT_TERMS = {'incident','accident','event','fell','fall','fallen','drop','dropped',
               'package','worker','machine','time','when','before','after','cause',
               'observation','observed','reported','record','information'}


def condition_match(condition, text):
    distinctive = terms(condition) - EVENT_TERMS
    question_terms = terms(text) - EVENT_TERMS
    shared = distinctive & question_terms
    return bool(shared) and overlap(condition, text) >= .25



def compile_matrix(hypotheses, gaps, existing_gaps=()):
    """Connect unresolved hypothesis conditions to questions by semantic overlap.

    `hypotheses` and `gaps` contain ONLY model-visible proposals. This method
    cannot inspect the custodian document inventory or reference conclusions.
    A missing condition counts as covered by a *question*, not as established.
    """
    material = []
    for h in hypotheses[:30]:
        if not isinstance(h, dict) or not isinstance(h.get('summary'), str):
            continue
        conditions = []
        for c in h.get('missing_conditions', [])[:12]:
            if isinstance(c, str) and c.strip():
                conditions.append(c.strip())
        material.append({'hypothesis': h['summary'], 'conditions': conditions})
    all_gaps = [g for g in list(existing_gaps) + list(gaps) if isinstance(g, dict)]
    coverage = defaultdict(list)
    uncovered = []
    discriminators = []
    for row in material:
        hyp = row['hypothesis']
        for condition in row['conditions']:
            matches = []
            for g in all_gaps:
                text = ' '.join(str(g.get(k, '')) for k in ('question', 'expected_change'))
                hints = ' '.join(str(r.get('topic', '')) for r in g.get('routes_to_consider', []) if isinstance(r, dict))
                if condition_match(condition, text) or condition_match(condition, hints):
                    matches.append(str(g.get('semantic_label') or g.get('id') or g.get('question')))
            if matches:
                coverage[hyp].append({'condition': condition, 'question_ids': matches[:8]})
            else:
                uncovered.append({'hypothesis': hyp, 'missing_condition': condition})
    # A question can be valuable because it probes conditions distinct between
    # competing mechanisms, not merely because it matches many hypotheses.
    for gap in gaps:
        text = ' '.join(str(gap.get(k, '')) for k in ('question', 'expected_change'))
        matches = []
        for row in material:
            if any(condition_match(c, text) for c in row['conditions']):
                matches.append(row['hypothesis'])
        if matches:
            gap['hypothesis_tests'] = matches[:10]
            gap['discrimination_class'] = ('mechanism_specific' if len(matches) == 1 and len(material) > 1
                                           else 'shared_condition')
            discriminators.append({'gap': gap.get('semantic_label'), 'tests': matches[:10],
                                   'kind': gap['discrimination_class']})
    return {
        'hypothesis_count': len(material),
        'missing_condition_count': sum(len(row['conditions']) for row in material),
        'question_coverage': dict(coverage),
        'unquestioned_conditions': uncovered[:35],
        'question_discriminators': discriminators[:35],
        'note': 'Question linkage is lexical/structural, not evidence or causal truth.',
    }

"""Allowlisted plug-in selector. No imports or code paths supplied by model outputs."""
from __future__ import annotations
import importlib
from shared.prompt_loader import load

PATHS={
 'intake':'intake.agents.intake_agent',
 'specialist':'reasoning.specialist',
 'lead':'reasoning.lead',
 'evidence_worker':'reasoning.evidence_worker',
 'assessor':'reasoning.assessor',
}
IMPLEMENTATIONS={
    'intake':{'v1_basic', 'v2_structured_llm'},
    'specialist':{'v1_basic', 'v2_causal_frontier', 'v2_iris_inspired'},
    'lead':{'v1_basic', 'v2_causal_guided', 'v2_joint_route_planner'},
    'evidence_worker':{'ablation_no_llm', 'v1_basic', 'v2_adaptive_routes'},
    'assessor':{'ablation_no_llm', 'v1_basic', 'v2_impact_aware'},
}

class ComponentRegistry:
    def __init__(self,config):
        self.config=config
        self.components={}
        self.prompts={}
        self.prompt_hashes={}
        self.prompt_variants={}
        for role,package in PATHS.items():
            impl=config['agents'][role]['implementation']
            if impl not in IMPLEMENTATIONS[role]:
                raise ValueError(f'Unknown implementation {role}.{impl}. Allowed: {sorted(IMPLEMENTATIONS[role])}')
            module=importlib.import_module(f'{package}.implementations.{impl}')
            # Prompt choice is independent of implementation for factorial
            # V1/V2 comparisons. Only allowlisted .md files are loadable.
            prompt_variant=config['agents'][role].get('prompt_implementation',impl)
            if prompt_variant not in IMPLEMENTATIONS[role]:
                raise ValueError(f'Unrecognized {role} prompt variant {prompt_variant}')
            prompt,sha=load(role,prompt_variant)
            self.components[role]=module
            self.prompts[role]=prompt
            self.prompt_hashes[role]=sha
            self.prompt_variants[role]=prompt_variant
    def selected_name(self,role):return self.config['agents'][role]['implementation']
    def prompt(self,role):return self.prompts[role]
    def normalize_intake(self,raw):return self.components['intake'].normalize(raw)
    def transform_frontier(self,raw,public):return self.components['specialist'].transform(raw,public)
    def rank_actions(self,runtime,actions,public):return self.components['lead'].rank(runtime,actions,public)
    def execute_evidence_action(self,runtime,action):return self.components['evidence_worker'].execute(runtime,action)
    def review_assessment(self,runtime,source,state,extraction,frontier,new_claims):
        return self.components['assessor'].review(runtime,source,state,extraction,frontier,new_claims)
    def postcommit_impact(self,runtime,corrections):return self.components['assessor'].postcommit(runtime,corrections)

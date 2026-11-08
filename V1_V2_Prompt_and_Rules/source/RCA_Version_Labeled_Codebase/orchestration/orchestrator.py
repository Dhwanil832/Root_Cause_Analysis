"""Thin orchestrator composes independent role entrypoints; v2 owns state commits."""
from __future__ import annotations
from intake.agents.intake_agent.agent import IntakeAgentMixin
from reasoning.specialist.agent import SpecialistAgentMixin
from reasoning.lead.agent import LeadAgentMixin
from reasoning.evidence_worker.agent import EvidenceWorkerAgentMixin
from reasoning.assessor.agent import AssessorAgentMixin
from orchestration.state import CaseState
from orchestration.scheduler import run_steps
from revision.controller import Controller
from shared.registry import ComponentRegistry
from shared.llm.factory import create_model_client
from shared.llm.fixture import FixtureModel
from shared.contracts.agent_inputs import AgentInput
from reasoning.context.context_builder import build_agent_context
from shared.contracts.agent_outputs import AgentOutput
from shared.contracts.task_validation import validate as validate_task, TaskContractError

class Investigator(CaseState,IntakeAgentMixin,SpecialistAgentMixin,LeadAgentMixin,
                   EvidenceWorkerAgentMixin,AssessorAgentMixin):
    """Five role interfaces, one actor at a time; strategies are selected by registry.

    In-process mixins share a case workspace but each task-specific module owns
    its logic. Replacements use allowlisted implementation modules and common
    JSON shape contracts; only the controller commits persistent source state.
    """
    def __init__(self,world,config,mode='fixture',model=None,max_steps=None,case_id=None,fixture_responses=None):
        super().__init__(world,case_id or config['project']['case_id'],
                         max_steps if max_steps is not None else config['project']['max_actions'])
        if config.get('revision',{}).get('implementation')!='v2':
            raise ValueError('Only the v2 revision controller is implemented in this build')
        if config.get('orchestration',{}).get('mode')!='sequential':
            raise ValueError('Only sequential orchestration is implemented in this build')
        self.config_snapshot=config
        self.registry=ComponentRegistry(config)
        self.controller=Controller()
        self.mode=mode
        if mode=='fixture':
            if model is not None:self._models={role:model for role in self.registry.components}
            else:
                if fixture_responses is None:raise ValueError('Fixture response file required')
                stub=FixtureModel(fixture_responses)
                self._models={role:stub for role in self.registry.components}
        elif mode=='live':
            if model is not None:self._models={role:model for role in self.registry.components}
            else:
                cfg=config['llm']
                self._models={}
                for role in self.registry.components:
                    role_config=config['agents'][role]
                    self._models[role]=create_model_client(
                        provider=role_config.get('provider',cfg['provider']),
                        model=role_config.get('model',cfg['model']),
                        base_url=role_config.get('base_url',cfg.get('base_url')),
                        timeout=cfg.get('timeout',120),
                        response_format=cfg.get('response_format','json_object'),
                        retries=cfg.get('retries',1))
        else:raise ValueError('Mode must be fixture or live')
        self.session.metadata['run_kind']='fixture_authored_responses' if mode=='fixture' else 'live_provider_pending'

    def ask_role(self,role,task,payload):
        public_payload=build_agent_context(payload)
        AgentInput(role,task,public_payload)
        model=self._models[role]
        allowed_retries=max(0,min(2,int(self.config_snapshot.get('llm',{}).get('contract_retries',1))))
        # On a schema/quote contract violation, a bounded retry receives ONLY
        # the validation error and original model-visible input. No gold data,
        # fixture answer, or hidden evidence is substituted.
        for attempt in range(allowed_retries+1):
            user_input=public_payload if attempt==0 else {
                **public_payload,
                '_contract_repair_feedback':{
                    'error':message,
                    'request':'Correct the format/quote error; use only supplied evidence and public identifiers. Return JSON only.',
                    'attempt':attempt,
                },
            }
            before=len(model.calls)
            result=model.ask(task,self.registry.prompt(role),user_input)
            if len(model.calls)<=before:
                raise RuntimeError(f'{role} model call did not produce a recorded completion')
            record=model.calls[-1]
            self.model_input_history.append({'role':role,'task':task,
                'attempt':attempt,'prompt_sha256':self.registry.prompt_hashes[role],
                'model':record.model,'actual_provider_completion':record.actual_call_performed,
                'payload':user_input})
            self.model_calls.append(record)
            self.last_model_name=record.model
            try:
                AgentOutput(role,result)
                validate_task(task,result,user_input)
                return result
            except TaskContractError as exc:
                message=str(exc)
                self.contract_rejections.append({'role':role,'task':task,'attempt':attempt,
                                                 'error':message,'model':record.model})
                if attempt == allowed_retries:
                    raise TaskContractError(f'{role}/{task} rejected after {attempt+1} response(s): {message}') from exc
        raise RuntimeError('Unreachable model contract state')

    def run(self):
        self.stop_reason='running'
        return run_steps(self)

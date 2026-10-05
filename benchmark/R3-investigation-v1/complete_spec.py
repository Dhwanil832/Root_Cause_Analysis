"""Complete evaluation metadata, delivery routes and readable criteria. Offline only."""
from build_package import *

routes=[
 ('motion','Yoke/carrier motion, video interval or direct crane-contact coverage',['D07']),
 ('execution','Actual blocking, isolation execution, work/permit configuration',['D05']),
 ('witness','Witness accounts or corroboration of yoke/carrier movement',['D06A','D06B']),
 ('incident_hydraulics','Tagged incident fluid/pressure/flow boundary or leakage path',['D08']),
 ('configuration','Applicable arrangement/revisions, stops, keeper installation',['D03A','D03C']),
 ('geometry','Clearance, primary engagement, centered overlap or dynamic retention envelope',['D10']),
 ('recovery','Keeper/fastener condition, fracture, recovery inspection or contact marks',['D14']),
 ('valve_exam','Preserved valve identity, bench leakage or component examination',['D09']),
 ('maintenance','V17 inspection/replacement history, defect discovery/detectability or maintenance practice',['D11']),
 ('availability','Retained keeper offset/envelope or contamination-onset availability',['D12']),
 ('actions','Proposed or implemented corrective actions',['D13'])]
save('custodian-policy.json',dict(initial=['D01','D02','D04','D15'],routes=[dict(id=i,request_meaning=q,return_documents=d) for i,q,d in routes],matching='Semantic scope matching, never exact document/request IDs. Match all relevant routes for a compound request. Returned document content is unchanged. Record every route decision before scoring.',delivery='At each genuine paused evidence boundary, respond to all currently relevant registered awaiting-user/partial requests. Requests still awaiting a scheduled local search wait for that search. D12 may accompany an explicit requested availability question; do not supply hidden measurements or gold states.',unsolicited=dict(document='D13',trigger='First actual custodian-response batch, once per connected run, independent of model identity or performance'),unmatched_answer='R3 benchmark record desk: the supplied package contains no additional record answering the following requested scope: {verbatim_unmatched_fields}. This is a limit of this supplied package, not evidence that the historical activity or record never existed. The physical explanation remains for investigation.',repeated_request='Return an association to the already supplied document or the same availability response, not independent corroboration. Record the duplicate request; no new synthetic incident facts.',operator='Prefer model-blinded operator mapping. Disclose and log when unblinded. No model-generated evidence or rubric-guided rescue.',automated_broker_implemented=False))
cfg=json.loads((OLD/'config.json').read_text())
save('execution-plan.json',dict(status='Evaluation frozen; runtime/adapter qualification pending; do not execute automatically',arms=['gpt_clean','gpt_connected','qwen_clean','qwen_connected'],repetitions=3,clean_packets=17,checks_per_run=96,connected_calls_per_invocation=12,connected_operational_ceiling=96,proposed_model_configurations={'gpt':cfg['gpt'],'qwen':cfg['qwen']},configuration_note='These are the recorded prior configurations, not a claim of live endpoint availability. A common schema-capable adapter and token-budget qualification must be frozen before execution. Do not switch model/configuration midway or drop context silently.',scoring='Presence primary; contradiction and committed-state retention separately. See PROTOCOL.md.'))
crit=json.loads((ROOT/'private/evaluator/criteria.json').read_text())
text='# Frozen R3 stage evaluation sheet\n\nVersion 1. 96 checks, one point each. Equivalent supported meanings earn credit. New model results are unscored. See PROTOCOL.md for exact input modes, stage windows and failure attribution.\n'
for s,name,role,band in STAGES:
 text+=f'\n## {s} — {name}\n\nRole in clean test: {role}. Evidence band: {band}. Maximum: 8.\n\n| ID | Expected output | Source/contract | Do not credit | Clean packet |\n|---|---|---|---|---|\n'
 for c in crit:
  if c['stage']==s:text+=f"| {c['id']} | {c['expected']} | {'; '.join(c['source_refs'])} | {c['not_credit']} | {c['clean_packet']} |\n"
write('EVALUATION_SHEET.md',text)
save('private/evaluator/annotations-template.json',dict(required_row_fields=['arm','repetition','criterion_id','outcome','exposure','output_reference','excerpt_or_absence_reason','contradiction','failure_origin'],outcomes=['Present','Missing','Not reached','Harness blocked'],exposures=['Supplied','Not obtained','Harness blocked'],failure_origins=['None','Interpretation','Acquisition','Composition','Retention','Routing','Harness','Transport','Resource','Unknown'],additional_diagnostics=['raw-versus-committed loss','first failure and affected downstream targets','later recovery outside primary stage window','unsupported additional claims with exact excerpts','repeat requests','wrong valid-proposal rejection','structural acceptance of unsupported claim','final report completeness'],missing='Unscored until required fields are populated. No synthetic performance results.'))
print('Protocol metadata and readable 96-check evaluation sheet prepared.')

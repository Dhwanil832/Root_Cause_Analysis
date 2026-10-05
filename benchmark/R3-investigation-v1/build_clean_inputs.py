"""Authored correct preceding states; independent isolated packets, no model calls."""
from build_package import *

INITIAL=['D01','D02','D04','D15']
MOTION=INITIAL+['D05','D06A','D06B','D07']
PHYSICAL=MOTION+['D03A','D03C','D08','D10','D14']
LATE=PHYSICAL+['D09','D11','D12','D13']
FACTS={
 'FALL':('The raised R3 carrier fell into the pit onto the sled/scaffold on 14 October 2024 at about 13:24.','reported',['D01']),
 'HYD':('Incident C17 fluid loss permitted loaded yoke descent, subject to restraint and applicable load/path conditions.','candidate',['D02']),
 'REL':('Sufficient yoke-down motion relative to the carrier could eliminate primary seating.','candidate',['D02']),
 'KEEP':('A dynamic keeper-release path could allow separation after primary seating is lost.','candidate',['D02']),
 'BLOCK':('No effective independent positive yoke block was present.','candidate',['D02','D04']),
 'PROC':('WP-031 omitted a positive-block instruction and off-center retention-envelope verification.','supported',['D04']),
 'LOAD':('The incident assembly was parked raised and gravity remained available.','supported',['D01','D02']),
 'YOKE':('YK-3 descended 40 +/- 1 mm during 13:00:00–13:24:00, before release at 13:24:03.','supported',['D07']),
 'CARRIER':('The carrier moved downward 0 +/- 1 mm over that same interval and reference frame.','supported',['D07']),
 'CONTACT':('Post/spreader contact was visible through that interval, compatible with temporarily holding the carrier.','supported',['D02','D05','D07']),
 'WITHDRAW':('Relative yoke-down withdrawal over the measured interval was 38–42 mm.','supported',['D02','D07']),
 'SEAT':('Relative withdrawal exceeded the defined 30 mm engagement and eliminated primary seating by 13:24:00.','supported',['D02','D07']),
 'LEAK':('0.400 +/- 0.010 L left C17 through V17 despite CLOSED indication over the incident measurement interval.','supported',['D08']),
 'NOBLOCK':('The incident photograph and boundary record show no independent positive block under YK-3.','supported',['D05','D08']),
 'CONFIG':('Current revision C has backup rolls removed, no backup-roll-associated stop and no separate maintenance travel stop.','supported',['D03C']),
 'CRANE':('Direct overhead-crane/load contact caused release within the fully covered 13:00:00–13:24:03 carrier envelope.','refuted',['D07']),
 'FRACTURE':('Gross keeper plate or fastener fracture/separation caused release within the recovered-assembly inspection scope.','refuted',['D14']),
 'CENTERED':('Recovered attachment and 8 +/- 1 mm centered seated overlap constrain simple centered passage, but do not establish incident dynamic retention.','supported',['D10','D14']),
 'BENCH':('Later V17 bench leakage is compatible with incident flow; contamination arrival time remains unknown.','supported',['D08','D09']),
 'HISTORY':('The retained V17 practice is replacement on reported defect with no scheduled seat-leak inspection in the preceding year.','supported',['D11']),
 'ACTION':('D13 lists identified action proposals; implementation and effectiveness are not established.','reported',['D13']),
 'ORIGIN_VALVE':('An upstream valve condition or contamination process caused the observed leakage; its specific origin is unresolved.','unresolved',['D08','D09','D11','D12']),
 'ORIGIN_BLOCK':('A particular procedural or execution decision caused the absence of a positive block; the decision bridge is unresolved.','unresolved',['D04','D05']),
 'ORIGIN_CONTACT':('A particular configuration/positioning sequence caused carrier contact; that origin is not fully established.','unresolved',['D03C','D05','D07'])
}
def record(id,claim,status,sources,kind='node',**kw):
 r=dict(id=id,kind=kind,scope_key=id,claim=claim,status=status,sources=sources,depends_on=[],from_ids=[],to_id=None,mode=None,asset=None,window=None,fields=[]);r.update(kw);return r
def operation(r):return dict(action='create',expected_version=0,replaces=None,reason='Reviewed preceding-state fixture supported by the supplied record sections.',record=r)
def commit(s,records):
 s,v=controller.apply(s,[operation(r) for r in records],'lead');assert v['accepted'],v;return s
def state(docs,keys):
 s=initial('At 13:24 on 14 October 2024 the R3 delivery carrier beam fell into the mill pit and struck the sled and scaffold. Investigate the physical mechanism and relevant upstream causes, preserving evidence limits.');s['queue']=[]
 for d in docs:s,_,_=documents.add(s,path=ROOT/'public/records'/f'{d}.json')
 return commit(s,[record(k,*FACTS[k]) for k in keys])
def req(id,claim,fields,targets,status='searching',sources=['D01']):
 return record(id,claim,status,sources,'request',depends_on=targets,asset='R3 CB-3/YK-3 C17/V17 raised maintenance assembly',window='14 October 2024 incident and stated relevant record interval',fields=fields)
def edge(id,inputs,target,claim,status='supported',sources=['D02','D07']):return record(id,claim,status,sources,'edge',from_ids=inputs,to_id=target,mode='all')
def base_candidates(docs=INITIAL):return state(docs,['FALL','HYD','REL','KEEP','BLOCK','PROC','LOAD'])
def motion_state(docs=MOTION):return state(docs,['FALL','HYD','KEEP','BLOCK','PROC','LOAD','YOKE','CARRIER','CONTACT','WITHDRAW','SEAT','CRANE'])
def physical_state(docs=PHYSICAL):return state(docs,['FALL','KEEP','PROC','LOAD','YOKE','CARRIER','CONTACT','WITHDRAW','SEAT','LEAK','NOBLOCK','CONFIG'])
def final_state():
 s=physical_state(LATE)
 s=commit(s,[record(k,*FACTS[k]) for k in ['BENCH','HISTORY','ACTION','ORIGIN_VALVE','ORIGIN_BLOCK','ORIGIN_CONTACT','CRANE','FRACTURE','CENTERED']])
 k=s['ledger']['KEEP'];k['record']['status']='unresolved';k['record']['sources']=['D02','D07','D10','D12','D14'];k['source_versions']={d:1 for d in k['record']['sources']}
 return commit(s,[
  edge('E_HYD',['LEAK','LOAD','NOBLOCK'],'YOKE','Incident support-fluid loss, raised load and no independent block jointly permit yoke descent.',sources=['D02','D05','D07','D08']),
  edge('E_REL',['YOKE','CARRIER'],'WITHDRAW','Both contemporaneous displacements determine relative withdrawal.'),
  edge('E_SEAT',['WITHDRAW'],'SEAT','Relative withdrawal beyond the defined engagement eliminates primary seating.'),
  edge('E_RELEASE',['SEAT','KEEP'],'FALL','Primary seating loss plus the unresolved keeper-release bridge could explain separation.','candidate',['D01','D02','D07','D10','D12'])])

def main():
 criteria,_=__import__('build_package').main();packets=[]
 def add(pid,stage,role,s,focus,targets,checks,tag=''):
  job=dict(kind=role,tag=tag,focus=focus,target_ids=targets,id='clean_'+pid)
  p=engine.packet(s,job)
  save('clean/packets/'+pid+'.json',p)
  save('clean/states/'+pid+'.json',s)
  packets.append(dict(id=pid,stage=stage,role=role,source_ids=list(s['sources']),target_ids=targets,criterion_ids=[f'{stage}.{i:02}' for i in checks],packet='clean/packets/'+pid+'.json',prompt='frozen/prompts/'+role+'.txt'))
  for c in criteria:
   if c['id'] in packets[-1]['criterion_ids']:c['clean_packet']=pid
 add('S01-A','S01','intake',state(INITIAL,[]),'Understand the incident and immediate clarification needs.',[],range(1,9))
 add('S02-H','S02','specialist',base_candidates(),'Investigate candidate hydraulic mechanisms and useful discriminating evidence.',['FALL'],range(1,5),'hydraulics')
 add('S02-M','S02','specialist',base_candidates(),'Investigate candidate mechanical retention/motion mechanisms and useful discriminating evidence.',['FALL'],range(5,9),'mechanical_retention')
 s=state(INITIAL,['FALL','PROC','LOAD']);s['proposals']=[]
 for label in ['hydraulics','mechanical']:
  leak=record('P_'+label,'Loss of C17 support-chamber fluid through V17 could permit yoke descent under load without independent restraint.','candidate',['D02'])
  motion=req('Q_'+label,'Obtain incident yoke and carrier motion to test relative withdrawal.',['yoke displacement','carrier displacement','common time window'],['FALL'],'proposed')
  others=[record('P_REL','Relative yoke/carrier motion could eliminate primary seating.','candidate',['D02']),record('P_KEEP','Dynamic keeper bypass could allow separation after primary seating loss.','candidate',['D02'])] if label=='mechanical' else []
  s['proposals'].append(dict(role='specialist',assignment=dict(kind='specialist',tag=label,target_ids=['FALL'],focus='Investigate scoped mechanisms'),output=dict(decision='Conditional mechanisms and evidence needs.',operations=[operation(x) for x in [leak,motion]+others],next_work=[],disposition='continue'),call_path='authored_preceding_fixture/'+label))
 add('S03-A','S03','lead',s,'Review the supplied specialist proposals and choose useful next work.',['FALL'],range(1,9))
 for suffix,docs,checks in [('A',INITIAL,range(1,5)),('B',MOTION,range(5,9))]:
  s=commit(base_candidates(docs),[req('R_MOTION','Acquire the incident motion record to assess yoke/carrier movement and coverage.',['yoke/carrier vertical displacement','common time window','release timing','keeper interface and lateral offset coverage'],['REL','KEEP'])])
  add('S04-'+suffix,'S04','evidence',s,'Determine which requested fields are covered and what remains.',['R_MOTION'],checks)
 add('S05-A','S05','assessor',base_candidates(MOTION),'Assess newly available motion and witness records.',['REL','KEEP','HYD'],range(1,9))
 add('S06-A','S06','assessor',motion_state(PHYSICAL),'Assess newly available hydraulic and execution evidence.',['HYD','BLOCK'],range(1,9))
 s=physical_state();s['proposals']=[dict(role='assessor',assignment=dict(kind='assessor',target_ids=['FALL'],focus='Assess physical evidence'),output=dict(decision='Incident flow and execution evidence support the established physical conditions; keeper mode and organizational origins remain unresolved.',operations=[],next_work=[],disposition='partial'),call_path='authored_preceding_fixture/physical_assessment')]
 add('S07-A','S07','lead',s,'Review established findings and assemble their warranted causal relationships.',['FALL'],range(1,9))
 for suffix,target,focus,checks in [('V','LEAK','Investigate upstream origins of the established valve leakage.',range(1,4)),('B','NOBLOCK','Investigate why the established no-block condition occurred.',range(4,7)),('C','CONTACT','Investigate origins of the observed carrier contact/holding condition.',range(7,9))]:
  add('S08-'+suffix,'S08','specialist',physical_state(),focus,[target],checks,'upstream_'+suffix)
 for suffix,target,claim,fields,checks in [('V','LEAK','Acquire component history and dated evidence to investigate valve leakage origin.',['V17 inspection/replacement practice','defect detectability','contamination onset'],range(1,5)),('K','KEEP','Acquire retained offset/dynamic keeper-envelope evidence.',['incident lateral/rotation measurement','validated envelope with bounded incident offset'],range(5,9))]:
  s=commit(physical_state(LATE),[req('R_'+suffix,claim,fields,[target])]);add('S09-'+suffix,'S09','evidence',s,'Assess coverage of the requested origin/availability evidence.',['R_'+suffix],checks)
 add('S10-A','S10','assessor',physical_state(LATE),'Assess the configuration, later examination, inspection, availability and action records.',[],range(1,9))
 s=final_state();s=commit(s,[
  req('R_MOTION','Acquire incident vertical motion/release coverage.',['yoke/carrier displacement and time window','release timing'],['WITHDRAW'],'partial'),
  req('R_HYD','Acquire incident hydraulic flow/boundary coverage.',['incident V17 flow','external and alternate paths'],['LEAK'],'partial'),
  req('R_KEEP','Acquire retained incident dynamic keeper evidence.',['incident offset','approved dynamic envelope'],['KEEP'],'partial'),
  req('R_ORIGIN','Acquire dated V17 origin evidence.',['inspection/replacement history','contamination onset'],['ORIGIN_VALVE'],'partial')])
 add('S11-A','S11','lead',s,'Review newly available request coverage, remaining origins and justified next actions.',[],range(1,9))
 add('S12-A','S12','lead',final_state(),'Review the current case and provide a self-contained account of the investigation and its evidence limits.',[],range(1,9))
 assert len(packets)==17 and all(c['clean_packet'] for c in criteria)
 save('clean/index.json',packets);save('private/evaluator/criteria.json',criteria)
 print('Prepared',len(packets),'independent clean packets and',len(criteria),'criteria. No model calls.')

if __name__=='__main__':main()

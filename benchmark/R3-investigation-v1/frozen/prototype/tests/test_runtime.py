import unittest,tempfile,json,copy
from pathlib import Path
from rca import controller,documents,engine
from rca.storage import initial,save,read

def rec(id='N',kind='node',**kw):
 r=dict(id=id,kind=kind,scope_key=id,claim='Claim '+id,status='candidate' if kind!='request' else 'proposed',sources=['D'],depends_on=[],from_ids=[],to_id=None,mode=None,asset=None,window=None,fields=[]);r.update(kw);return r
def op(r,action='create',v=0,replaces=None):return dict(action=action,expected_version=v,replaces=replaces,reason='Relevant update',record=r)
def base():
 s=initial('Test');s['sources']['D']=dict(id='D',version=1,content='Measured pump pressure and valve flow',title='Pump',revision='0',kind='record',request_ids=[]);s['source_revision']=1;return s
def commit(s,ops,actor='lead'):
 s,v=controller.apply(s,ops,actor);assert v['accepted'],v;return s
class ControllerTests(unittest.TestCase):
 def test_atomic_replace_retires_old(self):
  s=commit(base(),[op(rec('A')),op(rec('B')),op(rec('C')),op(rec('E','edge',from_ids=['A'],to_id='B',mode='all'))]);new=rec('E2','edge',from_ids=['A','C'],to_id='B',mode='all')
  s=commit(s,[op(new,'replace',1,'E')]);self.assertEqual(s['ledger']['E']['superseded_by'],'E2');self.assertEqual(s['ledger']['E']['record']['status'],'withdrawn');self.assertEqual(s['ledger']['E2']['supersedes'],'E')
 def test_noop_does_not_reject_other_changes(self):
  s=commit(base(),[op(rec('A'))]);s['ledger']['A']['review']='human_approved';s,v=controller.apply(s,[op(rec('A'),'revise',1),op(rec('B'))],'lead');self.assertTrue(v['accepted']);self.assertEqual(v['noops'],['A']);self.assertEqual(s['ledger']['A']['version'],1);self.assertEqual(s['ledger']['A']['review'],'human_approved');self.assertIn('B',s['ledger'])
 def test_bad_batch_rolls_back_all(self):
  s=base();before=copy.deepcopy(s);after,v=controller.apply(s,[op(rec('A')),op(rec('E','edge',from_ids=['missing'],to_id='A',mode='all'))],'lead');self.assertFalse(v['accepted']);self.assertEqual(after,before)
 def test_endpoint_change_explains_replace(self):
  s=commit(base(),[op(rec('A')),op(rec('B')),op(rec('C')),op(rec('E','edge',from_ids=['A'],to_id='B',mode='all'))]);r=copy.deepcopy(s['ledger']['E']['record']);r['from_ids']=['A','C'];_,v=controller.apply(s,[op(r,'revise',1)],'lead');self.assertEqual(v['reason'],'endpoints_or_mode_changed_use_replace')
 def test_endpoint_order_is_not_identity_change(self):
  s=commit(base(),[op(rec('A')),op(rec('B')),op(rec('C')),op(rec('E','edge',from_ids=['A','C'],to_id='B',mode='all'))]);r=copy.deepcopy(s['ledger']['E']['record']);r['from_ids']=['C','A'];s=commit(s,[op(r,'revise',1)]);self.assertEqual(s['ledger']['E']['version'],2)
 def test_node_replace_requires_dependents(self):
  s=commit(base(),[op(rec('A')),op(rec('B')),op(rec('E','edge',from_ids=['A'],to_id='B',mode='all'))]);_,v=controller.apply(s,[op(rec('A2'),'replace',1,'A')],'lead');self.assertFalse(v['accepted']);self.assertIn('retired_dependency',v['reason'])
 def test_node_and_edge_can_replace_together(self):
  s=commit(base(),[op(rec('A')),op(rec('B')),op(rec('E','edge',from_ids=['A'],to_id='B',mode='all'))]);s=commit(s,[op(rec('A2'),'replace',1,'A'),op(rec('E2','edge',from_ids=['A2'],to_id='B',mode='all'),'replace',1,'E')]);self.assertTrue(controller.active(s['ledger']['E2']))
 def test_stale_version_and_unknown_source(self):
  s=commit(base(),[op(rec())]);_,v=controller.apply(s,[op(rec(status='supported'),'revise',0)],'lead');self.assertFalse(v['accepted']);_,v=controller.apply(s,[op(rec('X',sources=['invented']))],'lead');self.assertEqual(v['reason'],'unknown_source')
 def test_request_not_physical_endpoint(self):
  s=commit(base(),[op(rec('A')),op(rec('R','request',asset='pump',window='event',fields=['pressure']))]);_,v=controller.apply(s,[op(rec('E','edge',from_ids=['R'],to_id='A',mode='all'))],'lead');self.assertEqual(v['reason'],'nonphysical_endpoint')
 def test_duplicate_request_scope(self):
  s=commit(base(),[op(rec('R','request',asset='pump',window='event',fields=['pressure']))]);_,v=controller.apply(s,[op(rec('R2','request',asset='Pump',window='EVENT',fields=['Pressure']))],'lead');self.assertIn('overlapping_request',v['reason'])
 def test_evidence_cannot_commit_causal_nodes(self):
  _,v=controller.apply(base(),[op(rec())],'evidence');self.assertEqual(v['reason'],'evidence_role_cannot_judge_physical_causes')
 def test_physics_is_not_validated_by_structure(self):
  s=commit(base(),[op(rec(claim='A deliberately unsupported physical assertion',status='supported'))]);self.assertEqual(s['ledger']['N']['review'],'pending_human')
 def test_changed_judgment_invalidates_approval_and_dependents(self):
  s=commit(base(),[op(rec('A')),op(rec('B')),op(rec('E','edge',from_ids=['A'],to_id='B',mode='all'))]);s['ledger']['A']['review']='human_approved';s=commit(s,[op(rec('A',status='supported'),'revise',1)]);self.assertEqual(s['ledger']['A']['review'],'pending_human');self.assertTrue(s['ledger']['E']['stale'])
class LifecycleTests(unittest.TestCase):
 def test_upstream_review_once_and_reopens_on_new_evidence(self):
  s=commit(base(),[op(rec('A',status='supported')),op(rec('B')),op(rec('CONTEXT',status='supported')),op(rec('E','edge',from_ids=['A'],to_id='B',mode='all'))]);s['queue']=[]
  self.assertTrue(engine.ensure_upstream_review(s));job=s['queue'].pop();self.assertEqual(job['target_ids'],['A'])
  data=dict(decision='A is an established premise; its origin is explicitly unavailable in D. Boundary retained.',operations=[],next_work=[],disposition='partial')
  s,v=engine.apply_result(s,job,data,'calls/review','review-sig');self.assertEqual(s['queue'],[]);self.assertFalse(engine.ensure_upstream_review(s))
  s,_,_=documents.add(s,answer='New upstream maintenance evidence');self.assertTrue(engine.ensure_upstream_review(s))
 def test_upstream_review_does_not_dispatch_while_work_is_pending(self):
  s=commit(base(),[op(rec('A',status='supported')),op(rec('B')),op(rec('E','edge',from_ids=['A'],to_id='B',mode='all'))])
  self.assertFalse(engine.ensure_upstream_review(s));s['queue']=[];s['pending_call']={'job':{}}
  self.assertFalse(engine.ensure_upstream_review(s));s.pop('pending_call');s['ledger']['A']['stale']=True
  self.assertFalse(engine.ensure_upstream_review(s))
 def test_correction_stales_dependents_not_independent(self):
  s=base();s['sources']['X']=dict(s['sources']['D'],id='X');s=commit(s,[op(rec('A')),op(rec('B',sources=['X'])),op(rec('E','edge',sources=['X'],from_ids=['A'],to_id='B',mode='all'))]);s,_,_=documents.add(s,answer='Corrected pump measurement',corrects='D');self.assertTrue(s['ledger']['A']['stale']);self.assertTrue(s['ledger']['E']['stale']);self.assertFalse(s['ledger']['B']['stale'])
 def test_search_miss_not_unavailability(self):
  q=rec('R','request',asset='zzqq',window='vvww',claim='xxuu',fields=['nnmm']);result=documents.search(base(),q);self.assertEqual(result['hits'],[]);self.assertIn('not proof',result['limitation'])
 def test_answer_persists_and_schedules_assessment(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=commit(base(),[op(rec('R','request',asset='pump',window='event',fields=['pressure'],status='awaiting_user'))]);s['queue']=[];save(Path(tmp)/'state.json',s);sid,changed=engine.submit(tmp,request_id='R',answer='No pressure record is available');s=read(Path(tmp)/'state.json');self.assertTrue(changed);self.assertIn(sid,s['sources']);self.assertEqual(s['ledger']['R']['record']['status'],'awaiting_user');self.assertEqual(s['queue'][0]['kind'],'assessor')
 def test_search_not_repeated_only_for_status_version(self):
  s=commit(base(),[op(rec('R','request',asset='pump',window='event',fields=['pressure'],status='searching'))]);job=dict(kind='evidence',tag='',focus='find pressure',target_ids=['R']);sig=engine.signature(s,job);s['completed_jobs']=[dict(signature=sig)];s['ledger']['R']['record']['status']='partial';s['ledger']['R']['version']+=1;accepted,reason=engine.enqueue(s,job);self.assertFalse(accepted);self.assertIn('already_completed',reason)
 def test_new_document_allows_new_search(self):
  s=commit(base(),[op(rec('R','request',asset='pump',window='event',fields=['pressure'],status='searching'))]);job=dict(kind='evidence',tag='',focus='find pressure',target_ids=['R']);s['completed_jobs']=[dict(signature=engine.signature(s,job))];s,_,_=documents.add(s,answer='Pressure trend attached');accepted,_=engine.enqueue(s,job);self.assertTrue(accepted)
 def test_rejected_human_review_stales_dependents(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=commit(base(),[op(rec('A',status='supported')),op(rec('B')),op(rec('E','edge',from_ids=['A'],to_id='B',mode='all'))]);s['ledger']['E']['review']='human_approved';save(Path(tmp)/'state.json',s)
   engine.review(tmp,'A',1,'rejected','Source does not establish occurrence');s=read(Path(tmp)/'state.json');self.assertTrue(s['ledger']['E']['stale']);self.assertEqual(s['ledger']['E']['review'],'pending_human')
 def test_existing_document_new_request_link_schedules_assessment(self):
  with tempfile.TemporaryDirectory() as tmp:
   s=commit(base(),[op(rec('R','request',asset='pump',window='event',fields=['pressure'],status='awaiting_user'))]);s['queue']=[];s,sid,_=documents.add(s,answer='Pressure was measured');save(Path(tmp)/'state.json',s)
   same,changed=engine.submit(tmp,request_id='R',answer='Pressure was measured',source_id=sid);s=read(Path(tmp)/'state.json');self.assertEqual(same,sid);self.assertTrue(changed);self.assertEqual(len(s['sources']),2);self.assertEqual(s['queue'][0]['kind'],'assessor')
 def test_unsupported_upload_fails_explicitly(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'image.png';p.write_bytes(b'PNG');self.assertRaises(ValueError,documents.extract,p)
 def test_pending_assessments_coalesce(self):
  s=commit(base(),[op(rec('A')),op(rec('B'))]);s['queue']=[]
  engine.enqueue(s,dict(kind='assessor',tag='',focus='Assess A',target_ids=['A']))
  engine.enqueue(s,dict(kind='assessor',tag='',focus='Assess B',target_ids=['B']))
  self.assertEqual(len(s['queue']),1);self.assertEqual(set(s['queue'][0]['target_ids']),{'A','B'})
 def test_mock_connected_run_and_restart(self):
  with tempfile.TemporaryDirectory() as tmp:
   engine.create(tmp,'An unexplained test event',[])
   calls=[]
   def fake(prompt,packet,folder):
    folder.mkdir(parents=True);role=packet['assignment']['kind'];calls.append(role)
    data=dict(decision='Initial understanding' if role=='intake' else 'Await evidence',operations=[],next_work=[],disposition='waiting')
    (folder/'answer.txt').write_text(json.dumps(data));save(folder/'result.json',{'status':'completed'});return data
   s=engine.run(tmp,1,fake);self.assertEqual(s['phase'],'budget_paused');s=engine.run(tmp,3,fake);self.assertEqual(s['phase'],'waiting');self.assertEqual(calls,['intake','lead']);self.assertEqual(len(read(Path(tmp)/'state.json')['calls']),2)
 def test_stale_pending_output_not_committed(self):
  s=base();s['pending_call']={'source_revision':0};job=dict(id='x',kind='lead',tag='',focus='',target_ids=[]);data=dict(decision='Old context',operations=[op(rec())],next_work=[],disposition='waiting');s,v=engine.apply_result(s,job,data,'calls/old','sig');self.assertNotIn('N',s['ledger']);self.assertFalse(v['accepted']);self.assertTrue(s['proposals'][0]['stale_context'])
if __name__=='__main__':unittest.main()

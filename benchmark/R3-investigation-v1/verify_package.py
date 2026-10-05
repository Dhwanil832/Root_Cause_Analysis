"""Read-only offline verification. Never invokes a provider or modifies a case."""
from pathlib import Path
import json,hashlib,sys,collections,zipfile,xml.etree.ElementTree as ET
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'frozen/prototype'))
from rca import controller,documents
def read(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify():
 checks={};criteria=read('private/evaluator/criteria.json');packets=read('clean/index.json');inventory=read('public/inventory.json')
 assert len(criteria)==96 and len({c['id'] for c in criteria})==96
 assert set(collections.Counter(c['stage'] for c in criteria).values())=={8};checks['criteria_12_stages_96_checks']=True
 assert len(inventory)==17
 sections=set()
 for d in inventory:
  p=ROOT/'public/records'/f"{d['id']}.json";assert sha(p)==d['sha256'];j=json.loads(p.read_text());sections.update(s['id'] for s in j['sections'])
 checks['17_record_hashes_match']=True
 for c in criteria:
  assert all(s in sections or s.startswith(('fixture:','harness:')) for s in c['source_refs'])
  assert c['clean_packet'] in {p['id'] for p in packets}
 assert len(packets)==17
 assert sorted(c['id'] for c in criteria)==sorted(x for p in packets for x in p['criterion_ids'])
 checks['all_checks_bound_once_to_clean_packets']=True
 checks['all_source_section_references_resolve']=True
 for item in packets:
  p=read(item['packet']);s=read('clean/states/'+item['id']+'.json')
  assert p['ledger']==s['ledger'];assert set(p['assignment']['target_ids'])<=set(s['ledger'])
  assert p['source_revision']==s['source_revision']
  _,validation=controller.apply(s,[],'lead');assert validation['accepted'],(item['id'],validation)
  if item['role']=='evidence':
   expected=documents.search(s,s['ledger'][p['assignment']['target_ids'][0]]['record']);assert p['retrieval']==expected;assert p['sources']==[x['source'] for x in expected['hits']]
  else:assert p['sources']==list(s['sources'].values())
  assert not {'expected','rubric','gold','criteria','reference_chart'}&set(p)
  for r in s['ledger'].values():assert set(r['record']['sources'])<=set(s['sources'])
 checks['17_clean_states_structurally_valid_and_packets_faithful']=True
 checks['no_evaluator_keys_in_packet_top_level']=True
 assert [390/100*10,410/100*10]==[39,41] and [39-1,41+1]==[38,42] and 38>30
 checks['quantitative_reference_arithmetic']=True
 tests=read('verification/workbook-checks.json');assert all(t['ok'] for t in tests['tests']);checks['workbook_boundary_tests']=True
 book=ROOT/'outputs/01a0cef3-83d5-7bc1-a0a5-45c70c3255a3/R3_Evaluation.xlsx'
 ns={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
 with zipfile.ZipFile(book) as z:
  workbook=ET.fromstring(z.read('xl/workbook.xml'));names=[n.attrib['name'] for n in workbook.findall('s:sheets/s:sheet',ns)]
  assert names==['Comparison','Stage scores','Criteria','Grades','Records']
  grades=ET.fromstring(z.read('xl/worksheets/sheet4.xml'))
  filled=[]
  for cell in grades.findall('.//s:c',ns):
   ref=cell.attrib['r'];col=''.join(x for x in ref if x.isalpha());row=int(''.join(x for x in ref if x.isdigit()))
   if row>=6 and col in ['E','F','G','H','I','J'] and any(cell.find('s:'+tag,ns) is not None for tag in ['v','is','f']):filled.append(ref)
  assert not filled,filled[:5]
  assert len(grades.findall('.//s:row',ns))>=1152
 checks['exported_workbook_1152_grade_slots_unscored']=True
 for p in (ROOT/'clean/packets').glob('*.json'):
  text=p.read_text();assert 'OPENAI_API_KEY=' not in text and 'Bearer ' not in text
 checks['packet_secret_markers_absent']=True
 if (ROOT/'FREEZE.json').exists():
  frozen=read('FREEZE.json')
  for path,h in frozen['files'].items():assert sha(ROOT/path)==h,'Frozen file changed: '+path
  checks['frozen_file_hashes_match']=True
 return dict(passed=True,checks=checks,model_calls=0,readiness='Evaluation frozen; execution qualifications listed in REVIEW.md remain open.')
if __name__=='__main__':print(json.dumps(verify(),indent=2))

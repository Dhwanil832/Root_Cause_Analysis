from __future__ import annotations
import json,os,threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import pytest
from shared.llm.client import ChatCompletionsModel,ModelFailure,parse_json
from shared.llm.fixture import FixtureModel
from shared.config_loader import load_config,ROOT
from integrations.evidence_sources.synthetic_world import EvidenceWorld
from orchestration.orchestrator import Investigator

class Handler(BaseHTTPRequestHandler):
    requests=[]
    fixture=FixtureModel(ROOT/'evaluation/private_reference/fixture_responses_DESIGNER_ONLY.json')
    def do_POST(self):
        raw=self.rfile.read(int(self.headers['Content-Length']))
        body=json.loads(raw)
        self.__class__.requests.append(body)
        assert self.path.endswith('/chat/completions')
        assert 'messages' in body
        payload=json.loads(body['messages'][1]['content'])
        task=self.headers.get('X-RCA-Task')
        assert task in {'extract','frontier','review_assessment','propose_actions','plan_route'}
        result=self.fixture.ask(task,body['messages'][0]['content'],payload)
        response=json.dumps({'choices':[{'message':{'content':json.dumps(result)}}], 'usage':{'total_tokens':10}}).encode()
        self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(response)))
        self.end_headers();self.wfile.write(response)
    def log_message(self,*args):pass

@pytest.fixture
def fake_server():
    Handler.requests=[]
    Handler.fixture=FixtureModel(ROOT/'evaluation/private_reference/fixture_responses_DESIGNER_ONLY.json')
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}/v1'
    finally:server.shutdown();server.server_close();thread.join(timeout=2)

def test_real_http_interface_to_fake_server(fake_server):
    model=ChatCompletionsModel('compatible','fake-model',base_url=fake_server,retries=0)
    # This test validates HTTP integration, NOT LLM intelligence.
    resp=model.ask('extract','Return assertions and corrections',{'document':{'id':'IR-01','text':'X'},'existing_claims':[]})
    assert resp['assertions']
    assert model.calls[0].actual_call_performed
    assert Handler.requests[-1]['model']=='fake-model'

def test_full_http_orchestration_with_simulated_response_server(fake_server):
    model=ChatCompletionsModel('compatible','simulated-responder',base_url=fake_server,retries=0)
    a=Investigator(EvidenceWorld(ROOT/'evaluation/fixtures/wet_floor/documents.json'),load_config(),
          mode='live',model=model,max_steps=18).run()
    assert set(a.session.documents)=={'IR-01','CAM-17','COR-17','MNT-81','WIT-06','OPS-02'}
    assert sum(x.actual_call_performed for x in a.model_calls)==len(Handler.requests)
    assert sum(x.actual_call_performed for x in a.model_calls)>10

def test_no_api_key_blocks_openrouter(monkeypatch):
    for k in ('OPENROUTER_API_KEY','RCA_LLM_API_KEY'):
        monkeypatch.delenv(k,raising=False)
    with pytest.raises(ModelFailure,match='No API credential'):
        ChatCompletionsModel('openrouter','nvidia/nemotron-3-super-120b-a12b:free')

def test_parse_json_tolerates_code_fence_not_nonjson():
    assert parse_json('```json\n{"a": 1}\n```')=={'a':1}
    assert parse_json('Here is JSON: {"actions": []}')=={'actions':[]}
    with pytest.raises(ValueError):parse_json('not JSON')

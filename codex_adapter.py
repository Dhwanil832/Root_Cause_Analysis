"""Isolated GPT-5.5 sessions; current/fallback runtime selected by run.py."""
import json,os,pathlib,shutil,subprocess,sys,tempfile,time
ROOT=pathlib.Path(__file__).resolve().parent
from rca import provider,schema
from rca.storage import save,digest,now
CLI=shutil.which('codex')
PROFILE=dict(provider='codex_chatgpt',model='gpt-5.5',reasoning_effort='medium',snapshot_verified=False,authentication='saved ChatGPT login',context='fresh ephemeral session per call',call_count_cap=None,application_timeout=None,original_api_profile_equivalent=False)
DISABLED=['shell_tool','unified_exec','apps','plugins','multi_agent','code_mode_host','browser_use','browser_use_external','in_app_browser','computer_use','image_generation','memories','hooks','view_image','goals','sleep_tool','skill_search','tool_suggest']
def parse_result(answer,events):
 if not any(e.get('type')=='turn.completed' for e in events):raise provider.CallFailure('incomplete_response','No completed Codex turn')
 for e in events:
  if e.get('type')=='turn.failed':raise provider.CallFailure('transport_error','Codex turn failed')
  item=e.get('item',{})
  if item and item.get('type') not in ['agent_message','reasoning','error']:
   raise provider.CallFailure('evaluation_isolation','Unexpected tool/action item: '+str(item.get('type')))
 messages=[e['item']['text'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
 if not messages or messages[-1].strip()!=answer.strip():raise provider.CallFailure('output_integrity','Saved answer differs from final completed message')
 try:data=json.loads(answer);schema.validate(data)
 except (ValueError,TypeError) as exc:raise provider.CallFailure('output_contract',str(exc)) from None
 usage=[e['usage'] for e in events if e.get('type')=='turn.completed'][-1]
 return data,usage

def call(prompt,packet,folder):
 folder=pathlib.Path(folder);folder.mkdir(parents=True,exist_ok=False);t=time.monotonic()
 save(folder/'packet.json',packet);save(folder/'schema.json',schema.OUTPUT)
 (folder/'role-instructions.txt').write_text(prompt)
 user=provider.messages(prompt,packet)[1]['content'];(folder/'user-message.txt').write_text(user)
 save(folder/'started.json',dict(at=now(),execution_profile=PROFILE,messages_hash=digest(provider.messages(prompt,packet)),schema_hash=digest(schema.OUTPUT)))
 # Only this call's role, public packet and output schema exist in the working directory.
 with tempfile.TemporaryDirectory(prefix='rca-codex55-',dir='/private/tmp') as work:
  wd=pathlib.Path(work);(wd/'role.txt').write_text(prompt);save(wd/'schema.json',schema.OUTPUT)
  command=[CLI,'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check','--model','gpt-5.5','--sandbox','read-only','--cd',work,'--output-schema',str(wd/'schema.json'),'--output-last-message',str(folder/'answer.txt'),'--json']
  for feature in DISABLED:command+=['--disable',feature]
  for config in ['web_search="disabled"','project_doc_max_bytes=0','model_reasoning_effort="medium"','features.skip_host_skill_discovery=true','tools.view_image=false','model_instructions_file='+json.dumps(str(wd/'role.txt'))]:command+=['-c',config]
  command+=['-'];save(folder/'invocation.json',dict(argv=command,stdin_sha256=digest(user),api_key_removed=True,answer_key_supplied=False))
  env=dict(os.environ)
  for key in ['OPENAI_API_KEY','CODEX_API_KEY']:env.pop(key,None)
  try:
   with (folder/'events.jsonl').open('w') as out,(folder/'stderr.txt').open('w') as err:
    completed=subprocess.run(command,input=user,text=True,stdout=out,stderr=err,env=env,cwd=work)
   if completed.returncode:raise provider.CallFailure('codex_execution','Codex exited '+str(completed.returncode)+'; preserved stderr/events')
   events=[json.loads(line) for line in (folder/'events.jsonl').read_text().splitlines() if line.strip()]
   answer=(folder/'answer.txt').read_text();data,usage=parse_result(answer,events)
   save(folder/'result.json',dict(status='completed',seconds=round(time.monotonic()-t,3),usage=usage,model='gpt-5.5',model_identity_scope='CLI requested alias; not API snapshot verification',provider='codex_chatgpt',answer_hash=digest(answer),messages_hash=digest(provider.messages(prompt,packet))))
   return data
  except Exception as exc:
   save(folder/'error.json',dict(status='execution_error',category=getattr(exc,'category','adapter_error'),type=type(exc).__name__,detail=str(exc),seconds=round(time.monotonic()-t,3)))
   raise

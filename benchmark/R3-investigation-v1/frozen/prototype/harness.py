#!/usr/bin/env python3
import argparse,json
from pathlib import Path
from rca import engine
from rca.storage import read

def main():
 ap=argparse.ArgumentParser(description='Persistent supervised RCA prototype')
 sub=ap.add_subparsers(dest='command',required=True)
 p=sub.add_parser('init');p.add_argument('case');p.add_argument('--description',required=True);p.add_argument('--document',action='append',default=[])
 p=sub.add_parser('run');p.add_argument('case');p.add_argument('--max-calls',type=int,default=16)
 p=sub.add_parser('submit');p.add_argument('case');p.add_argument('--request');p.add_argument('--document');p.add_argument('--answer');p.add_argument('--source-id');p.add_argument('--corrects')
 p=sub.add_parser('status');p.add_argument('case')
 p=sub.add_parser('reapply-last');p.add_argument('case');p.add_argument('--reason',required=True)
 p=sub.add_parser('review');p.add_argument('case');p.add_argument('record');p.add_argument('--version',type=int,required=True);p.add_argument('--decision',choices=['approved','rejected'],required=True);p.add_argument('--note',required=True)
 p=sub.add_parser('serve');p.add_argument('case');p.add_argument('--port',type=int,default=8765)
 a=ap.parse_args()
 if a.command=='init':s=engine.create(a.case,a.description,a.document);print('Created case with',len(s['sources']),'sources.')
 elif a.command=='run':s=engine.run(a.case,a.max_calls);print('Phase:',s['phase'])
 elif a.command=='submit':print(json.dumps(dict(zip(['source_id','changed'],engine.submit(a.case,a.document,a.request,a.answer,a.source_id,a.corrects)))))
 elif a.command=='reapply-last':print(json.dumps(engine.reapply_last(a.case,a.reason)))
 elif a.command=='review':engine.review(a.case,a.record,a.version,a.decision,a.note);print('Human review recorded.')
 elif a.command=='serve':
  from rca.server import serve
  serve(a.case,a.port)
 elif a.command=='status':
  s=read(engine.statepath(a.case));print(json.dumps(dict(phase=s['phase'],calls=len(s['calls']),sources=len(s['sources']),records=len(s['ledger']),queue=len(s['queue']),requests=[dict(id=k,**{f:v['record'][f] for f in ['claim','status','fields']}) for k,v in s['ledger'].items() if v['record']['kind']=='request']),indent=2))
if __name__=='__main__':main()

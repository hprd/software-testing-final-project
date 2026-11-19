import io,json,pathlib,sys,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import normative_review as n, resolve_contracts as rc
p1=rc.passage('Example','matched_method','Returns values in encounter order.',{},'f()')
p2=rc.passage('Example','declaring_class','Null inputs are forbidden.',{},'class Example')
record={'api_id':'x','owner':'Example','signature':'f()','resolution':'source_signature_match','passages':[p1,p2],'unresolved':['inherited contracts']}
statement=lambda claim,quote:{'kind':'obligation','claim':claim,'conditions':'always','scope':'result','quote':quote}
extract1={'statements':[statement('preserve order',p1['text'])],'unknowns':[],'more_may_exist':False}
extract2={'statements':[statement('no null input',p2['text'])],'unknowns':[],'more_may_exist':False}
audit1={'assessments':[{'statement_id':p1['id']+':0:0','verdict':'supported','kind_verdict':'supported','reason':'stated'}],'omissions':[],'unknowns':[]}
audit2={'assessments':[{'statement_id':p2['id']+':0:0','verdict':'unclear','kind_verdict':'unclear','reason':'scope requires review'}],'omissions':[{'claim':'possible missing fact','quote':p2['text']}],'unknowns':[]}
def responses(items, requests):
 it=iter(items)
 def send(req,timeout):
  requests.append(json.loads(req.data));return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(next(it))}}]}).encode())
 return send
req=[];snapshots=[];r=n.review(record,'http://unused','fake',request_fn=responses([extract1,extract2,audit1,audit2],req),progress=lambda x:snapshots.append(json.loads(json.dumps(x))))
assert r['status']=='needs_manual_resolution' and [x['audit_status'] for x in r['chunks']]==['complete','complete']
assert all('PASS 1' in req[i]['messages'][1]['content'] for i in (0,1)) and all('PASS 2' in req[i]['messages'][1]['content'] for i in (2,3))
assert r['chunks'][1]['audit']['omissions'] and len(snapshots)>=5
try:n.audit_statements(dict(audit1,assessments=[]),n.extract_statements(extract1,n.chunks_for(p1)[0]),n.chunks_for(p1)[0]);raise AssertionError('missing audit accepted')
except ValueError:pass
try:n.extract_statements(dict(extract1,statements=[statement('fake','fabricated source')]),n.chunks_for(p1)[0]);raise AssertionError('fabricated quote accepted')
except ValueError:pass
try:n.audit_statements(dict(audit1,omissions=[{'claim':'bad','quote':'invented source'}]),n.extract_statements(extract1,n.chunks_for(p1)[0]),n.chunks_for(p1)[0]);raise AssertionError('fabricated omission accepted')
except ValueError:pass
req=[];r=n.review(record,'http://unused','fake',request_fn=responses([dict(extract1,statements=[statement('bad','fake quote')]),extract2,audit2],req))
assert r['status']=='incomplete_requires_human_review' and r['chunks'][0]['audit_status']=='not_run_extraction_error'
assert n.review(dict(record,resolution='unresolved'),'http://unused','fake')['status']=='documentation_unresolved'
long=rc.passage('Example','matched_method','a'*5000,{},'f()');chunks=n.chunks_for(long);assert ''.join(x['text'] for x in chunks)==long['text']
print('PASS: two-pass ordering, evidence, audit coverage, omissions, error isolation and chunk coverage')
unconditional=dict(extract1,statements=[dict(extract1['statements'][0],conditions='')])
assert n.extract_statements(unconditional,n.chunks_for(p1)[0])[0]['conditions']==''
print('PASS: explicit empty condition accepted without inferring broader applicability')

try:n.audit_statements(dict(audit1,assessments=[{'statement_id':p1['id']+':0:0','verdict':'supported','reason':'no kind assessment'}]),n.extract_statements(extract1,n.chunks_for(p1)[0]),n.chunks_for(p1)[0]);raise AssertionError('missing kind verdict accepted')
except ValueError:pass
print('PASS: normative kind must be audited separately')

clean_audit2={'assessments':[{'statement_id':p2['id']+':0:0','verdict':'supported','kind_verdict':'supported','reason':'stated'}],'omissions':[],'unknowns':[]}
r=n.review(record,'http://unused','fake',request_fn=responses([extract1,extract2,audit1,clean_audit2],[]));assert r['status']=='requires_human_review'
r=n.review(record,'http://unused','fake',request_fn=responses([dict(extract1,more_may_exist=True),extract2,audit1,clean_audit2],[]));assert r['status']=='needs_manual_resolution'
print('PASS: omissions, flagged kinds and possible truncation block automatic handoff')
undefined=rc.passage('Example','matched_method','If modified, results are undefined.',{},'f()')
chunk=n.chunks_for(undefined)[0]
row={'kind':'prohibition','claim':'undefined if modified','conditions':'modified','scope':'results','quote':undefined['text']}
flagged=n.extract_statements({'statements':[row],'unknowns':[],'more_may_exist':False},chunk)
assert flagged[0]['review_flags']
row=dict(row,kind='undefined_condition')
assert not n.extract_statements({'statements':[row],'unknowns':[],'more_may_exist':False},chunk)[0]['review_flags']
print('PASS: undefined-result/prohibition mismatch is flagged for human review')
flag_record={'api_id':'y','owner':'Example','signature':'f()','resolution':'source_signature_match','passages':[undefined],'unresolved':[]}
wrong_kind={'kind':'prohibition','claim':'undefined if modified','conditions':'modified','scope':'results','quote':undefined['text']}
flag_extract={'statements':[wrong_kind],'unknowns':[],'more_may_exist':False}
flag_audit={'assessments':[{'statement_id':undefined['id']+':0:0','verdict':'supported','kind_verdict':'supported','reason':'stated'}],'omissions':[],'unknowns':[]}
r=n.review(flag_record,'http://unused','fake',request_fn=responses([flag_extract,flag_audit],[]))
assert r['status']=='needs_manual_resolution' and r['chunks'][0]['statements'][0]['review_flags']
print('PASS: an auditor missing the flagged category error cannot open the handoff gate')
conditional=rc.passage('Example','matched_method','If more control is required, use another collector.',{},'f()')
row={'kind':'permission','claim':'If more control is required, use another collector.','conditions':'','scope':'callers','quote':conditional['text']}
assert n.extract_statements({'statements':[row],'unknowns':[],'more_may_exist':False},n.chunks_for(conditional)[0])[0]['review_flags']
print('PASS: condition omitted from a conditional claim is flagged')
four={'statements':[statement('preserve order',p1['text']) for _ in range(4)],'unknowns':[],'more_may_exist':False}
four_audit={'assessments':[{'statement_id':p1['id']+':0:'+str(i),'verdict':'supported','kind_verdict':'supported','reason':'stated'} for i in range(4)],'omissions':[],'unknowns':[]}
one_record=dict(record,passages=[p1]);r=n.review(one_record,'http://unused','fake',request_fn=responses([four,four_audit],[]))
assert r['status']=='needs_manual_resolution' and r['chunks'][0]['review_flags']
print('PASS: hitting extraction cap requires review even if the model claims completeness')
import subprocess
with tempfile.TemporaryDirectory() as td:
 td=pathlib.Path(td);source=td/'resolved.jsonl';out=td/'output.json'
 source.write_text(json.dumps(record)+'\n');out.write_text('keep this')
 result=subprocess.run([sys.executable,str(ROOT/'normative_review.py'),'--resolved',str(source),'--select','Example.f()','--output',str(out)],capture_output=True,text=True)
 assert result.returncode!=0 and out.read_text()=='keep this'
print('PASS: existing review output is preserved')

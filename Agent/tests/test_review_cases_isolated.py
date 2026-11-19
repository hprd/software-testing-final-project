import io,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import review_cases_isolated as m
case={'id':'x','api':'C.f()','dimension':'ordering','scenario':'ordered input','alternative':'reverse output'}
import resolve_contracts
passage=resolve_contracts.passage('C','matched_method','Preserves encounter order.',{},'f()')
doc={'resolution':'source_signature_match','passages':[passage],'unresolved':['linked contracts']}
source_id=passage['id']
def responses(items,requests):
 it=iter(items)
 def send(req,timeout):
  requests.append(json.loads(req.data));return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(next(it))}}]}).encode())
 return send
select={'quotes':[{'source_id':source_id,'quote':'Preserves encounter order.'}],'unknowns':[]}
a={'label':'invalid','reason':'order required','unknowns':[]};b={'label':'candidate','reason':'uncertain','unknowns':[]}
req=[];out=m.assess(case,doc,'http://unused','fake',request_fn=responses([select,a,b],req))
assert out['label']=='inconclusive' and not out['agreement'] and len(out['stages'])==3
assert 'invalid' not in req[2]['messages'][1]['content'].split('INPUT JSON:',1)[1]
req=[];out=m.assess(case,doc,'http://unused','fake',request_fn=responses([select,a,a],req));assert out['label']=='invalid' and out['agreement']
try:m.assess(case,doc,'http://unused','fake',request_fn=responses([dict(select,quotes=[{'source_id':source_id,'quote':'invented quote'}])],[]));raise AssertionError('accepted fabricated quote')
except ValueError:pass
assert m.assess(case,dict(doc,resolution='unresolved'),'http://unused','fake')['status']=='documentation_unresolved'
print('PASS: source quote gate, independent context, disagreement, unresolved documentation')

tampered=dict(doc,passages=[dict(passage,text='tampered')])
try:m.assess(case,tampered,'http://unused','fake',request_fn=responses([],[]));raise AssertionError('accepted tampered passage')
except ValueError:pass
print('PASS: tampered passage ID rejected')

req=[];out=m.assess(case,doc,'http://unused','fake',request_fn=responses([{'quotes':[],'unknowns':[]},a,a],req));assert out['label']=='inconclusive' and not out['evidence_selected'] and len(req)==1
print('PASS: empty evidence cannot yield substantive classification')
check={'contradiction':'yes','undefined':'no','source_id':source_id,'quote':'Preserves encounter order.','reasons':['order required']}
req=[];out=m.assess(case,doc,'http://unused','fake',request_fn=responses([select,b,b,check],req),guard=True)
assert out['stage_labels']==['candidate','candidate'] and out['label']=='inconclusive'
req=[];out=m.assess(case,doc,'http://unused','fake',request_fn=responses([select,a,a,check],req),guard=True)
assert out['label']=='invalid' and out['constraint_check']['contradiction']=='yes'
assert 'candidate' not in req[3]['messages'][1]['content'].split('INPUT JSON:',1)[1]
print('PASS: isolated constraint check can downgrade but cannot upgrade')
import subprocess,tempfile
with tempfile.TemporaryDirectory() as td:
 td=pathlib.Path(td); out=td/'out.json'; source=td/'docs.jsonl';source.write_text('')
 cmd=[sys.executable,str(ROOT/'review_cases_isolated.py'),'--resolved',str(source),'--output',str(out),'--select','no-such-case']
 result=subprocess.run(cmd,capture_output=True,text=True)
 assert result.returncode!=0 and not out.exists() and 'unknown --select' in result.stderr
print('PASS: unknown case selection cannot appear complete')
with tempfile.TemporaryDirectory() as td:
 path=pathlib.Path(td)/'stage.json';trace=m.CheckpointTrace(path,'case',{'model':'fake'})
 trace.append({'stage':'select','response':{'parsed':{'quotes':[]}}})
 checkpoint=json.loads(path.read_text())
 assert checkpoint['case_id']=='case' and checkpoint['status']=='in_progress_or_interrupted' and len(checkpoint['completed_stages'])==1
print('PASS: completed role responses persist independently of case completion')

bad_check={'contradiction':'no','undefined':'yes','source_id':source_id,'quote':'Preserves encounter order.','reasons':['claimed undefined']}
out=m.assess(case,doc,'http://unused','fake',request_fn=responses([select,b,b,bad_check],[]),guard=True)
assert out['label']=='inconclusive' and out['constraint_evidence_error']
print('PASS: undefined claim requires supporting source wording')
with tempfile.TemporaryDirectory() as td:
 td=pathlib.Path(td);out=td/'out.json';source=td/'docs.jsonl';casefile=td/'cases.json'
 casefile.write_text(json.dumps({'cases':[case]}))
 source.write_text('\n'.join(json.dumps({'owner':'C','signature':'f()','resolution':'source_signature_match'}) for _ in range(2))+'\n')
 result=subprocess.run([sys.executable,str(ROOT/'review_cases_isolated.py'),'--cases',str(casefile),'--resolved',str(source),'--output',str(out)],capture_output=True,text=True)
 assert result.returncode==0 and json.loads(out.read_text())['results'][0]['status']=='documentation_ambiguous'
print('PASS: ambiguous API records do not reach the model')

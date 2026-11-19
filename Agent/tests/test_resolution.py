import importlib.util, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import resolve_contracts as r
base={'id':'a','owner':'x.Foo','signature':'get()','contract_context':{'class':{'doc':'Class docs.'},'matching_method_name_overloads':[{'declaration':'int get()','doc':'Zero args.'},{'declaration':'int get(int x)','doc':'One arg.'}]}}
docs={'x.Foo':{'class':base['contract_context']['class'],'methods':{'get':base['contract_context']['matching_method_name_overloads']}}}
x=r.resolve(base,docs,'hash','verified');assert x['resolution']=='source_signature_match';assert [p['text'] for p in x['passages']]==['Class docs.','Zero args.']
x=r.resolve(dict(base,signature='get(int)'),docs,'hash','verified');assert x['resolution']=='source_signature_match';assert x['passages'][-1]['text']=='One arg.'
x=r.resolve(dict(base,signature='get(java.lang.String)'),docs,'hash','verified');assert x['resolution']=='unresolved';assert all(p['kind']!='matched_method' for p in x['passages'])
ambiguous=dict(base,contract_context={'matching_method_name_overloads':[{'declaration':'int get()','doc':'a'},{'declaration':'long get()','doc':'b'}]})
ambiguous_docs={'x.Foo':{'methods':{'get':ambiguous['contract_context']['matching_method_name_overloads']}}}
assert r.resolve(ambiguous,ambiguous_docs,'hash','verified')['resolution']=='unresolved'
assert r.resolve(base,{},'hash')['resolution']=='unresolved'
tampered=dict(base,contract_context={'class':{'doc':'forged'},'matching_method_name_overloads':[{'declaration':'int get()','doc':'forged'}]})
assert r.resolve(tampered,docs,'hash','verified')['passages'][-1]['text']=='Zero args.'
spec=importlib.util.spec_from_file_location('score',ROOT/'evaluation/score.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
result=s.score([{'id':'a','label':'candidate'},{'id':'b','label':'invalid'}],[{'id':'a','label':'invalid'}]);assert result['correct']==0 and result['missing']==['b'] and result['confusion']['candidate']['invalid']==1
try:s.score([{'id':'a','label':'candidate'}],[{'id':'a','label':'candidate'},{'id':'a','label':'invalid'}]);raise AssertionError('duplicate accepted')
except ValueError:pass
print('PASS: exact source parameter matching, ambiguous and unmatched cases unresolved, scoring')
import io, review_cases as review
case={'id':'case','api':'x.Foo.get()','dimension':'ordering','scenario':'two values','alternative':'reverse them'}
doc={'resolution':'source_signature_match','passages':[{'id':'s','text':'Order is unspecified.'}],'unresolved':['inheritance']}
def response(value):
 def send(req,timeout):return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(value)}}]}).encode())
 return send
p={'label':'candidate','reason':'No order stated.','evidence_kind':'explicit','source_id':'s','quote':'Order is unspecified.','unknowns':[]}
assert review.assess(case,doc,'http://unused','fake',request_fn=response(p))['label']=='candidate'
try:review.assess(case,doc,'http://unused','fake',request_fn=response(dict(p,quote='invented quotation')));raise AssertionError('fabricated quote accepted')
except ValueError:pass
assert review.assess(case,dict(doc,resolution='unresolved'),'http://unused','fake')['status']=='documentation_unresolved'
print('PASS: case evidence verification and unresolved documentation gate')
import subprocess,tempfile
with tempfile.TemporaryDirectory() as td:
 td=pathlib.Path(td);queue=td/'queue';docfile=td/'docs';coverage=td/'coverage';out=td/'out'
 queue.write_text('');docfile.write_text('{}\n');coverage.write_text(json.dumps({'jdk_source_sha256':'hash','jdk_docs_sha256':'wrong'}))
 result=subprocess.run([sys.executable,str(ROOT/'resolve_contracts.py'),'--queue',str(queue),'--docs',str(docfile),'--coverage',str(coverage),'--output',str(out)],capture_output=True,text=True)
 assert result.returncode!=0 and not out.exists() and 'artifact hash mismatch' in result.stderr
print('PASS: mismatched documentation artifact rejected')

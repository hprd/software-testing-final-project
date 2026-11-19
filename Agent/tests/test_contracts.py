import hashlib, importlib.util, io, json, pathlib, sys, tempfile, unittest.mock
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('contracts',ROOT/'contracts_deep_dive.py'); mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
JAVA='/misc/scratch/aab5473/testing-tools/temurin-jdk21'
with tempfile.TemporaryDirectory() as td:
 root=pathlib.Path(td); inv=root/'calls.jsonl'; out=root/'out'
 calls=[{'owner':'java.util.Hashtable','signature':'keys()','kind':'method_invocation','resolved':True,'file':'Example.java','line':4,'expression':'t.keys()'}, {'owner':'external.X','signature':'x()','kind':'method_invocation','resolved':True,'file':'Example.java','line':5}, {'resolved':False,'kind':'method_invocation','file':'Example.java','line':6}]
 inv.write_text(''.join(json.dumps(c)+'\n' for c in calls))
 args=['contracts','--inventory',str(inv),'--java-home',JAVA,'--output',str(out)]
 with unittest.mock.patch.object(sys,'argv',args): mod.main()
 assert json.loads((out/'coverage.json').read_text())['jdk_docs_sha256']==hashlib.sha256((out/'jdk-docs.jsonl').read_bytes()).hexdigest()
 rows=[json.loads(s) for s in (out/'api-queue.jsonl').read_text().splitlines()]; row=next(r for r in rows if r['owner']=='java.util.Hashtable')
 assert row['status']=='pending_review' and row['contract_context']['matching_method_name_overloads']
 assert sum(r['call_count'] for r in rows)==3 and sum(r['status']=='documentation_unavailable' for r in rows)==2
 doc=row['contract_context']['matching_method_name_overloads'][0]['doc']; quote=doc[:30]
 def response(q):
  payload={'status':'candidate_variations','variations':[{'observable_behavior':'order','allowed_variation':'order','conditions':['stable table'],'preserved_constraints':['keys'],'perturbation_idea':'reorder','evidence_quote':q}],'unresolved_questions':['review']}
  return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(payload)}}]}).encode())
 args+=['--endpoint','http://unused/v1/chat/completions','--limit','1']
 with unittest.mock.patch.object(sys,'argv',args),unittest.mock.patch.object(mod.urllib.request,'urlopen',return_value=response('not a real quotation')):mod.main()
 result=json.loads(next((out/'analyses').glob('*.json')).read_text());assert result['status']=='model_error'
 with unittest.mock.patch.object(sys,'argv',args),unittest.mock.patch.object(mod.urllib.request,'urlopen',return_value=response(quote)):mod.main()
 result=json.loads(next((out/'analyses').glob('*.json')).read_text());assert result['status']=='model_proposal_requires_human_review'
 print('PASS: documentation grouping, missing-source status, evidence rejection, retry and review status')

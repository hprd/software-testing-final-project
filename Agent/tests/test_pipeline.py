import importlib.util, io, json, pathlib, sys, tempfile
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('pipeline', ROOT/'pipeline.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def responses(items):
    it = iter(items)
    def send(req, timeout):
        return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(next(it))}}]}).encode())
    return send
r = m.review_list([{'id':'a'}, {'id':'b'}], 'http://unused', 'fake', 1,
                  responses([{'api_ids':['a','a','invented'], 'notes':[]}]))
assert r['missing_ids'] == ['b'] and r['unknown_ids'] == ['invented'] and r['duplicate_ids'] == ['a']
record = {'id':'a', 'owner':'Example', 'signature':'f()', 'kind':'method', 'call_count':1,
          'status':'pending_review', 'contract_context':{'class':{'doc':'A documented example.'},
          'matching_method_name_overloads':[]}}
missing = {'id':'b', 'owner':None, 'signature':None, 'kind':'unresolved', 'call_count':2, 'status':'documentation_unavailable'}
extract = {'facts':[{'claim':'example','quote':'A documented example.'}],'unknowns':[]}
variation = {'proposals':[], 'unknowns':['insufficient evidence']}
critic = {'reviews':[], 'missing_contracts':['other contracts']}
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td); queue = td/'queue.jsonl'
    queue.write_text('\n'.join(json.dumps(x) for x in [record,missing])+'\n')
    result = m.run_pipeline(queue,td/'out','http://unused','fake',1,2,None,[],responses([
        {'api_ids':['a'], 'notes':[]}, extract, variation, critic]))
    assert result['call_count'] == 3 and result['statuses'] == {'requires_human_review':1,'documentation_unavailable':1}
    assert json.loads(next((td/'out/list-review').glob('*.json')).read_text())['missing_ids'] == ['b']
    result = m.run_pipeline(queue,td/'out','http://unused','fake',1,2,None,[],responses([]))
    assert result['statuses']['requires_human_review'] == 1
print('PASS: list discrepancies, unavailable groups, contract delegation and resume')
# Experiment routing is opt-in and requires the matching completed API review.
with tempfile.TemporaryDirectory() as td:
    td = pathlib.Path(td); calls=[]
    def execute(project, java_home, maven, repo, dest, timeout):
        calls.append((project, dest, timeout));dest.mkdir(parents=True)
        (dest/'result.json').write_text('{}')
        return {'status':'confirmed_scoped_order_dependency','finding_scope':'scoped test'}
    entry={'id':'h','owner':'java.util.Hashtable','signature':'keys()','kind':'method_invocation',
           'status':'error','review':'review.json'}
    summary={'groups':[entry]}
    stage=m.run_registered_experiment(summary,td,*([td]*4),10,execute_fn=execute)
    assert stage['status']=='not_run_contract_review_unavailable' and not calls
    entry['status']='requires_human_review'
    stage=m.run_registered_experiment(summary,td,*([td]*4),10,execute_fn=execute)
    assert stage['status']=='confirmed_scoped_order_dependency' and len(calls)==1
    assert json.loads((td/'manifest.json').read_text())['experiment']['model_review']=='review.json'
    stage=m.run_registered_experiment(summary,td,*([td]*4),10,execute_fn=execute)
    assert stage['status']=='not_run_output_exists' and len(calls)==1
    entry['kind']='method_reference'
    stage=m.run_registered_experiment(summary,td,*([td]*4),10,execute_fn=execute)
    assert stage['status']=='not_run_contract_review_unavailable' and len(calls)==1
print('PASS: experiment routing, review gate, existing-output preservation, scope')
# Normative extraction/audit must finish before staged proposals are requested.
with tempfile.TemporaryDirectory() as td:
    td=pathlib.Path(td);queue=td/'queue.jsonl';resolved=td/'resolved.jsonl';out=td/'out'
    queue.write_text(json.dumps(record)+'\n')
    resolved.write_text(json.dumps({'api_id':'a','owner':'Example','signature':'f()','kind':'method'})+'\n')
    calls=[]
    def normative(rec,endpoint,model,timeout,request_fn=None,kinds=None,progress=None):
        calls.append('normative')
        result={'api_id':rec['api_id'],'version':m.normative_review.VERSION,'model':model,'status':'requires_human_review','chunks':[]}
        progress(result);return result
    stages=m.run_normative_stages(queue,resolved,out,'http://unused','fake',1,[],1,review_fn=normative)
    assert stages['a']['status']=='requires_human_review' and calls==['normative']
    result=m.run_pipeline(queue,out,'http://unused','fake',1,2,None,[],responses([
        {'api_ids':['a'],'notes':[]}, extract, variation, critic]),normative_stages=stages)
    assert result['groups'][0]['status']=='requires_human_review' and result['groups'][0]['normative_review']['path']
    blocked=m.run_pipeline(queue,out,'http://unused','fake',1,2,None,[],responses([]),normative_stages={'a':{'status':'incomplete_requires_human_review'}})
    assert blocked['groups'][0]['status']=='normative_review_unavailable'
print('PASS: normative passes gate later staged contract analysis')
# A cached normative result is reusable only when source coverage and audit records validate.
import resolve_contracts
src=resolve_contracts.passage('Example','matched_method','Returns a value.','jdk','f()')
resolved_record={'api_id':'x','owner':'Example','signature':'f()','resolution':'source_signature_match','passages':[src],'unresolved':[]}
statement={'kind':'obligation','claim':'returns a value','conditions':'','scope':'return','quote':'Returns a value.'}
extract_norm={'statements':[statement],'unknowns':[],'more_may_exist':False}
audit_norm={'assessments':[{'statement_id':src['id']+':0:0','verdict':'supported','kind_verdict':'supported','reason':'stated'}],'omissions':[],'unknowns':[]}
r=m.normative_review.review(resolved_record,'http://unused','fake',request_fn=responses([extract_norm,audit_norm]))
meta={'resolved_file':'resolved','resolved_sha256':'hash','reviewer_sha256':'hash2','endpoint':'http://unused','source_kinds':None};r['run_metadata']=meta
assert m.valid_cached_normative(r,resolved_record,'fake',None,meta)
r=json.loads(json.dumps(r))
r['chunks'][0]['audit']['assessments'][0]['verdict']='unsupported'
assert not m.valid_cached_normative(r,resolved_record,'fake',None,meta)
print('PASS: cached normative evidence is checked before reuse')

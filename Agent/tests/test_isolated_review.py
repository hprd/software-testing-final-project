import io, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
import isolated_review as m
record={'id':'x','owner':'Example','signature':'f()','contract_context':{'class':{'doc':'Class constraint.'},'matching_method_name_overloads':[{'doc':'Method result.'}]}}
answers=iter([
 {'facts':[{'claim':'bad inference','quote':'Class constraint.'}],'unknowns':[]},
 {'verdict':'unsupported','reason':'The claim is not supported.'},
 {'facts':[{'claim':'result','quote':'Method result.'}],'unknowns':[]},
 {'verdict':'supported','reason':'The claim is stated.'},
 {'proposals':[{'behavior':'one','alternative':'two','conditions':'valid','must_preserve':['result'],'evidence_kind':'absence_inference','evidence_quote':'','reasoning':'not stated'}],'unknowns':[]},
 {'verdict':'needs_review','reasons':['context incomplete'],'missing_contracts':['inherited contract']},
])
requests=[]
def send(req, timeout):
    requests.append(json.loads(req.data)); return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(next(answers))}}]}).encode())
r=m.review(record,'http://unused','fake',request_fn=send)
assert r['status']=='requires_human_review' and len(r['fact_assessments'])==2
assert r['fact_assessments'][0]['assessment']['verdict']=='unsupported'
assert 'bad inference' not in requests[4]['messages'][1]['content']
assert 'model_supported_facts' not in requests[5]['messages'][1]['content']
assert len(r['reviews'])==1 and r['reviews'][0]['verdict']=='needs_review'
print('PASS: source isolation, unsupported fact exclusion, independent proposal audit')
assert 'Method result.' not in requests[0]['messages'][1]['content']
assert 'Method result.' not in requests[1]['messages'][1]['content']
assert 'Class constraint.' not in requests[2]['messages'][1]['content']
def invalid(req, timeout):
    return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps({'facts':[{'claim':'x','quote':'not a source quotation'}],'unknowns':[]})}}]}).encode())
try:
    m.review(record,'http://unused','fake',request_fn=invalid)
    raise AssertionError('accepted fabricated extraction quotation')
except ValueError:
    pass
print('PASS: extraction passage boundaries and quote rejection')

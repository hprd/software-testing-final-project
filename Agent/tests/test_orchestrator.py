import importlib.util, io, json, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('orchestrator',ROOT/'orchestrator.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
record={'id':'x','owner':'java.util.Hashtable','signature':'keys()','contract_context':{'class':{'declaration':'class Hashtable','doc':'The keys have unspecified order.'},'matching_method_name_overloads':[{'declaration':'Enumeration keys()','doc':'Returns an enumeration of the keys.'}]}}
extract={'facts':[{'claim':'Returns an enumeration','quote':'Returns an enumeration of the keys.'}],'unknowns':[]}
variation={'proposals':[{'behavior':'order','alternative':'reverse keys','conditions':'stable table','must_preserve':['keys'],'evidence_kind':'absence_inference','evidence_quote':'','reasoning':'No order guarantee in supplied text.'}],'unknowns':['inheritance']}
critic={'reviews':[{'proposal_index':0,'verdict':'needs_review','reasons':['inherited contracts']}],'missing_contracts':['inherited contracts']}
def responses(items):
 it=iter(items)
 def send(req,timeout):return io.BytesIO(json.dumps({'choices':[{'message':{'content':json.dumps(next(it))}}]}).encode())
 return send
res=m.review(record,'http://unused','fake',request_fn=responses([extract,variation,critic]));assert res['status']=='requires_human_review';assert len(res['stages'])==3
for broken in [dict(extract,facts=[{'claim':'x','quote':'fabricated text'}])]:
 try:m.review(record,'http://unused','fake',request_fn=responses([broken]));raise AssertionError('accepted false quote')
 except ValueError:pass
try:m.review(record,'http://unused','fake',request_fn=responses([extract,variation,dict(critic,reviews=[])]));raise AssertionError('accepted missing critic review')
except ValueError:pass
print('PASS: staged review, quote verification, complete critic coverage, human-review status')

bad_absence = dict(variation, proposals=[dict(variation["proposals"][0], evidence_quote="not a source quote")])
r = m.review(record, "http://unused", "fake", request_fn=responses([extract,bad_absence,critic]))
assert r["evidence_errors"] and r["status"] == "requires_human_review"
print("PASS: invalid absence quote retained as evidence error for critic")

# Prevent apparently successful reviews with no stated constraints or no critic rationale.
for bad_variation, bad_critic in [
    (dict(variation, proposals=[dict(variation['proposals'][0], must_preserve=[])]), critic),
    (variation, dict(critic, reviews=[dict(critic['reviews'][0], reasons=[])])),
]:
    try:
        m.review(record, 'http://unused', 'fake', request_fn=responses([extract, bad_variation, bad_critic]))
        raise AssertionError('accepted an incomplete review')
    except ValueError:
        pass
print('PASS: empty preserved constraints and critic rationale rejected')
try:
    m.review(record, 'http://unused', 'fake', request_fn=responses([
        extract, dict(variation, proposals=variation['proposals'] * 4)]))
    raise AssertionError('accepted too many proposals')
except ValueError:
    pass
print('PASS: proposal count limit')

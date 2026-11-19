import importlib.util,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('rel',ROOT/'evaluation/reliability_report.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cases={'split':'development','cases':[{'id':'a','label':'invalid'},{'id':'b','label':'candidate'},{'id':'c','label':'inconclusive'}]}
run={'complete':True,'metadata':{'cases_sha256':'hash'},'results':[{'id':'a','label':'candidate','status':'model_classification_requires_human_review'},{'id':'b','status':'model_error'},{'id':'c','label':'inconclusive','status':'model_classification_requires_human_review'}]}
r=m.report(cases,run,'hash');assert r['unsafe_false_positives']==['a'] and r['missing_or_failed']==['b'] and not r['meets_scenario_gate']
run['results']=[{'id':x['id'],'label':x['label'],'status':'model_classification_requires_human_review'} for x in cases['cases']]
assert not m.report(cases,run,'hash')['meets_scenario_gate']
cases['split']='held_out';assert m.report(cases,run,'hash')['meets_scenario_gate']
try:m.report(cases,{'results':[run['results'][0],run['results'][0]]});raise AssertionError('duplicate accepted')
except ValueError:pass
print('PASS: unsafe predictions, errors, holdout gate, duplicates')

run['complete']=False;assert not m.report(cases,run,'hash')['meets_scenario_gate']
print('PASS: incomplete run cannot meet gate')
import json,subprocess,sys,tempfile
with tempfile.TemporaryDirectory() as td:
 td=pathlib.Path(td);a=td/'cases.json';b=td/'run.json';a.write_text(json.dumps(cases));b.write_text(json.dumps(run))
 result=subprocess.run([sys.executable,str(ROOT/'evaluation/reliability_report.py'),'--cases',str(a),'--results',str(b)],capture_output=True,text=True)
 assert result.returncode==1 and not json.loads(result.stdout)['meets_scenario_gate']
print('PASS: failed gate returns nonzero for automation')

run['complete']=True;assert not m.report(cases,run,'different')['meets_scenario_gate']
print('PASS: mismatched case file cannot meet gate')

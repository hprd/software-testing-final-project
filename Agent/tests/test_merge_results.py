import importlib.util,json,pathlib,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1];spec=importlib.util.spec_from_file_location('merge',ROOT/'evaluation/merge_results.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as td:
 a=pathlib.Path(td)/'a';b=pathlib.Path(td)/'b'
 a.write_text(json.dumps({'complete':False,'results':[{'id':'a','status':'model_error'}]}));b.write_text(json.dumps({'complete':True,'results':[{'id':'b','status':'model_classification_requires_human_review','label':'invalid'}]}))
 result=m.merge([a,b]);assert not result['complete'] and len(result['results'])==2 and result['results'][0]['status']=='model_error'
 b.write_text(json.dumps({'complete':True,'results':[{'id':'a'}]}))
 try:m.merge([a,b]);raise AssertionError('accepted duplicate')
 except ValueError:pass
print('PASS: partial evidence preserved and duplicate cases rejected')
with tempfile.TemporaryDirectory() as td:
 a=pathlib.Path(td)/'a';b=pathlib.Path(td)/'b';meta={'model':'m','endpoint':'e','cases_sha256':'c','resolved_sha256':'r','reviewer_sha256':'v','constraint_check':True}
 a.write_text(json.dumps({'complete':True,'metadata':meta,'results':[{'id':'a'}]}));b.write_text(json.dumps({'complete':True,'metadata':meta,'results':[{'id':'b'}]}))
 assert m.merge([a,b])['metadata']['cases_sha256']=='c'
 b.write_text(json.dumps({'complete':True,'metadata':dict(meta,reviewer_sha256='other'),'results':[{'id':'b'}]}))
 assert m.merge([a,b])['metadata']=={}
print('PASS: provenance retained only for matching runs')

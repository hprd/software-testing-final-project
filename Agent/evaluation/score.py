#!/usr/bin/env python3
"""Score explicit case classifications; this does not interpret free-form model prose."""
import argparse, collections, json, pathlib
LABELS={'candidate','invalid','inconclusive'}
def score(cases, predictions):
 expected={x['id']:x['label'] for x in cases}; seen={}
 for item in predictions:
  case=item.get('id'); label=item.get('label')
  if case not in expected or case in seen or label not in LABELS: raise ValueError('unknown, duplicate or invalid prediction')
  seen[case]=label
 matrix=collections.Counter((expected[k],v) for k,v in seen.items())
 return {'cases':len(expected),'classified':len(seen),'correct':sum(expected[k]==v for k,v in seen.items()),
         'missing':[k for k in expected if k not in seen],
         'confusion':{a:{b:matrix[a,b] for b in sorted(LABELS)} for a in sorted(LABELS)},
         'note':'Labels do not validate implementations or establish site dependencies.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=pathlib.Path,default=pathlib.Path(__file__).with_name('cases.json'));p.add_argument('--predictions',type=pathlib.Path,required=True);a=p.parse_args()
 data=json.loads(a.predictions.read_text())
 if isinstance(data,dict): data=[{'id':x['id'],'label':x['label']} for x in data.get('results',[]) if x.get('status')=='model_classification_requires_human_review']
 print(json.dumps(score(json.loads(a.cases.read_text())['cases'],data),indent=2))
if __name__=='__main__':main()

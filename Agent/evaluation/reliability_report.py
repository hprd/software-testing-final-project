#!/usr/bin/env python3
"""Summarize model results with explicit unsafe and incomplete classifications."""
import argparse,collections,hashlib,json,pathlib,sys
LABELS={'candidate','invalid','inconclusive'}
def report(case_data,run,expected_cases_sha256=None):
 cases=case_data['cases'];ids=[x['id'] for x in cases]
 if len(ids)!=len(set(ids)):raise ValueError('duplicate evaluation IDs')
 expected={x['id']:x['label'] for x in cases}
 if any(x not in LABELS for x in expected.values()):raise ValueError('invalid evaluation label')
 rows=run['results'];seen=set();predictions={};errors=[]
 for row in rows:
  ident=row['id']
  if ident not in expected or ident in seen:raise ValueError('unknown or duplicate result ID')
  seen.add(ident)
  if row.get('status')=='model_classification_requires_human_review' and row.get('label') in LABELS:predictions[ident]=row['label']
  else:errors.append({'id':ident,'status':row.get('status')})
 missing=[i for i in ids if i not in predictions];unsafe=[i for i,v in predictions.items() if expected[i]=='invalid' and v=='candidate']
 wrong=[i for i,v in predictions.items() if expected[i]!=v];counts=collections.Counter(expected.values())
 held_out=case_data.get('split')=='held_out'
 thresholds={'case_file_matches_recorded_hash':bool(expected_cases_sha256) and run.get('metadata',{}).get('cases_sha256')==expected_cases_sha256,
             'run_marked_complete':run.get('complete') is True,'all_cases_classified':not missing,'zero_invalid_as_candidate':not unsafe,
             'all_labels_match':not wrong and not missing,'held_out_set':held_out,
             'all_three_labels_represented':all(counts[x]>0 for x in LABELS)}
 return {'case_count':len(cases),'classified':len(predictions),'correct':len(predictions)-len(wrong),
         'unsafe_false_positives':unsafe,'incorrect':wrong,'missing_or_failed':missing,'errors':errors,
         'criteria':thresholds,'meets_scenario_gate':all(thresholds.values()),
         'scope':'Scenario classification only; does not establish completeness, discovery, implementation validity or call-site dependencies.'}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=pathlib.Path,required=True);p.add_argument('--results',type=pathlib.Path,required=True);a=p.parse_args()
 case_bytes=a.cases.read_bytes()
 result=report(json.loads(case_bytes),json.loads(a.results.read_text()),hashlib.sha256(case_bytes).hexdigest())
 print(json.dumps(result,indent=2))
 return 0 if result['meets_scenario_gate'] else 1
if __name__=='__main__':sys.exit(main())

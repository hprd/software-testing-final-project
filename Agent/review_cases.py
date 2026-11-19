#!/usr/bin/env python3
"""Review one specified behavior per request; output provisional classifications."""
import argparse, json, pathlib
import orchestrator

PROMPT=('Assess only the stated behavior and scenario against the supplied source passages. '
 'Return {"label":"candidate or invalid or inconclusive","reason":"...","evidence_kind":"explicit or absence_inference",'
 '"source_id":"...","quote":"...","unknowns":["..."]}. '
 'Candidate means plausible for further review, not verified. Invalid means it contradicts a cited guarantee or relies on undefined results. '
 'Inconclusive means the supplied evidence or context is insufficient. Do not infer all behavior from a missing guarantee. '
 'Quote an exact substring of the indicated source including markup for explicit evidence. For absence inference use an empty quote and source_id. '
 'A matching quote is not proof; preserve conditions and do not infer requirements for unrelated arguments.')

def assess(case, resolved, endpoint, model, timeout=600, request_fn=None):
 if resolved['resolution']!='source_signature_match':
  return {'id':case['id'],'status':'documentation_unresolved','reason':'Exact applicable source method not resolved; no model classification made.'}
 docs=resolved['passages']
 payload={'api':case['api'],'dimension':case['dimension'],'scenario':case['scenario'],'alternative':case['alternative'],
          'passages':docs,'limitations':resolved['unresolved']}
 response=orchestrator.ask(endpoint,model,PROMPT,payload,timeout,request_fn); p=response['parsed']
 if p.get('label') not in ('candidate','invalid','inconclusive') or not isinstance(p.get('reason'),str) or not p['reason'].strip() or not orchestrator.string_list(p.get('unknowns')):raise ValueError('invalid review schema')
 if p.get('evidence_kind') not in ('explicit','absence_inference'):raise ValueError('invalid evidence kind')
 if p['evidence_kind']=='explicit':
  passage=next((x for x in docs if x['id']==p.get('source_id')),None); quote=p.get('quote')
  if not passage or not isinstance(quote,str) or len(orchestrator.normalized(quote))<8 or orchestrator.normalized(quote) not in orchestrator.normalized(passage['text']):raise ValueError('unverifiable quotation or source')
 elif p.get('source_id')!='' or p.get('quote')!='':raise ValueError('absence inference must not invent quotation or source')
 return {'id':case['id'],'status':'model_classification_requires_human_review','label':p['label'],'response':response,
         'warning':'Source match does not establish semantic entailment or complete applicable contracts.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=pathlib.Path,default=pathlib.Path(__file__).parent/'evaluation/cases.json');p.add_argument('--resolved',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--select',action='append',default=[]);p.add_argument('--endpoint',default='http://127.0.0.1:18080/v1/chat/completions');p.add_argument('--model',default='local-coder');p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
 cases=json.loads(a.cases.read_text())['cases']; docs=[json.loads(x) for x in a.resolved.read_text().splitlines() if x.strip()]; byapi={str(x['owner'])+'.'+str(x['signature']):x for x in docs}
 results=[]
 for case in cases:
  if a.select and case['id'] not in a.select:continue
  if case['api'] not in byapi:result={'id':case['id'],'status':'documentation_unavailable'}
  else:
   try:result=assess(case,byapi[case['api']],a.endpoint,a.model,a.timeout)
   except (ValueError,TypeError,KeyError,IndexError,OSError) as e:result={'id':case['id'],'status':'model_error','error':str(e)}
  results.append(result);orchestrator.atomic_write(a.output,{'results':results,'complete':False});print(case['id'],result['status'],flush=True)
 orchestrator.atomic_write(a.output,{'results':results,'complete':True,'warning':'Only classifications with valid responses are predictions; all require review.'})
if __name__=='__main__':main()

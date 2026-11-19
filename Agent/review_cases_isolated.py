#!/usr/bin/env python3
"""Evidence-first, separately reviewed scenario classification; no perturbation approval."""
import argparse, collections, hashlib, json, pathlib
import orchestrator as o

SELECT = ('Select up to three exact quotations from the supplied source passages that bear on the specified behavior. '
 'Return {"quotes":[{"source_id":"...","quote":"..."}],"unknowns":["..."]}. '
 'Copy verbatim including Javadoc markup. Do not decide whether an alternative is valid. '
 'An empty list is acceptable when no passage is relevant.')
JUDGE = ('Classify the proposed scenario using the selected excerpts as incomplete evidence. '
 'Return {"label":"candidate or invalid or inconclusive","reason":"...","unknowns":["..."]}. '
 'Candidate means a possible alternative requiring review, not proof. Invalid means a stated contract is violated '
 'or the scenario relies on undefined results. If excerpts or conditions are insufficient, use inconclusive. '
 'Do not confuse an unspecified property with permission to violate another guarantee.')
AUDIT = ('Independently classify this scenario against the original passages, without relying on another model verdict. '
 'Return {"label":"candidate or invalid or inconclusive","reason":"...","unknowns":["..."]}. '
 'Candidate is provisional, invalid requires a contradiction or undefined-result scenario, '
 'and inconclusive means insufficient evidence. Check precise conditions and the scope of requirements.')

GUARD = ('Check this one scenario against the excerpts. Is the proposed observation explicitly in conflict '
         'with a required guarantee? Separately, does the scenario meet a documented condition '
         'where results are undefined? Return {"contradiction":"yes or no or unclear",'
         '"undefined":"yes or no or unclear","source_id":"...","quote":"...","reasons":["..."]}. '
         'If either answer is yes, copy an exact quotation from a selected excerpt with its source_id; '
         'an undefined=yes quote must explicitly contain the word undefined. '
         'Pay close attention to negatives such as no mutation, and distinguish an unspecified '
         'property from an explicit guarantee. Do not decide whether to execute code.')

class CheckpointTrace(list):
 """Persist each completed role response without claiming the case completed."""
 def __init__(self,path,case_id,metadata):
  super().__init__();self.path=path;self.case_id=case_id;self.metadata=metadata
 def append(self,item):
  super().append(item)
  o.atomic_write(self.path,{'case_id':self.case_id,'status':'in_progress_or_interrupted',
                            'metadata':self.metadata,'completed_stages':list(self)})

def assess(case, resolved, endpoint, model, timeout=600, request_fn=None, trace=None, guard=False):
 trace=trace if trace is not None else []
 if resolved.get('resolution')!='source_signature_match':
  return {'id':case['id'],'status':'documentation_unresolved'}
 docs=resolved['passages']; byid={}
 for passage in docs:
  payload={k:v for k,v in passage.items() if k!='id'}
  expected=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()[:20]
  if passage.get('id')!=expected or expected in byid:raise ValueError('passage ID mismatch or duplicate')
  byid[expected]=passage
 metadata={'api':case['api'],'dimension':case['dimension'],'scenario':case['scenario']}
 selected=o.ask(endpoint,model,SELECT,{'context':metadata,'passages':docs},timeout,request_fn);trace.append({'stage':'select','response':selected})
 parsed=selected['parsed']; quotes=parsed.get('quotes')
 if not isinstance(quotes,list) or len(quotes)>3 or not o.string_list(parsed.get('unknowns')):raise ValueError('invalid evidence selection')
 for q in quotes:
  if not isinstance(q,dict):raise ValueError('invalid quote object')
  doc=byid.get(q.get('source_id'));quote=q.get('quote')
  if not doc or not isinstance(quote,str) or len(o.normalized(quote))<8 or o.normalized(quote) not in o.normalized(doc['text']):raise ValueError('unverifiable selected quotation')
 if not quotes:
  return {'id':case['id'],'status':'model_classification_requires_human_review','label':'inconclusive',
          'evidence_selected':False,'agreement':None,'stage_labels':[],'constraint_check':None,'stages':trace,
          'warning':'No source evidence selected; no substantive classification is made.'}
 base={'case':dict(metadata,alternative=case['alternative']),'limitations':resolved['unresolved']}
 first=o.ask(endpoint,model,JUDGE,dict(base,selected_excerpts=quotes,evidence_unknowns=parsed['unknowns']),timeout,request_fn);trace.append({'stage':'judge','response':first})
 independent=o.ask(endpoint,model,AUDIT,dict(base,passages=docs),timeout,request_fn);trace.append({'stage':'independent_audit','response':independent})
 for answer in (first,independent):
  v=answer['parsed']
  if v.get('label') not in ('candidate','invalid','inconclusive') or not isinstance(v.get('reason'),str) or not v['reason'].strip() or not o.string_list(v.get('unknowns')):raise ValueError('invalid judgment schema')
 a=first['parsed']['label']; b=independent['parsed']['label']
 label=a if a==b and quotes else 'inconclusive'; guard_result=None; constraint_evidence_error=None
 if guard:
  checked=o.ask(endpoint,model,GUARD,dict(base,selected_excerpts=quotes),timeout,request_fn);trace.append({'stage':'constraint_check','response':checked})
  guard_result=checked['parsed']
  if any(guard_result.get(k) not in ('yes','no','unclear') for k in ('contradiction','undefined')) or not o.string_list(guard_result.get('reasons'),True):raise ValueError('invalid constraint check')
  values=(guard_result['contradiction'],guard_result['undefined'])
  if 'yes' in values:
   quote=guard_result.get('quote');source_id=guard_result.get('source_id')
   supporting=next((q for q in quotes if q['source_id']==source_id),None)
   if (not supporting or not isinstance(quote,str) or len(o.normalized(quote))<8
       or o.normalized(quote) not in o.normalized(supporting['quote'])
       or (guard_result['undefined']=='yes' and 'undefined' not in quote.lower())):
    constraint_evidence_error='A yes constraint answer lacks a verifiable, appropriately scoped selected quotation.'
    label='inconclusive'
  # Only downgrade: a model constraint check cannot validate or upgrade a proposal.
  if 'unclear' in values or ('yes' in values and label!='invalid') or (values==('no','no') and label=='invalid'):
   label='inconclusive'
 return {'id':case['id'],'status':'model_classification_requires_human_review','label':label,
         'evidence_selected':bool(quotes),'agreement':a==b,'stage_labels':[a,b],'constraint_check':guard_result,'constraint_evidence_error':constraint_evidence_error,'stages':trace,
         'warning':'Same-model agreement is not semantic verification; selected evidence may be incomplete.'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--cases',type=pathlib.Path,default=pathlib.Path(__file__).parent/'evaluation/cases.json');p.add_argument('--resolved',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--select',action='append',default=[]);p.add_argument('--endpoint',default='http://127.0.0.1:18080/v1/chat/completions');p.add_argument('--model',default='local-coder');p.add_argument('--timeout',type=int,default=600);p.add_argument('--constraint-check',action='store_true');a=p.parse_args()
 if a.output.exists() or any(a.output.parent.glob(a.output.name+'.*.stages.json')):p.error('output or stage checkpoints exist; use a new path to preserve previous evidence')
 cases=json.loads(a.cases.read_text())['cases'];docs=[json.loads(x) for x in a.resolved.read_text().splitlines() if x.strip()]
 ids=[c['id'] for c in cases]
 if len(ids)!=len(set(ids)) or any(x not in ids for x in a.select):p.error('duplicate case IDs or unknown --select')
 byapi=collections.defaultdict(list)
 for doc in docs:byapi[str(doc['owner'])+'.'+str(doc['signature'])].append(doc)
 metadata={'model':a.model,'endpoint':a.endpoint,'cases_file':str(a.cases),'cases_sha256':hashlib.sha256(a.cases.read_bytes()).hexdigest(),'resolved_file':str(a.resolved),'resolved_sha256':hashlib.sha256(a.resolved.read_bytes()).hexdigest(),'reviewer_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'selected':a.select,'constraint_check':a.constraint_check}
 results=[]
 for case in cases:
  if a.select and case['id'] not in a.select:continue
  trace=CheckpointTrace(a.output.with_name(a.output.name+'.'+hashlib.sha256(case['id'].encode()).hexdigest()[:16]+'.stages.json'),case['id'],metadata)
  if case['api'] not in byapi:result={'id':case['id'],'status':'documentation_unavailable'}
  elif len(byapi[case['api']])!=1:result={'id':case['id'],'status':'documentation_ambiguous'}
  else:
   try:result=assess(case,byapi[case['api']][0],a.endpoint,a.model,a.timeout,trace=trace,guard=a.constraint_check)
   except (ValueError,TypeError,KeyError,IndexError,OSError) as e:result={'id':case['id'],'status':'model_error','error':str(e),'completed_stages':trace}
  results.append(result);o.atomic_write(a.output,{'version':'evidence-first-guarded-v1' if a.constraint_check else 'evidence-first-v1','metadata':metadata,'results':results,'complete':False});print(case['id'],result['status'],result.get('label',''),flush=True)
 o.atomic_write(a.output,{'version':'evidence-first-guarded-v1' if a.constraint_check else 'evidence-first-v1','metadata':metadata,'results':results,'complete':True})
if __name__=='__main__':main()

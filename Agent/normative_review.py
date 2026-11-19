#!/usr/bin/env python3
"""Extract and audit provisional normative statements in separate passes."""
import argparse, hashlib, json, pathlib, re
import orchestrator as base

VERSION = 'normative-two-pass-v1'
EXTRACT = ('PASS 1: Extract normative statements relevant to this API from this single source chunk. '
 'Return {"statements":[{"kind":"obligation|prohibition|permission|no_guarantee|undefined_condition",'
 '"claim":"...","conditions":"...","scope":"...","quote":"verbatim substring"}],'
 '"unknowns":["..."],"more_may_exist":true}. '
 'Use exact quotation including Javadoc markup. Conditions and scope must not overstate the source. Use an empty conditions string if no condition is stated in the selected claim. '
 'Do not infer a missing guarantee merely from silence; do not propose perturbations. Do not present examples or implementation notes as API-wide guarantees; mark implementation-specific requirements with their scope. '
 'Return at most four statements per chunk; set more_may_exist if any may be omitted. '
 'A statement is a model proposal and must be independently audited.')
AUDIT = ('PASS 2: Audit the extracted statements against the original source chunk. '
 'Return {"assessments":[{"statement_id":"...","verdict":"supported|unsupported|unclear",'
 '"kind_verdict":"supported|unsupported|unclear","reason":"..."}],"omissions":[{"claim":"...","quote":"verbatim substring"}],'
 '"unknowns":["..."]}. Cover every supplied statement ID exactly once. '
 'Check the entire claim, its conditions and scope; matching quotation is not proof. Independently evaluate the statement kind: an undefined result condition does not by itself prohibit the triggering action. '
 'Check that examples and implementation notes were not promoted to API-wide guarantees. Identify potentially missed normative statements, quoting exact source including markup. '
 'Mark incomplete sources and uncertain interpretations as unknown. Never claim completeness or approve a perturbation.')
KINDS = {'obligation','prohibition','permission','no_guarantee','undefined_condition'}
VERDICTS = {'supported','unsupported','unclear'}

def valid_quote(quote, text):
 return isinstance(quote,str) and len(base.normalized(quote))>=8 and base.normalized(quote) in base.normalized(text)

def verify_passages(passages):
 seen=set()
 for p in passages:
  expected=hashlib.sha256(json.dumps({k:v for k,v in p.items() if k!='id'},sort_keys=True).encode()).hexdigest()[:20]
  if p.get('id')!=expected or expected in seen:raise ValueError('passage ID mismatch or duplicate')
  seen.add(expected)

def chunks_for(passage, limit=2200):
 text=passage['text']; start=0; chunks=[]
 while start<len(text):
  end=min(len(text),start+limit)
  if end<len(text):
   cut=text.rfind('\n',start+limit//2,end)
   if cut>start:end=cut+1
  chunks.append({'source_id':passage['id'],'source_kind':passage['kind'],'owner':passage['owner'],
                 'offset_start':start,'offset_end':end,'text':text[start:end]})
  start=end
 return chunks

def extract_statements(parsed, chunk):
 rows=parsed.get('statements');unknowns=parsed.get('unknowns')
 if not isinstance(rows,list) or len(rows)>4 or not base.string_list(unknowns) or type(parsed.get('more_may_exist')) is not bool:raise ValueError('invalid extraction schema')
 statements=[]
 for i,row in enumerate(rows):
  if not isinstance(row,dict) or row.get('kind') not in KINDS or not all(isinstance(row.get(k),str) and row[k].strip() for k in ('claim','scope')) or not isinstance(row.get('conditions'),str) or not valid_quote(row.get('quote'),chunk['text']):raise ValueError('invalid statement or source quotation')
  flags=[]
  if not row['conditions'].strip() and re.search(r'\b(?:if|when|unless|provided\s+that)\b',row['claim'],re.I):
   flags.append('Conditional wording appears in the claim, but the conditions field is empty; review scope.')
  # A conservative triage warning, not a semantic proof or a replacement for audit.
  if (row['kind']=='prohibition' and re.search(r'\bundefined\b',row['quote'],re.I)
      and not re.search(r'\b(?:prohibited|forbidden|must\s+not|shall\s+not|not\s+permitted)\b',row['quote'],re.I)):
   flags.append('Undefined-result wording may have been misclassified as a prohibition; review the condition and source.')
  statements.append({'id':chunk['source_id']+':'+str(chunk['offset_start'])+':'+str(i),**row,'review_flags':flags})
 return statements

def audit_statements(parsed, statements, chunk):
 reviews=parsed.get('assessments');omissions=parsed.get('omissions')
 if not isinstance(reviews,list) or not isinstance(omissions,list) or not base.string_list(parsed.get('unknowns')):raise ValueError('invalid audit schema')
 ids={s['id'] for s in statements};seen=set()
 for item in reviews:
  if not isinstance(item,dict) or item.get('statement_id') not in ids or item['statement_id'] in seen or item.get('verdict') not in VERDICTS or item.get('kind_verdict') not in VERDICTS or not isinstance(item.get('reason'),str) or not item['reason'].strip():raise ValueError('invalid or duplicate audit assessment')
  seen.add(item['statement_id'])
 if seen!=ids:raise ValueError('audit did not cover every statement')
 for item in omissions:
  if not isinstance(item,dict) or not isinstance(item.get('claim'),str) or not item['claim'].strip() or not valid_quote(item.get('quote'),chunk['text']):raise ValueError('invalid audit omission quotation')
 return {'assessments':reviews,'omissions':omissions,'unknowns':parsed['unknowns']}

def review(record, endpoint, model, timeout=600, request_fn=None, kinds=None, progress=None):
 passages=record.get('passages') or [];verify_passages(passages)
 selected=[p for p in passages if not kinds or p['kind'] in kinds]
 excluded=[p['id'] for p in passages if p not in selected]
 result={'api_id':record['api_id'],'api':{'owner':record['owner'],'signature':record['signature']},
         'version':VERSION,'model':model,'documentation_resolution':record.get('resolution'),
         'docs_artifact_integrity':record.get('docs_artifact_integrity','unverified'),'jdk_source_sha256':record.get('jdk_source_sha256'),
         'source_limitations':record.get('unresolved',[]),'excluded_passage_ids':excluded,
         'chunks':[], 'status':'in_progress',
         'coverage':{'available_passages':len(passages),'selected_passages':len(selected),'excluded_passages':len(excluded),'exhaustiveness':'not established'},
         'warning':'All extracted statements and audit verdicts are model outputs requiring human review; coverage and entailment are not proven.'}
 def save():
  if progress:progress(result)
 if record.get('resolution')!='source_signature_match' or not selected:
  result['status']='documentation_unresolved';save();return result
 chunks=[chunk for p in selected for chunk in chunks_for(p)]
 result['coverage']['chunks']=len(chunks)
 for chunk in chunks:
  entry={'source_id':chunk['source_id'],'source_kind':chunk['source_kind'],'owner':chunk['owner'],
         'offset_start':chunk['offset_start'],'offset_end':chunk['offset_end'],'extraction_status':'pending','audit_status':'pending'}
  result['chunks'].append(entry)
  try:
   response=base.ask(endpoint,model,EXTRACT,{'api':result['api'],'source':chunk,'limitations':result['source_limitations']},timeout,request_fn)
   entry['extraction_response']=response
   entry['statements']=extract_statements(response['parsed'],chunk)
   entry['review_flags']=['Statement cap reached; additional statements may be omitted.'] if len(entry['statements'])==4 else []
   entry['extraction_status']='complete'
  except (ValueError,TypeError,KeyError,IndexError,OSError) as e:
   entry['extraction_status']='error';entry['extraction_error']=str(e)
  save()
 # The second pass begins only after all extraction requests have completed.
 for entry,chunk in zip(result['chunks'],chunks):
  if entry['extraction_status']!='complete':entry['audit_status']='not_run_extraction_error';save();continue
  try:
   response=base.ask(endpoint,model,AUDIT,{'api':result['api'],'source':chunk,'statements':entry['statements'],
                                          'limitations':result['source_limitations']},timeout,request_fn)
   entry['audit_response']=response
   entry['audit']=audit_statements(response['parsed'],entry['statements'],chunk)
   entry['audit_status']='complete'
  except (ValueError,TypeError,KeyError,IndexError,OSError) as e:
   entry['audit_status']='error';entry['audit_error']=str(e)
  save()
 if not all(e['extraction_status']=='complete' and e['audit_status']=='complete' for e in result['chunks']):
  result['status']='incomplete_requires_human_review'
 elif any(e['review_flags'] or e['extraction_response']['parsed']['more_may_exist'] or e['audit']['omissions'] or
          any(statement['review_flags'] for statement in e['statements']) or
          any(a['verdict']!='supported' or a['kind_verdict']!='supported' for a in e['audit']['assessments'])
          for e in result['chunks']):
  result['status']='needs_manual_resolution'
 else:result['status']='requires_human_review'
 save();return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--resolved',type=pathlib.Path,required=True);p.add_argument('--select',required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--source-kind',action='append',choices=['matched_method','declaring_class','related_class']);p.add_argument('--endpoint',default='http://127.0.0.1:18080/v1/chat/completions');p.add_argument('--model',default='local-coder');p.add_argument('--timeout',type=int,default=600);a=p.parse_args()
 if a.output.exists():p.error('output exists; select a new path')
 records=[json.loads(x) for x in a.resolved.read_text().splitlines() if x.strip()]
 matches=[r for r in records if a.select in str(r.get('owner'))+'.'+str(r.get('signature'))]
 if len(matches)!=1:p.error('select must match exactly one API group')
 metadata={'resolved_file':str(a.resolved),'resolved_sha256':hashlib.sha256(a.resolved.read_bytes()).hexdigest(),
           'reviewer_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
           'endpoint':a.endpoint,'select':a.select,'source_kinds':a.source_kind}
 def save(result):
  result['run_metadata']=metadata;base.atomic_write(a.output,result)
 try:
  result=review(matches[0],a.endpoint,a.model,a.timeout,kinds=a.source_kind,progress=save)
 except (ValueError,TypeError,KeyError,IndexError,OSError) as e:
  result={'status':'error','error':str(e)};save(result)
 print(result['status'])
 return 0 if result['status']=='requires_human_review' else 1
if __name__=='__main__':raise SystemExit(main())

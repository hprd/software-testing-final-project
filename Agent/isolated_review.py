#!/usr/bin/env python3
"""Experimental isolated contract roles; findings always require human review."""
import argparse, json, pathlib
import orchestrator as base

EXTRACT = ('Extract at most five explicit contract facts directly relevant to the selected method from this one source passage. Omit general performance guidance. If more may be relevant, state that in unknowns. '
           'Return {"facts":[{"claim":"...","quote":"verbatim substring"}],"unknowns":["..."]}. '
           'Copy each quote exactly including Javadoc markup, links and braces; never paraphrase it. Preserve conditions and argument scope. Do not propose variations.')
ENTAIL = ('Independently compare the claim to the supplied original passage. Does the passage support the whole claim, '
          'including its conditions and scope? Return {"verdict":"supported or unsupported or unclear","reason":"..."}. '
          'A matching quotation alone does not prove the claim. Do not use outside assumptions.')
VARIATIONS = ('Propose up to three different observable outcomes for the same valid input, or none if uncertain. '
              'Return {"proposals":[{"behavior":"...","alternative":"...","conditions":"...",'
              '"must_preserve":["..."],"evidence_kind":"explicit or absence_inference",'
              '"evidence_quote":"...","reasoning":"..."}],"unknowns":["..."]}. '
              'Preserve every applicable constraint. Do not treat undefined behavior as a variation. '
              'For explicit evidence quote the supplied documentation; for absence_inference use an empty quote.')
AUDIT = ('Review this one proposed alternative independently against the original passages. '
         'Return {"verdict":"reject or needs_review","reasons":["..."],"missing_contracts":["..."]}. '
         'Reject explicit contradictions and undefined-result scenarios. '
         'An unspecified property is not forbidden. Never claim compliance proven.')

def review(record, endpoint, model, timeout=1800, request_fn=None, trace=None):
    context=record.get('contract_context') or {}; cls=context.get('class') or {}
    docs=[]
    if cls.get('doc'): docs.append({'source':'class', 'declaration':cls.get('declaration'), 'doc':cls['doc']})
    for i, method in enumerate(context.get('matching_method_name_overloads') or []):
        if method.get('doc'): docs.append({'source':'same_name_method_'+str(i), 'declaration':method.get('declaration'), 'doc':method['doc']})
    if not docs: raise ValueError('no source documentation')
    if sum(len(d['doc']) for d in docs)>25000: raise ValueError('documentation exceeds limit')
    api={'owner':record['owner'],'signature':record['signature']}
    extracted=[]; decisions=[]; usable=[]; stage_responses=trace if trace is not None else []
    for doc in docs:
        answer=base.ask(endpoint,model,EXTRACT,{'api':api,'source':doc},timeout,request_fn)
        stage_responses.append({'stage':'extract','source':doc['source'],'response':answer})
        data=answer['parsed']
        if not isinstance(data.get('facts'),list) or len(data['facts'])>5 or not base.string_list(data.get('unknowns')): raise ValueError('invalid extraction')
        for fact in data['facts']:
            if not isinstance(fact,dict) or not isinstance(fact.get('claim'),str) or not fact['claim'].strip() or not isinstance(fact.get('quote'),str) or len(base.normalized(fact['quote']))<8 or base.normalized(fact['quote']) not in base.normalized(doc['doc']): raise ValueError('invalid extraction quote')
            entry={'source':doc['source'],**fact}; extracted.append(entry)
            audit=base.ask(endpoint,model,ENTAIL,{'api':api,'source':doc,'claim':fact['claim'],'quote':fact['quote']},timeout,request_fn)
            stage_responses.append({'stage':'entailment','source':doc['source'],'response':audit})
            decision=audit['parsed']
            if decision.get('verdict') not in ('supported','unsupported','unclear') or not isinstance(decision.get('reason'),str) or not decision['reason'].strip(): raise ValueError('invalid entailment response')
            decisions.append({'fact':entry,'assessment':decision})
            if decision['verdict']=='supported': usable.append(entry)
    proposal_response=base.ask(endpoint,model,VARIATIONS,{'api':api,'source_passages':docs,'model_supported_facts':usable,'limitations':['same-name overloads not resolved','linked and inherited contracts not expanded']},timeout,request_fn)
    stage_responses.append({'stage':'variation','response':proposal_response})
    proposed=proposal_response['parsed']; proposals=proposed.get('proposals')
    if not isinstance(proposals,list) or len(proposals)>3 or not base.string_list(proposed.get('unknowns')): raise ValueError('invalid proposals')
    reviews=[]
    evidence=base.normalized('\n'.join(d['doc'] for d in docs))
    for i,p in enumerate(proposals):
        if not isinstance(p,dict) or not all(isinstance(p.get(k),str) and p[k].strip() for k in ('behavior','alternative','conditions','reasoning')) or not base.string_list(p.get('must_preserve'),True) or p.get('evidence_kind') not in ('explicit','absence_inference'): raise ValueError('invalid proposal')
        quote=p.get('evidence_quote')
        if not isinstance(quote,str) or (p['evidence_kind']=='explicit' and (len(base.normalized(quote))<8 or base.normalized(quote) not in evidence)) or (p['evidence_kind']=='absence_inference' and quote): raise ValueError('invalid proposal evidence')
        audit=base.ask(endpoint,model,AUDIT,{'api':api,'source_passages':docs,'proposal':p},timeout,request_fn)
        stage_responses.append({'stage':'proposal_audit','proposal_index':i,'response':audit})
        result=audit['parsed']
        if result.get('verdict') not in ('reject','needs_review') or not base.string_list(result.get('reasons'),True) or not base.string_list(result.get('missing_contracts')): raise ValueError('invalid proposal audit')
        reviews.append({'proposal_index':i,**result})
    return {'api_id':record['id'],'version':'isolated-v1','status':'requires_human_review','extracted':extracted,
            'fact_assessments':decisions,'proposals':proposals,'reviews':reviews,'stages':stage_responses,
            'warning':'Model assessments are not verified facts. Documents, overloads and call context may be incomplete; no perturbation is approved.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--queue',type=pathlib.Path,required=True);p.add_argument('--select',required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--endpoint',default='http://127.0.0.1:18080/v1/chat/completions');p.add_argument('--model',default='local-coder');p.add_argument('--timeout',type=int,default=1800);a=p.parse_args()
    records=[json.loads(line) for line in a.queue.open() if line.strip()]
    matches=[r for r in records if r.get('status')=='pending_review' and a.select in str(r.get('owner'))+'.'+str(r.get('signature'))]
    if len(matches)!=1: p.error('selection must match exactly one documented group')
    trace=[]
    try: result=review(matches[0],a.endpoint,a.model,a.timeout,trace=trace)
    except (ValueError,TypeError,KeyError,IndexError,OSError) as e: result={'api_id':matches[0].get('id'),'status':'error','error':str(e),'completed_stages':trace}
    base.atomic_write(a.output,result);print(result['status'])
    if result['status']=='error': raise SystemExit(1)
if __name__=='__main__': main()

#!/usr/bin/env python3
"""Coordinate baseline, compiler inventory, model list review and contract stages."""
import argparse, collections, hashlib, json, pathlib, subprocess, sys
import orchestrator
import experiment
import normative_review

HERE = pathlib.Path(__file__).resolve().parent
LIST_ROLE = ('ROLE: inventory reviewer. List every supplied API group ID exactly once. '
             'Use only IDs in the input; do not infer missing calls or omit unresolved groups. '
             'Return exactly {"api_ids":["..."],"notes":["..."]}. '
             'The list is a compiler inventory, not proof of runtime dispatch or complete project coverage.')

def read_jsonl(path):
    with path.open() as f:
        return [json.loads(line) for line in f if line.strip()]

def review_list(groups, endpoint, model, timeout, request_fn=None):
    supplied = [g['id'] for g in groups]
    payload = [{'id': g['id'], 'owner': g.get('owner'), 'signature': g.get('signature'),
                'kind': g.get('kind'), 'call_count': g.get('call_count'),
                'sample_sites': g.get('sample_sites', [])} for g in groups]
    response = orchestrator.ask(endpoint, model, LIST_ROLE, {'api_groups': payload}, timeout, request_fn)
    ids = response['parsed'].get('api_ids')
    if not isinstance(ids, list) or not all(isinstance(x, str) for x in ids):
        raise ValueError('model list must contain string api_ids')
    counts = collections.Counter(ids)
    return {'response': response, 'missing_ids': [x for x in supplied if x not in counts],
            'unknown_ids': sorted(set(ids) - set(supplied)),
            'duplicate_ids': sorted(x for x, n in counts.items() if n > 1)}

def run_pipeline(queue, output, endpoint, model, timeout, batch_size, limit, select, request_fn=None, normative_stages=None):
    groups = read_jsonl(queue)
    ids = [g.get('id') for g in groups]
    if any(not isinstance(x, str) or not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError('queue IDs must be unique, nonempty strings')
    output.mkdir(parents=True, exist_ok=True)
    listing = output / 'list-review'; listing.mkdir(exist_ok=True)
    for offset in range(0, len(groups), batch_size):
        batch = groups[offset:offset + batch_size]
        digest = hashlib.sha256(json.dumps([model, batch], sort_keys=True).encode()).hexdigest()[:20]
        path = listing / (digest + '.json')
        if path.exists():
            try:
                old = json.loads(path.read_text())
                if old.get('status') == 'complete': continue
            except (ValueError, OSError): pass
        try:
            result = review_list(batch, endpoint, model, timeout, request_fn)
            result.update({'status': 'complete', 'supplied_ids': [g['id'] for g in batch]})
        except (ValueError, TypeError, KeyError, IndexError, OSError) as e:
            result = {'status': 'error', 'error': str(e), 'supplied_ids': [g['id'] for g in batch]}
        orchestrator.atomic_write(path, result)
        print('list batch', offset // batch_size + 1, result['status'], flush=True)
    reviews = output / 'reviews'; reviews.mkdir(exist_ok=True)
    statuses = collections.Counter(); processed = 0
    manifest = []
    for g in groups:
        name = str(g.get('owner')) + '.' + str(g.get('signature'))
        entry = {'id': g['id'], 'owner': g.get('owner'), 'signature': g.get('signature'),
                 'kind': g.get('kind'), 'call_count': g.get('call_count'), 'sample_sites': g.get('sample_sites'),
                 'documentation_status': g.get('status')}
        if g.get('status') != 'pending_review':
            entry['status'] = 'documentation_unavailable'
        elif select and not any(s in name for s in select):
            entry['status'] = 'not_selected'
        elif normative_stages is not None and normative_stages.get(g['id'],{}).get('status') != 'requires_human_review':
            entry['status'] = 'normative_review_unavailable'
            entry['normative_review'] = normative_stages.get(g['id'], {'status':'not_processed'})
        else:
            if normative_stages is not None:
                entry['normative_review'] = normative_stages[g['id']]
            key = hashlib.sha256((orchestrator.VERSION + '\0' + model + '\0' + json.dumps(g, sort_keys=True)).encode()).hexdigest()[:24]
            path = reviews / (key + '.json'); existing = None
            if path.exists():
                try: existing = json.loads(path.read_text())
                except (ValueError, OSError): pass
            if (existing and existing.get('status') == 'requires_human_review'
                    and existing.get('api_id') == g['id'] and existing.get('version') == orchestrator.VERSION
                    and existing.get('model') == model):
                entry.update(status='requires_human_review', review=str(path))
            elif limit is not None and processed >= limit:
                entry['status'] = 'not_processed_limit'
            else:
                processed += 1; trace = {}
                try: result = orchestrator.review(g, endpoint, model, timeout, request_fn=request_fn, trace=trace)
                except (ValueError, TypeError, KeyError, IndexError, OSError) as e:
                    result = {'api_id': g['id'], 'version': orchestrator.VERSION, 'model': model,
                              'status': 'error', 'error': str(e), 'retryable': True, 'completed_stages': trace}
                orchestrator.atomic_write(path, result)
                entry.update(status=result['status'], review=str(path))
                print('contract', name, entry['status'], flush=True)
        statuses[entry['status']] += 1; manifest.append(entry)
        # Preserve partial progress if interrupted between model requests.
        if entry.get('review'):
            orchestrator.atomic_write(output / 'manifest.json', {'groups': manifest, 'complete': False})
    summary = {'complete': True, 'queue': str(queue), 'group_count': len(groups),
               'call_count': sum(g.get('call_count', 0) for g in groups), 'statuses': dict(statuses),
               'groups': manifest, 'warning': 'Model list review cannot add or remove compiler inventory entries. '
               'Contract outputs are proposals requiring human review, not validated findings.'}
    orchestrator.atomic_write(output / 'manifest.json', summary)
    return summary

def valid_cached_normative(result, record, model, kinds, metadata):
    """Verify cached source coverage and structural checks before reusing a completed review."""
    try:
        if (result.get('status')!='requires_human_review' or result.get('api_id')!=record['api_id']
            or result.get('model')!=model or result.get('version')!=normative_review.VERSION
            or result.get('run_metadata')!=metadata or record.get('resolution')!='source_signature_match'):
            return False
        passages=record.get('passages') or [];normative_review.verify_passages(passages)
        selected=[p for p in passages if not kinds or p['kind'] in kinds]
        chunks=[c for p in selected for c in normative_review.chunks_for(p)]
        entries=result.get('chunks')
        if not chunks or not isinstance(entries,list) or len(entries)!=len(chunks):return False
        for entry,chunk in zip(entries,chunks):
            if any(entry.get(k)!=chunk[k] for k in ('source_id','source_kind','owner','offset_start','offset_end')):return False
            if entry.get('extraction_status')!='complete' or entry.get('audit_status')!='complete':return False
            statements=normative_review.extract_statements(entry['extraction_response']['parsed'],chunk)
            if statements!=entry.get('statements'):return False
            audit=normative_review.audit_statements(entry['audit_response']['parsed'],statements,chunk)
            if audit!=entry.get('audit'):return False
            if len(statements)==4 or entry['extraction_response']['parsed']['more_may_exist'] or audit['omissions'] or any(statement['review_flags'] for statement in statements) or any(
                    item['verdict']!='supported' or item['kind_verdict']!='supported' for item in audit['assessments']):return False
        return True
    except (ValueError, TypeError, KeyError, IndexError):return False

def run_normative_stages(queue, resolved_path, output, endpoint, model, timeout, select, limit, kinds=None, request_fn=None, review_fn=None):
    """Run both normative passes before the staged variation reviewer."""
    groups=read_jsonl(queue); records=read_jsonl(resolved_path); byid={}
    for record in records:
        ident=record.get('api_id')
        if not ident or ident in byid:raise ValueError('resolved API IDs must be unique and nonempty')
        byid[ident]=record
    resolved_hash=hashlib.sha256(resolved_path.read_bytes()).hexdigest()
    reviewer_hash=hashlib.sha256(pathlib.Path(normative_review.__file__).read_bytes()).hexdigest()
    root=output/'normative';root.mkdir(parents=True,exist_ok=True)
    statuses={}; processed=0
    for g in groups:
        name=str(g.get('owner'))+'.'+str(g.get('signature'))
        if g.get('status')!='pending_review' or (select and not any(x in name for x in select)):continue
        ident=g['id'];rec=byid.get(ident)
        if not rec:
            statuses[ident]={'status':'documentation_unavailable'};continue
        if (rec.get('owner'),rec.get('signature'),rec.get('kind'))!=(g.get('owner'),g.get('signature'),g.get('kind')):
            statuses[ident]={'status':'documentation_mismatch'};continue
        if processed>=limit:
            statuses[ident]={'status':'not_processed_limit'};continue
        processed+=1
        key=hashlib.sha256(json.dumps([normative_review.VERSION,reviewer_hash,endpoint,model,resolved_hash,kinds,rec],sort_keys=True).encode()).hexdigest()[:24]
        dest=root/(key+'.json');stage={'path':str(dest),'api_id':ident}
        metadata={'resolved_file':str(resolved_path),'resolved_sha256':resolved_hash,'reviewer_sha256':reviewer_hash,'endpoint':endpoint,'source_kinds':kinds}
        if dest.exists():
            try:existing=json.loads(dest.read_text())
            except (ValueError,OSError):existing={}
            if valid_cached_normative(existing,rec,model,kinds,metadata):
                stage['status']='requires_human_review'
            else:stage.update(status='not_run_output_exists',reason='Incomplete or unrecognized prior output is preserved.')
        else:
            try:
                def save(result):
                    result['run_metadata']=metadata;orchestrator.atomic_write(dest,result)
                result=(review_fn or normative_review.review)(rec,endpoint,model,timeout,request_fn=request_fn,kinds=kinds,progress=save)
                save(result);stage['status']=result['status']
            except (ValueError,TypeError,KeyError,IndexError,OSError) as e:
                stage.update(status='error',reason=str(e))
        statuses[ident]=stage
        orchestrator.atomic_write(output/'normative-manifest.json',{'complete':False,'groups':statuses})
        print('normative',name,stage['status'],flush=True)
    orchestrator.atomic_write(output/'normative-manifest.json',{'complete':True,'groups':statuses,'warning':'Completed passes and audit verdicts remain unverified model outputs.'})
    return statuses

def run_registered_experiment(summary, output, project, java_home, maven, maven_repo, timeout, execute_fn=None):
    """Run the reviewed fixture only after its matching documented group was reviewed."""
    matches = [g for g in summary['groups'] if g.get('owner') == 'java.util.Hashtable'
               and g.get('signature') == 'keys()' and g.get('kind') == 'method_invocation']
    stage = {'adapter': experiment.CASE,
             'note': 'Registered manual fixture; no model proposal or verdict establishes its validity.'}
    if len(matches) != 1 or matches[0].get('status') != 'requires_human_review':
        stage.update(status='not_run_contract_review_unavailable',
                     reason='A completed staged review of the matching API call group is required.')
    else:
        stage['api_id'] = matches[0]['id']
        stage['model_review'] = matches[0].get('review')
        dest = output / 'experiments' / experiment.CASE
        stage['output'] = str(dest)
        if dest.exists() and (not dest.is_dir() or any(dest.iterdir())):
            stage.update(status='not_run_output_exists', reason='Existing experiment evidence was preserved; use a new pipeline output directory.')
        else:
            try:
                result = (execute_fn or experiment.execute)(project, java_home, maven, maven_repo, dest, timeout)
                stage.update(status=result['status'], result=str(dest / 'result.json'),
                             finding_scope=result.get('finding_scope'))
            except (ValueError, OSError, subprocess.TimeoutExpired) as e:
                stage.update(status='experiment_error', reason=str(e))
    summary['experiment'] = stage
    orchestrator.atomic_write(output / 'manifest.json', summary)
    return stage

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=pathlib.Path, help='Project to baseline and inventory')
    p.add_argument('--java-home', type=pathlib.Path)
    p.add_argument('--maven-repo', type=pathlib.Path)
    p.add_argument('--queue', type=pathlib.Path, help='Reuse an existing prepared queue')
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--endpoint', default='http://127.0.0.1:18080/v1/chat/completions')
    p.add_argument('--model', default='local-coder'); p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--batch-size', type=int, default=15); p.add_argument('--limit', type=int)
    p.add_argument('--select', action='append', default=[])
    p.add_argument('--normative-resolved', type=pathlib.Path, help='Run extraction and audit before staged variation analysis')
    p.add_argument('--normative-limit', type=int, default=1)
    p.add_argument('--normative-source-kind', action='append', choices=['matched_method','declaring_class','related_class'])
    p.add_argument('--experiment', choices=[experiment.CASE], help='Run a registered fixture after its API review')
    p.add_argument('--experiment-project', type=pathlib.Path, help='Subject checkout for the registered fixture when using --queue')
    p.add_argument('--maven', type=pathlib.Path, help='Maven executable for the registered fixture')
    p.add_argument('--experiment-timeout', type=int, default=900)
    p.add_argument('--baseline', nargs=argparse.REMAINDER, help='Baseline command; must be last')
    a = p.parse_args()
    if a.batch_size < 1 or (a.limit is not None and a.limit < 1) or a.experiment_timeout < 1 or a.normative_limit < 1: p.error('batch-size, limits and experiment-timeout must be positive')
    if a.normative_source_kind and not a.normative_resolved: p.error('--normative-source-kind requires --normative-resolved')
    if a.experiment and not (a.experiment_project or a.project): p.error('--experiment requires --experiment-project (or --project for a fresh run)')
    if a.experiment and not (a.java_home and a.maven and a.maven_repo): p.error('--experiment requires --java-home, --maven and --maven-repo')
    if not a.experiment and (a.experiment_project or a.maven): p.error('--experiment-project and --maven require --experiment')
    if a.queue:
        if a.project or a.baseline: p.error('--queue cannot be combined with --project or --baseline')
        queue = a.queue
    else:
        if not (a.project and a.java_home and a.maven_repo and a.baseline):
            p.error('fresh inventory needs --project, --java-home, --maven-repo and --baseline')
        inventory = a.output / 'inventory'; docs = a.output / 'contracts'
        subprocess.run([sys.executable, str(HERE/'run.py'), str(a.project), '--java-home', str(a.java_home),
                        '--maven-repo', str(a.maven_repo), '--output', str(inventory), '--baseline', *a.baseline], check=True)
        subprocess.run([sys.executable, str(HERE/'contracts_deep_dive.py'), '--inventory', str(inventory/'calls.jsonl'),
                        '--java-home', str(a.java_home), '--output', str(docs)], check=True)
        queue = docs/'api-queue.jsonl'
    normative_stages = None
    if a.normative_resolved:
        normative_stages = run_normative_stages(queue, a.normative_resolved, a.output, a.endpoint, a.model, a.timeout, a.select, a.normative_limit, kinds=a.normative_source_kind)
    summary = run_pipeline(queue, a.output, a.endpoint, a.model, a.timeout, a.batch_size, a.limit, a.select, normative_stages=normative_stages)
    if normative_stages is not None:
        summary['normative_manifest'] = str(a.output/'normative-manifest.json')
        orchestrator.atomic_write(a.output/'manifest.json', summary)
    if a.experiment:
        stage = run_registered_experiment(summary, a.output, a.experiment_project or a.project, a.java_home, a.maven, a.maven_repo, a.experiment_timeout)
        print('experiment', stage['status'], flush=True)
    print(json.dumps({'groups': summary['group_count'], 'calls': summary['call_count'], 'statuses': summary['statuses'], 'experiment': summary.get('experiment')}, indent=2))
    if a.normative_resolved and (not normative_stages or any(x['status']!='requires_human_review' for x in normative_stages.values())):
        return 1
    if a.experiment and stage['status'] not in ('confirmed_scoped_order_dependency', 'no_failure_observed'):
        return 1
    return 0
if __name__ == '__main__': sys.exit(main())

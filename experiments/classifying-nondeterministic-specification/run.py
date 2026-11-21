#!/usr/bin/env python3
"""Reproduce the existing Agent inventory/documentation/review pilot for one test."""
import argparse
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
REVISION = 'd58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8'
SOURCE = 'src/test/java/org/apache/commons/lang3/stream/StreamsTest.java'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=['prepare', 'review'])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--project', type=Path)
    parser.add_argument('--java-home', type=Path)
    parser.add_argument('--maven-repo', type=Path)
    parser.add_argument('--maven', type=Path)
    parser.add_argument('--endpoint', default='http://127.0.0.1:8080/v1/chat/completions')
    parser.add_argument('--model', default='local-coder')
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    out = args.output.resolve()
    sys.path.insert(0, str(ROOT / 'Agent'))
    import pipeline

    if args.stage == 'prepare':
        if any(x is None for x in [args.project, args.java_home, args.maven_repo, args.maven]):
            parser.error('prepare requires project, java-home, maven-repo, and maven')
        out.mkdir(parents=True, exist_ok=False)
        project = args.project.resolve()
        revision = subprocess.check_output(['git', '-C', str(project), 'rev-parse', 'HEAD'], text=True).strip()
        status = subprocess.check_output(['git', '-C', str(project), 'status', '--porcelain', '--untracked-files=no'], text=True)
        if revision != REVISION or status:
            raise RuntimeError('Expected pinned subject with clean tracked files')
        env = os.environ.copy()
        for key in ['JDK_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'MAVEN_OPTS', 'MAVEN_ARGS']:
            env.pop(key, None)
        commands = []

        def run(label, command):
            with (out / (label + '.log')).open('w') as log:
                result = subprocess.run([str(x) for x in command], cwd=str(ROOT), env=env,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout)
            commands.append({'label': label, 'command': list(map(str, command)), 'exit_code': result.returncode})
            write(out / 'commands.json', commands)
            if result.returncode:
                raise RuntimeError(label + ' failed; inspect log')

        start = time.time()
        run('inventory', [sys.executable, ROOT / 'Agent/run.py', project,
                         '--java-home', args.java_home, '--maven-repo', args.maven_repo,
                         '--output', out / 'inventory', '--baseline', args.maven, '-o', '-B',
                         '-Dmaven.repo.local=' + str(args.maven_repo.resolve()),
                         '-Dtest=StreamsTest#testOfEnumeration', '-Drat.skip=true',
                         '-Dsurefire.rerunFailingTestsCount=0', 'test'])
        inventory_summary = json.loads((out / 'inventory/summary.json').read_text())
        if inventory_summary['baseline_exit_code'] != 0 or inventory_summary['failed_files']:
            raise RuntimeError('Baseline or inventory failed')
        report = project / 'target/surefire-reports/TEST-org.apache.commons.lang3.stream.StreamsTest.xml'
        suite = ET.parse(report).getroot()
        if (report.stat().st_mtime < start or suite.get('tests') != '1'
                or any(suite.get(k) != '0' for k in ['failures', 'errors', 'skipped'])
                or [x.get('name') for x in suite.findall('testcase')] != ['testOfEnumeration']):
            raise RuntimeError('Missing fresh passing target report')
        shutil.copy2(report, out / 'baseline-test.xml')
        source = project / SOURCE
        text = source.read_text()
        signature = '    void testOfEnumeration() {'
        if text.count(signature) != 1:
            raise RuntimeError('Ambiguous target method')
        begin = text.index(signature)
        end = text.index('\n    }', begin) + len('\n    }')
        first, last = text.count('\n', 0, begin) + 1, text.count('\n', 0, end) + 1
        (out / 'target-method.java.txt').write_text(text[begin:end] + '\n')
        calls = [json.loads(line) for line in (out / 'inventory/calls.jsonl').open()]
        selected = [c for c in calls if c['file'] == SOURCE and first <= c['line'] <= last]
        if not selected or not any(c['owner'] == 'java.util.Hashtable' and c['signature'] == 'keys()' for c in selected):
            raise RuntimeError('Expected target calls missing from compiler inventory')
        (out / 'test-calls.jsonl').write_text(''.join(json.dumps(c) + '\n' for c in selected))
        run('documentation', [sys.executable, ROOT / 'Agent/contracts_deep_dive.py',
                              '--inventory', out / 'test-calls.jsonl', '--java-home', args.java_home,
                              '--output', out / 'documentation'])
        provenance = {'subject_revision': revision, 'subject': str(project), 'source': SOURCE,
                      'source_sha256': digest(source), 'method': 'testOfEnumeration',
                      'method_lines': [first, last], 'scoped_call_count': len(selected),
                      'scope_selection': 'Pinned source method bounds; no filtering by expected API classification.',
                      'review_selection': 'Known Hashtable.keys() pilot; other extracted API groups are not contract-reviewed.',
                      'manual_rule_findings_used_as_model_input': False,
                      'prepared_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      'infrastructure_sha256': {name: digest(ROOT / 'Agent' / name) for name in
                          ['run.py', 'src/Inventory.java', 'contracts_deep_dive.py', 'src/Docs.java', 'pipeline.py', 'orchestrator.py']}}
        write(out / 'provenance.json', provenance)
        print(json.dumps(provenance), flush=True)
    else:
        provenance = json.loads((out / 'provenance.json').read_text())
        receipts = out / 'requests'
        receipts.mkdir(exist_ok=False)
        count = 0
        with urllib.request.urlopen(args.endpoint.rsplit('/chat/completions', 1)[0] + '/models', timeout=30) as response:
            write(out / 'server-models.json', json.load(response))

        def request_fn(request, timeout):
            nonlocal count
            count += 1
            path = receipts / ('%02d.json' % count)
            receipt = {'endpoint': request.full_url, 'request': json.loads(request.data),
                       'status': 'in_progress', 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
            write(path, receipt)
            try:
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    body = response.read()
                receipt.update(status='complete', response=json.loads(body))
                write(path, receipt)
                return io.BytesIO(body)
            except Exception as error:
                receipt.update(status='error', error=str(error))
                write(path, receipt)
                raise

        result = pipeline.run_pipeline(out / 'documentation/api-queue.jsonl', out / 'pipeline',
                                       args.endpoint, args.model, args.timeout, 50, 1,
                                       ['java.util.Hashtable.keys()'], request_fn=request_fn)
        write(out / 'review-run.json', {'provenance': provenance, 'endpoint': args.endpoint,
                                      'model': args.model, 'request_count': count,
                                      'statuses': result['statuses'],
                                      'warning': 'Model judgments are provisional; human review is separate.'})
        print(json.dumps(result['statuses']), flush=True)


if __name__ == '__main__':
    main()

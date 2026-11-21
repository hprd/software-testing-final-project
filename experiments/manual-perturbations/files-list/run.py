#!/usr/bin/env python3
"""Reproduce a manually scoped Files.list ordering witness; no LLM or NonDex integration."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import shlex
import signal
import subprocess
import tarfile
import time
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REVISION = '0c640aef74c65292ef313596f58c48b1b121e1e7'
TEST = 'org.apache.commons.io.function.IOBinaryOperatorStreamTest'
SOURCE = 'src/test/java/org/apache/commons/io/function/IOBinaryOperatorStreamTest.java'
SOURCE_HASH = '480c2a06bcc42c2b35b70680b90e9087888e344b2cd0ad2c4fe220091e476196'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_hashes(subject):
    return {str(p.relative_to(subject)): digest(p) for p in sorted(subject.rglob('*'))
            if p.is_file() and p.relative_to(subject).parts[0] != 'target'}


def execute(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    home, asm = args.java_home.resolve(), args.asm.resolve()
    env = os.environ.copy()
    for key in ('JDK_JAVA_OPTIONS', 'JAVA_TOOL_OPTIONS', '_JAVA_OPTIONS', 'MAVEN_OPTS', 'MAVEN_ARGS'):
        env.pop(key, None)
    env['JAVA_HOME'] = str(home)
    env['PATH'] = str(home/'bin') + os.pathsep + env.get('PATH', '')
    result = {'experiment': 'files-list-first-pair-swap', 'status': 'in_progress',
              'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'model_pipeline_used': False, 'nondex_modified': False, 'commands': {},
              'limitations': ['Manually scoped research fixture, not a general Files.list implementation.',
                              'Stable finite default-filesystem directory; sequential selected test only.',
                              'Reads up to two entries on first traversal; no eager traversal at API return.',
                              'Concurrency, provider-specific guarantees and arbitrary I/O timing are not validated.',
                              'The Agent/ LLM proposal pipeline and stock NonDex are not executed in this experiment.']}

    def save():
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')

    def run(label, command, cwd=None, extra_env=None):
        command = [str(x) for x in command]
        start = time.monotonic()
        log = out/(label+'.log')
        process_env = env.copy()
        process_env.update(extra_env or {})
        with log.open('w') as output:
            process = subprocess.Popen(command, cwd=str(cwd or out), env=process_env,
                                       stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            timed_out = False
            try:
                process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        text = log.read_text()
        result['commands'][label] = {'command': command, 'cwd': str(cwd or out),
            'exit_code': process.returncode, 'timed_out': timed_out, 'environment_overrides': extra_env or {},
            'seconds': round(time.monotonic()-start, 3), 'log': log.name, 'sha256': digest(log)}
        save()
        return process.returncode, text

    def require_run(label, command, cwd=None):
        code, text = run(label, command, cwd)
        if code:
            raise RuntimeError(label+' failed; inspect '+str(out/(label+'.log')))
        return text

    save()
    try:
        result['java_version'] = require_run('java-version', [home/'bin/java', '-version'])
        result['jdk_modules_sha256'] = digest(home/'lib/modules')
        result['asm_sha256'] = digest(asm)
        result['runner_sha256'] = digest(Path(__file__).resolve())
        fixture = out/'fixture'
        shutil.copytree(str(HERE/'src'), str(fixture/'src'))
        sources = sorted((fixture/'src').rglob('*.java'))
        result['fixture_sources_sha256'] = {str(p.relative_to(fixture)): digest(p) for p in sources}
        patch, tools = fixture/'patch', fixture/'tools'
        patch.mkdir(); tools.mkdir()
        require_run('compile-transform', [home/'bin/javac', '-cp', asm, '-d', tools, fixture/'src/Transform.java'])
        require_run('transform', [home/'bin/java', '-cp', str(tools)+os.pathsep+str(asm), 'Transform', patch])
        require_run('compile-helper', [home/'bin/javac', '--patch-module', 'java.base='+str(fixture/'src'),
                    '-d', patch, fixture/'src/java/nio/file/FilesListWitness.java'])
        require_run('compile-controls', [home/'bin/javac', '--patch-module', 'java.base='+str(patch),
                    '-d', tools, fixture/'src/Check.java'])
        controls = require_run('controls', [home/'bin/java', '--patch-module', 'java.base='+str(patch),
                    '-Dfileslist.fixture.controls=true', '-cp', tools, 'Check'])
        if 'PASS Files.list controls:' not in controls:
            raise RuntimeError('fixture controls did not report success')
        result['patch_sha256'] = {str(p.relative_to(patch)): digest(p) for p in sorted(patch.rglob('*.class'))}
        if args.controls_only:
            result['status'] = 'fixture_controls_passed'
            return result

        project = args.project.resolve()
        revision = require_run('revision', ['git', '-C', project, 'rev-parse', 'HEAD']).strip()
        dirty = require_run('subject-status', ['git', '-C', project, 'status', '--porcelain', '--untracked-files=no']).strip()
        if revision != REVISION or dirty:
            raise ValueError('subject must have pinned HEAD and clean tracked files')
        result['subject_revision'] = revision
        result['original_test_sha256'] = digest(project/SOURCE)
        if result['original_test_sha256'] != SOURCE_HASH:
            raise ValueError('subject test differs from reviewed test')
        result['maven_version'] = require_run('maven-version', [args.maven.resolve(), '-version'])
        archive = out/'subject.tar'
        require_run('archive', ['git', '-C', project, 'archive', '--format=tar', '-o', archive, REVISION])
        subject = out/'subject'; subject.mkdir()
        with tarfile.open(str(archive)) as tar:
            for member in tar.getmembers():
                target = (subject/member.name).resolve()
                if subject not in target.parents or member.issym() or member.islnk():
                    raise ValueError('unsupported archive entry '+member.name)
            tar.extractall(str(subject))
        original_hashes = source_hashes(subject)
        if digest(subject/SOURCE) != SOURCE_HASH:
            raise ValueError('archived test mismatch')
        result['archived_inputs_sha256'] = original_hashes
        command = [args.maven.resolve(), '-o', '-B', '-ntp', '-Drat.skip=true',
                   '-Dmaven.repo.local='+str(args.maven_repo.resolve()),
                   '-Dtest=IOBinaryOperatorStreamTest#testReduce', '-Dsurefire.rerunFailingTestsCount=0', 'test']
        report = subject/'target/surefire-reports'/('TEST-'+TEST+'.xml')

        def test_run(label, extra_env=None):
            # Remove only the previous generated target report, never a source file.
            if report.exists():
                report.unlink()
            code, log = run(label, command, subject, extra_env)
            if not report.is_file():
                return {'exit_code': code, 'assessment': 'missing_report'}
            snapshot = out/(label+'-test.xml')
            shutil.copyfile(str(report), str(snapshot))
            xml = ET.parse(str(snapshot)); suite = xml.getroot(); cases = suite.findall('testcase')
            assessment = 'unrelated_report'
            info = {'exit_code': code, 'report': snapshot.name, 'report_sha256': digest(snapshot)}
            if (suite.get('name') == TEST and suite.get('tests') == '1' and suite.get('errors') == '0'
                    and suite.get('flakes', '0') == '0'
                    and suite.get('skipped') == '0' and len(cases) == 1
                    and cases[0].get('name') == 'testReduce' and cases[0].get('classname') == TEST):
                case = cases[0]
                failures = case.findall('failure')
                if not failures and not case.findall('error') and not case.findall('skipped') and suite.get('failures') == '0' and code == 0:
                    assessment = 'pass'
                elif len(failures) == 1 and suite.get('failures') == '1' and code != 0:
                    failure = failures[0]
                    text = ''.join(failure.itertext())
                    message = failure.get('message', '')
                    match = re.fullmatch(r'expected: <(.+)> but was: <(.+)>', message)
                    if (failure.get('type') == 'org.opentest4j.AssertionFailedError'
                            and 'IOBinaryOperatorStreamTest.java:102' in text and match
                            and match.group(1) != match.group(2)):
                        assessment = 'expected_order_assertion_failure'
                        info.update(expected=match.group(1), actual=match.group(2), assertion_line=102)
            info['assessment'] = assessment
            info['fixture_calls'] = re.findall(r'FILES_LIST_FIXTURE call=(\d+) action=([^\s]+)', log)
            info['first_entries'] = re.findall(r'FILES_LIST_FIRST call=(\d+) path=([^\r\n]+)', log)
            return info

        result['baseline'] = test_run('baseline'); save()
        if result['baseline']['assessment'] != 'pass':
            result['status'] = 'inconclusive_baseline'
            return result
        # Freeze the directory entries and require distinct real paths before perturbation.
        root_entries = {p.name: str(p.resolve()) for p in subject.iterdir()}
        if len(set(root_entries.values())) < 2:
            raise ValueError('target directory needs two distinct real paths')
        result['directory_entries_before'] = root_entries
        # Commons IO's late @{argLine} expansion can be overwritten by JaCoCo.
        # JDK_JAVA_OPTIONS reaches the forked test JVM without modifying its POM.
        options = shlex.quote('--patch-module=java.base='+str(patch))+' '+shlex.quote('-Dfileslist.fixture.directory='+str(subject))
        result['perturbed'] = test_run('perturbed', {'JDK_JAVA_OPTIONS': options}); save()
        result['baseline_recheck'] = test_run('baseline-recheck'); save()
        result['directory_entries_after'] = {p.name: str(p.resolve()) for p in subject.iterdir()}
        result['archived_inputs_unchanged'] = source_hashes(subject) == original_hashes
        result['original_test_unchanged'] = digest(project/SOURCE) == SOURCE_HASH
        result['directory_entries_unchanged'] = result['directory_entries_after'] == root_entries
        perturbed = result['perturbed']
        calls_ok = perturbed['fixture_calls'] == [('1', 'identity'), ('2', 'swap-first-pair')]
        first = dict(perturbed['first_entries'])
        first_ok = (set(first) == {'1', '2'} and
                    str((subject/first['1']).resolve()) == perturbed.get('expected') and
                    str((subject/first['2']).resolve()) == perturbed.get('actual'))
        if (perturbed['assessment'] == 'expected_order_assertion_failure' and calls_ok and first_ok
                and not any(entry['timed_out'] for entry in result['commands'].values())
                and result['baseline_recheck']['assessment'] == 'pass'
                and result['archived_inputs_unchanged'] and result['original_test_unchanged']
                and result['directory_entries_unchanged']):
            result['status'] = 'confirmed_scoped_cross_listing_order_dependency'
        else:
            result['status'] = 'inconclusive_experiment'
        return result
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, ET.ParseError) as error:
        result.update(status='inconclusive_setup_or_execution', error=str(error))
        return result
    finally:
        result['finished_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        save()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--asm', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New output directory; must not exist')
    parser.add_argument('--controls-only', action='store_true')
    parser.add_argument('--project', type=Path)
    parser.add_argument('--maven', type=Path)
    parser.add_argument('--maven-repo', type=Path)
    parser.add_argument('--timeout', type=int, default=900)
    args = parser.parse_args()
    if args.timeout < 1:
        parser.error('--timeout must be positive')
    if not args.controls_only and not all((args.project, args.maven, args.maven_repo)):
        parser.error('full run requires --project, --maven and --maven-repo')
    result = execute(args)
    print(json.dumps({'status': result['status'], 'result': str(args.output.resolve()/'result.json')}))
    return 0 if result['status'] in ('fixture_controls_passed', 'confirmed_scoped_cross_listing_order_dependency') else 1


if __name__ == '__main__':
    raise SystemExit(main())

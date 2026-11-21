#!/usr/bin/env python3
"""Build the active instrumenter from source and compare plain/patched JVMs.

Dependencies must already be present in --deps; no network or Maven lifecycle.
Outputs are written to --output, outside the source checkouts.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import zipfile

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--nondex', type=Path, required=True)
p.add_argument('--java-home', type=Path, required=True)
p.add_argument('--deps', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root, home, deps, out = [x.resolve() for x in (a.nondex, a.java_home, a.deps, a.output)]
out.mkdir(parents=True, exist_ok=False)
classes = out / 'classes'
classes.mkdir()
def run(label, command):
    result = subprocess.run([str(x) for x in command], cwd=str(out), universal_newlines=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180)
    (out / (label + '.log')).write_text(result.stdout)
    if result.returncode:
        raise RuntimeError(f'{label}: exit {result.returncode}; see {out / (label + ".log")}')
    return result.stdout
jars = sorted(deps.glob('*.jar'))
cp = ':'.join(map(str, jars))
sources = []
for module in ('nondex-common', 'nondex-instrumentation'):
    sources.extend(sorted((root / module / 'src/main/java').rglob('*.java')))
run('compile', [home/'bin/javac', '-source', '8', '-target', '8', '-cp', cp, '-d', classes, *sources])
(classes / 'project.properties').write_text('version=2.2.5-SNAPSHOT\n')
version = run('java-version', [home/'bin/java', '-version'])
patch = out / 'instrumented.jar'
run('instrument', [home/'bin/java', '-cp', str(classes)+':'+cp,
                   'edu.illinois.nondex.instr.Main', patch])
disassembly = out/'bytecode'
disassembly.mkdir()
hooks = {}
with zipfile.ZipFile(str(patch)) as archive:
    for entry in archive.namelist():
        if entry.endswith('.class'):
            target = disassembly/Path(entry).name
            target.write_bytes(archive.read(entry))
            bytecode = run('bytecode/'+target.stem, [home/'bin/javap', '-p', '-c', target])
            header = ''
            methods = set()
            for line in bytecode.splitlines():
                if line.startswith('  ') and not line.startswith('    ') and '(' in line:
                    header = line.strip()
                if 'ControlNondeterminism.' in line:
                    methods.add(header)
            hooks[entry] = sorted(methods)
    instrumenter = (root/'nondex-instrumentation/src/main/java/edu/illinois/nondex/instr/Instrumenter.java').read_text()
    constants = dict(re.findall(r'String (\w+) = "([^"]+)";', instrumenter))
    registered = set(re.findall(r'standardClassesToInstrument.add\("([^"]+)"\)', instrumenter))
    registered.update(constants[k] for k in re.findall(r'specialClassesToInstrument.add\(Instrumenter\.(\w+)\)', instrumenter))
    assert registered == {e[:-4] for e in archive.namelist() if e.endswith('.md5')}, 'registry mismatch'
selectors = sorted(set(re.findall(r'apisReturningShufflableArrays.add\("([^"]+)"\)',
    (root/'nondex-instrumentation/src/main/java/edu/illinois/nondex/instr/ClassVisitorShufflingAdder.java').read_text())))
for selector in selectors:
    cl, method = selector.rsplit('.', 1)
    assert any(' '+method+'(' in h for h in hooks[cl+'.class']), 'missing injected hook: '+selector
source = Path(__file__).with_name('ApiAudit.java').resolve()
run('compile-probes', [home/'bin/javac', '-source', '8', '-target', '8', '-cp', classes,
                       '-d', out, source])
is8 = 'version "1.8.' in version
patched = ['-Xbootclasspath/p:'+str(patch)+':'+str(classes)] if is8 else [
    '--add-exports', 'java.base/edu.illinois.nondex.common=ALL-UNNAMED',
    '--add-exports', 'java.base/edu.illinois.nondex.shuffling=ALL-UNNAMED',
    '--patch-module', 'java.base='+str(patch)+':'+str(classes)+':'+str(deps/'jaxb-api-2.3.1.jar')]
def parse(output):
    rows = {}
    for line in output.splitlines():
        if line.startswith('PROBE\t'):
            _, name, choices, distinct, violations, sample = line.split('\t')
            rows[name] = {'choices': int(choices), 'distinct_outputs': int(distinct),
                          'membership_violations': int(violations), 'first_violation': sample}
    if not rows:
        raise RuntimeError('no probe results')
    return rows
results = {}
for mode, opts in [('plain', []), ('patched', patched)]:
    for seed in (933178, 974622, 1016066):
        key = f'{mode}-{seed}'
        output = run(key, [home/'bin/java', *opts, '-DnondexMode=FULL',
                          f'-DnondexSeed={seed}', f'-DnondexExecid={key}',
                          '-cp', str(out)+':'+str(classes)+':'+cp, 'ApiAudit'])
        results[key] = parse(output)
all_names = set(next(iter(results.values())))
assert all(set(rows) == all_names for rows in results.values())
assert all(row['choices'] == 0 for key, rows in results.items() if key.startswith('plain')
           for row in rows.values()), 'plain JVM reached NonDex'
assert all(row['membership_violations'] == 0 for key, rows in results.items() if key.startswith('plain')
           for row in rows.values()), 'invalid plain baseline'
summary = {'revision': run('revision', ['git', '-C', root, 'rev-parse', 'HEAD']).strip(),
           'java': version.strip(), 'probe_count': len(all_names), 'repeats': 24,
           'dependencies_sha256': {j.name: hashlib.sha256(j.read_bytes()).hexdigest() for j in jars},
           'probe_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
           'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'registered_classes': sorted(registered), 'standard_selectors': selectors,
           'direct_hook_methods': hooks,
           'compiled_sources_sha256': {str(s.relative_to(root)): hashlib.sha256(s.read_bytes()).hexdigest()
                                       for s in sources}, 'runs': results}
test_sources = sorted((root/'nondex-test/src/test/java').rglob('*.java'))
run('compile-upstream-tests', [home/'bin/javac', '-source', '8', '-target', '8', '-cp',
                              str(classes)+':'+cp, '-d', out, *test_sources])
test_names = ['edu.illinois.nondex.core.'+f.stem for f in test_sources
              if f.name.endswith('Test.java') and not f.name.startswith('Abstract')]
summary['upstream_tests'] = run('upstream-tests', [home/'bin/java', *patched,
    '-DnondexMode=FULL', '-DnondexExecid=upstream-tests', '-cp',
    str(out)+':'+str(classes)+':'+cp, 'org.junit.runner.JUnitCore', *test_names]).strip()
(out/'results.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps({'java': version.strip(), 'probe_count':len(all_names),
                  'patched_choices':sum(r['choices'] for r in results['patched-933178'].values()),
                  'results':str(out/'results.json')}))

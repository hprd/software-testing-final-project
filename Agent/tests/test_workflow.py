import json, pathlib, subprocess, tempfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
JAVA='/misc/scratch/aab5473/testing-tools/temurin-jdk21'
REPO='/misc/scratch/aab5473/testing-tools/maven-repository'
with tempfile.TemporaryDirectory() as td:
 p=pathlib.Path(td); src=p/'project/src/test/java'; src.mkdir(parents=True); (src/'Fixture.java').write_text((ROOT/'tests/Fixture.java').read_text()); out=p/'out'
 cmd=['python3.11',str(ROOT/'run.py'),str(p/'project'),'--java-home',JAVA,'--maven-repo',REPO,'--output',str(out),'--baseline','/bin/true']
 subprocess.run(cmd,check=True,stdout=subprocess.DEVNULL)
 calls=[json.loads(x) for x in (out/'calls.jsonl').read_text().splitlines()]
 missing=[x for x in calls if x['expression']=='MissingType.missing()']; assert len(missing)==1 and not missing[0]['resolved']
 findings=json.loads((out/'findings.json').read_text()); assert len(findings)==3
 assert [x['classification'] for x in findings]==['candidate dependency','inconclusive','inconclusive']
 assert 'compiler_errors=1' in (out/'diagnostics.log').read_text()
 print('PASS: direct order candidate, sorted and membership controls, unresolved call, compiler diagnostics')

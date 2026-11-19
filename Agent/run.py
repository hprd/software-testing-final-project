#!/usr/bin/env python3
"""Baseline and inventory Java source calls; no LLM or general dataflow yet."""
import argparse, collections, datetime, json, os, pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent

def run(command, cwd, env=None):
    return subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('project', type=pathlib.Path)
    p.add_argument('--java-home', type=pathlib.Path, required=True)
    p.add_argument('--maven-repo', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--baseline', nargs=argparse.REMAINDER, required=True, help='Explicit baseline command and arguments; must be last')
    a=p.parse_args(); project=a.project.resolve(); out=a.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    if not a.baseline: p.error('a baseline command is required')
    env=os.environ.copy(); env['JAVA_HOME']=str(a.java_home.resolve()); env['PATH']=str(a.java_home.resolve()/'bin')+os.pathsep+env.get('PATH','')
    # Prevent an inherited experiment from silently contaminating the baseline.
    for key in ('JDK_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS'): env.pop(key,None)
    version=run([str(a.java_home/'bin/java'),'-version'],project,env).stdout.strip()
    revision=run(['git','rev-parse','HEAD'],project,env)
    status=run(['git','status','--porcelain'],project,env)
    baseline=run(a.baseline,project,env); (out/'baseline.log').write_text(baseline.stdout)
    roots=[project/'src/main/java',project/'src/test/java']; roots=[x for x in roots if x.is_dir()]
    files=sorted(str(f) for root in roots for f in root.rglob('*.java'))
    classes=HERE/'build'; classes.mkdir(exist_ok=True)
    compiled=run([str(a.java_home/'bin/javac'),'-d',str(classes),str(HERE/'src/Inventory.java')],project,env)
    if compiled.returncode: sys.exit(compiled.stdout)
    jars=sorted(str(f) for f in a.maven_repo.resolve().rglob('*.jar'))
    cp=os.pathsep.join([str(project/'target/classes'),str(project/'target/test-classes')]+jars)
    sourcepath=os.pathsep.join(map(str,roots)); inventory=out/'calls.jsonl'; diagnostics=out/'diagnostics.log'
    processed=0; failed=[]; counts=collections.Counter(); candidates=[]
    contract=json.loads((HERE/'contracts/hashtable-keys.json').read_text())
    with inventory.open('w') as dest, diagnostics.open('w') as diag:
        for offset in range(0,len(files),80):
            batch=files[offset:offset+80]; batchfile=out/'batch.txt'; batchfile.write_text('\n'.join(batch)+'\n')
            cmd=[str(a.java_home/'bin/java'),'-Xmx2g','-cp',str(classes),'Inventory',str(batchfile),cp,sourcepath]
            result=subprocess.run(cmd,cwd=project,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            diag.write(f'Batch {offset//80+1}, exit={result.returncode}\n{result.stderr}\n')
            if result.returncode: failed.extend(batch); continue
            processed+=len(batch)
            for line in result.stdout.splitlines():
                try: call=json.loads(line)
                except json.JSONDecodeError: diag.write('Invalid scanner output: '+line+'\n'); continue
                call['file']=os.path.relpath(call['file'],project)
                counts['calls']+=1; counts['resolved' if call['resolved'] else 'unresolved']+=1
                if call['owner']=='java.util.Hashtable' and call['signature']=='keys()':
                    statement=call['statement'] or ''
                    # Only direct syntax is assessed; no dataflow conclusion for other uses.
                    if 'assertEquals' in statement and ('Arrays.asList' in statement or 'List.of' in statement) and '.sorted(' not in statement: classification='candidate dependency'; reason='Direct fixed-list equality contains this API call; verify encounter-order propagation and that no helper imposes an order.'
                    elif 'contains' in statement or 'count()' in statement: classification='inconclusive'; reason='Local syntax suggests membership or count, but cross-statement uses are not traced.'
                    else: classification='inconclusive'; reason='No supported direct-use rule; dataflow is not traced.'
                    candidates.append({'call':call,'classification':classification,'reason':reason,'contract':contract})
                dest.write(json.dumps(call,ensure_ascii=False)+'\n')
            print(f'Inventory {min(offset+80,len(files))}/{len(files)} files',file=sys.stderr,flush=True)
    (out/'batch.txt').unlink(missing_ok=True)
    summary={'project':str(project),'git_revision':revision.stdout.strip() if revision.returncode==0 else None,'git_status':status.stdout.strip(),'java_version':version,'baseline_command':a.baseline,'baseline_exit_code':baseline.returncode,'baseline_log':'baseline.log','source_roots':[str(x.relative_to(project)) for x in roots],'source_files_discovered':len(files),'source_files_processed':processed,'failed_files':failed,'counts':dict(counts),'contracts_assessed':['java.util.Hashtable.keys()'],'analysis_limitations':['Only src/main/java and src/test/java are scanned; other source sets, dependencies, generated sources, bytecode and runtime-only calls are excluded.','All method invocations, constructors and method references in parsed files are inventoried, including project calls; resolution is best effort, not proof of a correct runtime target.','Compiler attribution uses all JARs found in the given cache, not the project’s exact build classpath; version conflicts and missing dependencies can produce incorrect or unresolved types.','Only a narrow direct-assertion rule for Hashtable.keys() is implemented; all other API contracts and cross-statement/interprocedural dataflow are unassessed.','No LLM, documentation retrieval, automated perturbation, or comprehensive behavioral-dependency analysis is implemented.'], 'generated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); (out/'findings.json').write_text(json.dumps(candidates,indent=2)+'\n')
    print(json.dumps({'baseline_exit_code':baseline.returncode,'files':len(files),'processed':processed,'counts':dict(counts),'hashtable_calls':len(candidates),'failed_files':len(failed)},indent=2))
    return 1 if failed else 0
if __name__=='__main__': sys.exit(main())

#!/usr/bin/env python3
"""Run a bounded, reviewed perturbation experiment against Commons Lang."""
import argparse, datetime, hashlib, io, json, os, pathlib, re, shutil, signal, subprocess, sys, tarfile, time, xml.etree.ElementTree as ET

ROOT=pathlib.Path(__file__).resolve().parent.parent
FIXTURE=ROOT/'experiments/manual-perturbations/hashtable'
REVISION='d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8'
CASE='hashtable-keys-two-key-reversal'
TEST='StreamsTest#testOfEnumeration'
SOURCE='src/test/java/org/apache/commons/lang3/stream/StreamsTest.java'
REVIEWED_FIXTURE={
 'src/Check.java':'3a390cd61ed425b75af838da737d93f4bba26c547ebefbd85d530238d211f022',
 'src/Transform.java':'4da50a585c261d49b3bf35266327f38898009ba5a60f302259a2ffcccc59481e',
 'src/java/util/HashtableWitness.java':'46fea23c72143559deb713d262509599291d8e77f00634b2466f1dcae4e0e589'}
REVIEWED_BUILD='701df2c3619057bb1153898cf1594311d5ac03bf9eab836c93bf37f6d79dff03'
REVIEWED_CONTRACT='ebae4bb2afc6e6abc3fb75b15f4216817610ceae2358e172d1df9c9ac0df6374'
REVIEWED_JDK_MODULES='ce298990407d3a6e79ba7f9e158b5ce77614dc53dce6b1ca6a156be187969e92'
REVIEWED_ASM='03d99a74ad1ee5c71334ef67437f4ef4fe3488caa7c96d8645abc73c8e2017d4'

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def run(command, cwd, env, log, timeout):
 start=time.monotonic()
 try:
  process=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           text=True,errors='replace',start_new_session=True)
  try:
   output,_=process.communicate(timeout=timeout);code=process.returncode;timed_out=False
  except subprocess.TimeoutExpired:
   try:os.killpg(process.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:output,_=process.communicate(timeout=5)
   except subprocess.TimeoutExpired:
    try:os.killpg(process.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    output,_=process.communicate()
   output+='\n[experiment timed out; process group terminated]\n';code=None;timed_out=True
 except OSError as e:
  output='Failed to start command: '+str(e)+'\n';code=None;timed_out=False
 log.write_text(output)
 return {'command':command,'cwd':str(cwd),'exit_code':code,'timed_out':timed_out,'seconds':round(time.monotonic()-start,3),'log':str(log),'output_sha256':digest(log)}

def classify(baseline, controls, perturbed, revision_ok, source_unchanged, post_baseline=None):
 """Identify the narrowly reviewed assertion; never certify arbitrary failures."""
 if not revision_ok or not source_unchanged:return 'inconclusive_subject_changed'
 if baseline['exit_code']!=0 or not baseline.get('target_passed'):return 'inconclusive_baseline'
 if controls['exit_code']!=0 or not controls.get('fixture_controls_passed'):return 'inconclusive_fixture_controls'
 if perturbed is None:return 'inconclusive_not_run'
 if not post_baseline or post_baseline.get('exit_code')!=0 or not post_baseline.get('target_passed'):
  return 'inconclusive_baseline_recheck'
 if perturbed['exit_code']==0 and perturbed.get('target_passed'):return 'no_failure_observed'
 if perturbed.get('expected_order_failure') and perturbed['exit_code'] not in (0,None):return 'confirmed_scoped_order_dependency'
 return 'inconclusive_perturbed_failure'

def baseline_passed(text):
 return bool(re.search(r'Tests run:\s*1,\s*Failures:\s*0,\s*Errors:\s*0,\s*Skipped:\s*0',text) and 'StreamsTest' in text)

def expected_failure(text):
 return bool('testOfEnumeration' in text and re.search(r'StreamsTest\.java:246\b',text) and
             'expected: <[OneOne, TwoTwo]> but was: <[TwoTwo, OneOne]>' in text and
             re.search(r'Tests run:\s*1,\s*Failures:\s*1,\s*Errors:\s*0,\s*Skipped:\s*0',text))

def read_surefire(report):
 """Read only the expected single target case; malformed or unrelated reports are inconclusive."""
 try:
  root=ET.parse(report).getroot(); cases=root.findall('testcase')
  if root.tag!='testsuite' or root.get('name')!='org.apache.commons.lang3.stream.StreamsTest' or len(cases)!=1:return None
  case=cases[0]
  if case.get('name')!='testOfEnumeration' or case.get('classname')!='org.apache.commons.lang3.stream.StreamsTest':return None
  if root.get('tests')!='1' or root.get('errors')!='0' or root.get('skipped')!='0' or root.get('flakes','0')!='0':return None
  failures=case.findall('failure'); errors=case.findall('error'); skipped=case.findall('skipped')
  if errors or skipped:return None
  if not failures and root.get('failures')=='0':return 'pass'
  if len(failures)==1 and root.get('failures')=='1':
   failure=failures[0]
   if (failure.get('type')=='org.opentest4j.AssertionFailedError' and
       failure.get('message')=='expected: <[OneOne, TwoTwo]> but was: <[TwoTwo, OneOne]>' and
       'StreamsTest.java:246' in ''.join(failure.itertext())):return 'expected_order_failure'
  return None
 except (OSError, ET.ParseError, ValueError):return None

def capture_report(subject, dest):
 report=subject/'target/surefire-reports/TEST-org.apache.commons.lang3.stream.StreamsTest.xml'
 try:
  stamp=report.stat().st_mtime_ns; shutil.copyfile(report,dest)
  return {'source':str(report),'snapshot':str(dest),'sha256':digest(dest),'mtime_ns':stamp,'assessment':read_surefire(dest)}
 except OSError:
  return {'source':str(report),'snapshot':None,'sha256':None,'mtime_ns':None,'assessment':None}

def report_is_fresh(baseline, perturbed):
 return (perturbed.get('mtime_ns') is not None and baseline.get('mtime_ns') is not None
         and perturbed['mtime_ns'] > baseline['mtime_ns'])

def execute(project, java_home, maven, maven_repo, output, timeout):
 project=project.resolve();java_home=java_home.resolve();maven=maven.resolve();maven_repo=maven_repo.resolve();output=output.resolve()
 if output.exists() and any(output.iterdir()):raise ValueError('output directory must be empty; existing results are preserved')
 output.mkdir(parents=True,exist_ok=True)
 if not (project/SOURCE).is_file():raise ValueError('expected Commons Lang test source not found')
 env=os.environ.copy();env['JAVA_HOME']=str(java_home);env['PATH']=str(java_home/'bin')+os.pathsep+env.get('PATH','')
 for key in ('JDK_JAVA_OPTIONS','JAVA_TOOL_OPTIONS','_JAVA_OPTIONS','MAVEN_OPTS','MAVEN_ARGS','ASM'):env.pop(key,None)
 asm=maven_repo/'org/ow2/asm/asm/9.9/asm-9.9.jar'
 if not asm.is_file():raise ValueError('ASM 9.9 not found in supplied Maven repository')
 env['ASM']=str(asm)
 def query(cmd):
  result=subprocess.run(cmd,cwd=project,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30)
  return result.returncode,result.stdout.strip()
 revision_code,revision=query(['git','rev-parse','HEAD']);status_code,status=query(['git','status','--porcelain','--untracked-files=no'])
 java_code,java_version=query([str(java_home/'bin/java'),'-version'])
 source_before=digest(project/SOURCE); contract=ROOT/'Agent/contracts/hashtable-keys.json'
 result={'experiment':CASE,'project':str(project),'revision':revision if not revision_code else None,'tracked_status_before':status,
         'java_version':java_version,'java_version_exit_code':java_code,'java_binary_sha256':digest(java_home/'bin/java'),
         'asm_jar':str(asm),'asm_sha256':digest(asm),'jdk_modules_sha256':digest(java_home/'lib/modules'),
         'fixture_build_sha256':digest(FIXTURE/'run-build.sh'),
         'test_source_sha256_before':source_before,'contract_reference':str(contract),'contract_sha256':digest(contract),
         'fixture_sources':{str(p.relative_to(FIXTURE)):digest(p) for p in sorted((FIXTURE/'src').rglob('*.java'))},
         'model_proposal_status':'not used; manually scoped research fixture','contract_status':'manually reviewed for stable unmodified table, not generally validated',
         'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'limitations':['This adapter is limited to a plain Hashtable with keys One and Two in the named test.',
                        'Fixture controls do not establish general contract compliance, concurrency, subclass or other API behavior.',
                        'A failing command alone does not establish a behavioral dependency; the unperturbed recheck does not establish absence of all flakiness.',
                        'Tests execute against a clean git archive of the recorded revision; untracked files and git metadata are excluded.']}
 result_path=output/'result.json'
 def save():result_path.write_text(json.dumps(result,indent=2)+'\n')
 save()
 revision_ok=revision_code==0 and revision==REVISION and status_code==0 and not status and java_code==0 and 'Temurin-21.0.13.1+2' in java_version
 fixture_ok=(result['fixture_sources']==REVIEWED_FIXTURE and result['fixture_build_sha256']==REVIEWED_BUILD and result['contract_sha256']==REVIEWED_CONTRACT and result['jdk_modules_sha256']==REVIEWED_JDK_MODULES and result['asm_sha256']==REVIEWED_ASM)
 if not fixture_ok:
  result.update(status='inconclusive_unreviewed_fixture',reason='Fixture, reviewed contract, JDK modules or ASM differ from the recorded experiment.');save();return result
 if not revision_ok:
  result.update(status='inconclusive_subject_changed',reason='Expected pinned revision, unmodified tracked files, and Temurin 21.0.13.1+2.');save();return result
 archive=subprocess.run(['git','archive','--format=tar',REVISION],cwd=project,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout)
 if archive.returncode:
  result.update(status='inconclusive_archive',reason=archive.stderr.decode(errors='replace'));save();return result
 subject=output/'subject';subject.mkdir()
 with tarfile.open(fileobj=io.BytesIO(archive.stdout),mode='r:') as tar:tar.extractall(subject,filter='data')
 result['execution_project']=str(subject);result['test_source_sha256_in_archive']=digest(subject/SOURCE)
 if result['test_source_sha256_in_archive']!=source_before:
  result.update(status='inconclusive_subject_changed',reason='Archived test source differs from original.');save();return result
 fixture=output/'fixture';shutil.copytree(FIXTURE/'src',fixture/'src');shutil.copy2(FIXTURE/'run-build.sh',fixture/'run-build.sh')
 cmd=[str(maven),'-o','-B',f'-Dmaven.repo.local={maven_repo}',f'-Dtest={TEST}','test']
 baseline=run(cmd,subject,env,output/'baseline.log',timeout); baseline['report']=capture_report(subject,output/'baseline-test.xml');baseline['target_passed']=baseline_passed((output/'baseline.log').read_text()) and baseline['report']['assessment']=='pass';result['baseline']=baseline;save()
 if baseline['exit_code']!=0 or not baseline['target_passed']:
  result['status']='inconclusive_baseline';save();return result
 controls=run(['bash',str(fixture/'run-build.sh')],fixture,env,output/'controls.log',timeout)
 controls['fixture_controls_passed']='PASS empty, singleton, two keys, membership, exhaustion; order=[Two, One]' in (output/'controls.log').read_text();result['controls']=controls;save()
 if controls['exit_code']!=0 or not controls['fixture_controls_passed']:
  result['status']='inconclusive_fixture_controls';save();return result
 patch=fixture/'build/patch';result['patch_sha256']={str(p.relative_to(patch)):digest(p) for p in sorted(patch.rglob('*.class'))}
 patched_env=env.copy();patched_env['JDK_JAVA_OPTIONS']='--patch-module=java.base='+str(patch)
 perturbed=run(cmd,subject,patched_env,output/'perturbed.log',timeout)
 perturbed_text=(output/'perturbed.log').read_text();perturbed['report']=capture_report(subject,output/'perturbed-test.xml')
 fresh=report_is_fresh(baseline['report'],perturbed['report'])
 perturbed['report_fresh']=fresh
 perturbed['target_passed']=fresh and baseline_passed(perturbed_text) and perturbed['report']['assessment']=='pass'
 perturbed['expected_order_failure']=fresh and expected_failure(perturbed_text) and perturbed['report']['assessment']=='expected_order_failure'
 perturbed['java_options']=patched_env['JDK_JAVA_OPTIONS'];result['perturbed']=perturbed;save()
 post=run(cmd,subject,env,output/'baseline-recheck.log',timeout)
 post['report']=capture_report(subject,output/'baseline-recheck-test.xml')
 post['report_fresh']=report_is_fresh(perturbed['report'],post['report'])
 post['target_passed']=post['report_fresh'] and baseline_passed((output/'baseline-recheck.log').read_text()) and post['report']['assessment']=='pass'
 result['baseline_recheck']=post;save()
 status_after_code,status_after=query(['git','status','--porcelain','--untracked-files=no']);result['tracked_status_after']=status_after
 result['test_source_sha256_after']=digest(project/SOURCE)
 source_unchanged=result['test_source_sha256_after']==source_before and digest(subject/SOURCE)==source_before and status_after_code==0 and not status_after
 result['status']=classify(baseline,controls,perturbed,revision_ok,source_unchanged,post)
 result['finding_scope']='Scoped experimental dependency at StreamsTest.java:246' if result['status']=='confirmed_scoped_order_dependency' else 'No dependency confirmed by this run.'
 result['finished_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();save();return result

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--proposal',required=True,choices=[CASE]);p.add_argument('--project',type=pathlib.Path,required=True);p.add_argument('--java-home',type=pathlib.Path,required=True);p.add_argument('--maven',type=pathlib.Path,required=True);p.add_argument('--maven-repo',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--timeout',type=int,default=900);a=p.parse_args()
 if a.timeout<1:p.error('--timeout must be positive')
 try:result=execute(a.project,a.java_home,a.maven,a.maven_repo,a.output,a.timeout)
 except (ValueError,OSError,subprocess.TimeoutExpired) as e: print('experiment error:',e,file=sys.stderr);return 2
 print(json.dumps({'status':result['status'],'result':str(a.output/'result.json')},indent=2))
 return 0 if result['status'] in ('confirmed_scoped_order_dependency','no_failure_observed') else 1
if __name__=='__main__':sys.exit(main())

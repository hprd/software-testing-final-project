import pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import experiment as e
clean='Running org.apache.commons.lang3.stream.StreamsTest\nTests run: 1, Failures: 0, Errors: 0, Skipped: 0'
fail='StreamsTest.testOfEnumeration:246 expected: <[OneOne, TwoTwo]> but was: <[TwoTwo, OneOne]>\n at org.apache.commons.lang3.stream.StreamsTest.testOfEnumeration(StreamsTest.java:246)\nTests run: 1, Failures: 1, Errors: 0, Skipped: 0'
assert e.baseline_passed(clean) and not e.baseline_passed('BUILD SUCCESS')
assert e.expected_failure(fail) and not e.expected_failure(fail.replace('TwoTwo, OneOne','OneOne, TwoTwo'))
b={'exit_code':0,'target_passed':True};c={'exit_code':0,'fixture_controls_passed':True};p={'exit_code':1,'expected_order_failure':True}
assert e.classify(b,c,p,True,True,b)=='confirmed_scoped_order_dependency'
assert e.classify(dict(b,target_passed=False),c,p,True,True,b)=='inconclusive_baseline'
assert e.classify(b,dict(c,fixture_controls_passed=False),p,True,True,b)=='inconclusive_fixture_controls'
assert e.classify(b,c,dict(p,expected_order_failure=False),True,True,b)=='inconclusive_perturbed_failure'
assert e.classify(b,c,p,True,False,b)=='inconclusive_subject_changed'
assert e.classify(b,c,{'exit_code':0,'target_passed':True},True,True,b)=='no_failure_observed'
print('PASS: baseline, controls, reviewed assertion, unrelated failure and changed-subject gates')
import tempfile
with tempfile.TemporaryDirectory() as td:
 report=pathlib.Path(td)/'report.xml'
 report.write_text('<testsuite name="org.apache.commons.lang3.stream.StreamsTest" tests="1" errors="0" skipped="0" failures="0"><testcase classname="org.apache.commons.lang3.stream.StreamsTest" name="testOfEnumeration"/></testsuite>')
 assert e.read_surefire(report)=='pass'
 report.write_text('<testsuite name="org.apache.commons.lang3.stream.StreamsTest" tests="1" errors="0" skipped="0" failures="1"><testcase classname="org.apache.commons.lang3.stream.StreamsTest" name="testOfEnumeration"><failure type="org.opentest4j.AssertionFailedError" message="expected: &lt;[OneOne, TwoTwo]&gt; but was: &lt;[TwoTwo, OneOne]&gt;">StreamsTest.java:246</failure></testcase></testsuite>')
 assert e.read_surefire(report)=='expected_order_failure'
 report.write_text(report.read_text().replace('testOfEnumeration','differentTest'))
 assert e.read_surefire(report) is None
 report.write_text('<bad')
 assert e.read_surefire(report) is None
print('PASS: exact Surefire test identity, passing and failing reports, malformed and unrelated controls')
assert e.report_is_fresh({'mtime_ns':10},{'mtime_ns':11})
assert not e.report_is_fresh({'mtime_ns':10},{'mtime_ns':10})
assert not e.report_is_fresh({'mtime_ns':10},{'mtime_ns':None})
print('PASS: stale, missing and fresh Surefire report gates')
import os
with tempfile.TemporaryDirectory() as td:
 td=pathlib.Path(td)
 run=e.run([sys.executable,'-c','import time; print("started",flush=True); time.sleep(30)'],td,os.environ.copy(),td/'timeout.log',1)
 assert run['timed_out'] and run['exit_code'] is None and 'started' in (td/'timeout.log').read_text()
 assert e.classify(b,c,dict(p,exit_code=None),True,True,b)=='inconclusive_perturbed_failure'
print('PASS: timeout terminates experiment process group and stays inconclusive')

assert e.classify(b,c,p,True,True,dict(b,target_passed=False))=='inconclusive_baseline_recheck'
print('PASS: failed post-perturbation baseline is inconclusive')

# NonDex runs of the two experiment test cases

Recorded November 20, 2026 (America/Chicago).

These runs compare the unchanged Apache test cases with stock NonDex, without either standalone experiment patch. The authoritative API/path coverage documentation remains [NonDex.wiki/SUPPORTED-APIS.md](../../NonDex.wiki/SUPPORTED-APIS.md); this document records subject-test executions and their detection outcomes.

## Results

**Stock NonDex did not flag either experiment test case in these runs.** Both unchanged tests passed cleanly and at every verified seed, whereas the known order-dependent HashSet control was flagged at all three seeds.

| Test case | Clean executions | Seed 933178 | Seed 974622 | Seed 1016066 | NonDex outcome |
| --- | --- | --- | --- | --- | --- |
| Commons Lang `StreamsTest#testOfEnumeration` | 2 passed | 2 passed | 2 passed | 2 passed | Not flagged; Maven exit 0. |
| Commons IO `IOBinaryOperatorStreamTest#testReduce` | 1 passed | 1 passed | 1 passed | 1 passed | Not flagged; Maven exit 0. |
| Positive control `AppTest#testHashSet` | 1 passed | 1 assertion failure | 1 assertion failure | 1 assertion failure | Flagged; expected Maven exit 1. |

Every execution ran exactly the selected method, with zero errors and skips. Commons Lang's inherited and project-specific Surefire executions cause two clean runs and two instrumented runs per seed; these are repetitions of the same test, not additional cases or seeds.

The instrumented JVMs recorded these whole-process shuffle counts:

| Subject | Seed 933178 | Seed 974622 | Seed 1016066 |
| --- | --- | --- | --- |
| Commons Lang | 7,321 in each execution | 7,321 in each execution | 7,321 in each execution |
| Commons IO | 614 | 613 | 613 |
| HashSet control | 88 | 88 | 88 |

These counts confirm active instrumentation in the subject JVMs. They include framework and other supported API calls and do **not** mean NonDex shuffled `Hashtable.keys()` or `Files.list(Path)`.

Together with the independently checked coverage documented in the wiki, these results demonstrate a detection gap for the two specific cases: the [manual Hashtable perturbation](hashtable/README.md) exposes the ordered-list assertion, and the [manual Files.list perturbation](files-list/RESULTS.md) exposes the cross-listing first-path assertion, while this pinned stock NonDex flags neither. Their API paths remain documented as uncovered in [SUPPORTED-APIS.md](../../NonDex.wiki/SUPPORTED-APIS.md).

## Saved evidence

The [result manifest](nondex-runs/evidence/verified-run/result.json) records commands, environment cleanup, revisions, unchanged target-source hashes, installed plugin/runtime JAR hashes, generated instrumentation hashes, JVM-verified seeds and execution IDs, invocation counts, and hashes for the saved reports. Companion evidence includes:

- [Commons Lang Maven log](nondex-runs/evidence/verified-run/commons-lang/maven.log), plus all clean/per-seed XML reports and NonDex configuration/counter/failure files in that directory.
- [Commons IO Maven log](nondex-runs/evidence/verified-run/commons-io/maven.log), plus its corresponding reports and NonDex records.
- [Positive-control Maven log](nondex-runs/evidence/verified-run/positive-control/maven.log), plus the clean pass and three assertion-failure reports.

The positive-control failure lists identify `edu.illinois.nondex.it.AppTest#testHashSet`; the target subjects' failure lists are empty. Runtime diagnostics and Surefire dumpstream files are retained, including incidental name-service and logging-channel warnings. The fresh test XML and NonDex records, rather than warnings or Maven exit status alone, determine the outcomes.

Generated subject archives, classes, dependencies, and instrumented JARs remain under ignored `nondex-runs/build/run-1/`; selected logs and reports above are shareable. The original checkouts and tracked NonDex sources remained unchanged.

## Setup

- NonDex `2.2.5-SNAPSHOT`, built from the clean pinned revision `f1f407ce3e026f597567e7d96ee08cb08875690f`.
- Eclipse Temurin 11.0.33+10 and Maven 3.9.9.
- Commons Lang revision `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8`: `org.apache.commons.lang3.stream.StreamsTest#testOfEnumeration`.
- Commons IO revision `0c640aef74c65292ef313596f58c48b1b121e1e7`: `org.apache.commons.io.function.IOBinaryOperatorStreamTest#testReduce`.
- Separate Git archives of the pinned subject revisions, preserving the original checkouts and test source. Inherited JVM/Maven option variables were cleared; neither manual perturbation patch was loaded.
- NonDex FULL mode, three instrumented seeds (`933178`, `974622`, `1016066`), with a clean execution before the instrumented runs. Surefire failure retries were disabled. The unrelated Apache RAT check was skipped; these were focused tests, not full Apache test suites.

## Evidence checks

The saved Surefire XML must identify the intended test method, with no skips. For instrumented runs, its JVM properties must agree with the seed and execution ID in the NonDex configuration. Nonempty invocation counters establish that stock instrumentation ran somewhere in the test JVM; they do not attribute those choices to the candidate API itself.

The positive control is NonDex's own `simple-it` `AppTest#testHashSet`. Its source is unchanged; only its template POM placeholders were resolved to the built plugin coordinates. It is expected to pass cleanly and fail when NonDex shuffles its supported HashSet path.

## Interpretation

A test passing for three seeds alone does not prove that an API is uninstrumented: a covered path might happen to preserve the assertion. The relevant evidence chain combines the unchanged tests' failures under the separate manual patches, their results under stock NonDex, and the source/path and opportunity-counter analysis linked from the wiki's [SUPPORTED-APIS.md](../../NonDex.wiki/SUPPORTED-APIS.md).

The conclusion is bounded to this pinned stock tool and the checked Java 11 paths. It does not establish anything about future NonDex releases, all filesystem providers, all seeds, or every possible assumption in either test. The historical Hashtable manual patch used Java 21; this comparison runs its unchanged subject test on Java 11.

## Execution details

The initial attempts encountered missing cached dependencies. After obtaining them, the first completed invocations also exposed a Surefire property-forwarding issue: explicitly setting `-DnondexSeed=933178` as a Maven user property caused later test JVMs to use that same seed, despite different seeds in the plugin configurations. Those attempts are excluded from the final three-seed evidence. The final invocations omit that user property, let NonDex choose its default seed sequence, and check the seed inside every test JVM's XML report. Missing dependencies and repeated initial seeds are not counted as additional successful seed trials.

## Reproduction

Build the pinned plugin with Java 11 and Maven dependencies available:

```sh
export JAVA_HOME=/path/to/jdk-11
export PATH="$JAVA_HOME/bin:$PATH"
export EXPERIMENT_MAVEN=/path/to/maven/bin/mvn
export EXPERIMENT_REPO=/path/to/maven-repository

cd NonDex
"$EXPERIMENT_MAVEN" -B "-Dmaven.repo.local=$EXPERIMENT_REPO" \
  -DskipTests -Dcheckstyle.skip -Drat.skip=true \
  -pl nondex-maven-plugin -am install
```

Create fresh Git archives of each pinned subject as described in the setup. Clear `JDK_JAVA_OPTIONS`, `JAVA_TOOL_OPTIONS`, `_JAVA_OPTIONS`, `MAVEN_OPTS`, and `MAVEN_ARGS` before running. In the isolated Commons Lang directory, execute:

```sh
"$EXPERIMENT_MAVEN" -o -B "-Dmaven.repo.local=$EXPERIMENT_REPO" \
  '-Dtest=StreamsTest#testOfEnumeration' \
  -Drat.skip=true -Dsurefire.rerunFailingTestsCount=0 \
  -DnondexRuns=3 -DnondexRunsWithoutShuffling=1 \
  edu.illinois:nondex-maven-plugin:2.2.5-SNAPSHOT:nondex
```

Use the same command in the isolated Commons IO directory with `'-Dtest=IOBinaryOperatorStreamTest#testReduce'`. The final saved commands additionally set logging to INFO for Commons Lang and FINE for Commons IO/control; exact invocations are in the manifest. FULL mode and initial seed 933178 are the pinned plugin defaults. Leave `nondexSeed` unset as a Maven user property, then verify the actual three per-JVM seeds in `.nondex/*/TEST-*.xml` against their `config` files. Inspect every clean and instrumented report, not only the final console summary.

To reproduce the positive control, copy `NonDex/nondex-maven-plugin/src/it/simple-it/`, resolve its POM placeholders to `edu.illinois:nondex-maven-plugin:2.2.5-SNAPSHOT`, and run the same command with `'-Dtest=AppTest#testHashSet'`. Expect a clean pass, three assertion failures, and Maven exit 1.

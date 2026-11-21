# Experiment history

These are chronological notes from execution of the earlier milestone plan. For current status and next work, read [HANDOFF.md](../HANDOFF.md); the general roadmap is in [PROJECT_OVERVIEW.md](../PROJECT_OVERVIEW.md).

## Update: unchanged Commons IO test, 2026-11-20

The new [Files.list experiment](../experiments/manual-perturbations/files-list/README.md) patches the runtime's `Files.list(Path)` return, limited to the configured directory and exact `IOBinaryOperatorStreamTest#testReduce` caller. Odd matching calls retain the underlying order; even matching calls lazily swap the first pair, preserving membership and forwarding close. With Commons IO pinned at `0c640aef74c65292ef313596f58c48b1b121e1e7`, the unchanged target passed normally, failed at line 102 under the patch (first real path `.asf.yaml` versus `.gitattributes`), and passed in a fresh unpatched recheck. Subject inputs and directory entries remained unchanged.

The run used Temurin 11.0.33+10, ASM 9.8, and Maven 3.9.9, with Surefire retries disabled and the unrelated RAT license check skipped. Controls cover lazy construction, two-entry read-ahead, empty/singleton/multiple-entry listings, membership, sorting, close propagation, unmatched scope, and representative exceptions. This is a manual scoped order-dependency witness, not a general NIO implementation, an LLM-pipeline result, or a NonDex extension. Earlier attempts that supplied the patch via `argLine` did not reach the hook because of the project's late JaCoCo configuration; those attempts remained inconclusive. The corrected runner uses `JDK_JAVA_OPTIONS` and requires both test-time hook diagnostics before confirming the result.

See the experiment's `RESULTS.md` and selected `evidence/` files for the reproducible record. This update supersedes earlier statements below that the Files.list perturbation was unimplemented.

## Update: unchanged Hashtable test, 2026-11-18

At the recorded Commons Lang revision, the unchanged `StreamsTest#testOfEnumeration` passed without perturbation and with stock NonDex (three seeds). A manually patched JDK `Hashtable.keys()` implementation, limited to the exact two-key plain table, produced a reversed enumeration and the unchanged test failed at line 246: expected `[OneOne, TwoTwo]`, got `[TwoTwo, OneOne]`. Empty, singleton, two-key membership and exhaustion controls passed. This is a deterministic scoped experiment, not a general NonDex extension; eager snapshotting and the exact-key restriction limit its applicability. Implementation and commands: `experiments/manual-perturbations/hashtable/README.md`.

## Update: 2026-11-18 candidate experiments

Both targeted baseline tests passed (one test each) on the pinned Commons Lang and Commons IO revisions using Temurin 21.0.13.1 and Maven 3.9.9. Stock NonDex 2.2.5-SNAPSHOT, FULL mode, seeds 933178, 974622, and 1016066, also reported no failures for either targeted test. The Commons Lang project caused multiple Surefire executions; the summary reported all passing. These runs do not establish that stock NonDex can perturb the candidate APIs.

For an exploratory local witness, `hashtable-witness.patch` changes only the enumeration supplied to the last ordered assertion: it collects the original two keys, reverses them, and makes an enumeration of the result. It leaves the assertion and the surrounding membership checks intact. Running the targeted Maven test with this patch failed at that assertion: expected `[OneOne, TwoTwo]`, observed `[TwoTwo, OneOne]`. The tracked source was restored after the run. The modified test demonstrates sensitivity to the alternative key order for this stable two-key example; it is not an unmodified-client run or a NonDex interception, and it does not validate a general implementation's concurrent modification, laziness, or subclass behavior. Compiled test artifacts may reflect the patched source until Maven recompiles it.

The Files.list perturbation remains unimplemented; no failure has been demonstrated for that candidate. See the previous notes for commands and the relevant source revisions.

## Update: 2026-11-18 control and client baselines

The user supplied a successful NonDex build log for the pinned 2.2.5-SNAPSHOT: all seven reactor modules succeeded and 10 Maven plugin integration tests passed. That run installed to the home Maven repository. This session copied its dependencies, plus the integration-test local repository, to `/misc/scratch/aab5473/testing-tools/maven-repository` for writable offline use. Runtime: Temurin 21.0.13.1+2 and Maven 3.9.9.

From `NonDex/nondex-maven-plugin/target/it/simple-it`, with those tools and `-o -B -Dmaven.repo.local=/misc/scratch/aab5473/testing-tools/maven-repository`:

- `mvn ... test` passed: one `AppTest.testHashSet` test, zero failures.
- `mvn ... edu.illinois:nondex-maven-plugin:2.2.5-SNAPSHOT:nondex` ran one clean execution successfully and reported that same test failing in FULL mode for seeds 933178, 974622, and 1016066. Maven exited 1 as the plugin reports discovered failures. The fixture assumes HashSet iteration order when removing an element through an iterator and then comparing its string representation. Perturbation can therefore change both the removed element and the displayed order. This is an existing deliberately order-dependent control, not a new bug.
- This generated fixture is under `target` and can be regenerated by the NonDex integration build; `NonDex/nondex-maven-plugin/src/it/simple-it/` is its source.

The pinned Commons Lang and Commons IO checkouts are present. Offline `mvn ... '-Dtest=StreamsTest#testOfEnumeration' test` and `mvn ... '-Dtest=IOBinaryOperatorStreamTest#testReduce' test` respectively both stopped before compiling because `org.apache.commons:commons-parent:pom:107` was absent. Neither candidate baseline nor a stock NonDex candidate run has yet occurred. Online dependency resolution in the writable scratch Maven repository is the next requirement.

Date: 2026-11-17. This is a progress record, not evidence of a detected flaky test.

## Environment and attempts

- Parent checkout: `ed7dd72`; NonDex: `f1f407ce3e026f597567e7d96ee08cb08875690f`; wiki: `85f654bc534c87f415a54d0156a23c5bf2c0e9cd`.
- Default Java: OpenJDK 8u512; Maven: 3.5.4. NonDex documents Java 8–21 and Maven 3.6+; a Java 11 installation is also present. The original candidate projects' own JDK requirements have not been established here.
- From `NonDex/`, `mvn -B -DskipTests install` failed while resolving `org.sonatype.plugins:nexus-staging-maven-plugin:1.6.13`: DNS could not resolve `repo.maven.apache.org`. This did not build or execute NonDex. Maven also falls below the documented minimum.
- From the project root, `git clone --no-checkout https://github.com/apache/commons-lang.git search/sources/commons-lang` failed because DNS could not resolve `github.com`. The research clones used in the earlier search are not present. The Commons Lang and Commons IO baselines and candidate perturbations have therefore not been run.
- No seed, client test result, stock NonDex result, or valid perturbation result is available from these attempts. Restore network/dependencies and use Maven 3.6+ before interpreting experiment outcomes.

## Instrumentation trace

In the pinned checkout, `nondex-instrumentation/src/main/java/edu/illinois/nondex/instr/Instrumenter.java` adds `java/util/HashMap$HashIterator.class` to the special instrumentation set. `instrumentSpecialClass` delegates visitor selection to `CVFactory`; `HashMapShufflingAdder` adds a shuffler field and delegates iterator methods to it. `HashIteratorShufflerASMDump` supplies generated shuffler bytecode. This is source inspection, not a demonstrated execution. The same target list does not name Hashtable or NIO directory listing classes; absence from this list alone is not a complete runtime coverage proof.

## Resume

1. Supply network access or a complete local Maven dependency cache and the recorded client checkouts. Install or locate Maven 3.6+ and a JDK compatible with each pinned subject.
2. Build NonDex and run a documented stock example, recording complete commands, output, JDK, seed, and configurations. Then run each candidate at its recorded revision without and with stock NonDex.
3. Implement and validate a narrowly scoped Hashtable enumeration perturbation, followed by the NIO candidate if feasible. Preserve contracts and distinguish a valid alternate behavior from an actual client failure.

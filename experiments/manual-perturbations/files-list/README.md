# Scoped Files.list ordering experiment

This experiment exercises the `java.nio.file.Files.list(Path)` candidate identified in the [test-guided search](../../../search/NONDEX-TEST-GUIDED-SEARCH.md). It targets the unchanged Commons IO test `org.apache.commons.io.function.IOBinaryOperatorStreamTest#testReduce` at revision `0c640aef74c65292ef313596f58c48b1b121e1e7`.

The fixture is a standalone JDK bytecode patch, separate from NonDex. It was designed and implemented in this coding session; it does not invoke or consume proposals from the `Agent/` local-LLM analysis pipeline. `model_pipeline_used: false` in the result manifest refers to that experimental pipeline, not to whether a coding assistant helped author these files.

## What the test assumes

The test opens the current directory twice. The first stream reduction repeatedly retains its left operand's real path, then the second reduction does the same and asserts equality with the first result at line 102. With at least two distinct real paths, this assumes the independent listings select the same first entry.

This is different from the Hashtable fixture: returning the same changed order on every listing could still make this assertion pass. The variation must exercise different first entries between the two calls.

## Ordering freedom and example

The directory-entry encounter order is unspecified. Two independent listings of the same unchanged directory need not return entries in the same order. This freedom does not require Java to randomize listings: a filesystem may return a repeatable order that makes the test's assumption appear reliable. The contract references and validation limits are described below.

For a stable directory with three distinct real paths, the experiment behaves like this:

```text
First listing, unchanged:       [apple.txt, banana.txt, cherry.txt]
Second listing, first pair swapped:
                               [banana.txt, apple.txt, cherry.txt]
First reduction selects:        apple.txt's real path
Second reduction selects:       banana.txt's real path
Equality assertion:             fails
```

The entries are identical as a set; only their encounter order changes. This is an illustrative example, not the filenames used by the actual run. Applying the same reordered sequence to both listings could let the test pass, which is why the fixture varies the order between calls.

## Recorded results

| Stage | Outcome |
| --- | --- |
| Unpatched target baseline | One test passed; zero failures, errors, or skips. |
| Fixture controls | Passed, including lazy construction, bounded read-ahead, membership, sorting, closing, and representative exceptions. |
| Patched, unchanged target | One assertion failure at `IOBinaryOperatorStreamTest.java:102`. |
| Fresh unpatched recheck | One test passed; zero failures, errors, or skips. |
| Subject inputs and directory entries | Unchanged. |

In the verified run, the first listing selected `./.asf.yaml` and the second selected `./.gitattributes`. Their distinct real paths caused the equality assertion to fail. The result was classified as `confirmed_scoped_cross_listing_order_dependency`: the perturbation successfully exposed this test's cross-listing order assumption.

Earlier attempts were inconclusive because the Maven configuration replaced the patch arguments and the hook did not run. The corrected runner confirmed both expected hooks and completed baseline, perturbation, and recheck without recorded command timeouts. These are saved results, not a fresh rerun during this documentation update. See [RESULTS.md](RESULTS.md) for the configuration, execution history, and links to the [verified manifest](evidence/verified-run/result.json) and logs.

## Perturbation

`src/Transform.java` reads the selected runtime's `java.nio.file.Files` bytecode and inserts a hook at the single return from `list(Path)`. It does not modify the test or the filesystem provider. The patch is loaded with `--patch-module java.base=...` in the test JVM.

`src/java/nio/file/FilesListWitness.java` applies the hook only when:

- The listed path is the explicitly configured directory on the default filesystem.
- The stack contains the exact target test method, or the fixture-control process explicitly enables controls.

For matching calls, odd calls retain the underlying order; even calls swap only the first two entries and then continue in the underlying order. A diagnostic records the selected action and first emitted entry. There is no random seed; this is a deterministic exploration schedule.

The swapping wrapper does not traverse entries when `Files.list()` returns. It reads up to two entries when traversal first starts, emits the second followed by the first, then forwards subsequent entries. Closing the returned stream closes the original stream. Its spliterator does not split. The tested subject calls it sequentially.

## Contract basis and scope

The [Java 11 DirectoryStream contract](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/nio/file/DirectoryStream.html) specifies no particular element order. The audited Java 11 `Files.list` implementation uses a directory stream; the [Files.list contract](https://docs.oracle.com/en/java/javase/11/docs/api/java.base/java/nio/file/Files.html#list(java.nio.file.Path)) also describes lazy population, closing, weak consistency, and I/O errors.

The intended permitted variation is encounter order for one stable, finite directory. Entry membership, path values, directory identity, the subject source, and the assertion remain unchanged. Sorting or comparing membership should still work.

This is **not a general contract-compliance claim**. Two-entry read-ahead can change when an I/O error or concurrent modification becomes observable. The fixture checks lazy construction, bounded read-ahead, closing, and representative exceptions, but does not establish all error-timing, concurrent-close, mutation, parallel-performance, or provider-specific behavior. It neither snapshots nor locks the directory. Custom filesystem providers are outside the reviewed scope. A reusable NonDex extension would require broader modeling and validation.

## Files

| Path | Purpose |
| --- | --- |
| `run.py` | Build the fixture, run controls, archive the pinned subject, execute baseline/perturbed/recheck tests, and classify the result. |
| `src/Transform.java` | Bytecode interception for this runtime's `Files.list(Path)` return. |
| `src/java/nio/file/FilesListWitness.java` | Scoped selection and lazy first-pair swapping. |
| `src/Check.java` | Synthetic stream controls and actual directory-listing controls. |
| `build/` | Ignored generated classes, isolated subject archives, logs, and manifests. Each output directory must be new. |
| `evidence/` | Selected shareable results from completed runs, when present; no subject builds or dependency JARs. |

## Requirements and reproduction

Use a full JDK with module patching (`java`, `javac`, and `lib/modules`), Python 3.6 or later, ASM, Maven, and the pinned Commons IO checkout. Initial verification uses Temurin 11.0.33+10, ASM 9.8, and Maven 3.9.9. Other runtimes require their own validation.

The runner is deliberately offline for Maven. First obtain Commons IO's dependencies using your normal Maven setup. All runs disable Surefire retries so a perturbed failure cannot be hidden by a passing rerun. The runner also skips the unrelated RAT license check for the focused experiment; it does not run the complete Commons IO test suite or all build checks.

From the parent repository root, replace the example paths:

```sh
python3 experiments/manual-perturbations/files-list/run.py \
  --java-home /path/to/jdk-11 \
  --asm /path/to/asm-9.8.jar \
  --project search/sources/commons-io \
  --maven /path/to/maven/bin/mvn \
  --maven-repo /path/to/maven-repository \
  --output experiments/manual-perturbations/files-list/build/new-run
```

The input checkout must be at the pinned revision with clean tracked files. The runner uses a separate Git archive and verifies the reviewed target source hash. It clears inherited JVM patch options, runs the same Maven test configuration before and after perturbation, and checks that the archived input files, original test, and root directory entries remain unchanged. A passing baseline is required before the patched run. Generated reports are removed before each stage so stale reports cannot satisfy the checks.

The patched run supplies `JDK_JAVA_OPTIONS`, which reaches Maven and its forked test JVM. The helper's directory and caller filters prevent it changing unrelated build-time listings. This avoids Commons IO's late `@{argLine}` / JaCoCo configuration replacing a command-line `argLine`. Baseline and recheck runs have the patch options removed. The manifest records the exact environment override, and confirmation requires diagnostics from the two test-time hooks.

Run only fixture controls without Maven or a subject checkout:

```sh
python3 experiments/manual-perturbations/files-list/run.py \
  --java-home /path/to/jdk-11 \
  --asm /path/to/asm-9.8.jar \
  --controls-only \
  --output experiments/manual-perturbations/files-list/build/new-controls
```

Controls cover empty, singleton, two-entry, and five-entry directories; exact permutation and membership; sorted comparison; exhaustion; no traversal at construction; two-element read-ahead for `findFirst()`; close propagation before/after traversal and after a synthetic read error; unmatched directory scope; and a missing-directory exception. They check both the wrapper directly and actual patched `Files.list` calls.

## Interpreting results

Inspect `result.json`, the command logs, and the fresh Surefire XML snapshots. A confirmation requires:

1. A passing unpatched target and passing fixture controls.
2. Exactly the expected matching calls: identity, then first-pair swap.
3. One target test failing with the expected unequal-path assertion at line 102, with paths agreeing with the recorded first entries.
4. A passing fresh unpatched recheck.
5. Unchanged subject inputs and directory entries.

`confirmed_scoped_cross_listing_order_dependency` describes only this test under this bounded experiment. Setup errors, timeouts, unrelated failures, missing reports, unobserved hooks, and changed inputs are inconclusive. A failing Maven process alone does not establish the finding. The runner records commands, runtime and source hashes, report hashes, assertion details, and fixture diagnostics.

The stock NonDex source/coverage audit already identifies `Files.list` as uncovered. This runner does not execute stock NonDex or modify its instrumentation, and does not register this experiment in `Agent/pipeline.py`.

## Stock NonDex coverage reference

Consult [NonDex.wiki/SUPPORTED-APIS.md](../../../NonDex.wiki/SUPPORTED-APIS.md) for authoritative coverage, runtime evidence, and limitations. The standalone experiment above does not add support to stock NonDex.

Fresh Maven-plugin executions of this unchanged test are recorded in [NonDex test results](../NONDEX-TEST-RESULTS.md), with per-seed evidence and an active positive control.

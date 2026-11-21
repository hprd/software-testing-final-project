# Files.list experiment results

Recorded November 20, 2026 (America/Chicago).

## Outcome

The unchanged Commons IO `IOBinaryOperatorStreamTest#testReduce` exhibited the predicted cross-listing order dependency under the scoped JDK patch:

| Stage | Outcome |
| --- | --- |
| Fixture controls | Passed. |
| Unpatched baseline | One target test, zero failures/errors/skips. |
| Patched run | One target test, one assertion failure at `IOBinaryOperatorStreamTest.java:102`. |
| Fresh unpatched recheck | One target test, zero failures/errors/skips. |
| Subject input hashes | Unchanged. |
| Original checkout's target source | Unchanged. |
| Directory entry names and resolved paths | Unchanged across the patched run and recheck. |

The first listing emitted `./.asf.yaml` first. The second listing, with its first pair swapped, emitted `./.gitattributes` first. The failed equality compared the corresponding distinct real paths. These filenames are observations in this archived checkout, not hardcoded inputs or conditions in the perturbation.

The manifest classification is `confirmed_scoped_cross_listing_order_dependency`. This is a deterministic bounded witness for this test, not proof of a generally valid Files.list implementation, a newly established discovery-novelty claim, or completed NonDex support.

## Configuration and evidence

- Commons IO revision: `0c640aef74c65292ef313596f58c48b1b121e1e7`.
- Target source SHA-256: `480c2a06bcc42c2b35b70680b90e9087888e344b2cd0ad2c4fe220091e476196`.
- Runtime: Eclipse Temurin 11.0.33+10, Linux default filesystem.
- ASM 9.8; Maven 3.9.9; Python 3.6.
- Offline targeted Maven execution, with Surefire retries disabled and the unrelated RAT license check skipped.
- No `Agent/` local-model requests and no stock NonDex execution in this experiment.

The selected completed run is preserved in [evidence/verified-run/result.json](evidence/verified-run/result.json). It records exact commands and environment overrides, runtime/module/ASM/source hashes, generated patch hashes, all archived input hashes, assertion paths, and report assessments. Companion evidence:

- [Fixture control output](evidence/verified-run/controls.log).
- [Baseline log](evidence/verified-run/baseline.log) and [fresh XML report](evidence/verified-run/baseline-test.xml).
- [Patched log](evidence/verified-run/perturbed.log) and [fresh XML report](evidence/verified-run/perturbed-test.xml).
- [Unpatched recheck log](evidence/verified-run/baseline-recheck.log) and [fresh XML report](evidence/verified-run/baseline-recheck-test.xml).

Generated subjects, classes, archives, and dependency caches are excluded from the evidence bundle. Their absolute paths in the manifest describe the original run; use [README.md](README.md) to produce new outputs on another machine.

## Limits and execution checks

The fixture is restricted to the configured directory and exact test caller. It preserves the entries while varying their first-pair encounter order. Synthetic and actual-directory controls check lazy construction, bounded two-entry look-ahead, exact permutation, membership, sorted comparison, exhaustion, close forwarding, and representative exceptions. They do not certify arbitrary concurrent mutations, custom providers, parallel traversal, resource races, or all error timing.

Earlier local attempts supplied a patch via the command-line `argLine`. Commons IO's late expansion and JaCoCo preparation replaced that JVM argument; all three test stages passed and no fixture hooks were observed, so those runs were classified inconclusive. The corrected runner uses `JDK_JAVA_OPTIONS` and confirms the two expected test-time hooks. A subsequent verification run exercises the final runner, including its explicit timeout exclusion. Earlier development outputs remain under ignored `build/` directories and are not the result reported above.

The original checkout and stock NonDex sources were not modified. The perturbation was authored as a scoped coding experiment, not generated through the existing contract-analysis pipeline. The next research step is to evaluate that pipeline's suggestions against known NonDex-supported APIs before connecting proposals to executable implementations.

# Reproducing the supported-API audit

This is a coverage audit for NonDex revision `f1f407ce3e026f597567e7d96ee08cb08875690f`, not a new NonDex implementation. The probes compile and execute the actual `nondex-common` and `nondex-instrumentation` sources. No historical replacement JDK sources from `nondex-core` are used. The Maven/Gradle plugin lifecycles are not exercised.

## Requirements

- Python 3.6 or later.
- A full JDK 8 or 11 with `java`, `javac`, and `javap`. These are the runtime families tested; other versions require a fresh audit.
- A separate dependency directory containing these Maven Central artifacts:

| Group | Artifact | Version |
| --- | --- | --- |
| `org.ow2.asm` | `asm`, `asm-util`, `asm-tree`, `asm-analysis` | `9.8` |
| `javax.xml.bind` | `jaxb-api` | `2.3.1` |
| `junit` | `junit` | `4.13.2` |
| `org.hamcrest` | `hamcrest-core` | `1.3` |

Use the ordinary artifact names, including `jaxb-api-2.3.1.jar`. These are the declared ASM/JAXB/JUnit versions in the pinned source; `asm-tree` and `asm-analysis` support ASM's verification utilities. Dependency hashes are recorded in the saved manifests. JARs and generated classes are not included in the wiki.

## Run

From a directory containing adjacent `NonDex` and `NonDex.wiki` checkouts, replace the example absolute paths with paths on your machine:

```sh
python3 NonDex.wiki/verification/verify.py \
  --nondex ./NonDex \
  --java-home /absolute/path/to/jdk8 \
  --deps /absolute/path/to/dependencies \
  --output /absolute/path/to/new-java8-output

python3 NonDex.wiki/verification/verify.py \
  --nondex ./NonDex \
  --java-home /absolute/path/to/jdk11 \
  --deps /absolute/path/to/dependencies \
  --output /absolute/path/to/new-java11-output
```

Use a **new output directory** for each run. The runner never downloads dependencies, changes the NonDex sources, or reuses an existing instrumented JAR. It writes generated files and logs under the output directory. Probe-created temporary directories are removed on normal completion.

The runner:

1. Compiles the active runtime and instrumenter with the selected JDK and generates a fresh instrumented JAR.
2. Checks the complete registry (15 target classes), disassembles the generated classes, and verifies every unique standard selector (20 class/method pairs) has an injected call. Records direct hook signatures, including special transformers and helper classes.
3. Compiles `ApiAudit.java`, then runs 175 API/path probes on a plain JVM and an instrumented JVM for each of seeds 933178, 974622, and 1016066 in `FULL` mode.
4. Measures NonDex opportunity-counter deltas around 24 calls per path, after warm-up, and records distinct outputs. Array and traversal probes compare element multisets; zone-string probes check the original seven columns plus the optional trailing null. Parameter-annotation canonicalization checks membership, while source/bytecode inspection verifies that only inner arrays are shuffled.
5. Checks that plain runs reach no NonDex choices and have no membership violations.
6. Compiles and runs all 92 JUnit tests in the upstream `nondex-test` module under instrumentation. These tests must pass for the runner to complete.
7. Writes `results.json` with JDK output, source/dependency/probe/runner hashes, hook signatures, all measurements, and the upstream JUnit result. Full build, bytecode, and process logs remain in the output directory.

Membership violations in the custom probes are **recorded rather than hidden or treated as successful support**. A successful verifier process means it completed the audit and the upstream tests passed; it does not mean every probe passed. Inspect `membership_violations` and `first_violation`. The saved results deliberately retain the observed ConcurrentHashMap parallel traversal failures.

## Evidence and limits

- [Coverage matrix](COVERAGE-MATRIX.md): all 175 measured paths, with per-seed choice counts and correctness flags.
- [Java 8 results](java8-results.json): Red Hat OpenJDK 8u514, build 25.514-b01.
- [Java 11 results](java11-results.json): Temurin 11.0.33+10.
- [Probe source](ApiAudit.java) and [runner](verify.py).

Both environments emit incidental `yp_bind_client_create_v3` name-service warnings; these are retained in the raw JDK/JUnit output in the manifests. They are not test failures.

The probes use small, unchanged collections. They are not a concurrency, collision, resizing, provider-compatibility, or complete API-contract test suite. `toString()` probes measure variations without asserting their textual grammar; corresponding traversal probes check element membership. The normal probe returns define membership expectations except for map parallel streams, which use a separate iterator snapshot as their known expected multiset. Plain and patched JVMs use independently created temporary directories, so filesystem path strings are not compared across processes.

`Field.getAnnotationsByType` and its indirect declared variant preserve annotation membership while violating repeated-annotation order for this fixture; this contract issue is identified separately from the membership counter. Passing that counter cannot validate the perturbation. See [Supported APIs](../SUPPORTED-APIS.md) for the ordering specification and hash-code history.

Only one filesystem root was available, so `File.listRoots()` is bytecode-verified but not dynamically exercised with multiple roots. Java 17/21 and other JVM vendors were not tested. Exhaustiveness applies to the pinned instrumenter's registry and selectors plus the explicitly enumerated public-path matrix, not every transitive caller in Java or application code.

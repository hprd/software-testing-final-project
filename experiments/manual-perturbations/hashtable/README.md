# Scoped Hashtable order experiment

This is a manual research fixture, not a NonDex extension. On Temurin 21.0.13.1 it instruments the current JDK's `Hashtable.keys()` return using ASM, then patches `java.base` at startup. It reverses the actual returned enumeration only for a plain Hashtable containing exactly `One` and `Two`. The same order is used deterministically on each call; there is no random seed. Other tables return the original enumeration untouched.

## Purpose and the test's assumption

The target is the unchanged Commons Lang `StreamsTest#testOfEnumeration` at revision `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8`. The experiment asks whether the test relies on a particular order from `Hashtable.keys()`.

The enumeration's key order is unspecified: a stable implementation can repeatedly return one order without guaranteeing that order to callers. The test's final assertion expects the sequence `[OneOne, TwoTwo]` after transforming the enumerated keys. Its earlier membership and count checks do not require that sequence.

## What was perturbed: example

The JDK patch reverses only the returned key enumeration for the selected stable, plain two-key table. It preserves the keys and their count and leaves the subject test and assertion unchanged. For this fixture:

```text
                         Keys enumeration    Transformed result
Unpatched:               [One, Two]         [OneOne, TwoTwo]
Patched:                 [Two, One]         [TwoTwo, OneOne]
Test's expected result:                     [OneOne, TwoTwo]
```

The patched result contains the same elements but fails the ordered equality assertion. Unlike the [Files.list experiment](../files-list/README.md), which needs different first entries across two independent listings, this test directly expects a particular sequence. A consistent reversal is sufficient to expose its assumption.

## Recorded results

| Stage | Outcome |
| --- | --- |
| Unpatched target baseline | Passed. |
| Fixture controls | Empty, singleton, two-key membership, ordering, and exhaustion checks passed. |
| Patched, unchanged target | Failed at `StreamsTest.java:246`: expected `[OneOne, TwoTwo]`, received `[TwoTwo, OneOne]`. Earlier membership and count assertions passed. |
| Fresh unpatched recheck | Passed in the later recorded experiment described in the handoff. |
| Stock NonDex comparison | Target passed for three seeds; those runs did not expose this dependency. |

The perturbation successfully demonstrated a scoped order dependency. This is a manual JDK-patch result; it does not demonstrate LLM-generated support or completed NonDex integration. A passing stock NonDex run does not establish that the relevant enumeration path was perturbed.

These are historical recorded outcomes, not a fresh rerun. See the chronological [experiment status](../../../search/EXPERIMENT-STATUS.md#update-unchanged-hashtable-test-2026-11-18) and [handoff](../../../HANDOFF.md#existing-prototype-and-recorded-results). The ignored `Agent/results/` raw artifacts are absent from the current checkout, so the documentation record is the available evidence here.

## Build and reproduction

Run `./run-build.sh` to build the patch and check empty, singleton, membership, two-element ordering, and exhaustion. Defaults use the JDK and ASM in `/misc/scratch/aab5473/testing-tools`; override `JAVA_HOME` or `ASM` as needed. The baseline JDK order for this exact table must be `[One, Two]` for the control's expected reversed order to hold. The bytecode transformer depends on the JDK implementation and has only been checked on the recorded JDK.

With Commons Lang at `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8`, run the unchanged test with the patch:

```sh
export JAVA_HOME=/misc/scratch/aab5473/testing-tools/temurin-jdk21
export PATH="$JAVA_HOME/bin:/misc/scratch/aab5473/testing-tools/apache-maven-3.9.9/bin:$PATH"
export JDK_JAVA_OPTIONS='--patch-module=java.base=/misc/scratch/aab5473/software-testing-final-project/experiments/manual-perturbations/hashtable/build/patch'
cd /misc/scratch/aab5473/software-testing-final-project/search/sources/commons-lang
mvn -o -B -Dmaven.repo.local=/misc/scratch/aab5473/testing-tools/maven-repository '-Dtest=StreamsTest#testOfEnumeration' test
```

Unset `JDK_JAVA_OPTIONS` before the baseline and unpatched recheck runs.

## Scope and limitations

The reversal eagerly consumes a snapshot while `keys()` holds the table's synchronization lock. This is justified only for the stable, unmodified test fixture; it does not establish a general implementation preserving timing, side effects, concurrent behavior, subclasses, or all related APIs. No claim of general contract compliance or integration with NonDex is made. A reusable extension would need a principled interception mechanism, seed integration, broader validation, and separate treatment of mutation and subclass contracts.

## Stock NonDex coverage reference

Consult [NonDex.wiki/SUPPORTED-APIS.md](../../../NonDex.wiki/SUPPORTED-APIS.md) for authoritative coverage, runtime evidence, and limitations. The standalone experiment above does not add support to stock NonDex.

Fresh Maven-plugin executions of this unchanged test are recorded in [NonDex test results](../NONDEX-TEST-RESULTS.md), with per-seed evidence and an active positive control.

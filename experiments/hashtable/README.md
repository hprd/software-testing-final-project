# Scoped Hashtable order experiment

This is a manual research fixture, not a NonDex extension. On Temurin 21.0.13.1 it instruments the current JDK's `Hashtable.keys()` return using ASM, then patches `java.base` at startup. It reverses the actual returned enumeration only for a plain Hashtable containing exactly `One` and `Two`. The same order is used deterministically on each call; there is no random seed. Other tables return the original enumeration untouched.

Run `./run-build.sh` to build the patch and check empty, singleton, membership, two-element ordering, and exhaustion. Defaults use the JDK and ASM in `/misc/scratch/aab5473/testing-tools`; override `JAVA_HOME` or `ASM` as needed. The baseline JDK order for this exact table must be `[One, Two]` for the control's expected reversed order to hold. The bytecode transformer depends on the JDK implementation and has only been checked on the recorded JDK.

With Commons Lang at `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8`, run the unchanged test with the patch:

```sh
export JAVA_HOME=/misc/scratch/aab5473/testing-tools/temurin-jdk21
export PATH="$JAVA_HOME/bin:/misc/scratch/aab5473/testing-tools/apache-maven-3.9.9/bin:$PATH"
export JDK_JAVA_OPTIONS='--patch-module=java.base=/misc/scratch/aab5473/software-testing-final-project/experiments/hashtable/build/patch'
cd /misc/scratch/aab5473/software-testing-final-project/search/sources/commons-lang
mvn -o -B -Dmaven.repo.local=/misc/scratch/aab5473/testing-tools/maven-repository '-Dtest=StreamsTest#testOfEnumeration' test
```

Unset `JDK_JAVA_OPTIONS` before the baseline run. In the experiment, the original test passed unpatched and failed patched at its ordered assertion: expected `[OneOne, TwoTwo]`, got `[TwoTwo, OneOne]`. Earlier membership and count assertions passed. Stock NonDex passed this test for three seeds. See `search/experiment-status.md`.

The reversal eagerly consumes a snapshot while `keys()` holds the table's synchronization lock. This is justified only for the stable, unmodified test fixture; it does not establish a general implementation preserving timing, side effects, concurrent behavior, subclasses, or all related APIs. No claim of general contract compliance or integration with NonDex is made. A reusable extension would need a principled interception mechanism, seed integration, broader validation, and separate treatment of mutation and subclass contracts.

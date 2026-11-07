# Recommended NonDex extension: Class.getPermittedSubclasses()

For the updated task's emphasis on real test usage and new failures, see the
[test-guided search](NonDex-Test-Guided-Search.md). It prioritizes concrete
Hashtable and NIO test assertions over this initial API-only recommendation.

Research date: 2026-11-06. Scope: documentation and source inspection only;
no instrumentation, Java examples, or tests were implemented or executed.

**Recommendation:** target `java.lang.Class.getPermittedSubclasses()` as the
first new API. The documented order is explicitly unspecified, the checked-out
NonDex does not perturb it, and its returned array fits NonDex's existing
instrumentation approach. This identifies a supported research candidate and a
failure mechanism, not a newly confirmed bug in a client project.

## Documentation evidence

The [Java SE 25 method documentation](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Class.html#getPermittedSubclasses())
states:

> The order of such elements is unspecified.

The method returns direct permitted subtypes of a sealed class or interface.
Non-sealed receivers return null; sealed receivers return an array, possibly
empty. Classes that cannot be obtained are omitted. This API dates from Java 17.

Thus a repeatable order on one JVM is an implementation behavior, not a client
guarantee. The appropriate perturbation is a permutation of the actual result,
rather than introducing different subtypes or altering the class hierarchy.

## Coverage check against this project's NonDex

The conclusion applies to the local NonDex checkout at
`f1f407ce3e026f597567e7d96ee08cb08875690f`, and the wiki at
`85f654bc534c87f415a54d0156a23c5bf2c0e9cd`. I did not update these submodules.

Evidence:

- [The supported-APIs wiki](../NonDex.wiki/Supported-APIs.md) does not list the
  method.
- [ClassVisitorShufflingAdder.java](../NonDex/nondex-instrumentation/src/main/java/edu/illinois/nondex/instr/ClassVisitorShufflingAdder.java),
  lines 45–73, explicitly enumerates the array-returning methods to perturb.
  It covers several `Class` methods but excludes `getPermittedSubclasses`.
- [Instrumenter.java](../NonDex/nondex-instrumentation/src/main/java/edu/illinois/nondex/instr/Instrumenter.java),
  lines 92–108, already includes `java/lang/Class.class` among standard
  instrumentation targets. Instrumenting the class does not automatically
  instrument every method: the visitor checks the explicit method list.
- A repository-wide search of `NonDex/` and `NonDex.wiki/` found no occurrence
  of `getPermittedSubclasses` or `getNestMembers`.

This checks implementation as well as documentation: the wiki alone is not
sufficient evidence, because it does not enumerate every entry in the current
array-shuffling list.

## How it can expose a flaky test

Consider a hypothetical application that discovers the variants of a sealed
interface named `Payment`, with two concrete permitted types, `CardPayment`
and `CashPayment`.

Suppose its default-selection logic chooses the first returned class and a
test expects that default to be `CardPayment`.

| Observed array order | Application's selected default | Test result |
| --- | --- | --- |
| CardPayment, CashPayment | CardPayment | Pass |
| CashPayment, CardPayment | CashPayment | Fail |

Both orders are allowed by the cited contract. The test/application combination
adds an ordering assumption the API does not supply. A JVM may consistently
return the first order; NonDex could reveal the latent dependency by exploring
the second. This does not assert that ordinary reruns on an unchanged JVM will
already alternate between the outcomes.

A second plausible failure is a snapshot test comparing an ordered JSON array
of discovered subtype names against a fixed expected string. The research lead
is the propagation of reflection order into an observable application result.
Whether a real project has either pattern remains to be investigated.

The repair depends on intent: choose a default by an explicit rule; sort by a
defined stable key when order is part of the application's output; or compare
membership when order is irrelevant. The tool should not label every use of
this API as a bug.

## Proposed perturbation constraints

These are design requirements for a future implementation, not implemented
behavior:

1. Let the original method finish normally before permuting its result. Preserve
   null, empty, and singleton results.
2. Preserve array length, runtime array type, and the exact multiset of `Class`
   references. Only positions may change. Do not invent, drop, duplicate, or
   initialize classes to produce alternative results.
3. Preserve exceptions and class-loader behavior. In particular, shuffle only
   the classes the original invocation actually returned; do not independently
   re-resolve the declared permitted types.
4. Use NonDex's seed and configuration so the explored behavior can be
   reproduced and attributed to this API.
5. Validate repeated calls explicitly. The ordering clause gives no stability
   guarantee; an initial conservative experiment can nevertheless use one
   ordering per receiver per run and vary it across seeds. Per-call exploration
   should be a separately documented choice, rather than an accidental effect.
6. Include control cases where the client sorts or compares membership. Those
   clients should continue to pass under every permutation.

The null/empty behavior and class-loading qualifications also appear in the
[Java SE 17 contract](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/lang/Class.html#getPermittedSubclasses()).
That version additionally documents a possible `SecurityException`; preserve
version-specific exceptions rather than treating Java 25 documentation as a
complete contract for every runtime.

## Why integration looks manageable

The existing visitor, lines 92–119, inserts an array-shuffling call before
selected methods return and restores the declared array type with a cast.
[ControlNondeterminism.shuffle](../NonDex/nondex-common/src/main/java/edu/illinois/nondex/shuffling/ControlNondeterminism.java),
lines 77–98, already handles null and short arrays and permutes array entries.

The [OpenJDK 25 release source](https://github.com/openjdk/jdk/blob/jdk-25%2B36/src/java.base/share/classes/java/lang/Class.java#L3861)
shows that the public method has a Java body, calls a private native helper,
filters for direct subtypes, and returns the resulting array. This suggests a
return interception in the public method, after its filtering, rather than
modifying native code or changing subtype discovery.

This is a feasibility assessment. Bootstrap initialization, interception of
internal calls, the selected NonDex exploration mode, class-file compatibility,
and the actual target JDK implementation still require validation. In-place
shuffling also deserves a check that it cannot alter shared internal state.

## Version and client-project limits

[NonDex's README](../NonDex/README.md), line 25, advertises Java 8–21 support.
Reading Java 25 documentation does not establish that NonDex can run on JDK 25.
Use Java 17 or 21 for the initial experiment and inspect that runtime's contract
and implementation before generating instrumentation.

Your checkpoint proposes using clients from the original NonDex evaluation.
Historical client revisions may predate this API and contain no calls to it.
Check API usage in the selected revisions, including dependencies, before
investing in support. This is a strong initial extension/template exercise, but
it does not guarantee additional failures in that historical benchmark.

## Nearby alternatives screened

| API | Assessment |
| --- | --- |
| `Class.getDeclaredMethods()` | Already supported in the local visitor; useful as a withheld reconstruction target, but not new coverage. |
| `Class.getNestMembers()` | Also absent locally. The host must remain first; only later positions are unordered, and duplicates are permitted. A full-array shuffle would be invalid. A useful later constraint-extraction exercise. |
| `Class.getRecordComponents()` | Reject for this perturbation: components have declaration order. |
| `Class.getInterfaces()` | Reject for this perturbation: interface order follows the declaration. |

These ordering constraints are documented in the
[Java SE 25 Class API](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Class.html).
The simpler whole-array permutation makes `getPermittedSubclasses()` the
preferred first target among these candidates.

## Relation to the supplied project material

I read the proposal and checkpoint and consulted the supplied NonDex papers'
discussions of specification inspection and permutation models. The
identification paper, §III-A, describes screening documentation and returned
arrays, followed by manual contract reasoning; this candidate follows that
process. The tool paper's instrumentation discussion motivates reuse of the
existing interception mechanism.

The supplied ChaosAPI paper, §4.2, discusses false positives from inconsistent
temporal perturbations. The proposal's emphasis on preserving relationships
between calls and on separating discovery from validated generation is relevant
here too, even though this recommendation targets NonDex.

Extracted paper text is kept locally in `search/*.txt` and ignored by Git. The
original documents remain in `Literature/`. No new client failure or successful
instrumentation run is claimed by this report.

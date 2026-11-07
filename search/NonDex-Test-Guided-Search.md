# Test-guided search for new NonDex API coverage

Research date: 2026-11-06. This follows the updated `SEARCH-TASK.md`.
The search inspected documentation, real test sources, and dataset metadata.
No implementation code was changed, and no client tests or perturbations were run.

**The two most actionable findings are `Hashtable.keys()` and `Files.list(Path)`.**
Each has a concrete order-dependent assertion in a current Apache test. These
are source-level failure candidates, not experimentally confirmed flaky tests.
For broader test usage, immutable collection factories and collectors are also
worth targeting. The earlier sealed-subtype recommendation remains a valid API
gap, but is a lower priority for finding failures in widely used test patterns.

## Search scope and reproducibility

I checked the local NonDex at `f1f407ce3e026f597567e7d96ee08cb08875690f`
and its wiki at `85f654bc534c87f415a54d0156a23c5bf2c0e9cd`, including
the instrumentation target lists, array visitor, special visitors, and legacy
core sources. Relevant files are
[Instrumenter.java](../NonDex/nondex-instrumentation/src/main/java/edu/illinois/nondex/instr/Instrumenter.java),
[ClassVisitorShufflingAdder.java](../NonDex/nondex-instrumentation/src/main/java/edu/illinois/nondex/instr/ClassVisitorShufflingAdder.java),
and the [support wiki](../NonDex.wiki/Supported-APIs.md).

I scanned 5,047 Java files under `src/test/java/` across shallow research copies
of Commons Lang, Commons IO, AssertJ, and Jimfs. These are source-file counts,
not numbers of independent tests, executions, or bugs; test helpers and duplicate
integration-test sources are included. Keyword searches are a discovery aid,
not type-resolved call analysis. Comments can match and static imports, reflection,
wrappers, or other formatting can escape the searches.

- [Source-revisions.json](Source-revisions.json) records every downloaded repo's
  exact revision and URL.
- [API-test-usage.csv](API-test-usage.csv) records matching files, lines, and
  occurrence counts for the searched API families.
- Research clones are in `search/sources/`, ignored by Git. They are not new
  project submodules.

The [iDoft repository](https://github.com/TestingResearchIllinois/idoft) was
searched as a known-flaky-test index. The
[FlakeFlagger project metadata](https://zenodo.org/records/5014076/files/Project_Info.csv?download=1)
guided selection of Jimfs and AssertJ. The
[Zenodo record](https://zenodo.org/records/5014076) contains project revisions,
test results, features, and execution archives; it is not an API-coverage list.
I inspected the record and project CSV, not the large execution archives.
The source scans use the revisions recorded in our manifest, not the historical
FlakeFlagger revisions. Commons IO was added as a focused NIO-client search.

## Candidate list

Counts below are matching test-source files in this sample. They establish local
usage evidence, not Java-wide prevalence or a guarantee of new failures.

| Priority | API or API family | Test usage found | Proposed permitted variation | Failure to look for / evidence status |
| --- | --- | --- | --- | --- |
| 1 | `Hashtable.keys()`; related `elements()` | 1 Commons Lang file, using both methods | Change enumeration order while preserving the key/value multiset and cursor behavior | A concrete fixed-list assertion in `StreamsTest.testOfEnumeration`; see below. Limited prevalence evidence, strong failure witness. |
| 2 | `Files.list(Path)` | 2 Commons IO files | Change encounter order of entries in a stable directory | A concrete cross-call first-entry assumption in `IOBinaryOperatorStreamTest.testReduce`; see below. |
| 3 | Views/iteration of `Map.of`, `Map.ofEntries`, `Map.copyOf` results | 34 AssertJ files for factory mentions | Permute whole mappings, preserving key/value association | Strong usage evidence; inspect ordered diagnostics, snapshots, and first-entry selection. Inspected examples often correctly ignore order. |
| 4 | Iteration of `Set.of`, `Set.copyOf` results | 10 AssertJ files | Permute elements without changing membership | Inspect conversion to lists/strings and positional assertions. No concrete vulnerable assertion established in the inspected examples. |
| 5 | `Files.newDirectoryStream` and `DirectoryStream.iterator()` | 1 Commons IO file and 4 Jimfs files for qualified factory calls; additional wrapper usage | Change sibling encounter order | Genuine coverage opportunity, but preserve streaming/resource semantics and provider-specific promises. Jimfs's ordered self-test is not counted as a new bug. |
| 6 | `Collectors.toList()` result mutability | 8 Commons Lang, 3 Commons IO, 10 AssertJ files | Return an unmodifiable result instead of a mutable result, preserving contents and order | Look for subsequent `add`, `sort`, `remove`, or concrete-type casts. Frequent in this sample, but no vulnerable use confirmed. |
| 7 | `Files.readAllLines(...)` result mutability | 1 Commons IO and 2 Jimfs files | Vary modifiability while preserving decoded lines and their order | Look for modifying the returned list. The inspected reverse-reader test copies lines into a separate stack and is a useful control. |
| 8 | `Locale.getAvailableLocales()` | 1 Commons Lang and 1 Commons IO file | Explore array ordering without changing locale membership | No documented order guarantee was found; weaker evidence than an explicit unordered clause. Indirect existing coverage needs runtime tracing. Current Commons Lang sorts the result. |
| 9 | `Class.getPermittedSubclasses()` | Manually traced from AssertJ's sealed-class tests through a reflective helper | Permute the returned subtype array | Actual usage exists, but inspected assertions compare membership. Retain as a template exercise; not the first discovery target. |

## Concrete candidate 1: Commons Lang / Hashtable.keys()

**Test:** `org.apache.commons.lang3.stream.StreamsTest.testOfEnumeration`
at Commons Lang commit `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8`.

The [test source, lines 234–247](https://github.com/apache/commons-lang/blob/d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8/src/test/java/org/apache/commons/lang3/stream/StreamsTest.java#L234)
puts two keys, `One` and `Two`, into a plain `Hashtable`. Its final non-empty
assertion compares the mapped enumeration to a fixed ordered list.

| Key enumeration | Mapped list | Consequence for that assertion |
| --- | --- | --- |
| One, Two | OneOne, TwoTwo | Matches the expected list |
| Two, One | TwoTwo, OneOne | Does not match the expected list |

The [Java 25 Hashtable contract](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Hashtable.html#keys())
requires an enumeration of keys and describes behavior under structural
modification, but supplies no insertion, lexical, hash, or other traversal-order
guarantee. This is an inference from the complete contract's absence of an
ordering promise, not an explicit quote saying that order is unspecified.
The [Enumeration contract](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Enumeration.html)
still requires a coherent sequence and the proper exhaustion behavior.

I traced the client adapter: `Streams.of(Enumeration)` uses an ordered
`EnumerationSpliterator`, whose traversal forwards `nextElement()` calls.
See [Streams.java](https://github.com/apache/commons-lang/blob/d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8/src/main/java/org/apache/commons/lang3/stream/Streams.java#L127),
including the factory around line 687. Therefore the adapter does not justify
the test's particular expected order; it preserves whichever sequence it receives.

**Coverage gap:** NonDex's special targets cover HashMap and other map iterators,
but not `Hashtable` or `Hashtable$Enumerator`. The
[OpenJDK 25 Hashtable source](https://github.com/openjdk/jdk/blob/jdk-25%2B36/src/java.base/share/classes/java/util/Hashtable.java#L261)
routes `keys()` and `elements()` to its own enumerator, not HashMap's iterator.
This provides stronger evidence than merely finding no wiki entry.

**Future perturbation design:** choose one ordering for an enumeration, then
advance through it without replacement. Preserve duplicates for value
enumerations, exhaustion exceptions, and synchronization expectations. Do not
shuffle a generic `Enumeration`: vector and other ordered sources must retain
their contracts. Start with a plain, unmodified Hashtable; do not generalize to
subclasses that supply additional guarantees. A complete shared-enumerator
extension must also preserve iterator removal and fail-fast behavior.

The count/contains assertions earlier in this same test should remain valid;
the ordered list assertion is the particular predicted failure. No baseline
or perturbed execution was performed.

## Concrete candidate 2: Commons IO / Files.list(Path)

**Test:** `org.apache.commons.io.function.IOBinaryOperatorStreamTest.testReduce`
at Commons IO commit `0c640aef74c65292ef313596f58c48b1b121e1e7`.

The [test source, lines 88–103](https://github.com/apache/commons-io/blob/0c640aef74c65292ef313596f58c48b1b121e1e7/src/test/java/org/apache/commons/io/function/IOBinaryOperatorStreamTest.java#L88)
opens two independent listings of the current directory. Each reduction keeps
its left operand's real path; the second result is compared with the first.
`REAL_PATH_BO`, declared around lines 44–45, has the same left-selecting behavior.

For a directory with at least two entries resolving to different real paths,
selecting `a` first in one listing and `b` first in the other makes the equality
assertion false. Merely reordering later entries would not expose this assumption.
A stable ordering per directory across the whole run would also miss this case:
the experiment must explore variation between the two independent listings.

The [Files.list documentation](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/file/Files.html#list(java.nio.file.Path))
defines a lazy, nonrecursive listing without promising sorted or repeatable order.
[DirectoryStream](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/file/DirectoryStream.html)
explicitly says its iterator has no specific element order. The
[OpenJDK 25 implementation](https://github.com/openjdk/jdk/blob/jdk-25%2B36/src/java.base/share/classes/java/nio/file/Files.java)
builds `Files.list` on a directory stream, linking that contract to this call path.

**Coverage gap:** neither `Files` nor the directory-stream implementations appear
in NonDex's target lists. Existing `java.io.File.list/listFiles` perturbations
are not equivalent to coverage of this NIO path.

**Future perturbation design:** retain each listing's entries, directory identity,
and path values while selecting a different encounter sequence. Do not change
the filesystem to manufacture the failure. Preserve laziness, close handling,
filter invocation semantics where applicable, and exception propagation.
Eagerly collecting every directory entry at API return time is not generally
equivalent to the original stream. Begin with stable, finite directories and
explicitly validate resource and read-ahead behavior before broadening support.

This is a source-level witness conditional on distinct entries and normal
execution of the test. Its baseline environment and a permitted perturbed run
remain to be checked. `FileSystemTest`'s membership-based listing checks are a
useful contrasting control.

## Broader-usage candidates: contracts and limits

### Immutable factory collections

[Set's unmodifiable-set section](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Set.html#unmodifiable)
and [Map's unmodifiable-map section](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Map.html#unmodifiable)
explicitly leave iteration order unspecified. Preserve unmodifiability, contents,
null/duplicate validation, and map associations. Do not substitute a mutable
LinkedHashMap or HashSet as the visible result merely to control traversal.

The [OpenJDK immutable-collections implementation](https://github.com/openjdk/jdk/blob/jdk-25%2B36/src/java.base/share/classes/java/util/ImmutableCollections.java)
uses its own set/map implementations and a JVM-wide salt for iteration order.
These are not NonDex's HashMap iterator targets. Intercept result iteration,
views, spliterators, and array conversions consistently; shuffling factory input
alone does not ensure a chosen output traversal order. Some `copyOf` paths can
still exercise supported code while constructing their result; that is not
control over subsequent immutable-result iteration.

Concrete usage controls include AssertJ's
[MapAssert_keys_Test](https://github.com/assertj/assertj/blob/11c9de396300b624a69955956b8a0cc9d2a37d93/assertj-core/src/test/java/org/assertj/core/api/map/MapAssert_keys_Test.java)
and corresponding `MapAssert_values_Test`, which use membership assertions.
`CollectionAssert_isUnmodifiable_Test` exercises multi-element `Set.of` results.
These establish usage and validation opportunities, not new order bugs.

### Mutability rather than order

[Collectors.toList](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/stream/Collectors.html#toList())
does not guarantee result mutability or concrete list type; it does preserve
encounter order. A result with identical contents but restricted mutation can
expose unsupported assumptions. Do not scramble ordered streams or alter all
ArrayLists globally. A collector-level change needs a valid finalization step,
compatible characteristics, and working sequential/parallel accumulation; an
unmodifiable accumulator would be an invalid shortcut.

[Files.readAllLines](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/nio/file/Files.html#readAllLines(java.nio.file.Path,java.nio.charset.Charset))
also leaves list modifiability unspecified. Preserve line contents, order,
decoding, and errors. The Commons IO reverse-reader test copies these lines into
a separate stack, so that use does not require a mutable returned list.

Both result-mutability families lack dedicated support in this NonDex checkout.
They offer different specification choices from the permutation model, but
their presence in tests alone does not identify a failure.

### Lower-confidence or constrained leads

[Locale.getAvailableLocales](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/util/Locale.html#getAvailableLocales())
specifies available membership but gives no array-order promise. Keep membership
and required locales unchanged; changing the default locale is a separate
environmental intervention. NonDex has no direct Locale target, but locale
provider internals can use supported collections. Therefore genuine additional
coverage needs version-specific tracing. Commons Lang's current
`LocaleUtilsTest.testAvailableLocaleList` sorts before comparing and its set test
compares membership; neither is an ordering-failure witness.

For [Class.getPermittedSubclasses](https://docs.oracle.com/en/java/javase/25/docs/api/java.base/java/lang/Class.html#getPermittedSubclasses()),
the prior [recommendation](NonDex-API-Recommendation.md) still documents the
explicit unordered array and local coverage gap. I now traced real usage from
AssertJ's `ClassAssert_hasPermittedSubclasses_Test` to
`AbstractClassAssert`'s reflective helper. Its inspected checks use membership,
so they do not supply the missing failure witness. This changes its priority
under the updated task.

## Exclusions that prevent misleading results

- HashMap/HashSet iteration, supported reflection methods, and `File.listFiles`
  are not counted as new gaps merely because a test has an ordering assertion.
- Arbitrary list shuffling is invalid for `List.of`, `Collectors.toList`, and
  `Files.readAllLines`; their contents have ordering constraints.
- Jimfs's `testSecureDirectoryStream` does compare an ordered directory list.
  However, its implementation intentionally uses a sorted snapshot, documented
  in `Directory.snapshot()` and used by `JimfsSecureDirectoryStream`. This is an
  implementation self-test, not a confirmed client portability bug. Perturbing
  the generic interface could invalidate a deliberate implementation property.
- Custom providers, collection subclasses, and explicitly supplied factories
  may impose stronger guarantees than the generic JDK interface. Respect those
  guarantees when selecting interceptions.
- For file-tree walks, preserve depth-first traversal, ancestor-before-child
  rules, visit callbacks, and link/depth controls. Reordering an entire flattened
  walk is not a valid way to explore unspecified sibling order.

## Novelty and next experiment

Neither fully qualified candidate test name matched an entry in iDoft's
`pr-data.csv` or `gr-data.csv` at the recorded revision. That narrow check does
not establish novelty: reports can use other names, revisions, repositories,
or datasets, and current source can differ from historical subjects.

I recommend starting with the Hashtable assertion as the smallest concrete
discovery experiment, then the independent-listing case for broader NIO coverage.
For expanding to frequently appearing test idioms, prioritize immutable map/set
results and collector-result mutability. The sample does not establish that
Hashtable itself is broadly prevalent; its priority comes from the concrete
assertion, not a frequency claim.

A future validation should show the unmodified target passing, identify the
precise intercepted API, show a legal alternate behavior causing the predicted
failure, record JDK/seed/configuration, and verify appropriate controls. Check
both baseline and perturbed source revisions for existing reports before
claiming a newly discovered flaky test. The local NonDex README advertises Java
8–21 support, so Java 25 documentation is not evidence that NonDex can run on 25.
Validate the chosen runtime's contract and implementation, initially on 17 or 21.

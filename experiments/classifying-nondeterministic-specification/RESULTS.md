# Classification pilot results: StreamsTest#testOfEnumeration

Recorded November 20, 2026 (America/Chicago).

## Preparation results

The unchanged Commons Lang target passed its fresh unpatched baseline. The existing compiler inventory processed all 636 conventional project source files, recording 92,282 calls: 92,280 resolved and two unresolved. All eight scanner batches reported zero compiler errors; the two unresolved records are outside the selected method.

The wrapper selected all 47 compiler-observed calls in `StreamsTest.java:234–248`, covering `testOfEnumeration` at Commons Lang revision `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8`. All 47 selected calls resolved and grouped into 21 APIs. Java 11 source documentation was collected for 15 groups; six project/JUnit groups lack documentation in this collector. No unavailable group was silently dropped.

The model's inventory-review role returned all 21 IDs exactly once, with no missing, invented, or duplicate groups. This checks processing of the supplied static inventory, not discovery of calls the compiler scanner missed.

## LLM outcome

**The raw model response identified an ordering candidate, but the existing pipeline did not complete an accepted contract review.** Its final status for `Hashtable.keys()` was `error: unverifiable variation quote`.

| Stage | Result |
| --- | --- |
| Fresh target baseline | Passed. |
| Full-project compiler inventory | Completed; 636 files and 92,282 calls. |
| Method-scoped API extraction | 47 calls, 21 groups. |
| JDK documentation preparation | 15 groups collected; six unavailable. |
| Model inventory review | All 21 IDs exactly once. |
| Contract extractor | Response passed structural and quotation checks; source-based review found an omission. |
| Variation analyst | Returned three proposals; an explicit quotation failed validation. |
| Adversarial critic | Not called because the earlier evidence gate failed. |
| Final queue statuses | One error, 14 not selected, six documentation unavailable. |

Three local-model requests completed: inventory review, extraction, and variation. All responses ended normally (`finish_reason: stop`); this was neither a timeout nor output-token truncation. The pipeline manifest's `complete: true` means queue processing ended, not that its contract review succeeded.

## Source-based assessment of the model output

The following assessment was written by the coding assistant after inspecting the source and original responses. It is separate from the local model output and is not independent human validation.

| Original proposal | Assessment |
| --- | --- |
| Make the enumeration fail-fast after structural modification | Reject: conflicts with the supplied class statement that these enumerations are not fail-fast and treats an undefined-result mutation scenario as a normal variation. |
| Preserve insertion order versus return keys in another order | A provisional ordering candidate matching the manual experiment's dimension. It still requires complete contract review and explicit stable-table preconditions. |
| Omit or change standard `Enumeration` methods | Reject: the returned object must satisfy the `Enumeration` interface. Missing interface documentation does not permit breaking that contract. |

The ordering proposal was marked `absence_inference` by the model, with an empty evidence quotation. It did not provide an explicit ordering freedom from the supplied documentation. Its reasoning that a hash table implies no ordering guarantee is insufficient on its own: concrete API contracts determine guarantees. For a bounded ordering perturbation, review the applicable contracts and require an unmodified table, every original key exactly once, and preserved enumeration behavior. The known [manual witness](../manual-perturbations/hashtable/README.md) independently demonstrates the test's sensitivity; it does not certify the model's other proposals or its reasoning.

The extractor listed whether the enumeration is fail-fast as an unknown, although the supplied Hashtable class Javadoc explicitly answers that. The variation response then proposed the contrary behavior. Its first explicit quotation also removed raw Javadoc `{@link ...}` markup. The validator permits whitespace normalization, but the altered text was not a matching source quotation, so the review stopped before the critic. The gate caught the evidence mismatch; it did not issue a completed semantic verdict on all proposals.

This pilot therefore shows successful input preparation and provisional recognition of the intended ordering dimension, alongside a failed staged review and invalid alternatives. It does **not** show reliable automatic classification or an approved perturbation. No existing reviewer prompts or gates were modified to make this run succeed.

## Saved evidence

- [Evidence manifest](evidence/run-1/evidence-manifest.json): hashes, source provenance, final statuses, and the omitted full-inventory digest.
- [Extracted target calls](evidence/run-1/test-calls.jsonl), [method text](evidence/run-1/target-method.java.txt), and [baseline XML](evidence/run-1/baseline-test.xml).
- [API queue](evidence/run-1/documentation/api-queue.jsonl) and [JDK documentation provenance](evidence/run-1/documentation/coverage.json).
- Exact requests and full responses: [inventory review](evidence/run-1/requests/01.json), [contract extraction](evidence/run-1/requests/02.json), and [variation proposal](evidence/run-1/requests/03.json).
- [Pipeline manifest](evidence/run-1/pipeline/manifest.json) and [review-run status](evidence/run-1/review-run.json). The manifest links the errored staged review and its completed-stage trace; copies are preserved under the evidence's `pipeline/reviews/` directory.
- [Separate assessment](evidence/run-1/assessment.json). Additional `Dictionary` and `Enumeration` sources under `assessment-context/` were inspected only after the run and were not model inputs.

The evidence also includes snapshots of the existing infrastructure sources and prompts, raw JDK comments, scanner diagnostics, and the fresh baseline log. The full project inventory stays under ignored `build/run-1/`; selected evidence preserves all calls from the target method. Exact request JSON makes clear which documentation the model actually received.

## Extracted method API groups

The known `Hashtable.keys()` group is the selected contract-review pilot. Listing the remaining groups is not a claim that their nondeterministic specifications have been assessed.

| API group | Calls | JDK documentation | Contract review |
| --- | --- | --- | --- |
| `java.lang.String.isEmpty()` | 2 | Collected | Not selected |
| `java.util.Arrays.<T>asList(T...)` | 1 | Collected | Not selected |
| `java.util.Hashtable.Hashtable()` | 2 | Collected | Not selected |
| `java.util.Hashtable.elements()` | 3 | Collected | Not selected |
| `java.util.Hashtable.keys()` | 4 | Collected | Error: quote validation |
| `java.util.Hashtable.put(K,V)` | 2 | Collected | Not selected |
| `java.util.List.contains(java.lang.Object)` | 2 | Collected | Not selected |
| `java.util.List.size()` | 1 | Collected | Not selected |
| `java.util.Optional.isPresent()` | 2 | Collected | Not selected |
| `java.util.stream.Collectors.<T>toList()` | 2 | Collected | Not selected |
| `java.util.stream.Stream.<R,A>collect(java.util.stream.Collector<? super T,A,R>)` | 2 | Collected | Not selected |
| `java.util.stream.Stream.<R>map(java.util.function.Function<? super T,? extends R>)` | 1 | Collected | Not selected |
| `java.util.stream.Stream.count()` | 3 | Collected | Not selected |
| `java.util.stream.Stream.filter(java.util.function.Predicate<? super T>)` | 2 | Collected | Not selected |
| `java.util.stream.Stream.findFirst()` | 2 | Collected | Not selected |
| `org.apache.commons.lang3.stream.Streams.<E>of(java.util.Enumeration<E>)` | 7 | Unavailable | Not selected |
| `org.junit.jupiter.api.Assertions.assertEquals(int,int)` | 1 | Unavailable | Not selected |
| `org.junit.jupiter.api.Assertions.assertEquals(java.lang.Object,java.lang.Object)` | 1 | Unavailable | Not selected |
| `org.junit.jupiter.api.Assertions.assertEquals(long,long)` | 3 | Unavailable | Not selected |
| `org.junit.jupiter.api.Assertions.assertFalse(boolean)` | 2 | Unavailable | Not selected |
| `org.junit.jupiter.api.Assertions.assertTrue(boolean)` | 2 | Unavailable | Not selected |

## Inputs and attribution

The run uses Temurin 11.0.33+10 and Maven 3.9.9, with JDK documentation extracted from that runtime's `lib/src.zip`. The model endpoint advertises `local-coder`, served by llama.cpp, with 30,532,122,624 parameters, Q4_K-M quantization, and a 16,384-token context. The server's model-list response is retained; it does not independently authenticate the model weights. The repository's configured model is described in [local-llm/README.md](../../local-llm/README.md).

The three contract roles use the existing `staged-v4` prompts, temperature zero, and a 1,400-token output cap per call. The separate inventory-review request uses the same model. The manual Hashtable reversal and its expected failure were not supplied as a scenario to the staged reviewer. The scanner's built-in hand-written Hashtable rule was not used as the model's classification.

This is a known-site reconstruction pilot. It does not measure held-out accuracy, classify every extracted API, establish a complete contract closure, or generate executable support. Compare the eventual model proposal with the [separate manual experiment](../manual-perturbations/hashtable/README.md); that experiment's success cannot validate a model's reasoning.


## Next work

Improve exact source-quotation adherence and extraction of class-level facts while preserving the evidence checks. Expand inherited and interface documentation supply, then repeat in a fresh output directory and compare original responses and error counts against reviewed controls. Review the ordering candidate independently before connecting it to an implementation. The 14 unselected documented API groups have not been assessed for permitted variability in this pilot.

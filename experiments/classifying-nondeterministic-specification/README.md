# Classifying nondeterministic specification

This experiment tests Aryan's existing `Agent/` infrastructure on the unchanged Commons Lang `StreamsTest#testOfEnumeration`. It inventories the project, isolates that method's compiler-observed calls, collects their Java documentation, and asks the existing staged LLM reviewer to analyze `Hashtable.keys()` for specification-permitted alternatives and preserved constraints.

The review target is deliberately selected as a known manual experiment. This is a reconstruction pilot, not a blind search for a new API, a held-out accuracy evaluation, or an automatically confirmed client dependency. The other extracted API groups remain visible in the queue, with their documentation and review statuses.

## Stages and boundaries

1. `Agent/run.py` runs a fresh unpatched target baseline and inventories the full project's conventional main/test source roots using `Agent/src/Inventory.java`.
2. The experiment wrapper selects records in the pinned source bounds of `testOfEnumeration`. It preserves all calls within the method, including constructors, references, project calls, and unresolved calls; selection does not depend on an expected classification.
3. `Agent/contracts_deep_dive.py` groups those calls and extracts raw class and same-name method Javadoc from the selected JDK's `lib/src.zip`. It retains source-archive and documentation hashes and leaves unavailable documentation explicit.
4. `Agent/pipeline.py` asks the model's inventory-review role to list every scoped API group, then uses `Agent/orchestrator.py` for the contract-extraction, variation-proposal, and adversarial-review roles on `Hashtable.keys()`. These are sequential requests to the same local model.
5. Record a separate source-based assessment of the actual model response. The coding assistant's assessment is not independent human validation. A model proposal and a matching quotation do not establish a correct contract interpretation or a valid implementation.

The wrapper calls the existing infrastructure; it does not replace its prompts, supply the manual reversal scenario, or feed the scanner's built-in Hashtable `findings.json` rule to the LLM. The staged reviewer sees documentation and an API signature, without the manual patch or its failure result. The list-review role sees the scoped API groups and sample call expressions. This run does not generate or execute a perturbation.

The method-bound selection is specific to the pinned source format. The scanner uses an approximate classpath assembled from the Maven cache and does not trace values across statements or methods. Documentation collection includes same-name overloads and does not automatically expand all inherited or linked contracts. These limits remain visible even if the model review completes.

## Reproduction

Use Python 3.11, a full Java 11 JDK with `lib/src.zip`, Maven 3.9.9, the pinned Commons Lang checkout, and a populated Maven cache. Start the repository's local model server separately as documented in [local-llm/README.md](../../local-llm/README.md). The verified endpoint for this pilot is `http://127.0.0.1:8080/v1/chat/completions`.

From the repository root, use a new output directory:

```sh
python3.11 experiments/classifying-nondeterministic-specification/run.py prepare \
  --project search/sources/commons-lang \
  --java-home /path/to/jdk-11 \
  --maven-repo /path/to/maven-repository \
  --maven /path/to/maven/bin/mvn \
  --output experiments/classifying-nondeterministic-specification/build/new-run

python3.11 experiments/classifying-nondeterministic-specification/run.py review \
  --output experiments/classifying-nondeterministic-specification/build/new-run \
  --endpoint http://127.0.0.1:8080/v1/chat/completions \
  --model local-coder --timeout 1800
```

Preparation requires the pinned revision with clean tracked source. It requires a fresh passing single-target Surefire report before collecting documentation. The baseline runs offline and clears inherited JVM/Maven options. Review preserves the exact request JSON before each request and the full response afterward, including failures. It refuses to overwrite an existing request directory; preserve interrupted evidence and use another output for a fresh attempt.

`build/` contains the full generated inventory and local run artifacts and is ignored. Selected shareable evidence is under `evidence/`; [RESULTS.md](RESULTS.md) records the live run and its separate source-based assessment. The model proposed ordering variability, but its staged review stopped at quotation validation before the critic. Absolute paths in saved evidence describe the original run and are not portable setup requirements.

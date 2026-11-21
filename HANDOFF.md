# Handoff: Java API contract and perturbation research

Last updated: November 20, 2026.

This is the operational status document: completed work, evidence, limitations, directory meanings, immediate next work, and reproduction. [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) contains the purpose, terminology, target workflow, design ideas, and general roadmap. [README.md](README.md) provides a short introduction and checkout/setup entry points.

## Latest work and immediate next step

- **Two manual order-dependency witnesses are established.** The scoped Hashtable reversal exposed the ordered assertion in unchanged Commons Lang `StreamsTest#testOfEnumeration`; the scoped Files.list first-pair swap exposed the cross-listing assertion in unchanged Commons IO `IOBinaryOperatorStreamTest#testReduce`. Both have recorded passing baselines, fixture controls, expected perturbed failures, and passing unpatched rechecks. The Hashtable perturbation results are historical records; the Files.list run has saved local evidence. Neither patch is LLM-generated or integrated into NonDex. Start with [manual perturbations](experiments/manual-perturbations/README.md).
- **Fresh stock NonDex subject runs did not flag either case.** On Java 11, the unchanged tests passed at JVM-verified seeds 933178, 974622, and 1016066. Commons Lang ran twice per seed through its Surefire configurations. The HashSet positive control passed cleanly and was flagged at all three seeds. Exact commands, source hashes, reports, counters, and the corrected seed invocation are in [NonDex test results](experiments/manual-perturbations/NONDEX-TEST-RESULTS.md). Passing these tests alone is not proof of absent API instrumentation; use the independent path analysis in the wiki.
- **The live classification pilot prepared inputs successfully but failed its staged review.** The existing infrastructure scanned 636 Commons Lang files and recorded 92,282 calls. The experiment then isolated only `testOfEnumeration` (47 calls, 21 API groups), collected JDK documentation for 15 groups, and ran contract review only on `Hashtable.keys()`. The model listed all 21 IDs and proposed ordering variability, fail-fast behavior, and omission/change of Enumeration methods. The ordering proposal matches the manual witness's behavioral dimension; the other two alternatives are invalid in the source-based assessment. Quotation validation stopped the review with `unverifiable variation quote` before the critic. Three model requests completed without timeout or token truncation. This is a provisional ordering proposal, not an accepted classification, independent human validation, or generated implementation. See [results and original responses](experiments/classifying-nondeterministic-specification/RESULTS.md).
- **NonDex coverage has one authoritative document:** [NonDex.wiki/SUPPORTED-APIS.md](NonDex.wiki/SUPPORTED-APIS.md). The pinned instrumenter's 15 target classes and 20 unique standard selectors were audited with 175 path probes across three seeds on Java 8 and 11, plus all 92 upstream tests on each JDK. A fresh Java 11 recheck also measured zero choices for both candidate API paths with an active HashSet control. Java 17/21, multi-root filesystems, and broader provider behavior were not freshly audited. Path-specific bypasses and correctness caveats remain in the wiki. `AGENTS.md` and the overview require maintaining this document when verified support or limitations change.
- **Experiments and documentation are organized for continuation.** Manual fixtures, their evidence, and the stock NonDex comparison now live under `experiments/manual-perturbations/`. The live pilot and reproducible wrapper live under `experiments/classifying-nondeterministic-specification/`. The registered adapter's fixture path and documentation links were updated; historical raw evidence retains its original bytes and absolute execution paths. The existing experiment and pipeline control tests passed after relocation; all 81 saved NonDex report hashes and 32 classification evidence hashes were checked. The overview owns design/roadmap, this handoff owns status, and [experiments/README.md](experiments/README.md) indexes the runs.
- **Immediate next work:** preserve the original failed classification run, improve exact raw-Javadoc quotation adherence and class-fact extraction, and supply missing inherited/interface contracts without weakening the evidence gates. Repeat in a fresh output directory with reviewed controls. Then evaluate supported-API reconstruction before connecting an LLM proposal to executable perturbation generation and NonDex integration. See the ordered [general roadmap](PROJECT_OVERVIEW.md#general-roadmap).

The November 19 prototype and Hashtable perturbation results below were recorded in Aryan Agarwal's commit `1c7fef2`; they have not all been rerun here. The current session did rerun the Commons Lang baseline/inventory, the two Apache cases through stock NonDex on Java 11, and the new classification pilot. These fresh runs do not reproduce the historical Java 21 Hashtable patch. Check live Git status for committed versus local work.

## Existing prototype and recorded results

- Commons Lang was inventoried at revision `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8`. The current classification pilot reproduced 92,282 compiler-observed calls across 636 files with a passing targeted baseline; two calls were unresolved, both outside the selected method. It is a best-effort static inventory, not complete runtime coverage. Most API groups have not been analyzed.
- The overall coordinator, `Agent/pipeline.py`, can run a baseline, build an inventory and documentation queue, ask the local model to review the list, and run staged contract analysis on selected API groups. It can optionally run the two-pass normative review and the one registered experiment. See [Agent/README.md](Agent/README.md) and [Agent/WORKFLOW.md](Agent/WORKFLOW.md) for commands and task boundaries.
- The two-pass prototype, `Agent/normative_review.py`, first extracts attributed normative statements from documentation chunks, then makes a separate model request to audit each statement and look for omissions. Both passes use the same model. Exact quotations and a clean structural audit do not establish correct interpretation or completeness. The optional coordinator gate can stop a flagged review; its extracted statements are not passed as verified facts to the subsequent staged reviewer.
- A manually reviewed, narrowly scoped Hashtable experiment demonstrated that the unchanged Commons Lang `StreamsTest#testOfEnumeration` depends on the order for a stable plain table with keys `One` and `Two`. The normal test and fixture controls passed; the targeted JDK patch reversed the enumeration and the assertion at `StreamsTest.java:246` failed, expecting `[OneOne, TwoTwo]` and receiving `[TwoTwo, OneOne]`. A fresh unpatched recheck also passed in the later recorded experiment. This is a scoped research witness, not a general-purpose Hashtable implementation or NonDex extension. Details and controls are in [experiments/manual-perturbations/hashtable/README.md](experiments/manual-perturbations/hashtable/README.md) and [search/EXPERIMENT-STATUS.md](search/EXPERIMENT-STATUS.md).
- Stock NonDex detected an existing deliberately order-dependent HashSet control. The current Java 11 Maven-plugin comparison independently confirmed that the two targeted Apache cases pass under stock NonDex while the HashSet control is flagged. The standalone `experiments/manual-perturbations/files-list/` fixture demonstrates a scoped order dependency in the Commons IO target without extending stock NonDex. Broader file-provider, concurrent-mutation, error-timing, and parallel behavior remain unvalidated.
- `Collectors.toList()` is a contract control: the result's mutability is unspecified, but the collector must preserve encounter order for an ordered stream. A collector returning a shuffled result for such a stream is invalid. No general `toList()` perturbation has been validated or executed here.
- Reliability is not established. In one nine-case development evaluation, only two classifications matched and five invalid scenarios were labeled candidates. A later guarded pilot matched two of three reviewed development controls, left one inconclusive, and did not run six others. These are development cases, not an independently curated held-out evaluation. See [Agent/evaluation/ITERATION-LOG.md](Agent/evaluation/ITERATION-LOG.md) and [Agent/LIVE-EVALUATION.md](Agent/LIVE-EVALUATION.md) for the exact runs and limitations.

## Remaining capability gaps

- Automatic, path-aware matching of inventoried methods against existing NonDex support.
- Reliable discovery of new permitted variations and complete applicable constraints from documentation.
- General LLM generation and behavioral validation of perturbation implementations and their instrumentation.
- Integration of accepted new support into NonDex with reproducible seeded execution alongside existing support.
- A demonstrated end-to-end run that discovers a previously uncovered API, generates and validates its support, and uses the extended tool without relying on the prewritten Hashtable fixture.
- A complete independent evaluation of accuracy, manual effort, false positives, cost, and added coverage; subsequent ChaosAPI integration.

## Repository directory guide

| Path | Meaning and role |
| --- | --- |
| `Agent/` | Research prototype for inventory, documentation preparation/resolution, LLM review, evaluation, and execution coordination. This is project-owned code, not an implemented general NonDex extension. Start with [Agent/README.md](Agent/README.md) and [Agent/WORKFLOW.md](Agent/WORKFLOW.md). |
| `Agent/src/` | Java compiler/documentation helpers used by the Python workflow. |
| `Agent/contracts/` | Small manually reviewed contract references, including Hashtable and collector controls; not a complete supported-API catalog. |
| `Agent/evaluation/` | Development cases, scoring/reporting helpers, and the [iteration record](Agent/evaluation/ITERATION-LOG.md). Classification of supplied scenarios is different from discovering and implementing new support. |
| `Agent/tests/` | Prototype tests, including mocked orchestration checks and some environment-dependent integration controls. Passing mocks does not establish LLM accuracy. |
| `Agent/results/` | Ignored generated inventories, documentation artifacts, model responses, and experiment logs. Mentioned historical results may not exist in a new clone. |
| `NonDex/` | Git submodule containing the existing tool being extended. Pinned at `f1f407ce3e026f597567e7d96ee08cb08875690f`. Its active instrumentation is under `nondex-instrumentation/`; historical source files in `nondex-core/` are not an authoritative support list. |
| `NonDex.wiki/` | Separate Git submodule for NonDex documentation. [SUPPORTED-APIS.md](NonDex.wiki/SUPPORTED-APIS.md) now contains the local audited support list, indirect paths, bypasses, and correctness caveats. Local edits do not imply changes were published upstream. |
| `NonDex.wiki/verification/` | Source-based coverage verifier, Java API probes, runtime manifests, and [coverage matrix](NonDex.wiki/verification/COVERAGE-MATRIX.md). This verifies stock-tool coverage on Java 8 and 11, not the project's LLM pipeline. |
| `experiments/` | Experiment index: [manual perturbations](experiments/manual-perturbations/README.md) and [nondeterministic-specification classification](experiments/classifying-nondeterministic-specification/README.md). |
| `experiments/classifying-nondeterministic-specification/` | Reproducible wrapper around the existing full-project inventory, method-scoped JDK documentation queue, and staged LLM review for `StreamsTest#testOfEnumeration`. Raw requests/responses and the source-based assessment are kept separate. |
| `experiments/manual-perturbations/hashtable/` | Standalone, manually scoped JDK bytecode patch and controls for the known Commons Lang test. Read its [README](experiments/manual-perturbations/hashtable/README.md). It is not integrated into stock NonDex. Generated `build/` files are ignored. |
| `experiments/manual-perturbations/files-list/` | Standalone scoped JDK patch for independent `Files.list(Path)` order in the unchanged Commons IO target. Includes a reproducible runner, lazy stream wrapper, controls, and selected evidence. It is not registered in `Agent/pipeline.py` or integrated into stock NonDex. Generated `build/` files are ignored. |
| `search/` | Exploratory API recommendations, test-usage evidence, source revision records, original [search task](search/SEARCH-TASK.md), and chronological experiment notes. Earlier notes can be superseded by later results. |
| `search/hashtable-witness.patch` | Earlier exploratory modification to the client test's supplied enumeration. Distinct from the later JDK patch that exercises the unchanged test. |
| `search/sources/` | Ignored external subject checkouts, such as Apache Commons projects. These are analysis inputs, not the project's own implementation. |
| `Literature/` | Reference papers and course checkpoint documents. Checkpoint PDFs describe work at their publication dates. Extracted text accompanies the reference material; treat these documents as historical sources. |
| `ChaosAPI/` | Git submodule containing the future target tool/reference implementation. General LLM-driven support generation for it has not been implemented here. |
| `local-llm/` | Scripts and documentation for local model setup and serving; `llama.cpp/` is a pinned submodule. Weights, runtime configuration, builds, and caches are ignored. See [local setup](local-llm/README.md). |

## Sharing evidence and local artifacts

Inspect live Git status before sharing work. The parent records the NonDex submodule at `f1f407ce3e026f597567e7d96ee08cb08875690f`. Submodule changes have their own history and, when shared, require the relevant submodule commit and parent pointer update; a parent-repository push alone does not transfer uncommitted nested files.

Several important local artifacts are explicitly ignored and will **not** accompany an ordinary push:

- `Agent/results/`: inventories, prepared documentation, model responses, manifests and experiment logs.
- `search/sources/`: cloned subject projects, including Commons Lang.
- `experiments/manual-perturbations/hashtable/build/`: generated fixture build products.
- `experiments/manual-perturbations/files-list/build/`: generated patches, isolated Commons IO archives, and complete run outputs; selected shareable evidence is kept under the experiment's `evidence/` directory.
- `experiments/manual-perturbations/nondex-runs/build/`: isolated subject/control builds and complete initial/final run outputs; selected final reports are saved under `nondex-runs/evidence/`.
- `experiments/classifying-nondeterministic-specification/build/`: full project inventory, baseline/build outputs, and live model-run artifacts; selected target calls, documentation, requests/responses, source snapshots, and the failed review are saved under `evidence/run-1/`.
- `local-llm/models/`, build products, caches, logs and configuration: model weights and local runtime state.

Selected shareable evidence now exists for the Files.list witness, the stock NonDex subject comparison, and the classification pilot. Include those experiment sources and evidence with their documentation when committing; the full classification inventory is intentionally omitted and its digest is recorded. Preserve raw evidence bytes when moving files, including historical paths.

The NonDex wiki audit is committed as `df3b723`: `Supported-APIs.md` is replaced by `SUPPORTED-APIS.md`, and `verification/` contains the audit sources and results. The parent records this submodule revision. That commit must also be available from the wiki remote for recipients to initialize the submodule; a parent push alone does not publish it. The parent documentation consolidations and experiment reorganization include intentional moves and superseded documents.

The prose records summarize prior runs, but a recipient cannot independently inspect ignored raw results from the push unless selected evidence is shared separately. If sharing results, review their size and contents, include the relevant input files, logs, manifests, hashes and model responses together, and avoid blindly adding generated subject builds or model weights. The source code and tests alone do not recreate the past observations. Use `git status --short`, `git status --ignored --short` on selected paths, and `git submodule status` to review what will be transferred.

## Environment and setup

The commands below reproduce the earlier `Agent/` and Hashtable work. The newer Files.list experiment has its own [setup and runner instructions](experiments/manual-perturbations/files-list/README.md), verified separately with Java 11 and Python 3.6 or later. Do not substitute those runtime requirements into the fingerprint-pinned Hashtable runner.

Use Python 3.11, a full JDK with `javac` and `lib/src.zip`, Maven, and the subject's dependencies. The recorded Hashtable experiment used Temurin JDK `21.0.13.1+2` and Maven `3.9.9`. The registered fixture checks exact JDK modules and ASM 9.9 fingerprints as well as the subject revision and fixture files, so another JDK build or a missing dependency will stop reproduction even if its version looks similar. Maven dependencies must be available locally for the offline commands below; obtain them through the recipient's normal Maven setup. The model server is needed for model review, but not for the mocked tests or direct registered experiment.

Initialize the repository's submodules as appropriate and create a separate subject checkout. For example, from the repository root:

```sh
git submodule update --init --recursive
mkdir -p search/sources
git clone https://github.com/apache/commons-lang.git search/sources/commons-lang
git -C search/sources/commons-lang checkout --detach d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8
```

The last command assumes this is a new checkout without local work. Export paths for the recipient's machine, replacing the placeholders:

```sh
export JAVA_HOME=/path/to/jdk-21
export HANDOFF_MAVEN=/path/to/maven/bin/mvn
export HANDOFF_MAVEN_REPO=/path/to/maven-repository
export PATH="$JAVA_HOME/bin:$PATH"
```

`local-llm/serve.sh` is the local launcher used in the original environment. It requires its own runtime and model setup; the ignored weights are not included in the repository. With that setup available, start it using `PORT=18080 local-llm/serve.sh` and check `curl -sS http://127.0.0.1:18080/health`. The prototype's default model is `local-coder` and its chat endpoint is `http://127.0.0.1:18080/v1/chat/completions`. Check `local-llm/` documentation and the script for machine-specific dependencies. The server responded successfully in the handoff author's environment; that does not establish that it is available on the recipient's machine. The current classification pilot used the existing server at `http://127.0.0.1:8080/v1/chat/completions`, model `local-coder`, and Temurin 11.0.33+10. Its wrapper defaults to port 8080; the older coordinator defaults to port 18080, so pass `--endpoint` explicitly when reusing that server. See the [pilot README](experiments/classifying-nondeterministic-specification/README.md) for its separate prepare/review commands.

## Reproduce the analysis

Run these from the repository root after warming the Maven cache and building the subject. The first command runs only the targeted test as its baseline; it does not establish that the full project test suite passes. Use fresh output paths for new runs. A baseline failure is recorded and does not automatically stop all later analysis, so inspect `baseline.log` and `summary.json` before drawing conclusions.

```sh
python3.11 Agent/run.py search/sources/commons-lang \
  --java-home "$JAVA_HOME" --maven-repo "$HANDOFF_MAVEN_REPO" \
  --output Agent/results/commons-lang \
  --baseline "$HANDOFF_MAVEN" -o -B \
  "-Dmaven.repo.local=$HANDOFF_MAVEN_REPO" \
  '-Dtest=StreamsTest#testOfEnumeration' test

python3.11 Agent/contracts_deep_dive.py \
  --inventory Agent/results/commons-lang/calls.jsonl \
  --java-home "$JAVA_HOME" --output Agent/results/contracts

python3.11 Agent/resolve_contracts.py \
  --queue Agent/results/contracts/api-queue.jsonl \
  --docs Agent/results/contracts/jdk-docs.jsonl \
  --coverage Agent/results/contracts/coverage.json \
  --output Agent/results/resolved-handoff.jsonl \
  --select 'java.util.Hashtable.keys()' \
  --select 'java.util.stream.Collectors.<T>toList()'
```

The inventory uses an approximate classpath and conventional source roots. Inspect `diagnostics.log`, unresolved calls and the source revision. Fresh documentation output records hashes; the resolver verifies the documentation artifact against the accompanying hash, which detects mismatches but is not independent authentication. It conservatively matches declarations by textual signature and may leave valid matches unresolved. It does not fully resolve inheritance, links, dependency documentation, runtime receivers or applicable contracts.

With the model server running, run the two passes for a selected API:

```sh
python3.11 Agent/normative_review.py \
  --resolved Agent/results/resolved-handoff.jsonl \
  --select 'java.util.Hashtable.keys()' \
  --output Agent/results/normative-hashtable.json
```

Inspect every extraction, quotation, condition, scope, audit, omission and error. `needs_manual_resolution` is an expected outcome when material is incomplete or flagged; `requires_human_review` does not mean the claims are correct. `--source-kind matched_method` makes a shorter but explicitly partial review. Chunk boundaries, the four-statement extraction cap, missing sources and same-model blind spots can hide requirements.

To run the overall coordinator against the prepared queue, including the optional two-pass gate:

```sh
python3.11 Agent/pipeline.py \
  --queue Agent/results/contracts/api-queue.jsonl \
  --output Agent/results/handoff-pipeline \
  --select 'java.util.Hashtable.keys()' --limit 1 \
  --normative-resolved Agent/results/resolved-handoff.jsonl \
  --normative-limit 1
```

The list-review stage still asks the model to process the entire queue in batches, even when `--select` restricts later contract reviews; this may take a long time. The compiler inventory remains the routing source, and model omissions do not remove inventoried groups. The subsequent extractor, variation analyst and adversarial reviewer produce proposals, not approved implementations. The experimental evidence-first scenario reviewer is separate from this coordinator.

## Reproduce the scoped perturbation

With the exact pinned subject, JDK, ASM and Maven dependencies available, run:

```sh
python3.11 Agent/experiment.py \
  --proposal hashtable-keys-two-key-reversal \
  --project search/sources/commons-lang \
  --java-home "$JAVA_HOME" --maven "$HANDOFF_MAVEN" \
  --maven-repo "$HANDOFF_MAVEN_REPO" \
  --output Agent/results/handoff-hashtable-experiment --timeout 900
```

Use a new output directory and a clean tracked subject checkout. The runner creates a clean archive, checks fingerprints, runs an unpatched baseline, fixture controls, the patched target and an unpatched recheck. It checks the fresh Surefire report and expected assertion. Read `result.json` and companion logs: an unrelated failure, missing test, failed control or baseline, timeout, or fingerprint mismatch cannot confirm the dependency. A passing test under a perturbation does not prove independence. `confirmed_scoped_order_dependency` applies only to this reviewed witness; it does not validate arbitrary generated perturbations. The same registered fixture can optionally be invoked after matching staged review through `pipeline.py --experiment`; see [Agent/README.md](Agent/README.md).

## Verification and next work

A lightweight set of mocked and local controls can be run without a model server:

```sh
for test in Agent/tests/test_normative_review.py Agent/tests/test_pipeline.py \
  Agent/tests/test_experiment.py Agent/tests/test_resolution.py \
  Agent/tests/test_orchestrator.py Agent/tests/test_review_cases_isolated.py \
  Agent/tests/test_reliability_report.py Agent/tests/test_merge_results.py \
  Agent/tests/test_isolated_review.py; do
  python3.11 "$test" || break
done
```

Some other integration tests, including `test_workflow.py` and `test_contracts.py`, contain paths configured for the original workspace and need an appropriate JDK and Maven setup. A passing mocked suite checks orchestration and gates, not model reliability or the validity of new perturbations.

Technical follow-up backlog (the ordered project roadmap is in `PROJECT_OVERVIEW.md`):

1. Commit the existing selected evidence bundles with their sources and docs, preserve failed as well as successful outcomes, and confirm setup on a second machine. Regenerate missing historical artifacts only as new, separately identified runs.
2. Improve documentation resolution for overloads, inherited and linked contracts, dependency APIs, receiver-specific behavior and project dataflow. Keep unresolved applicability visible; a matching quotation is not evidence that its interpretation follows.
3. Review the two normative passes against complete applicable contracts, including omissions, cross-chunk context, conditions and implementation notes. Develop independently reviewed positive, negative and inconclusive cases, then measure the entire fixed development set and a genuinely held-out set. Report missing cases and false positives; scenario classification does not measure discovery.
4. Trace candidate values to actual call sites and assertions. For each new API, independently review the contract and concrete use, implement a bounded adapter, verify its contract-preserving controls, and compare an unchanged subject's baseline, perturbed test and unpatched recheck. The Hashtable and Files.list witnesses provide manually scoped examples, not general generated support. Keep model proposals, human contract reviews, site candidates and experimentally confirmed findings separate.

See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) for the design and ordered roadmap, [Agent/WORKFLOW.md](Agent/WORKFLOW.md) for gates and [Agent/evaluation/ITERATION-LOG.md](Agent/evaluation/ITERATION-LOG.md) for the eight reliability iterations. Historical progress documents are chronological; later updates supersede earlier statements about blocked experiments.

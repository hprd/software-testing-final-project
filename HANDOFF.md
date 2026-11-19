# Handoff: Java API contract and perturbation research

This project investigates whether Java code or tests depend on API behavior that the specification does not guarantee. The intended workflow inventories calls, gathers applicable documentation, identifies permitted alternatives, traces uses in the subject project, and tests carefully reviewed perturbations. It is a research prototype: model suggestions are not verified contracts, a candidate is not a confirmed dependency, and the system does not establish that it has found every valid perturbation.

## Current state

- Commons Lang was inventoried at revision `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8`. The inventory contains 92,282 compiler-observed calls across 636 files in the recorded run, with a targeted test baseline. It is a best-effort static inventory, not complete runtime coverage. Most API groups have not been analyzed.
- The overall coordinator, `Agent/pipeline.py`, can run a baseline, build an inventory and documentation queue, ask the local model to review the list, and run staged contract analysis on selected API groups. It can optionally run the two-pass normative review and the one registered experiment. See [Agent/README.md](Agent/README.md) and [Agent/WORKFLOW.md](Agent/WORKFLOW.md) for commands and task boundaries.
- The two-pass prototype, `Agent/normative_review.py`, first extracts attributed normative statements from documentation chunks, then makes a separate model request to audit each statement and look for omissions. Both passes use the same model. Exact quotations and a clean structural audit do not establish correct interpretation or completeness. The optional coordinator gate can stop a flagged review; its extracted statements are not passed as verified facts to the subsequent staged reviewer.
- A manually reviewed, narrowly scoped Hashtable experiment demonstrated that the unchanged Commons Lang `StreamsTest#testOfEnumeration` depends on the order for a stable plain table with keys `One` and `Two`. The normal test and fixture controls passed; the targeted JDK patch reversed the enumeration and the assertion at `StreamsTest.java:246` failed, expecting `[OneOne, TwoTwo]` and receiving `[TwoTwo, OneOne]`. A fresh unpatched recheck also passed in the later recorded experiment. This is a scoped research witness, not a general-purpose Hashtable implementation or NonDex extension. Details and controls are in [experiments/hashtable/README.md](experiments/hashtable/README.md) and [search/experiment-status.md](search/experiment-status.md).
- Stock NonDex detected an existing deliberately order-dependent HashSet control. The two targeted Apache tests passed normally and under stock NonDex in the recorded runs. The separate Commons IO `Files.list()` candidate has no implemented, validated perturbation or demonstrated failure.
- `Collectors.toList()` is a contract control: the result's mutability is unspecified, but the collector must preserve encounter order for an ordered stream. A collector returning a shuffled result for such a stream is invalid. No general `toList()` perturbation has been validated or executed here.
- Reliability is not established. In one nine-case development evaluation, only two classifications matched and five invalid scenarios were labeled candidates. A later guarded pilot matched two of three reviewed development controls, left one inconclusive, and did not run six others. These are development cases, not an independently curated held-out evaluation. See [Agent/evaluation/iteration-log.md](Agent/evaluation/iteration-log.md) and [Agent/live-evaluation.md](Agent/live-evaluation.md) for the exact runs and limitations.

## What needs to be included in the push

`HANDOFF.md` and much of the research implementation and documentation were untracked when this handoff was written. Review and add the intended files before pushing; a push only transfers commits. The working tree also had a tracked `SEARCH-TASK.md` deletion and a dirty `NonDex` submodule; inspect them rather than assuming either is intentional. The parent records the NonDex submodule at `f1f407ce3e026f597567e7d96ee08cb08875690f`. Submodule working-tree changes require their own review and, if intended for sharing, their own commit and parent pointer update.

Several important local artifacts are explicitly ignored and will **not** accompany an ordinary push:

- `Agent/results/`: inventories, prepared documentation, model responses, manifests and experiment logs.
- `search/sources/`: cloned subject projects, including Commons Lang.
- `experiments/hashtable/build/`: generated fixture build products.
- `local-llm/models/`, build products, caches, logs and configuration: model weights and local runtime state.

The prose records summarize prior runs, but a recipient cannot independently inspect ignored raw results from the push unless selected evidence is shared separately. If sharing results, review their size and contents, include the relevant input files, logs, manifests, hashes and model responses together, and avoid blindly adding generated subject builds or model weights. The source code and tests alone do not recreate the past observations. Use `git status --short`, `git status --ignored --short` on selected paths, and `git submodule status` to review what will be transferred.

## Environment and setup

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

`local-llm/serve.sh` is the local launcher used in the original environment. It requires its own runtime and model setup; the ignored weights are not included in the repository. With that setup available, start it using `PORT=18080 local-llm/serve.sh` and check `curl -sS http://127.0.0.1:18080/health`. The prototype's default model is `local-coder` and its chat endpoint is `http://127.0.0.1:18080/v1/chat/completions`. Check `local-llm/` documentation and the script for machine-specific dependencies. The server responded successfully in the handoff author's environment; that does not establish that it is available on the recipient's machine.

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

Recommended next steps:

1. Preserve or regenerate a small, shareable evidence bundle with pinned sources, tool versions, complete raw model responses, manifests and experiment logs. Confirm setup on a second machine.
2. Improve documentation resolution for overloads, inherited and linked contracts, dependency APIs, receiver-specific behavior and project dataflow. Keep unresolved applicability visible; a matching quotation is not evidence that its interpretation follows.
3. Review the two normative passes against complete applicable contracts, including omissions, cross-chunk context, conditions and implementation notes. Develop independently reviewed positive, negative and inconclusive cases, then measure the entire fixed development set and a genuinely held-out set. Report missing cases and false positives; scenario classification does not measure discovery.
4. Trace candidate values to actual call sites and assertions. For each new API, independently review the contract and concrete use, implement a bounded adapter, verify its contract-preserving controls, and compare an unchanged subject's baseline, perturbed test and unpatched recheck. Keep model proposals, human contract reviews, site candidates and experimentally confirmed findings separate.

See [plan.txt](plan.txt) for the broader goal, [Agent/WORKFLOW.md](Agent/WORKFLOW.md) for gates and [Agent/evaluation/iteration-log.md](Agent/evaluation/iteration-log.md) for the eight reliability iterations. Historical progress documents are chronological; later updates supersede earlier statements about blocked experiments.

# Java API analysis prototype

This is the first narrow milestone, not a complete agent. It runs a user-supplied baseline command, inventories source-level method invocations, constructor calls and method references with javac, and applies one manually reviewed contract rule for `Hashtable.keys()`. It reports a direct fixed-list assertion as a candidate and leaves other uses inconclusive. It does not trace values across statements or methods, inspect arbitrary API contracts, use an LLM, retrieve documentation, or prove a dependency. Sorting and membership examples are deliberately left inconclusive, not certified safe.

Requirements: Python 3.8+, a JDK with `javac` (tested on 21), and a Maven cache containing the project's dependencies. Build the subject first. The prototype accepts any explicit baseline command, but scans only `src/main/java` and `src/test/java`. It includes JARs in the provided cache plus `target/classes` and `target/test-classes` as an approximate classpath. That can resolve the wrong library version; it is not a substitute for the actual build classpath. It does not scan dependencies, alternate source sets, generated code, or runtime calls. Diagnostics should be reviewed, particularly if the project uses a different JDK release or compilation configuration. Dynamic dispatch and reflection are not resolved to every runtime target. javac can add implicit constructor calls to the analyzed tree.

Example (the baseline command must be last):

```bash
cd /misc/scratch/aab5473/software-testing-final-project
python3.11 Agent/run.py search/sources/commons-lang \
  --java-home /misc/scratch/aab5473/testing-tools/temurin-jdk21 \
  --maven-repo /misc/scratch/aab5473/testing-tools/maven-repository \
  --output Agent/results/commons-lang \
  --baseline /misc/scratch/aab5473/testing-tools/apache-maven-3.9.9/bin/mvn \
  -o -B -Dmaven.repo.local=/misc/scratch/aab5473/testing-tools/maven-repository \
  '-Dtest=StreamsTest#testOfEnumeration' test
```

`summary.json` records revision, working-tree status, JDK, baseline command and exit code, scanned roots, counts and limitations. `baseline.log` contains the test output. `calls.jsonl` has one JSON object per compiler-observed call, including source, line, expression, compiler-resolved owner and signature when available, and containing statement. `diagnostics.log` records per-batch compiler errors (first ten details per batch) and process failures. `findings.json` contains the Hashtable call sites, supporting contract record and narrow classifications. Other APIs are inventoried but **not assessed**. `resolved` is the compiler's best-effort static resolution with the approximate classpath; it does not establish the runtime target.

The baseline above runs one targeted test, not the entire suite. The program returns nonzero if an inventory batch fails, but records rather than treats a failing baseline as a fatal error. Unresolved calls are explicitly marked. Output and compiled scanner files are ignored by Git. Run `python3.11 Agent/tests/test_workflow.py` for the small direct-assertion, sorting, membership and missing-type controls; its tool paths are currently configured for this workspace.

A first run against Commons Lang revision `d58c7ed8d4d3283ee5fbd01a866ce9a10ecf80a8` scanned 636 files and recorded 92,282 compiler-observed calls with no compiler errors in its batches. The targeted baseline passed. The rule flagged the direct assertion at `StreamsTest.java:246` as a candidate and reported three other `Hashtable.keys()` calls as inconclusive. This count is not the number of unique APIs or a claim that the project has been fully analyzed for nondeterministic assumptions.

A reproducible method-scoped live experiment using these inventory, documentation, and staged-review components is in [experiments/classifying-nondeterministic-specification](../experiments/classifying-nondeterministic-specification/README.md). The manual fixtures and their stock NonDex comparison runs are under [manual-perturbations](../experiments/manual-perturbations/README.md).

## Documentation and perturbation review queue

Run the contract-preparation stage after an inventory:

```bash
python3.11 Agent/contracts_deep_dive.py \
  --inventory Agent/results/commons-lang/calls.jsonl \
  --java-home /misc/scratch/aab5473/testing-tools/temurin-jdk21 \
  --output Agent/results/contracts
```

This groups all inventory entries by static owner, signature and call kind, counts uses, and extracts raw Javadoc from that JDK's `src.zip`. `api-queue.jsonl` records every group and up to five example sites. `jdk-docs.jsonl` records class and same-name method documentation; `coverage.json` records the JDK source archive hash and status counts. `pending_review` means evidence was collected, not that the API was analyzed or is perturbable. Project, third-party, unresolved, missing, synthetic and inherited members without a matching declaration remain `documentation_unavailable` and need separate investigation. Comments are not rendered Javadoc: `inheritDoc`, links, interface contracts and exact overload matching require further work.

To request a bounded, resumable set of LLM proposals from an already-running OpenAI-compatible endpoint, add for example:

```bash
--endpoint http://127.0.0.1:8080/v1/chat/completions --model local-coder --limit 10
```

Optionally use `--select 'java.util.Hashtable.keys()'` (repeatable). Each response is stored separately in `analyses/`. Evidence quotes must exactly match supplied raw documentation; malformed, unsupported or unquoted proposals are recorded as retryable errors. Matching a quote does **not** prove that a model interpreted the contract correctly or selected the right overload. All model proposals require human review and downstream validation; the model's analysis is not automatically substituted into Java code. Existing reviewed proposals are skipped; failed proposals are retried. IDs include the JDK source archive hash.

The manually reviewed references in `contracts/` cover Hashtable key ordering and Collector list mutability/order. They are not a complete catalogue. No method can guarantee enumeration of every specification-permitted behavior from documentation alone; the correct result may be insufficient evidence. The pipeline does not yet resolve exact inherited contracts, identify concrete receiver guarantees, analyze dependencies beyond JDK source, generate or validate perturbations, or perform project dataflow analysis. Do not treat the queue as a list of confirmed nondeterministic APIs or bugs.

Run `python3.11 Agent/tests/test_contracts.py` for grouping, missing evidence, invalid quotation rejection and retry behavior.

## Staged contract-review orchestrator

`orchestrator.py` implements three specialized LLM roles as separate, sequential calls to the configured model: a contract extractor, a variation analyst, and an adversarial reviewer. These are role-specific model requests orchestrated in code, not independently deployed models or autonomous processes. The orchestrator supplies the original Javadoc to each stage, checks response schemas, checks quoted evidence with whitespace normalization, requires the critic to address each proposal, and records completed stage responses on an error. Inferences from absent guarantees are explicitly marked and require review of missing inherited and overload contracts. No response is automatically considered contract-compliant, exhaustive, or ready for execution.

With the local server running, pilot the known Hashtable reference:

```bash
python3.11 Agent/orchestrator.py \
  --queue Agent/results/contracts/api-queue.jsonl \
  --output Agent/results/staged-reviews \
  --endpoint http://127.0.0.1:18080/v1/chat/completions \
  --model local-coder \
  --select 'java.util.Hashtable.keys()' --limit 1
```

This may make three model calls. Successful results are retained and skipped on rerun; errors are retried. Use `--force` to rerun a successful review. Review the JSON, including every role's response and unresolved questions, against the documentation and the manual reference before expanding to a larger batch. The pipeline does not fetch missing documents, decide the exact overload, expand inherited contracts, trace project dataflow, or produce and execute instrumentation. Run `python3.11 Agent/tests/test_orchestrator.py` for deterministic mocked-role checks.

## Overall coordinator

`pipeline.py` connects the baseline and compiler inventory in `run.py`, the JDK documentation queue, a model list-review stage, and the staged contract reviewer. For a fresh project run (the baseline command must be last):

```sh
python3.11 Agent/pipeline.py \
  --project search/sources/commons-lang \
  --java-home /misc/scratch/aab5473/testing-tools/temurin-jdk21 \
  --maven-repo /misc/scratch/aab5473/testing-tools/maven-repository \
  --output Agent/results/full-pipeline \
  --baseline /misc/scratch/aab5473/testing-tools/apache-maven-3.9.9/bin/mvn \
  -o -B -Dmaven.repo.local=/misc/scratch/aab5473/testing-tools/maven-repository \
  '-Dtest=StreamsTest#testOfEnumeration' test
```

Or reuse a prepared queue: `python3.11 Agent/pipeline.py --queue Agent/results/contracts/api-queue.jsonl --output Agent/results/full-pipeline --limit 3`. The model is asked to list every compiler-observed group in bounded batches; missing, invented and duplicate IDs are recorded in `list-review/`. The compiler inventory remains authoritative for routing: model omissions never silently exclude a group, and model additions do not become calls. The model sees grouped signatures and sample locations, not entire source files, and cannot discover calls missed by the scanner. The manifest keeps every group, including unresolved or unavailable documentation. `--limit` caps new contract reviews, `--select` can restrict them by owner/signature substring, and `--batch-size` controls list-review batch size. Without a limit the program attempts all eligible groups; this may take a very long time on the local single-slot model. Completed list batches and successful contract reviews are reused, while errors are retried. Fresh runs rerun the baseline and inventory; use `--queue` to resume without doing so.

Contract stages run once per owner/signature/call-kind group, not once per individual site. Their outputs are unvalidated proposals requiring human review. The manifest and list results are not findings and do not establish complete coverage, correct overload resolution, concrete runtime receiver contracts, or dataflow. A nonzero baseline is recorded by `run.py` and must be inspected; it does not automatically stop later analysis. Inspect `baseline.log`, compiler diagnostics, and all staged responses before interpreting results. Run `python3.11 Agent/tests/test_pipeline.py` for coordinator controls. The live pilot and manual assessments are in `LIVE-EVALUATION.md`.

The staged reviewer currently uses the `staged-v4` prompt and schema rules; its output directory identity includes that version. It asks for at most three alternatives and requires nonempty preserved constraints and critic reasons. These checks enforce response shape, not semantic validity. The 2026-11-19 live controls in `LIVE-EVALUATION.md` still expose missed guarantees, invented operations, and incorrect critic judgments; continue to review every proposal independently.

## Experimental isolated roles

`isolated_review.py` is a separate prototype; the overall coordinator still uses `orchestrator.py`. It requests facts from each class or same-name method passage separately, asks a second model call whether each claim is supported by its original passage, proposes alternatives using the source passages and only model-supported facts, and audits each alternative in a separate call with the original passages. The source and raw role responses are retained on completion; in the current version completed responses are also retained when a later stage errors. Run:

```sh
python3.11 Agent/isolated_review.py --queue Agent/results/contracts/api-queue.jsonl \
  --select 'java.util.Hashtable.keys()' --output Agent/results/isolated-hashtable.json --timeout 600
python3.11 Agent/tests/test_isolated_review.py
```

These are separate requests to the same model, not independently verified agents. Its entailment decisions can be wrong; `model_supported_facts` are provisional and are not manually reviewed facts. Each proposal audit still sees all supplied same-name overload passages because exact overload matching, linked and inherited contracts are unresolved. The source passages are also passed to the proposal stage, so excluded facts can still be inferred again. A successful schema and matching quote do not prove a contract interpretation. The approach needs live evaluation against the existing controls before it can replace the staged reviewer. The number of model requests grows with extracted facts and proposals and may be slow on the single-slot CPU server.

## Evidence resolution and scenario controls (experimental)

`resolve_contracts.py` builds attributed passages from a prepared queue and `jdk-docs.jsonl`. It conservatively selects a method comment only when the inventory signature and exactly one source declaration have textually matching method names and parameter types. Type spelling differences, missing documentation and ambiguous declarations remain unresolved; it does not perform generic erasure, type resolution or guess. Textual matching does not establish complete applicability. Class and selected method passages retain owner, source entry, declaration and a stable ID; the source archive digest is recorded. A small manually chosen list attaches relevant JDK class documentation as review leads, not as a complete contract closure. Links, inherited methods, package documentation, third-party dependencies, concrete receivers and dataflow remain unresolved. The existing queue and overall pipeline still use the earlier extraction; this is a separate pilot.

```sh
python3.11 Agent/resolve_contracts.py \
  --queue Agent/results/contracts/api-queue.jsonl \
  --docs Agent/results/contracts/jdk-docs.jsonl \
  --coverage Agent/results/contracts/coverage.json \
  --output Agent/results/resolved-pilot-v2.jsonl \
  --select 'java.util.Hashtable.keys()' \
  --select 'java.util.stream.Collectors.<T>toList()' \
  --select 'java.util.stream.Stream.findFirst()' \
  --select 'java.util.Arrays.<T>asList(T...)' \
  --select 'java.util.Collections.<T>singletonList(T)'
```

`evaluation/cases.json` contains manually reviewed scenario labels: candidate, invalid, or inconclusive. These are scenario-classification controls and **do not measure whether the model discovers a variation by itself**. `review_cases.py` sends one provided scenario and behavioral dimension per request. It requires evidence tied to an existing passage ID and exact quote, or an explicitly marked absence inference; unmatched methods are not sent to the model. The review has no automatic claim-entailment or implementation validation. Example:

```sh
python3.11 Agent/review_cases.py --resolved Agent/results/resolved-pilot-v2.jsonl \
  --output Agent/results/case-pilot.json \
  --select hashtable-stable-order --select tolist-ordered-shuffle --select findfirst-unordered
python3.11 Agent/evaluation/score.py --predictions Agent/results/case-pilot.json
python3.11 Agent/tests/test_resolution.py
```

The scorer reports the confusion matrix and missing cases; failed or unavailable documentation reviews are not counted as successful predictions. This small set was used in development and is not held out. The separate `evaluation/site-cases.json` records the known Hashtable site and scoped experiment with their distinct evidence statuses. No scenario result automatically becomes a call-site finding; tracing and new perturbation execution remain future work.

## Preliminary perturbation experiment

`experiment.py` runs one registered, manually scoped research fixture selected by `--proposal hashtable-keys-two-key-reversal`. Model prose and generated code are not executed. The runner checks the recorded Commons Lang revision, tracked source cleanliness, and fingerprints of the reviewed contract, fixture sources/build script, JDK modules and ASM. It creates a clean git archive of the project in a new output directory, runs the targeted test without perturbation, builds the fixture and runs its empty/singleton/membership/order/exhaustion controls, then reruns the identical test with the patch and performs a fresh unpatched recheck. Logs, commands, hashes, version, timings and the classification are stored in `result.json` and companion logs. The original project source and existing build outputs are not used as the execution directory.

```sh
python3.11 Agent/experiment.py --proposal hashtable-keys-two-key-reversal \
  --project search/sources/commons-lang \
  --java-home /misc/scratch/aab5473/testing-tools/temurin-jdk21 \
  --maven /misc/scratch/aab5473/testing-tools/apache-maven-3.9.9/bin/mvn \
  --maven-repo /misc/scratch/aab5473/testing-tools/maven-repository \
  --output Agent/results/my-hashtable-experiment --timeout 900
python3.11 Agent/tests/test_experiment.py
```

Use a new empty output directory for each run. `confirmed_scoped_order_dependency` requires the baseline, post-patch unperturbed recheck and controls to pass, the pinned subject and fixture to remain unchanged, and the exact reviewed `StreamsTest.java:246` ordered assertion to fail with the expected reversed values. An unrelated test failure, missing test execution, failed control, baseline failure, changed subject or unreviewed fixture is inconclusive. A passing perturbed test is `no_failure_observed`, not proof of independence. The exact fixture is a deterministic patch to the JDK's `Hashtable.keys()` behavior, not source replacement in arbitrary call sites or a general NonDex extension. Its evidence is limited to the stable two-key plain table; eager enumeration and subclass/concurrency behavior are not generally validated. Additional API proposals need their own reviewed adapters, controls, attribution and contract evidence before this runner can investigate them.

### Run the registered experiment from the overall coordinator

The overall coordinator can invoke the Hashtable experiment **after** the matching `java.util.Hashtable.keys()` method-invocation group has a completed staged documentation review. It does so only when explicitly requested with `--experiment`; it does not generate, select, or execute a model's proposed patch. The reviewed fixture and the model review are independent evidence: a completed model review is a workflow gate, not proof that the model found the variation or that the fixture is generally valid.

For an existing documentation queue, for example:

```sh
python3.11 Agent/pipeline.py \
  --queue Agent/results/contracts/api-queue.jsonl \
  --output Agent/results/overall-with-experiment \
  --select 'java.util.Hashtable.keys()' --limit 1 \
  --experiment hashtable-keys-two-key-reversal \
  --experiment-project search/sources/commons-lang \
  --java-home /misc/scratch/aab5473/testing-tools/temurin-jdk21 \
  --maven /misc/scratch/aab5473/testing-tools/apache-maven-3.9.9/bin/mvn \
  --maven-repo /misc/scratch/aab5473/testing-tools/maven-repository \
  --experiment-timeout 900
```

For a fresh project inventory, use the earlier `--project` example and add the `--experiment`, `--maven`, and `--experiment-timeout` options **before** `--baseline`; the project passed to `--project` is also the experiment subject unless `--experiment-project` is specified. With a full queue, model list review still processes all inventory groups in batches even when `--select` limits the contract reviews, so it can take substantial time. A previously completed matching review is reused only when its API ID, reviewer version and model match; an errored or unselected review does not open the experiment gate.

The final `manifest.json` has an `experiment` object with the adapter, relevant model-review path, fixture result path and status. `not_run_contract_review_unavailable` means there was no matching completed review; `not_run_output_exists` preserves existing experiment evidence and requires a new pipeline output directory for a new run. Other `inconclusive_*` statuses come from the fixture runner's baseline, identity, controls or attribution checks. A `confirmed_scoped_order_dependency` applies only to the known two-key plain-table fixture and assertion. Without `--experiment`, the coordinator does not run perturbations. Unregistered APIs or arbitrary model proposals cannot be executed by this adapter.

## Reliability iteration and task boundaries

[WORKFLOW.md](WORKFLOW.md) specifies the inputs, outputs, decision gates and unresolved limitations of each current task. `review_cases_isolated.py` is an experimental evidence-first scenario evaluator: quotation selection, a scenario judgment, and a blind same-model assessment are separate requests. It preserves their raw responses, validates selected quote/source IDs, and makes disagreement or absent evidence inconclusive. Same-model agreement and matching quotations are not proof. It is not yet integrated into the overall coordinator or used to authorize implementation. `Agent/tests/test_review_cases_isolated.py` covers its context and fail-closed gates.

The Hashtable experiment also snapshots the exact Surefire XML for baseline and perturbed runs and requires the patched report to be fresh and match the target test and reviewed failure. Timed-out test commands terminate their own process group and remain inconclusive. `Agent/tests/test_experiment.py` covers these report and timeout gates.

`evaluation/reliability_report.py` reports invalid scenarios labeled candidate, missing/errored cases, incorrect labels and whether a dataset is *declared* held out. For example:

```sh
python3.11 Agent/evaluation/reliability_report.py \
  --cases Agent/evaluation/cases.json --results Agent/results/iteration-baseline-merged.json
```

The `held_out` flag is dataset metadata, not proof of independent curation. Passing this scenario gate alone would not establish variation discovery, valid instrumentation or confirmed site dependencies. The development set has no held-out designation and the baseline failed; see `LIVE-EVALUATION.md` for outcomes. The optional experimental `review_cases_isolated.py --constraint-check` adds an independent same-model constraint question; it can only downgrade judgments to inconclusive and cannot approve execution.

Fresh documentation preparation records the generated `jdk-docs.jsonl` SHA-256 in `coverage.json`. The resolver verifies that hash when available and reads passage text from the documentation artifact rather than trusting queue-embedded comments. Legacy output without the hash is marked unverified, and a mismatch is rejected. This check detects artifact mismatch; it does not authenticate mutable local metadata or establish contract completeness.

The eight-iteration reliability record is in [evaluation/ITERATION-LOG.md](evaluation/ITERATION-LOG.md). The current guarded reviewer remains a separate experiment and has not passed the full development or independently curated held-out gate; it is not used to authorize perturbations. The original and clarified case files have different wording and must not be scored interchangeably. New reviewer outputs include the case-file hash, and the reliability report refuses to pass a run scored against different or unverified case text.

## Two-pass normative review

`normative_review.py` performs two model passes over the selected resolved source passages. The first extracts at most four source-quoted normative statements per chunk, identifying a proposed kind, claim, condition and scope. The second audits every statement in that chunk, separately assessing its wording and kind, and may report additional quoted omissions. A condition left blank means the model did not state one; it is not proof the requirement is unconditional. Every response, chunk offset, source ID, omission and error is recorded incrementally. Large passages are split, so a requirement spanning chunks may be missed. A completed pair of passes is **not** proof that the statements, audit or source coverage are correct. The same local model performs both passes, and exact quotes do not prove entailment.

Run one API against a resolved documentation file:

```sh
python3.11 Agent/normative_review.py \
  --resolved Agent/results/iteration-resolved-provenance.jsonl \
  --select 'java.util.Hashtable.keys()' \
  --output Agent/results/normative-example.json
python3.11 Agent/tests/test_normative_review.py
```

By default the reviewer processes all included class, matched-method and related-class passages. Add `--source-kind matched_method` for a shorter pilot; omitted passage IDs are recorded and this is **partial** documentation review. An unmatched method, failed extraction, invalid quote, incomplete audit or model error is reported as unresolved/incomplete. Reported omissions, unsupported or unclear audit verdicts, flagged source/condition issues, an extraction that flags possible additional statements, and a chunk that reaches the four-statement cap are marked `needs_manual_resolution` and block automatic handoff. Existing result files are not overwritten. Source archive provenance and unresolved linked, inherited, dependency and receiver contracts remain material limitations.

To run the two passes from the overall coordinator **before** the existing staged variation review, add:

```sh
--normative-resolved Agent/results/iteration-resolved-provenance.jsonl \
--normative-limit 1 --normative-source-kind matched_method
```

Place these options before `--baseline` if starting a fresh inventory. Without `--normative-source-kind`, all supplied passage types are processed. `normative-manifest.json` links the two-pass output for each selected group; a missing, failed or incomplete two-pass result blocks that group's later staged review. `--normative-limit` limits API groups and defaults to one. The later staged reviewer runs independently and does **not** consume or treat the audited statements as verified facts. An auditor saying `supported` is still a model judgment. The separately registered experiment remains a manually scoped fixture, not a generated implementation from these statements.

The normative reviewer includes conservative triage flags for an undefined-result passage categorized as a prohibition and for conditional wording with an empty conditions field. These flags can produce false alarms and cannot establish that unflagged statements are correct.

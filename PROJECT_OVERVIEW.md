# Project overview

## Purpose

The goal is to integrate LLMs into existing flaky-test tools so that adding support for a new Java API requires substantially less manual effort. **NonDex is the current target; ChaosAPI is future work.**

Today, supporting another API in NonDex involves understanding its contract, identifying legal alternative behaviors, designing a perturbation, writing instrumentation, and validating the result. This project aims to automate that workflow: identify APIs used by an input Java project and its tests, analyze APIs that NonDex does not already cover, generate specification-permitted perturbations and integration code, and run the existing tests with the expanded coverage.

Finding additional flaky tests is an important outcome. The main research contribution is **automating discovery and implementation of new API support**, including measuring how much human work is still required. The end goal goes beyond manually demonstrating that one test can fail or asking an LLM to explain an API contract.

This document describes the project design and general roadmap. Read [HANDOFF.md](HANDOFF.md) for current status, limitations, directory meanings, and reproduction instructions. The current milestone has established manual ordering witnesses and exercised the existing inventory/documentation/LLM pipeline on a known test. Reliable classification, generated perturbations, and integration remain unfinished; the handoff and [experiment index](experiments/README.md) record the outcomes and evidence.

## Terminology

- **Underdetermined specification / specification-permitted variability:** the contract allows multiple observable behaviors. An implementation can behave repeatably while still leaving other implementations free to behave differently. An unspecified iteration order is an example; random behavior is not required.
- **Permitted variation:** a behavior that may change under stated inputs and conditions without violating the applicable contract.
- **Preserved constraint:** a guarantee the perturbation must respect, including relationships across calls and object state, not just the contents of one return value.
- **ADINS assumption:** client or test code assumes a deterministic implementation of a nondeterministic specification. The API's freedom alone does not establish that a client makes an incorrect assumption.
- **New API support:** executable perturbation and interception/instrumentation integrated into the target tool. A model proposal or standalone JDK patch is an earlier milestone.

## Intended end-to-end workflow

**This is the target system, not a claim about current NonDex or the current prototype.** Generation and validation should happen before the affected test run, rather than requiring an LLM request on every API invocation.

1. **Accept a Java project and tests; inventory API calls.** The extended NonDex workflow identifies the Java methods used by the input code/tests, with declaring classes, signatures/overloads, and call sites. Program analysis supplies this inventory; the LLM interprets contracts. Record the scope and limitations of the inventory rather than claiming complete runtime coverage.

2. **Compare the inventory with existing NonDex support.** Retain the existing perturbation support and route uncovered APIs or uncovered execution paths to analysis. Coverage must match the particular method and path: an instrumented iterator does not imply that a stream or bulk method is covered. Use [NonDex.wiki/SUPPORTED-APIS.md](NonDex.wiki/SUPPORTED-APIS.md) as the authoritative coverage document and ground truth for its pinned tool and verified JDKs. Read it before selecting uncovered APIs. Maintain it whenever investigation confirms additional existing API/path support, new support is integrated and verified, or coverage limitations are discovered. Record the exact method/path, tool revision, JDK scope, supporting evidence, and caveats there; other documents should reference it rather than maintain parallel coverage lists. A standalone patch or model proposal is not integrated NonDex support.

3. **Load applicable Java API documentation.** Supply documentation for the subject's Java version and exact API, including relevant class, method, inherited, and linked contracts. Record missing evidence instead of assuming that a missing guarantee permits any change. Implementation source is useful context, but does not override the specification.

4. **Ask the LLM to identify specification-permitted variability.** For each uncovered API, determine whether the contract allows alternative observable behavior. Flag candidates and explain the permitted variations, their preconditions, and the supporting documentation. Also allow no identified opportunity or insufficient evidence; the goal does not assume that every API is perturbable.

5. **Record both freedoms and constraints.** Produce a structured description of what may vary and what must remain unchanged. For example, unspecified enumeration order may admit reordering while still requiring the correct elements. By contrast, `Collectors.toList()` must preserve the encounter order of an ordered stream; unspecified result mutability does not permit shuffling that stream's result.

6. **Provide the implementation and structured contract analysis to the LLM.** Have it design concrete alternative behaviors that exercise the permitted freedom while preserving the constraints. Generate the behavior-changing code and the interception/instrumentation needed to invoke it in NonDex. Designing a helper and integrating it into the tool are separate tasks.

7. **Validate the generated behavior and integration.** First establish that it builds and runs. Then check the preserved constraints and relevant input/state cases, and check that the interception actually affects the intended API path. Compilation alone does not demonstrate specification compliance. Reject or revise invalid candidates; establish an explicit validation policy and measure the human review it requires.

8. **Run existing tests through NonDex with expanded coverage.** Exercise both previously supported APIs and accepted new API support in the intended final system. Record which support is active, versions, seeds, configuration, and results so the run can be reproduced.

9. **Inspect failures and report outcomes.** Compare with an unperturbed baseline and investigate whether the failure comes from a valid variation exposing a client assumption, invalid generated behavior, instrumentation problems, or unrelated failures. Report inconclusive results and unsuccessful attempts as well as confirmed dependencies. A failure induced by a tool is not automatically a genuine flaky-test finding.

The future ChaosAPI extension would reuse suitable discovery and analysis stages but need its own behavior families, integration, and validation. Its environmental, timing, and random perturbations should not be assumed interchangeable with NonDex's unspecified-order models.

## Design considerations

Keep an evidence chain for each proposed addition:

**Target API → versioned documentation evidence → permitted variation and conditions → preserved constraints → implementation and instrumentation → validation results.**

- Define whether the inventory covers test code, production code, dependencies, reflection, generated code, and dynamic dispatch. Mark unresolved or ambiguous calls instead of guessing.
- Check arguments, repeated-call consistency, state, related APIs, exceptions, side effects, resource lifecycles, and explicit controls such as fixed seeds. One individually permitted return value does not establish a legal execution.
- Trace results into assertions and other uses when feasible to prioritize candidate dependencies. Separate an API's permitted freedom from an actual client assumption.
- A manageable starting family is returned arrays with explicitly unspecified order. Trusted instrumentation templates are an initial strategy to investigate; unrestricted generation can be a later comparison.
- Use independent human review to evaluate model interpretations and generated behavior during development. Measure that work as manual effort; model agreement alone is not independent validation.
- Cache accepted perturbation support with the applicable API, JDK, tool, and implementation versions. Cached model output alone is not validated support.
- Establish a reproducible unperturbed baseline, then preserve seeds, configurations, versions, logs, and exact test identities for perturbed runs. Investigate failures before calling them findings.

### Future ChaosAPI direction

A shared discovery and contract-analysis workflow can feed different execution backends. Candidate families include unspecified implementation choices, environmental conditions such as dates and locales, random outcomes, and timing or scheduling. These families overlap.

Environmental simulation must remain consistent across related APIs. Distinguish specification-permitted alternatives from stress transformations that deliberately change semantics; do not count every induced failure as a genuine flaky-test finding.

## General roadmap

This is the intended order of work. It builds on the existing `Agent/` documentation-to-LLM analysis and variation-proposal infrastructure; those stages do not need to be recreated. Executable perturbation generation and general NonDex integration are separate milestones. Completion, reliability limitations, and experimental results belong in [HANDOFF.md](HANDOFF.md), rather than being duplicated here.

1. **Establish manual reference experiments.** Use the scoped Hashtable and `java.nio.file.Files.list(Path)` witnesses as fixed controls for input preparation, ordering assumptions, and attribution. Preserve their baseline/control/perturbed/recheck evidence and compare the unchanged tests with stock NonDex. These references establish the manual stage; their current results and runtime limits belong in the handoff.
2. **Exercise the existing LLM classification infrastructure.** First pilot project API inventory, JDK documentation supply, and staged review on a known manually reviewed case such as `StreamsTest#testOfEnumeration`; keep the original model responses and a separately attributed assessment apart from the manual perturbation results. Treat failed quotation checks, omitted facts, unavailable documentation, and invalid alternatives as outcomes to address before calling classification reliable; preserve failures and rerun with fresh outputs. A coding-assistant assessment is not independent human validation. The reproducible pilot lives under `experiments/classifying-nondeterministic-specification/`, and the standalone fixtures live under `experiments/manual-perturbations/`. Then use the existing review infrastructure on APIs already supported by NonDex to identify permitted variations and constraints and suggest perturbations. Compare with existing NonDex support and independently reviewed contracts. Then investigate generating and validating executable implementations. Treat these as reconstruction controls, not new API discoveries.
3. **Try an LLM-proposed perturbation for an unsupported API.** Use the existing proposal stage, then develop the missing implementation and validation connection. Preserve the model's original proposal, human corrections, implementation provenance, validation controls, and test results. Distinguish a suggestion from executable, integrated support; running the prewritten Hashtable fixture does not demonstrate implementation of a model proposal.
4. **Build the automated input preparation around NonDex.** Accept a Java project/test selection, extract method calls and overloads, compare against actual tool coverage, and collect applicable documentation and implementation context. Reuse and improve the existing `Agent/` inventory and documentation infrastructure where appropriate.
5. **Connect the prepared inputs to the existing LLM invocation stages.** Extend the current coordinator into the NonDex workflow so that coverage filtering and input preparation lead to model analysis without manual per-API setup. Reuse the existing model requests for structured evidence, variations, constraints, and inconclusive outcomes; evaluate and improve their reliability.
6. **Automate implementation and validation.** Generate behavior and interception code, compile it, check invariants and applicability, and revise or reject invalid candidates. Preserve the evidence and human interventions.
7. **Integrate accepted support into NonDex.** Add reproducible seeded perturbations, reuse accepted additions, and exercise both existing and newly supported paths on the input tests.
8. **Evaluate the complete workflow.** Separate existing-API reconstruction from new coverage, freeze subject revisions and independently reviewed cases, report failures and exclusions, and measure automation quality and manual effort.
9. **Extend to ChaosAPI after the NonDex workflow is established.** Adapt the behavior models, interception, and validation to its environmental, random, and timing strategies.

## Evaluation

Measure discovery precision and recall against reviewed contracts; implementation compilation, integration, and behavioral validation success; human time and corrections per API; new supported coverage; known and new confirmed failures; invalid-perturbation false positives; runtime overhead; and LLM cost.

Withhold some existing supported APIs to measure support reconstruction. Keep those results separate from genuinely new coverage, and separate development controls from independently reviewed held-out evaluation. Scenario classification alone does not measure discovery or code generation.

## Research basis

Reference papers are in `Literature/`:

- *NonDex: A Tool for Detecting and Debugging Wrong Assumptions on Java API Specifications*: instrumentation, execution, detection, and debugging.
- *Detecting Assumptions on Deterministic Implementations of Non-deterministic Specifications*: specification variability and API models.
- *Detecting Flaky Tests by Controlling Nondeterministic API Behavior*: ChaosAPI wrappers, strategies, and false-positive limitations.

The automated workflow described here is the proposed project contribution, not a capability already supplied by those tools or papers.

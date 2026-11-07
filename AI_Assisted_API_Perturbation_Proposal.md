# AI-Assisted API Perturbation for NonDex and ChaosAPI

## Project goal

Build an extension that analyzes Java API usage, interprets API documentation with an LLM, and generates validated perturbation support for NonDex and potentially ChaosAPI. The extended tool then runs existing tests to expose unsupported assumptions about API behavior.

The contribution is **automating API discovery and perturbation support generation**, with reduced manual effort and potentially broader coverage. Finding new flaky tests is valuable, but is not the only measure of success.

## Refined terminology

The central question is:

> What aspects of this API's observable behavior can vary while still satisfying its documented contract?

- **Nondeterministic implementation:** an implementation can produce different behavior across executions or calls, depending on its inputs, state, or environment.
- **Underdetermined specification:** the contract permits multiple behaviors even when a particular implementation behaves consistently. This is the central NonDex case: a repeatable iteration order does not necessarily imply a guaranteed order.
- **Perturbation opportunity:** a documented source of permitted variation that the tool could exercise. Identifying one does not establish that the application uses the API incorrectly.
- **Unsupported assumption:** application or test logic depends on behavior the contract does not guarantee. Perturbed test execution investigates whether such a dependency matters.

Use “specification-permitted variability” as the umbrella term. Distinguish contract-preserving perturbations from stress transformations that intentionally change the original execution's semantics.

## Proposed system stages

| Stage | Work performed | Output |
| --- | --- | --- |
| 1. Identify API usage | Use program analysis to resolve called classes, methods, and overloads. Define whether analysis includes dependencies as well as project code. | Inventory of API calls and locations |
| 2. Retrieve contracts | Obtain documentation for the project's Java version, including relevant class and inherited contracts. | Versioned documentation evidence |
| 3. Identify permitted variation | Ask the LLM which observable behaviors may vary and why. Allow “insufficient evidence.” | Candidate APIs, variation categories, and supporting passages |
| 4. Specify constraints | Describe what may change and what must remain consistent across inputs, state, and related calls. | Structured perturbation specification |
| 5. Generate support | Generate behavior-changing code and the instrumentation needed to invoke it through the chosen tool. | Perturbation implementation and integration code |
| 6. Validate and cache | Check compilation, integration, and contract constraints using focused examples. Reject or revise invalid proposals and cache accepted additions. | Validated support tied to relevant versions |
| 7. Execute and inspect | Run baseline and perturbed tests, record configuration and failures, and investigate whether failures expose legitimate assumptions. | Reproducible failure reports and validation decisions |

Use ordinary program analysis to discover calls; use the LLM to interpret contracts and propose models. Generation should occur before the affected test execution, rather than requiring an LLM decision on every API invocation.

**Generating a perturbation and integrating it are separate tasks.** A helper that shuffles an array still needs an interception point. NonDex's instrumentation for returned arrays is simpler than its handling of lazy iterators.

## Incorporating both tools

A shared discovery and contract-analysis pipeline can feed different perturbation families and execution backends.

| Family | Analysis question | Example behavior to explore |
| --- | --- | --- |
| Underspecified choices | What does the contract leave unspecified? | Alternative collection or array orders |
| Environment-dependent behavior | What external conditions influence results? | Different dates or default locales |
| Random behavior | Which permitted outcomes are rarely exercised? | Boundary values within valid ranges |
| Timing and scheduling | Which execution conditions affect waiting or completion? | Delays or changes in perceived time |

NonDex naturally fits underspecified implementation choices. ChaosAPI offers additional strategies for environmental, random, and timing behavior. These categories overlap; they are not a strict partition between the tools.

For ChaosAPI, avoid the goal “change expected outputs.” Instead, identify **uncontrolled conditions and justified alternative behaviors**. Environmental simulation must remain consistent across related APIs. Changing one clock or date source while another observes incompatible values can create artificial failures.

## Validity requirements

Every generated proposal should record:

**Target API → documentation evidence → permitted variation → preserved constraints → implementation → validation examples.**

Validation must consider arguments, repeated-call consistency, object state, relationships between APIs, explicit controls such as fixed seeds, exceptions, and side effects. A permitted return value in isolation does not establish a valid execution.

Compilation and passing validation tests provide evidence, not proof of compliance. Human review remains important for evaluation. ChaosAPI itself reports false positives from inconsistent or unrealistic perturbations and acknowledges that its sleep-decrease strategy is not specification-compliant. Label such stress strategies separately; do not automatically count every induced failure as genuine flakiness.

## Initial scope and evaluation

Start with NonDex and one manageable API family, such as returned arrays with explicitly unspecified ordering. Have the LLM produce structured specifications and instantiate trusted instrumentation templates. Add one ChaosAPI family after the initial pipeline works; unrestricted code generation can be a later comparison.

Evaluate:

- **Discovery quality:** precision and recall against manually reviewed API contracts.
- **Generation quality:** proportion compiling, integrating, and satisfying behavioral validation.
- **Manual effort:** time and corrections needed per API.
- **Detection ability:** known failures reproduced and new confirmed failures found.
- **Coverage and cost:** additional APIs supported, analysis/runtime overhead, and LLM cost.
- **False positives:** failures caused by invalid perturbations or inconsistent simulated conditions.

Withhold some existing supported APIs and regenerate their support as a controlled evaluation. Keep these results separate from genuinely new API coverage; known targets measure reconstruction ability, not discovery novelty.

## Paper basis

- *NonDex: A Tool for Detecting and Debugging Wrong Assumptions on Java API Specifications*, §3: instrumentation, execution, detection, and debugging.
- *Detecting Assumptions on Deterministic Implementations of Non-deterministic Specifications*, §III: specification variability and API models.
- *Detecting Flaky Tests by Controlling Nondeterministic API Behavior*, §§3–4 and evaluation discussion: ChaosAPI's wrappers, strategies, and false-positive limitations.

The staged automation pipeline above is the proposed extension, not a capability already supplied by these papers.

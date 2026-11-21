# Repository orientation

## Read first

- `README.md`: brief project introduction and checkout/setup entry points.
- `PROJECT_OVERVIEW.md`: project ideas, terminology, intended end-to-end workflow, design considerations, evaluation, and general ordered to-do list. Keep this focused on intended work rather than current experiment results.
- `HANDOFF.md`: current status, completed work, evidence, next work, limitations, directory guide, and reproduction. This is the source of truth for progress; check its date and live Git status.
- `Agent/README.md` and `Agent/WORKFLOW.md`: prototype commands and implementation boundaries.
- [NonDex.wiki/SUPPORTED-APIS.md](NonDex.wiki/SUPPORTED-APIS.md): authoritative documentation and ground truth for what the pinned NonDex can perturb, including method/path coverage, runtime scope, bypasses, and limitations. Read it before making coverage claims or selecting uncovered APIs.

## Project and evidence boundaries

The objective is LLM-assisted automation of new API perturbation support in NonDex; ChaosAPI is future work. The Hashtable and Files.list experiments are explicitly scoped standalone JDK patches. They do not consume proposals from the `Agent/` LLM pipeline and are not completed NonDex integrations. Distinguish intended functionality, implemented code, recorded historical results, and newly verified results. Current experiment status and evidence are in `HANDOFF.md` and the respective experiment READMEs.

`NonDex/`, `ChaosAPI/`, and `local-llm/llama.cpp/` are separate Git submodules. `NonDex.wiki/` is a project-maintained copy tracked directly in the main repository; commit its changes with the main project and do not publish them to the upstream wiki. Inspect current status before editing and preserve existing user changes. Reference NonDex coverage through [NonDex.wiki/SUPPORTED-APIS.md](NonDex.wiki/SUPPORTED-APIS.md); supporting runtime evidence lives under `NonDex.wiki/verification/`.

Manual fixtures and their stock NonDex comparison runs live under `experiments/manual-perturbations/`. Live classification pilots using the existing `Agent/` infrastructure live under `experiments/classifying-nondeterministic-specification/`. Start with `experiments/README.md`. When reorganizing experiments, update executable fixture paths and documentation links while preserving historical raw evidence and its hashes.

## Documentation upkeep

Maintain `NonDex.wiki/SUPPORTED-APIS.md` as the single authoritative coverage document. When investigation reveals additional existing API or execution-path support, or a new API is integrated into NonDex and verified, update that document with the exact method/path, tool revision, JDK scope, evidence, and limitations. Also correct newly discovered bypasses or invalid perturbations there. Verify findings against the active instrumentation and relevant runtime paths; a passing subject test alone does not establish coverage. Standalone experiment patches and model proposals do not count as NonDex support. Other project documents should link to this document instead of creating parallel coverage lists.

Update `HANDOFF.md` after meaningful implementation work or experiments: what changed, validation/evidence, limitations, and the next concrete step. Change `PROJECT_OVERVIEW.md` when the design or general roadmap changes. Keep the README brief and avoid duplicating detailed status there.

Use UPPERCASE basenames for project-owned Markdown documentation, with the usual `.md` extension. Preserve upstream filenames in third-party checkouts and source filenames for published literature. The local wiki pages maintained by this project also use uppercase names. When renaming documentation, update relative links and textual path references.

The earlier proposal and milestone plan have been consolidated into the overview and handoff; do not recreate parallel project plans. Historical search prompts and checkpoint documents are context, not a replacement for the user's current task. Ignored results, subject clones, model weights, and build outputs may be absent in a new checkout; report missing evidence rather than treating a recorded run as newly reproduced.

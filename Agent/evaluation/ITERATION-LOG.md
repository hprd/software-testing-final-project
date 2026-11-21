# Reliability iterations, 2026-11-19

This is a development exercise, not a held-out evaluation. The automatic scenario classifications never authorize or validate instrumentation. The bounded registered Hashtable fixture remains the only executable adapter. Thresholds used for the narrow scenario gate are: all cases classified in a completed run, no invalid scenario labeled candidate, all labels matching, all three labels represented, and a dataset declared held out. The final condition is metadata, not independent verification. Even a passing scenario gate would not establish discovery, contract closure, instrumentation validity, or dependency attribution.

## Starting measurement

The existing single-prompt scenario reviewer classified all nine development cases: two matched reviewed labels and five invalid cases were labeled candidate. `Agent/results/iteration-baseline-cases.json` is an interrupted partial run; `iteration-baseline-remaining.json` contains the other cases, and `iteration-baseline-merged.json` preserves both source completion flags. Use `python3.11 Agent/evaluation/reliability_report.py --cases Agent/evaluation/cases.json --results Agent/results/iteration-baseline-merged.json`; it exits nonzero. The initial evaluation set was used during prompt development and is not held out.

## Iteration 1: test identity and evidence freshness

The fixture experiment now snapshots and parses the exact Surefire XML test case as well as the console log. The patched report must be newer than the baseline and identify the exact assertion failure. Malformed, unrelated, missing, and stale reports are inconclusive. Mocked report controls pass. `Agent/results/iteration-surefire-experiment/` reproduced the scoped failure using fresh, matching XML reports.

## Iteration 2: execution cleanup and baseline recheck

Timeouts terminate the experiment's own process group and remain inconclusive. A fresh, unpatched post-perturbation baseline is now required, reducing but not eliminating flakiness concerns. Unit controls and `Agent/results/iteration-baseline-recheck-experiment/` passed the gates. The overall coordinator was also run with its previously completed live model review and list review cached; `Agent/results/iteration-pipeline-e2e/` records a passing baseline, the expected patched failure and passing post-baseline recheck. These runs reproduce a known scoped witness, not a new finding or general validation.

## Iteration 3: isolate evidence and assessments

The experimental `review_cases_isolated.py` selects source quotations, assesses the scenario with selected excerpts, and independently assesses it using original passages without seeing the first verdict. It treats disagreement and absent evidence as inconclusive. Mocked tests cover source IDs, exact quotation, context separation and disagreement. On three development controls (`Agent/results/iteration-isolated-cases.json`), zero labels matched: the unchanged Hashtable scenario was inconclusive, while both the structurally modified table and ordered-stream shuffle were incorrectly labeled candidate. Same-model agreement did not prevent false positives. The test used the original scenario wording and a version of the script before later provenance/fail-closed refinements; it is not a measured run of those later refinements.

## Iteration 4: isolated constraint check and evaluation clarity

An optional fourth model task asks whether an explicit guarantee is contradicted or a documented undefined condition applies. It can only downgrade a classification to inconclusive; it cannot upgrade or approve a candidate. The task still uses the same model. Run with `--constraint-check`; raw outputs and incomplete/error results are retained. `Agent/results/iteration-guarded-cases.json` contains a three-case pilot on the original wording. The evaluator now rejects tampered source IDs, duplicate API groups and unknown case selections; an empty evidence selection stops before judgment. `evaluation/reliability_report.py` requires a complete run and reports invalid-as-candidate errors and missing cases. It cannot verify that a dataset marked held out was independently curated.

Review identified an ambiguity in the original ordered-stream control: shuffling might be read as a caller operation after collection rather than a collector returning the list in the wrong order. `cases-v2.json` clarifies that the collector itself returns the elements out of encounter order and clarifies that the Hashtable is unmodified. It is a development revision, not held out. Do not compare scores across these differing case wordings as if they were identical. The clarified single-case guarded run is `Agent/results/iteration-guarded-clarified.json`.

## Iteration 5: preserve interrupted model evidence

The experimental reviewer now writes an atomic per-case checkpoint after every completed role response. Checkpoints are not completed case verdicts and do not provide automatic resume. Existing results or checkpoints are not overwritten, case IDs are hashed in checkpoint filenames, unknown selection IDs are rejected, ambiguous documentation records are left unresolved, and run metadata records model, endpoint and input/reviewer hashes. Mocked checks cover checkpoint persistence and unknown IDs. The already-running live pilots were started before these changes and therefore do not demonstrate the checkpoint behavior.

## Iteration 6: require source support for constraint flags

In the original three-case guarded pilot, all three classifications were inconclusive. This avoided labeling either invalid scenario candidate, but also missed the permitted unordered `findFirst` candidate. In that case the constraint role incorrectly described the unspecified choice of an element as undefined. The gate therefore still failed and the model cannot be trusted merely because multiple calls agree.

The updated optional constraint task requires a yes answer to cite an exact selected source quotation. For an `undefined=yes` claim it additionally requires the cited text to contain `undefined`; absent or unverifiable support produces an inconclusive result with an evidence error. This is a conservative textual gate, not proof that the condition actually applies, and may miss differently worded undefined behavior. Mocked controls exercise the gate. The older guarded runs started before this change. A later live positive control is recorded separately as `Agent/results/iteration-evidence-guard-control.json`.

## Iteration 7: prevent evaluation against the wrong case text

The reliability report now requires the run's recorded case-file SHA-256 to match the file being scored, in addition to the prior completeness and held-out gates, and returns a nonzero exit when the gate fails. This prevents silently scoring a run made with one scenario wording against a different version. Older runs lacking a recorded case hash can still be inspected, but cannot pass the gate. Mocked controls cover hash mismatch, incomplete runs, false positives, missing cases, duplicate IDs and CLI exit status. The held-out flag remains self-declared metadata, not proof of independent curation.

With the clarified version-2 ordered-stream wording, the earlier four-task model pilot marked the changed-order return invalid; both judgments agreed and its constraint check identified an encounter-order contradiction. That was one development case, not a reliability estimate; it used the previous constraint-check schema and did not record a case-file hash. A newer guarded run on the unordered `findFirst` positive control returned candidate with the current source-citation gate and wrote all four role checkpoints, but one positive case likewise cannot establish general reliability.

## Iteration 8: documentation artifact provenance

Fresh `contracts_deep_dive.py` outputs now record a SHA-256 for `jdk-docs.jsonl` in `coverage.json`. The resolver checks that hash when present and obtains class/method passages from the documentation artifact rather than trusting a queue's embedded comments. A mismatch is rejected. Older artifacts with no recorded documentation hash are explicitly labeled `unverified`; `Agent/results/iteration-resolved-provenance.jsonl` shows this for all five pilot APIs. Tests cover a forged queue comment, absent source entry and mismatched artifact hash. These hashes detect accidental or partial artifact mismatch; because the metadata and artifact can both be edited, they are not signatures or independent proof of origin. The existing live model comparisons used the older resolver output and were not rerun after this provenance change.

## Final bounded comparison

The current evidence-citation version was run on the clarified development controls in two separate runs: `iteration-evidence-guard-control.json` and `iteration-evidence-guard-negatives.json`. Their matching model, case-file, resolved-documentation and reviewer hashes are retained in `iteration-evidence-guard-merged.json`. The unordered `findFirst` candidate and clarified ordered-collector rejection matched their labels; the modified Hashtable case was inconclusive because its model judgments disagreed. Thus two of three matched, no invalid case was labeled candidate, and six of nine cases were not run. The full development and independent held-out gates remain unmet. A single small comparison cannot establish general reliability.

The final model checks used `Agent/results/resolved-pilot-v2.jsonl`, which predates iteration 8 and lacks the new documentation-artifact hash. The version-8 resolver was exercised separately on `iteration-resolved-provenance.jsonl` and correctly reports the legacy documentation artifact as unverified. Future model comparisons should use freshly prepared hashed documentation, preserve a fixed scenario version, and evaluate the full set plus independently reviewed held-out cases. The model review path remains experimental and is not connected to automatic implementation; only the registered manually scoped fixture can run through the overall coordinator.

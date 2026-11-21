# Manual perturbation experiments

These experiments manually change a narrowly selected JDK API path and run an unchanged subject test. They are independent of the `Agent/` LLM proposal pipeline.

- [Hashtable](hashtable/README.md): reverse the key enumeration for the stable two-key table used by Commons Lang's `StreamsTest#testOfEnumeration`.
- [Files.list](files-list/README.md): swap the first two entries on the second listing in Commons IO's `IOBinaryOperatorStreamTest#testReduce`. See its [results](files-list/RESULTS.md).
- [Stock NonDex test results](NONDEX-TEST-RESULTS.md): run both unchanged cases through the NonDex Maven plugin, with a HashSet positive control and saved per-seed evidence under `nondex-runs/evidence/`.

The standalone patches exposed both known order dependencies; the pinned stock NonDex did not flag either case in the recorded runs. The authoritative coverage analysis is [NonDex.wiki/SUPPORTED-APIS.md](../../NonDex.wiki/SUPPORTED-APIS.md).

The folders, including ignored generated builds and selected evidence, were moved here from `experiments/`. Historical manifests, exact commands, logs, XML, counters, and hashes retain their original absolute paths and bytes; those paths describe the original executions. Use the current README commands for new outputs. A directory move does not constitute a fresh execution of those experiments.

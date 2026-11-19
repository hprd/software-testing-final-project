Background info:
The Literature folder contains paper's covering NonDex, ChaosAPI, and my project's checkpoint which has information about my project scope.

The project is to create an extension to NonDex and ChaosAPI, described in /misc/scratch/hkp423/software-testing-final-project/AI_Assisted_API_Perturbation_Proposal.md

You can look into the NonDex folder (that is the NonDex repo) and also NonDex.wiki folder (which has information about which APIs are currently supported by NonDex)

There are some repositories with many Java tests in them. You can reference the projects NonDex mentions and also visit:
https://github.com/apache/commons-lang under src/test/java
https://github.com/TestingResearchIllinois/idoft
https://zenodo.org/records/5014076




Task:
For now, I want to focus on extending NonDex. I don't want to build any code yet, I want to look in the java documentation to find one good example of an API that is not yet covered by NonDex which has a nondeterministic specification and can meaningfully be perturbed to expose a flaky test. https://docs.oracle.com/en/java/javase/25/docs/api/index.html

Please, search through the java documentation of APIs and find tests that are currently not supported by NonDex and have nondeterministic specification that can be perturbed and expose a flaky test. If you need to, create a "search" folder for any work you need to save / pulling any data, etc. Remember, the goal is to discover new flaky tests, so this API needs to be used commonly in tests. 

Once you identify APIs, include information about if they are typically in tests, how it would be perturbed, what behavior can be modified/exercised. Make a list of these sorts of APIs and related information.



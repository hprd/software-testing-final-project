# Software Testing Final Project

## Clone the project

Clone the repository with its submodules:

```bash
git clone --recurse-submodules https://github.com/hprd/software-testing-final-project.git
cd software-testing-final-project
```

This also downloads `ChaosAPI`, `NonDex`, `NonDex.wiki`, and
`local-llm/llama.cpp` at the commits recorded by this repository.
The NonDex wiki documentation is available locally in `NonDex.wiki/`.

If you already cloned the project and the submodule folders are empty, run
this from the project root:

```bash
git submodule update --init --recursive
```

## Pull project updates

From the project root:

```bash
git pull
git submodule update --init --recursive
```

The second command checks out each submodule at the commit recorded by the
updated parent repository. It does not automatically select the latest upstream
version.

## Keep the tested llama.cpp version

The project pins `local-llm/llama.cpp` to the tested commit
`972d2313bc0bf0a45f634f77d95c9fb03aeab12c`. A detached HEAD inside a submodule
is normal. Use the commands above to reproduce the recorded versions; avoid
`git submodule update --remote` or pulling inside the submodule unless you
intend to change its version.

To inspect the recorded submodule commits:

```bash
git submodule status --recursive
```

Model weights, compiled binaries, caches, logs, and local runtime settings are
ignored by Git and are not downloaded by cloning the project. See the
[local LLM setup instructions](local-llm/README.md) for model provenance,
build instructions, and usage.

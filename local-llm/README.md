# Local coding LLM

Runtime files for this installation live in this `local-llm` directory.
The runtime is built from the `llama.cpp/` Git submodule inside this directory,
with generated binaries in `build/`.
No packages, shell profiles, or system services were installed.

## Use

Run these examples from the `local-llm` directory. Launchers also work from
other directories when invoked using the appropriate relative path.

Start the server in one terminal:

```bash
./serve.sh
```

Use another terminal for chat:

```bash
./chat.sh
./chat.sh 'Write a Python binary search with tests'
./chat.sh --file path/to/source.py 'Find bugs and propose a patch'
```

Use `/quit` or Ctrl-D to exit interactive chat; Ctrl-C stops a foreground server.
The chat client sends file contents for analysis; it does not apply patches or run commands.
The server exposes an OpenAI-compatible API at `http://127.0.0.1:8080/v1`,
with model ID `local-coder` and no API key required. It binds only to localhost.
Browser UI assets are not bundled in this build; use the terminal client or API.

Default context is 16,384 tokens shared by the prompt and response, one request
slot, 16 generation threads and 32 prompt threads. Override with environment
variables, for example:

```bash
CONTEXT=32768 THREADS=16 THREADS_BATCH=32 PORT=8081 ./serve.sh
PORT=8081 ./chat.sh 'Explain memory ownership in C++'
```

After downloading, inference runs offline. Launchers redirect HOME, temporary
files and caches into this directory, without changing your login environment.

## Model and provenance

- Model: Qwen3-Coder-30B-A3B-Instruct, Apache-2.0, 30.5B parameters / 3.3B activated.
- Quantization: Q4_K_M, 17,988,419,552 bytes (16.75 GiB).
- Source: https://huggingface.co/ggml-org/Qwen3-Coder-30B-A3B-Instruct-GGUF
- Pinned revision: `0ca51122012fe4a20dc82988ee58780b008ce4e3`.
- SHA-256: `f6050b4da22869aa3fb9d94bb3314e9fc5a027d4741c1f97761c387d6b2b2335`.
- Model card: https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
- Runtime source commit: `972d2313bc0bf0a45f634f77d95c9fb03aeab12c`
  (clean checkout, detached at this commit).
- Original build used GCC toolset 14 and native x86 CPU instructions.
- Local copies: `MODEL-LICENSE`, `MODEL-CARD.md`, `model-metadata.json`.

The model fits comfortably in this machine's RAM. This is CPU inference; speed
depends on shared machine load and prompt length. Quantization trades some
accuracy for a smaller footprint. Review generated changes before using them.

## Validation

With the server running:

```bash
source ./env.sh
python3 ./verify.py
```

This checks analysis of a mutable-default Python bug and generates an interval
merging function, then checks four cases and preservation of its input. The
generated function runs with restricted builtins. Detailed responses and timing
are saved in `logs/verification.json`. This is a smoke test, not a coding benchmark.
Build output for the independent checkout is in `logs/build-local.log`.

Rebuilt on 2026-11-06 from the clean project-local source. The server loaded the
model and passed a health check and a short API inference check; details are in
`logs/local-checkout-smoke.json`. The previous build is retained in
`build.previous/` as a fallback.

Verified on 2026-11-05: publisher SHA-256 matched; both API coding checks passed.
Measured generation speed was 14.9 tokens/second on the interval-merging task,
with 92.5 prompt tokens/second. Installation occupies about 17 GiB.
These short-prompt measurements do not predict long repository-analysis latency.

To rebuild, keep the llama.cpp checkout at `./llama.cpp` and run
`bash ./build.sh` from this directory. The build uses `gcc` and `g++` from
`PATH`; set `CC` and `CXX` to select other compilers. To use GCC toolset 14,
enable it in your shell before building.

The source is registered as a submodule of `software-testing-final-project`,
using `https://github.com/ggml-org/llama.cpp` as its upstream remote. Initialize
it after cloning the project by running this from the project root:

```bash
git submodule update --init local-llm/llama.cpp
```

The parent repository records the tested source commit; this does not follow
the latest upstream version automatically. Model weights, builds, caches,
logs, and runtime settings are ignored by Git and must be obtained or generated
locally. Rebuilding and
running do not depend on the previous installation. The old checkout's optional
Lab 3 ARM accelerator changes are excluded; this installation uses native x86 CPU
inference. `llama.cpp.commit` records the pinned source revision.

Generated files in `build/` and historical logs may contain absolute paths
from the original installation. Regenerate the build directory with CMake
when moving the installation; these generated paths are not portable.

#!/usr/bin/env python3
"""Verify analysis and code generation through the actual local API."""
import ast
import json
from pathlib import Path
import urllib.request

root = Path(__file__).resolve().parent
def ask(prompt):
    request = urllib.request.Request(
        "http://127.0.0.1:8080/v1/chat/completions",
        data=json.dumps({"model": "local-coder", "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 700}).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=1800) as response:
        return json.load(response)

analysis = ask("Review this Python code. Identify the bug and give the fix concisely:\ndef add_item(x, items=[]):\n    items.append(x)\n    return items\n")
text = analysis["choices"][0]["message"]["content"]
assert "mutable" in text.lower() and "None" in text, text
generation = ask("Write only Python code, no markdown or explanation. Implement def merge_intervals(intervals): returning sorted merged overlapping or touching [start,end] intervals. Handle empty input. Do not mutate the input. No imports, no top-level calls.")
code = generation["choices"][0]["message"]["content"].strip()
if code.startswith("```"):
    code = code.split("\n", 1)[1].rsplit("```", 1)[0]
tree = ast.parse(code)
assert all(isinstance(node, ast.FunctionDef) for node in tree.body), code
assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)), code
namespace = {"__builtins__": {"sorted": sorted, "min": min, "max": max, "len": len, "range": range, "list": list, "tuple": tuple}}
exec(compile(tree, "<generated-code>", "exec"), namespace)
merge = namespace["merge_intervals"]
cases = [([], []), ([[1, 3], [2, 6], [8, 10], [10, 18]], [[1, 6], [8, 18]]), ([[5, 7], [1, 10], [2, 3]], [[1, 10]]), ([[-5, -2], [-2, 0], [3, 4]], [[-5, 0], [3, 4]])]
for value, expected in cases:
    original = [item[:] for item in value]
    assert merge(value) == expected, (value, expected)
    assert value == original, "Input mutated"
report = {"analysis": analysis, "generation": generation, "checks": "PASS: mutable-default bug analysis; generated interval merge passes four cases and input preservation"}
(root / "logs" / "verification.json").write_text(json.dumps(report, indent=2))
print(report["checks"])
print(json.dumps(generation.get("timings", {}), indent=2))

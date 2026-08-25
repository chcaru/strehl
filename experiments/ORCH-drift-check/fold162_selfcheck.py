"""Confirm fold162.py's literal blocks match what is actually in SYNTHESIS.md.

ORCH amended fact 1740 after the fold had already run. A fold script whose text
has drifted from the corpus is a false record of what was inserted, so this
checks the two are back in agreement rather than assuming it.
"""
import ast
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT = sys.argv[1] if len(sys.argv) > 1 else "experiments/ORCH-drift-check/fold162.py"
SYN = "docs/research/SYNTHESIS.md"

src = open(SCRIPT, encoding="utf-8").read()
syn = open(SYN, encoding="utf-8").read()

tree = ast.parse(src)
blocks = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
        name = node.targets[0].id
        if name in ("NEW_FACTS", "NEW_DISCIPLINES"):
            blocks[name] = node.value.value

if set(blocks) != {"NEW_FACTS", "NEW_DISCIPLINES"}:
    print(f"FAIL: could not find both blocks, got {sorted(blocks)}")
    sys.exit(1)

bad = []
for name, block in blocks.items():
    for line in block.strip().split("\n"):
        line = line.strip()
        if line and line not in syn:
            bad.append((name, line[:110]))

if bad:
    print(f"FAIL: {len(bad)} line(s) in the script are NOT in {SYN}:")
    for name, line in bad:
        print(f"  {name}: {line}...")
    sys.exit(1)

n_lines = sum(len([x for x in b.strip().split("\n") if x.strip()])
              for b in blocks.values())
print(f"OK: all {n_lines} fold162 block line(s) present verbatim in {SYN}")

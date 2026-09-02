"""Print the top qualifying segments from a census JSON, best first.

Used to choose a defensible ROI for the SFR reduction rather than the
hand-placed one the early half-width sweeps used.
"""
import json
import sys

d = json.load(open(sys.argv[1]))
print("top-level keys:", list(d)[:20] if isinstance(d, dict) else f"list[{len(d)}]")
if isinstance(d, dict):
    for k, v in d.items():
        if isinstance(v, list):
            print(f"  {k}: list[{len(v)}]", end="")
            if v and isinstance(v[0], dict):
                print("  item keys:", list(v[0]))
            else:
                print("  head:", v[:6])
        elif isinstance(v, dict):
            print(f"  {k}: dict keys {list(v)}")
        else:
            print(f"  {k}: {v!r}")

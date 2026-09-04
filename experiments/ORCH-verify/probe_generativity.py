"""Independent re-test of M168's exact finding against M164's repaired verifier.

M168's defect 3 was that verify.py printed `PASS: 8 checks` while
`np.random.default_rng` was forced to raise -- proving it re-read stored
ratios instead of regenerating. M164 claims the repaired verifier is
generative. A claim of generativity is testable by exactly one experiment:
block the RNG and require the verifier to FAIL.

If it still passes, the repair is cosmetic and the report string is still
over-trusted. This edits nothing in M164's lane.
"""
import runpy
import sys
import traceback

import numpy as np

CALLS = {"n": 0}
_real = np.random.default_rng


def poisoned(*a, **k):
    CALLS["n"] += 1
    raise RuntimeError("default_rng blocked by generativity probe")


np.random.default_rng = poisoned
if hasattr(np.random, "Generator"):
    pass

target = sys.argv[1]
sys.argv = [target]
print("=== generativity probe: np.random.default_rng forced to raise ===")
rc = 0
try:
    runpy.run_path(target, run_name="__main__")
except SystemExit as e:
    rc = e.code if isinstance(e.code, int) else 1
except BaseException:
    rc = 99
    traceback.print_exc()

print(f"=== default_rng call attempts: {CALLS['n']} ===")
print(f"=== exit under blocked RNG: {rc} ===")
if CALLS["n"] == 0:
    print("VERDICT: NOT GENERATIVE -- verifier never asked for an RNG at all.")
elif rc == 0:
    print("VERDICT: NOT GENERATIVE -- verifier passed despite a blocked RNG.")
else:
    print("VERDICT: GENERATIVE -- blocking the RNG broke the verifier, as it must.")

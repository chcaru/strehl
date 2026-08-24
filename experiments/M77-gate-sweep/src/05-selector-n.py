"""M77 Fact 17 -- does the SELECTOR's cost depend on bracket length?

One stack, one flat ROI, one binary. Only `--limit` changes, so the number of
frames the per-pixel argmax chooses among is the only varying quantity.

This arm is POST HOC. It was written after arm G0's control K3 failed on all
five stacks, to establish the mechanism of that failure rather than to assert it.
It is labelled post hoc everywhere it is reported and no pre-registered bar reads
it.
"""

import pathlib
import re
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m77  # noqa: E402

BIN = m77.EXP / "target-m77" / "release" / "strehl.exe"
STACK = "coffee-bean"
FLAT = "32,288,256,256"
DETAIL = "1184,416,256,256"
LIMITS = [10, 25, 52, 105]
HP = re.compile(r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)x\s+\[")
NE = re.compile(r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)%")


def main():
    m77.banner("M77 -- selector cost vs bracket length (POST HOC)")
    print(f"  binary {BIN}")
    print(f"  stack {STACK}  flat ROI {FLAT}  (fixed)   only --limit varies")
    print(f"\n  {'N':>5} {'gate':>5} {'n_eff':>9} {'HP RATIO':>10}")
    for n in LIMITS:
        p = subprocess.run(
            [str(BIN), "stack", str(pathlib.Path(m77.CORPUS) / STACK),
             "--limit", str(n), "--gate", "0", "4",
             "--flat-roi", FLAT, "--detail-roi", DETAIL],
            capture_output=True, text=True, encoding="utf-8", errors="replace")
        if p.returncode != 0:
            raise SystemExit(p.stderr[-2000:])
        neff, hp = {}, {}
        for line in p.stderr.splitlines():
            m = NE.match(line)
            if m and float(m.group(2)) in (0.0, 0.086063):
                neff[float(m.group(1))] = float(m.group(3))
            m = HP.match(line)
            if m:
                hp[float(m.group(1))] = float(m.group(3))
        for g in (0.0, 4.0):
            print(f"  {n:5d} {g:5g} {neff.get(g, float('nan')):9.3f} "
                  f"{hp.get(g, float('nan')):10.3f}")
    print("\n  gate 0 is pure selection (n_eff == 1 by construction at every N).")


if __name__ == "__main__":
    main()

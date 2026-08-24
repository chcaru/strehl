"""M69 control K2 -- is the Python field the shipped Rust field?

Every rho in this milestone is computed by M69's own Python operator. K2 decides
whether that operator may be called the shipped one. It runs the full winner
election and noise gate in Python over an entire real stack at full plane
resolution, and compares the resulting `mean n_eff` against the number the
shipped binary printed for itself on the same stack at the same gates.

Bar: within 0.2% at gates 0.5, 1, 2 and 4 on at least two real stacks.
Consequence if not met: every arm computed in Python is reported as an
emulation, not as the shipped operator.

Two streaming passes so no frame cube is ever held.
"""

import json
import pathlib
import re
import sys
import time

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

GATES = [0.5, 1.0, 2.0, 4.0]
ROW = re.compile(
    r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%\s+([0-9.]+)x\s*$",
    re.M,
)


def shipped(stack):
    txt = (m69.OUT / f"60-ladder-{stack}.log").read_text(encoding="utf-8", errors="replace")
    return {float(r[0]): float(r[2]) for r in ROW.findall(txt)}


def field(path, iso):
    return m69.regularised(m69.luma_of(path), iso).astype(np.float32)


def run(stack):
    files = m69.stack_files(stack)
    iso = m69.iso_of(files[0])
    t0 = time.time()
    best = None
    for p in files:
        f = field(p, iso)
        best = f if best is None else np.maximum(best, f)
    print(f"    pass one: {len(files)} frames, {time.time() - t0:.0f}s, plane {best.shape}",
          flush=True)
    counts = {g: np.zeros(best.shape, dtype=np.int32) for g in GATES}
    for p in files:
        f = field(p, iso)
        d = best - f
        for g in GATES:
            counts[g] += d <= np.float32(g * np.sqrt(2.0) * m69.FOCUS_NOISE_SD)
    print(f"    pass two done, {time.time() - t0:.0f}s total", flush=True)
    return {g: float(counts[g].mean()) for g in GATES}, iso, len(files)


def main():
    stacks = sys.argv[1:] or ["109MSDCF", "coffee-bubbles"]
    m69.banner("M69 control K2 -- Python field vs the shipped binary")
    m69.dump_constants()
    out = {}
    worst = 0.0
    for st in stacks:
        m69.banner(f"K2 -- {st}")
        got, iso, n = run(st)
        want = shipped(st)
        print(f"\n  {'gate':>6} {'tolerance':>11} {'shipped n_eff':>14} {'M69 n_eff':>11} {'rel':>9}")
        print("  " + "-" * 56)
        rows = {}
        for g in GATES:
            tol = g * np.sqrt(2.0) * m69.FOCUS_NOISE_SD
            rel = got[g] / want[g] - 1.0
            worst = max(worst, abs(rel))
            rows[str(g)] = {"tolerance": tol, "shipped": want[g], "m69": got[g], "rel": rel}
            print(f"  {g:>6.2f} {tol:>11.6f} {want[g]:>14.3f} {got[g]:>11.3f} {rel:>+8.3%}")
        out[st] = {"iso": iso, "frames": n, "rows": rows}
    met = worst <= 0.002
    print(f"\n  K2 worst |relative deviation| = {worst:.3%}   bar 0.2%"
          f"  ->  {'MET' if met else 'NOT MET'}")
    (m69.OUT / "15-k2.json").write_text(
        json.dumps({"stacks": out, "worst_rel": worst, "met": bool(met)}, indent=2),
        encoding="utf-8",
    )
    print("\n  wrote out/15-k2.json")


if __name__ == "__main__":
    main()

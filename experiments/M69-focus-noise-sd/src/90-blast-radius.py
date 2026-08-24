"""M69 arm A6 -- the blast radius, priced.

`Gate::tolerance() = T * sqrt(2) * FOCUS_NOISE_SD` is exactly linear in the
constant, so running the shipped binary at gate `T * rho` is arithmetically
identical to running at gate `T` with the constant multiplied by `rho`. Nothing
under `crates/` has to change to price any recalibration, and nothing here did.

Two things are priced:

1. The corpus-wide guard. `strehl stack <dir> --gate ...` was run by M69 on a
   17-rung ladder that brackets every rho this milestone measured, and the
   binary's own reported `mean n_eff` is read off, which is M62 Requirement G's
   observable and M64 section 2.4's table.

2. M62's certified sqrt(N) result. That is scored on a synthetic static burst
   with an acceptance harness M69 does not own, so it is re-priced by monotone
   interpolation of M62's OWN published gate ladder rather than re-measured.
"""

import json
import pathlib
import re
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

ROW = re.compile(
    r"^\s*([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)%\s+([0-9.]+)%\s+([0-9.]+)x\s*$",
    re.M,
)

# M62-sqrt-n.md, "`strehl merge`, the shipped estimator, gate ladder".
M62_GATES = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 16.0]
M62_R = [0.97682, 1.35937, 1.96845, 3.77637, 5.43162, 5.47768, 5.47768]
SQRT30 = np.sqrt(30.0)

N_BY_STACK = {
    "coffee-bubbles": 19, "109MSDCF": 22, "119MSDCF": 33, "113MSDCF": 63,
    "112MSDCF": 79, "foam": 100, "coffee-bean": 105,
}
GUARD = 0.95  # M62 Requirement G


def ladders():
    out = {}
    for p in sorted((m69.OUT).glob("60-ladder-*.log")):
        stack = p.name[len("60-ladder-") : -len(".log")]
        rows = ROW.findall(p.read_text(encoding="utf-8", errors="replace"))
        if not rows:
            print(f"  (skipping {stack}: no ladder rows -- run incomplete)")
            continue
        g = np.array([float(r[0]) for r in rows])
        ne = np.array([float(r[2]) for r in rows])
        o = np.argsort(g)
        out[stack] = (g[o], ne[o])
    return out


def n_eff_at(g, ne, gate):
    f = PchipInterpolator(np.log(g), ne, extrapolate=True)
    return float(f(np.log(gate)))


def main():
    m69.banner("M69 arm A6 -- blast radius")
    m69.dump_constants()
    lad = ladders()
    rho = json.loads((m69.OUT / "80-corpus-rho.json").read_text(encoding="utf-8"))

    m69.banner("A6.1 -- corpus guard: mean n_eff and n_eff/N at gate 4 and gate 4*rho")
    print(f"  {'stack':<16} {'N':>4} {'rho_true':>9} {'n_eff@4':>9} {'n_eff/N':>8}"
          f" {'n_eff@4rho':>11} {'n_eff/N':>8} {'change':>8}")
    print("  " + "-" * 80)
    rows = {}
    for stack, (g, ne) in lad.items():
        n = N_BY_STACK.get(stack)
        r = rho.get(stack, {}).get("rho_true")
        if n is None or r is None:
            continue
        a = n_eff_at(g, ne, 4.0)
        b = n_eff_at(g, ne, 4.0 * r)
        rows[stack] = {"N": n, "rho": r, "n_eff_4": a, "n_eff_4rho": b,
                       "ratio_4": a / n, "ratio_4rho": b / n}
        print(f"  {stack:<16} {n:>4} {r:>9.4f} {a:>9.3f} {a / n:>8.5f}"
              f" {b:>11.3f} {b / n:>8.5f} {b / a - 1:>+7.2%}")
    w0 = max(v["ratio_4"] for v in rows.values())
    w1 = max(v["ratio_4rho"] for v in rows.values())
    s0 = w0 / min(v["ratio_4"] for v in rows.values())
    s1 = w1 / min(v["ratio_4rho"] for v in rows.values())
    print(f"\n  worst n_eff/N  gate 4: {w0:.5f} (margin {GUARD / w0:.2f}x to the 0.95 guard)"
          f"   gate 4*rho: {w1:.5f} (margin {GUARD / w1:.2f}x)")
    print(f"  corpus spread of n_eff/N   gate 4: {s0:.2f}x   gate 4*rho: {s1:.2f}x")

    m69.banner("A6.2 -- corpus guard under a uniform recalibration")
    print(f"  {'rho':>8} {'gate':>8} " + " ".join(f"{s[:9]:>9}" for s in rows) + f" {'worst n/N':>10}")
    print("  " + "-" * (18 + 10 * len(rows) + 11))
    uni = {}
    for r in (0.28, 0.50, 0.75, 0.8380, 0.8614, 0.9285, 0.9481, 1.0, 1.0147, 1.0176, 1.0985, 1.1009, 1.1386, 1.1921, 1.30):
        vals = {}
        for stack, (g, ne) in lad.items():
            if stack not in rows:
                continue
            vals[stack] = n_eff_at(g, ne, 4.0 * r)
        worst = max(vals[s] / rows[s]["N"] for s in vals)
        uni[r] = {"gate": 4.0 * r, "n_eff": vals, "worst_ratio": worst}
        print(f"  {r:>8.4f} {4.0 * r:>8.4f} "
              + " ".join(f"{vals[s]:>9.3f}" for s in rows) + f" {worst:>10.5f}")

    m69.banner("A6.3 -- M62's certified sqrt(N) result, re-priced")
    print("  Interpolated from M62's own published ladder (M62-sqrt-n.md), monotone")
    print(f"  PCHIP in log gate. sqrt(30) = {SQRT30:.5f}; certified value 5.43162 at gate 4.\n")
    f = PchipInterpolator(np.log(np.array(M62_GATES[1:])), np.array(M62_R[1:]))
    print(f"  {'rho':>8} {'gate':>8} {'R':>9} {'vs sqrt(30)':>12} {'vs certified':>13}")
    print("  " + "-" * 54)
    m62 = {}
    for r in (0.28, 0.50, 0.75, 0.8380, 0.8614, 0.9285, 0.9481, 1.0, 1.0147, 1.0176, 1.0985, 1.1009, 1.1386, 1.1921, 1.30):
        R = float(f(np.log(4.0 * r)))
        m62[r] = {"gate": 4.0 * r, "R": R, "vs_sqrt30": R / SQRT30 - 1.0,
                  "vs_certified": R / 5.43162 - 1.0}
        print(f"  {r:>8.4f} {4.0 * r:>8.4f} {R:>9.5f} {R / SQRT30 - 1:>+11.3%}"
              f" {R / 5.43162 - 1:>+12.3%}")
    chk = float(f(np.log(4.0)))
    print(f"\n  interpolator check at gate 4.0: {chk:.5f} vs published 5.43162"
          f"  ({chk / 5.43162 - 1:+.4%})")

    m69.banner("A6.4 -- what a PER-PIXEL sigma_F would do, bounded by the ladder")
    print("  A uniform rescale is priced exactly by the linear-gate identity. A")
    print("  per-pixel sigma_F is not a uniform rescale, and this arm cannot price")
    print("  it -- doing that needs a merge whose tolerance varies per pixel, which")
    print("  is a change under crates/ and outside M69's brief. What CAN be bounded")
    print("  is the range: run the ladder at 4*p05 and 4*p95 of each stack's own")
    print("  per-pixel rho distribution and read how far n_eff travels.\n")
    print(f"  {'stack':<16} {'p05':>7} {'p95':>7} {'n_eff@4p05':>11} {'n_eff@4':>9}"
          f" {'n_eff@4p95':>11} {'swing':>8}")
    print("  " + "-" * 74)
    pp = {}
    for stack, (g, ne) in lad.items():
        if stack not in rows:
            continue
        lo = rho[stack]["p05"]
        hi = rho[stack]["p95"]
        a = n_eff_at(g, ne, 4.0 * lo)
        c = n_eff_at(g, ne, 4.0 * hi)
        b = rows[stack]["n_eff_4"]
        pp[stack] = {"p05": lo, "p95": hi, "n_eff_lo": a, "n_eff_hi": c, "swing": c / a}
        print(f"  {stack:<16} {lo:>7.4f} {hi:>7.4f} {a:>11.3f} {b:>9.3f} {c:>11.3f}"
              f" {c / a:>7.2f}x")

    (m69.OUT / "90-blast.json").write_text(
        json.dumps({"per_stack": rows, "uniform": {str(k): v for k, v in uni.items()},
                    "m62": {str(k): v for k, v in m62.items()},
                    "per_pixel_bound": pp}, indent=2),
        encoding="utf-8",
    )
    print("\n  wrote out/90-blast.json")


if __name__ == "__main__":
    main()


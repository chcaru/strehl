"""M87 / 114 -- is the co-movement PERIODIC in the quantum? Registered test.

113 refuted my own rank framing (T1: 0/2000 mismatches -- medians commute
with the quantiser, so a median's error is value-determined) and then FAILED
its own T3: I predicted co-movement would DECAY with value separation, and it
did not. It went +0.7957 at 0.02D, fell to -0.4982 at 0.50D, and returned to
+0.8205, +0.7669, +0.8117, +0.8194 at 1D, 2D, 4D, 8D.

That is not decay and it is not noise. It is the signature of a sawtooth:
e(x) = q(x) - x has period Delta, so two populations separated by an INTEGER
number of quanta sit at the same phase and co-move, while a HALF-integer
separation puts them in antiphase.

I noticed that pattern in data I had already seen, so it is a hypothesis and
not yet a result. This script registers it and tests it on a grid chosen to
discriminate periodicity from every alternative I can think of.

REGISTERED BEFORE ANY NUMBER EXISTS
  T5  antiphase repeats: rho at 1.5D is negative (< -0.20), like 0.5D.
      A decay model forbids this -- it predicts rho -> 0 and stays there.
  T6  phase restores at integers: rho at 2.0D and 3.0D both > 0.60.
  T7  THE ONE THAT SPEAKS TO M121. A test that bins "near in value" over a
      window spanning many phases averages the sawtooth away: drawing
      separations UNIFORMLY over [0, 2D] gives |rho| < 0.25, even though
      every individual pair is perfectly value-determined.
  T8  the same three results hold for a MEAN as for a median, which kills
      the rank-vs-mean discriminator outright.

FALSIFIER: if T5 fails -- if 1.5D is not negative -- periodicity is wrong and
I have no mechanism to offer, and I will say exactly that rather than look
for a third story. Two failed framings is already the honest answer.
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
RNG = np.random.default_rng(8714)


def q(x, d):
    return np.round(x / d) * d


def rho_at(sel, D, sep, n=50, trials=600, stat=np.median):
    lo, hi = sel.min() + 500, sel.max() - 500
    a, b = [], []
    for _ in range(trials):
        c = RNG.uniform(lo, hi)
        A = c + RNG.normal(0, 0.15 * D, n)
        B = c + sep + RNG.normal(0, 0.15 * D, n)
        a.append(stat(q(A, D)) - stat(A))
        b.append(stat(q(B, D)) - stat(B))
    return float(np.corrcoef(a, b)[0, 1])


def main():
    out = {"registered": {"T5": "rho(1.5D) < -0.20", "T6": "rho(2D),rho(3D) > 0.60",
                          "T7": "uniform sep over [0,2D] gives |rho| < 0.25",
                          "T8": "means behave as medians do"}}
    sel = np.asarray(np.load(CACHE / "bee3-leg-sel.npy")).ravel().astype(np.float64)
    D = (sel.max() - sel.min()) / 255.0
    print(f"quantum Delta = {D:.4f} DN\n")

    print("  sep/D    rho(median)   rho(mean)")
    grid = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
    rows = []
    for s in grid:
        rm = rho_at(sel, D, s * D, stat=np.median)
        ra = rho_at(sel, D, s * D, stat=np.mean)
        rows.append({"sep_quanta": s, "rho_median": rm, "rho_mean": ra})
        mark = "  <- integer" if abs(s - round(s)) < 1e-9 and s > 0 else (
            "  <- half-integer" if abs((s % 1) - 0.5) < 1e-9 else "")
        print(f"  {s:5.2f}    {rm:+.4f}       {ra:+.4f}{mark}")
    out["grid"] = rows

    g = {r["sep_quanta"]: r for r in rows}
    t5 = g[1.5]["rho_median"] < -0.20
    t6 = g[2.0]["rho_median"] > 0.60 and g[3.0]["rho_median"] > 0.60
    print(f"\nT5  rho(1.5D) = {g[1.5]['rho_median']:+.4f} -> "
          f"{'PASS, antiphase repeats' if t5 else 'FAIL, periodicity refuted'}")
    print(f"T6  rho(2D) = {g[2.0]['rho_median']:+.4f}, "
          f"rho(3D) = {g[3.0]['rho_median']:+.4f} -> "
          f"{'PASS, phase restores at integers' if t6 else 'FAIL'}")
    out["T5"] = {"rho": g[1.5]["rho_median"], "pass": t5}
    out["T6"] = {"rho_2": g[2.0]["rho_median"], "rho_3": g[3.0]["rho_median"],
                 "pass": t6}

    # ---- T7: what a phase-blind "near in value" bin actually measures ----
    lo, hi = sel.min() + 500, sel.max() - 500
    a, b = [], []
    for _ in range(6000):
        c = RNG.uniform(lo, hi)
        sep = RNG.uniform(0, 2 * D)
        A = c + RNG.normal(0, 0.15 * D, 50)
        B = c + sep + RNG.normal(0, 0.15 * D, 50)
        a.append(np.median(q(A, D)) - np.median(A))
        b.append(np.median(q(B, D)) - np.median(B))
    r7 = float(np.corrcoef(a, b)[0, 1])
    t7 = abs(r7) < 0.25
    print(f"T7  uniform separation over [0,2D]: rho = {r7:+.4f} -> "
          f"{'PASS' if t7 else 'FAIL'}")
    print("    every pair is perfectly value-determined, and a phase-blind "
          "bin still reads ~0")
    out["T7"] = {"rho": r7, "pass": t7}

    t8 = (g[1.5]["rho_mean"] < -0.20 and g[2.0]["rho_mean"] > 0.60
          and g[3.0]["rho_mean"] > 0.60)
    print(f"T8  mean at 1.5D = {g[1.5]['rho_mean']:+.4f}, 2D = "
          f"{g[2.0]['rho_mean']:+.4f}, 3D = {g[3.0]['rho_mean']:+.4f} -> "
          f"{'PASS, means behave identically' if t8 else 'FAIL, means differ'}")
    out["T8"] = {"pass": t8}

    if t5 and t6 and t7:
        v = ("PERIODIC IN THE QUANTUM -- co-movement is a phase relation, "
             "value-locking holds pairwise and vanishes under phase-blind "
             "binning")
    elif not t5:
        v = "NO MECHANISM TO OFFER -- periodicity refuted, two framings dead"
    else:
        v = "PARTIAL -- see arms"
    print(f"\nVERDICT: {v}")
    out["verdict"] = v
    out["discriminator_rank_vs_mean_survives"] = not t8
    with open(DATA / "114-phaseperiod.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"wrote {DATA / '114-phaseperiod.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

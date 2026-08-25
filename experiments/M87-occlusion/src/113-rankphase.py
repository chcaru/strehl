"""M87 / 113 -- is my "arbitrary sign" a RANK property, or a PHASE property?

ORCH proposes routing my third direction to M121 as: a rank statistic breaks
value-locking, because the error's sign is set by which side of a lattice
boundary the rank lands on, which is not monotone in value. Before I hand
that over I have to test it, because I think MY OWN FRAMING IS WRONG and the
bridge would be a story.

The reason to doubt it: quantisation is a MONOTONE map, and medians commute
with monotone maps. For odd n, median(q(X)) = q(median(X)) exactly. So the
error in a median is e(m) evaluated at the median's own value -- which is
value-determined, not rank-determined. Fact 1765 would be untouched.

If that is right, the real mechanism is not rank at all. It is PHASE: e(x) is
a sawtooth of period Delta, so two populations co-move only while they share
a lattice cell. My near band sits near 2900 DN and my far band near 3143 DN,
about 7 quanta apart -- different cells, unrelated phases, so their errors are
effectively independent and their DIFFERENCE carries arbitrary sign. That is
a statement about value SEPARATION relative to the quantum, and it applies to
means and medians alike.

REGISTERED BEFORE ANY NUMBER EXISTS
  T1  median(q(X)) == q(median(X)) exactly, for odd n. If this holds, the
      rank framing is dead on arrival and I must retract it.
  T2  the error of a median is a sawtooth in its own value, period Delta:
      max |e| <= Delta/2, and e reverses sign across a cell boundary.
  T3  co-movement of two populations' quantisation errors decays with their
      VALUE SEPARATION measured in quanta:
        rho > 0.80 when separation < 0.1 Delta
        |rho| < 0.30 when separation > 2 Delta
      If T3 holds, the mechanism is phase decorrelation, not rank.
  T4  a MEAN of n values is not exempt -- its error shrinks as ~1/sqrt(n) but
      its co-movement decays with separation on the SAME scale as a median's.
      If T4 holds, ORCH's proposed discriminator (rank fails, mean holds) is
      the wrong discriminator and I must say so.

FALSIFIER, registered: if T3 fails -- if correlation stays high past 2 Delta
-- then separation is not the controlling variable and I have no mechanism to
offer M121. I will report that and stop, rather than look for a third story.

Reads only M87's own cube. Touches no other milestone's files.
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
RNG = np.random.default_rng(8713)


def q(x, delta):
    return np.round(x / delta) * delta


def main():
    out = {"registered": {"T1": "median commutes with monotone quantisation",
                          "T2": "median error is a sawtooth, |e| <= D/2",
                          "T3": "rho>0.80 under 0.1D; |rho|<0.30 over 2D",
                          "T4": "means decay on the same separation scale"}}
    sel = np.asarray(np.load(CACHE / "bee3-leg-sel.npy")).ravel().astype(np.float64)
    D = (sel.max() - sel.min()) / 255.0
    print(f"quantum Delta = {D:.4f} DN on the real cube's range")

    # ---- T1: does the median commute with the quantiser? ------------------
    bad = 0
    for _ in range(2000):
        s = RNG.choice(sel, 51, replace=False)
        if np.median(q(s, D)) != q(np.median(s), D):
            bad += 1
    t1 = bad == 0
    print(f"\nT1  median(q(X)) vs q(median(X)) over 2000 draws: "
          f"{bad} mismatches -> {'PASS' if t1 else 'FAIL'}")
    if t1:
        print("    the median's error IS value-determined; the RANK framing "
              "is refuted and I retract it")
    out["T1"] = {"mismatches": bad, "pass": t1}

    # ---- T2: is that error a sawtooth in the median's own value? ---------
    base = float(np.median(sel))
    xs = base + np.linspace(0, 3 * D, 601)
    e = q(xs, D) - xs
    t2 = (np.abs(e).max() <= D / 2 + 1e-9) and (e.min() < 0 < e.max())
    print(f"T2  max |e| = {np.abs(e).max():.4f} vs Delta/2 = {D / 2:.4f}; "
          f"sign range [{e.min():+.3f}, {e.max():+.3f}] -> "
          f"{'PASS' if t2 else 'FAIL'}")
    out["T2"] = {"max_abs_e": float(np.abs(e).max()), "half_delta": D / 2,
                 "pass": t2}

    # ---- T3/T4: co-movement vs value separation, in quanta ---------------
    print("\nT3/T4  correlation of quantisation error between two populations")
    print("  sep/D    rho(median-of-50)   rho(mean-of-50)")
    rows = []
    for sepq in (0.02, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
        sep = sepq * D
        em_a, em_b, ea_a, ea_b = [], [], [], []
        for _ in range(400):
            c = RNG.uniform(sel.min() + 500, sel.max() - 500)
            A = c + RNG.normal(0, 0.15 * D, 50)
            B = c + sep + RNG.normal(0, 0.15 * D, 50)
            em_a.append(np.median(q(A, D)) - np.median(A))
            em_b.append(np.median(q(B, D)) - np.median(B))
            ea_a.append(np.mean(q(A, D)) - np.mean(A))
            ea_b.append(np.mean(q(B, D)) - np.mean(B))
        rm = float(np.corrcoef(em_a, em_b)[0, 1])
        ra = float(np.corrcoef(ea_a, ea_b)[0, 1])
        rows.append({"sep_quanta": sepq, "rho_median": rm, "rho_mean": ra})
        print(f"  {sepq:5.2f}    {rm:+.4f}              {ra:+.4f}")

    near = [r for r in rows if r["sep_quanta"] < 0.1]
    far = [r for r in rows if r["sep_quanta"] > 2.0]
    t3 = (min(r["rho_median"] for r in near) > 0.80
          and max(abs(r["rho_median"]) for r in far) < 0.30)
    t4 = (min(r["rho_mean"] for r in near) > 0.80
          and max(abs(r["rho_mean"]) for r in far) < 0.30)
    print(f"\nT3 (median) -> {'PASS' if t3 else 'FAIL'}    "
          f"near min {min(r['rho_median'] for r in near):+.4f}, "
          f"far max |rho| {max(abs(r['rho_median']) for r in far):.4f}")
    print(f"T4 (mean)   -> {'PASS' if t4 else 'FAIL'}    "
          f"near min {min(r['rho_mean'] for r in near):+.4f}, "
          f"far max |rho| {max(abs(r['rho_mean']) for r in far):.4f}")
    out["T3"] = {"rows": rows, "pass": t3}
    out["T4"] = {"pass": t4}

    if t1 and t3 and t4:
        v = ("PHASE, NOT RANK -- separation in quanta is the controlling "
             "variable and it governs means and medians alike")
    elif t1 and t3 and not t4:
        v = "SEPARATION CONTROLS MEDIANS ONLY -- rank framing partly survives"
    elif not t3:
        v = "NO MECHANISM TO OFFER -- separation does not control co-movement"
    else:
        v = "MIXED -- see arms"
    print(f"\nVERDICT: {v}")
    out["verdict"] = v

    # my own two bands, for scale
    sep_real = 243.0 / D
    print(f"\nM87's own near/far medians are ~243 DN apart = {sep_real:.1f} "
          f"quanta -- far outside the co-moving regime")
    out["m87_band_separation_quanta"] = sep_real
    with open(DATA / "113-rankphase.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"wrote {DATA / '113-rankphase.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""M68 step 02 - apply the criteria pre-registered in 01's docstring.

This script makes NO new choices. Every band, every comparison and every
consequence it prints was fixed in `01-dark-iso-sweep.py`, committed at
71cd54c before the sweep was run. It reads only `data/01-dark-iso-sweep.json`.

  C0  decode gate      - reproduce M4 section 8.1's 44 cells to 0.5%
  C1  control          - G1 vs G2: |alpha ratio - 1| <= 0.10 and the
                         sigma-ratio excursion over 11 ISOs <= 0.03
  C2  split-half null  - disjoint 10-frame halves of the SAME plane:
                         |alpha ratio - 1| <= 0.05, |delta ratio - 1| <= 0.35
  C3  discrimination   - alpha_B/alpha_G in 1.000 +/- 0.05  => {P1, P5}
                                          in 0.705 +/- 0.05 => {P2, P3, P4}
                                          else               => NEITHER
  C4  cannot-separate  - (a) C1 fails (b) C2a fails (c) C3 neither
                         (d) delta_G2 not resolved at 3x its jackknife sd
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent.parent
DATA = HERE / "data"

BASE_ISO = 100.0
S_PTC = 0.8396
S2_PTC = S_PTC * S_PTC
C0_BAND = 0.005
C1A_BAND = 0.10
C1B_BAND = 0.03
C2A_BAND = 0.05
C2B_BAND = 0.35
C3_HALF = 0.05

M4_TABLE = {
    50: (1.0079, 1.0054, 1.0120, 0.9211),
    100: (1.0048, 1.0042, 1.0105, 0.9185),
    200: (1.7709, 1.7782, 1.7929, 1.6246),
    250: (2.1927, 2.2104, 2.2284, 2.0201),
    400: (1.2130, 1.2266, 1.2403, 1.1146),
    500: (1.4940, 1.4949, 1.5105, 1.3724),
    640: (1.8308, 1.8438, 1.8657, 1.6914),
    800: (2.2752, 2.2872, 2.3138, 2.1100),
    1000: (2.8376, 2.8582, 2.8920, 2.6463),
    1600: (4.4369, 4.4702, 4.5407, 4.1739),
    2000: (5.5866, 5.6165, 5.6883, 5.2406),
}
PLANES = ["R", "G1", "G2", "B"]


def fit(g, mode, var, shared_delta=True):
    g2 = g**2
    if shared_delta:
        d = np.column_stack([g2 * (mode == 0), g2 * (mode == 1), np.ones_like(g2)])
        c = np.linalg.lstsq(d, var, rcond=None)[0]
        return {"alpha_low": c[0], "alpha_high": c[1], "delta_low": c[2], "delta_high": c[2]}
    d = np.column_stack([g2 * (mode == 0), g2 * (mode == 1),
                         1.0 * (mode == 0), 1.0 * (mode == 1)])
    c = np.linalg.lstsq(d, var, rcond=None)[0]
    return {"alpha_low": c[0], "alpha_high": c[1], "delta_low": c[2], "delta_high": c[3]}


def resid_pct(g, mode, var, shared_delta=True):
    f = fit(g, mode, var, shared_delta)
    pred = np.where(mode == 0, f["alpha_low"], f["alpha_high"]) * g**2 + \
        np.where(mode == 0, f["delta_low"], f["delta_high"])
    return 100.0 * np.max(np.abs(pred / var - 1.0))


def jk_scalar(g, mode, va, vb, key, shared_delta=True):
    """Leave-one-ISO-out jackknife sd of the ratio fit(va)[key]/fit(vb)[key]."""
    vals = []
    for i in range(len(g)):
        s = np.ones(len(g), bool)
        s[i] = False
        fa = fit(g[s], mode[s], va[s], shared_delta)
        fb = fit(g[s], mode[s], vb[s], shared_delta)
        vals.append(fa[key] / fb[key])
    vals = np.asarray(vals)
    return float(np.sqrt((len(g) - 1) / len(g) * np.sum((vals - vals.mean()) ** 2)))


def jk_single(g, mode, v, key, shared_delta=True):
    vals = []
    for i in range(len(g)):
        s = np.ones(len(g), bool)
        s[i] = False
        vals.append(fit(g[s], mode[s], v[s], shared_delta)[key])
    vals = np.asarray(vals)
    return float(np.sqrt((len(g) - 1) / len(g) * np.sum((vals - vals.mean()) ** 2)))


def main() -> None:
    blob = json.loads((DATA / "01-dark-iso-sweep.json").read_text())
    isos = np.array(blob["isos"], float)
    g = np.maximum(isos, BASE_ISO)
    mode = (isos >= 400).astype(int)
    rows = blob["rows"]
    print(f"geometry {blob['geometry']}, ISOs {isos.astype(int).tolist()}")

    def series(arm, plane, key):
        return np.array([r[key] for r in rows[arm][plane]], float)

    # ----------------------------------------------------------------- C0
    print("\n=== C0 decode gate: rawpy against M4 section 8.1 (rawler), 44 cells ===")
    worst, worst_cell, n_ok = 0.0, None, 0
    print(f"{'ISO':>5s} " + " ".join(f"{p:>19s}" for p in PLANES))
    for i, iso in enumerate(isos.astype(int)):
        cells = []
        for j, p in enumerate(PLANES):
            mine = rows["none"][p][i]["rms"]
            theirs = M4_TABLE[iso][j]
            rel = mine / theirs - 1.0
            n_ok += abs(rel) <= C0_BAND
            if abs(rel) > worst:
                worst, worst_cell = abs(rel), (iso, p, mine, theirs)
            cells.append(f"{mine:8.5f}/{theirs:7.4f}{rel * 100:+5.2f}%")
        print(f"{iso:5d} " + " ".join(f"{c:>19s}" for c in cells))
    c0 = n_ok == 44
    print(f"C0: {n_ok}/44 cells within {C0_BAND:.1%}; worst "
          f"{worst * 100:.3f}% at {worst_cell}")
    print(f"C0 -> {'PASS' if c0 else 'FAIL'}")
    if not c0:
        print("C0 FAILED. Pre-registered consequence: THE MILESTONE STOPS.")
        return

    # ------------------------------------------------- defect exclusion effect
    print("\n=== defect exclusion (M48c criterion B, recurrence >= 6) ===")
    print(f"{'plane':>5s} {'kept':>10s} {'excluded':>9s} "
          f"{'sig@100 none':>13s} {'sig@100 r6':>11s} {'d%':>7s} "
          f"{'sig@2000 none':>14s} {'sig@2000 r6':>12s} {'d%':>7s}")
    for p in PLANES:
        n_none = rows["none"][p][0]["n"]
        n_r6 = rows["r6"][p][0]["n"]
        i100 = list(isos.astype(int)).index(100)
        i2000 = list(isos.astype(int)).index(2000)
        a, b = rows["none"][p][i100]["rms"], rows["r6"][p][i100]["rms"]
        c, d = rows["none"][p][i2000]["rms"], rows["r6"][p][i2000]["rms"]
        print(f"{p:>5s} {n_r6:10d} {n_none - n_r6:9d} {a:13.5f} {b:11.5f} "
              f"{100 * (b / a - 1):+6.2f}% {c:14.5f} {d:12.5f} {100 * (d / c - 1):+6.2f}%")

    # ----------------------------------------------------- the sigma ratios
    ARM = "r6"
    var = {p: series(ARM, p, "var") for p in PLANES}
    var["Gpool"] = 0.5 * (var["G1"] + var["G2"])
    sig = {k: np.sqrt(v) for k, v in var.items()}

    print(f"\n=== sigma ratios per ISO (arm {ARM}) ===")
    print(f"{'ISO':>5s} {'sigG2/sigG1':>12s} {'sigR/sigG1':>11s} "
          f"{'sigB/sigG2':>11s} {'sigB/sigGpool':>14s} {'sigR/sigGpool':>14s}")
    for i, iso in enumerate(isos.astype(int)):
        print(f"{iso:5d} {sig['G2'][i] / sig['G1'][i]:12.5f} "
              f"{sig['R'][i] / sig['G1'][i]:11.5f} {sig['B'][i] / sig['G2'][i]:11.5f} "
              f"{sig['B'][i] / sig['Gpool'][i]:14.5f} "
              f"{sig['R'][i] / sig['Gpool'][i]:14.5f}")

    # --------------------------------------------------------- alpha / delta
    print(f"\n=== two-term fit sigma^2 = alpha*G^2 + delta (shared delta, arm {ARM}) ===")
    fits = {}
    print(f"{'plane':>6s} {'alpha_low':>12s} {'alpha_high':>12s} {'delta':>9s} "
          f"{'jk(a_hi)':>10s} {'jk(delta)':>10s} {'max resid':>10s}")
    for p in ["R", "G1", "G2", "B", "Gpool"]:
        f = fit(g, mode, var[p])
        fits[p] = f
        print(f"{p:>6s} {f['alpha_low']:12.5e} {f['alpha_high']:12.5e} "
              f"{f['delta_high']:9.5f} {jk_single(g, mode, var[p], 'alpha_high'):10.3e} "
              f"{jk_single(g, mode, var[p], 'delta_high'):10.5f} "
              f"{resid_pct(g, mode, var[p]):9.2f}%")

    def ratio(a, b, key="alpha_high"):
        return fits[a][key] / fits[b][key], jk_scalar(g, mode, var[a], var[b], key)

    print(f"\n{'comparison':>16s} {'alpha ratio':>13s} {'+/- jk':>9s} "
          f"{'delta ratio':>13s} {'+/- jk':>9s}")
    pairs = [("G2", "G1"), ("R", "G1"), ("B", "G2"), ("B", "Gpool"), ("R", "Gpool")]
    R = {}
    for a, b in pairs:
        ar, ae = ratio(a, b, "alpha_high")
        dr, de = ratio(a, b, "delta_high")
        R[(a, b)] = (ar, ae, dr, de)
        print(f"{a + '/' + b:>16s} {ar:13.5f} {ae:9.5f} {dr:13.5f} {de:9.5f}")

    # ----------------------------------------------------------------- C1
    print("\n=== C1 control: G1 vs G2 ===")
    ar, ae, dr, de = R[("G2", "G1")]
    gg = sig["G2"] / sig["G1"]
    exc = float(gg.max() - gg.min())
    c1a = abs(ar - 1.0) <= C1A_BAND
    c1b = exc <= C1B_BAND
    print(f"C1a |alpha_G2/alpha_G1 - 1| = {abs(ar - 1):.5f} <= {C1A_BAND} -> "
          f"{'PASS' if c1a else 'FAIL'}")
    print(f"C1b sigma-ratio excursion   = {exc:.5f} <= {C1B_BAND} -> "
          f"{'PASS' if c1b else 'FAIL'}  (min {gg.min():.5f} max {gg.max():.5f})")
    c1 = c1a and c1b
    print(f"C1 -> {'PASS' if c1 else 'FAIL'}")

    # ----------------------------------------------------------------- C2
    print("\n=== C2 split-half null: disjoint 10-frame halves of the SAME plane ===")
    c2a = c2b = True
    for p in ["G1", "B"]:
        va = series(ARM, p, "var_a")
        vb = series(ARM, p, "var_b")
        fa, fb = fit(g, mode, va), fit(g, mode, vb)
        arr = fa["alpha_high"] / fb["alpha_high"]
        drr = fa["delta_high"] / fb["delta_high"]
        ok_a = abs(arr - 1.0) <= C2A_BAND
        ok_d = abs(drr - 1.0) <= C2B_BAND
        c2a &= ok_a
        c2b &= ok_d
        print(f"  {p:>3s} alpha A/B = {arr:.5f} (|d|={abs(arr - 1):.5f} "
              f"<= {C2A_BAND}) -> {'PASS' if ok_a else 'FAIL'};  "
              f"delta A/B = {drr:.5f} (|d|={abs(drr - 1):.5f} "
              f"<= {C2B_BAND}) -> {'PASS' if ok_d else 'FAIL'}")
    print(f"C2a -> {'PASS' if c2a else 'FAIL'};  C2b -> {'PASS' if c2b else 'FAIL'}")

    # ----------------------------------------------------------------- C3
    print("\n=== C3 discrimination ===")
    verdicts = {}
    for a, b in [("B", "G2"), ("B", "Gpool")]:
        ar, ae, dr, de = R[(a, b)]
        if abs(ar - 1.000) <= C3_HALF:
            v = "{P1, P5} - the scale does NOT touch the dark noise"
        elif abs(ar - S2_PTC) <= C3_HALF:
            v = "{P2, P3, P4} - the scale IS upstream of the dark noise"
        else:
            v = "NEITHER BAND - refuse the binary"
        verdicts[(a, b)] = v
        print(f"  alpha_{a}/alpha_{b} = {ar:.5f} +/- {ae:.5f}   "
              f"(1.000 +/- {C3_HALF} | {S2_PTC:.3f} +/- {C3_HALF})  ->  {v}")

    # ----------------------------------------------------------------- C4
    print("\n=== C4 can the observable separate the hypotheses? ===")
    d_g2 = fits["G2"]["delta_high"]
    d_g2_jk = jk_single(g, mode, var["G2"], "delta_high")
    c4d = d_g2 > 3.0 * d_g2_jk
    print(f"  (a) C1 failed?  {'YES' if not c1 else 'no'}")
    print(f"  (b) C2a failed? {'YES' if not c2a else 'no'}")
    print(f"  (c) C3 neither? {'YES' if 'NEITHER' in verdicts[('B', 'G2')] else 'no'}")
    print(f"  (d) delta_G2 = {d_g2:.5f} vs 3x jackknife {3 * d_g2_jk:.5f} -> "
          f"{'resolved' if c4d else 'NOT RESOLVED'}")

    if c4d:
        f_up = 1.0 - fits["G2"]["delta_high"] / var["G2"]
        print("\n  upstream variance fraction of G2 by ISO "
              "(1 = all dark noise generated ahead of any pre-ADC scale):")
        print("   " + "  ".join(f"{int(i)}:{x:.3f}" for i, x in zip(isos, f_up)))

    # ---------------------------------------------------------- robustness
    print("\n=== robustness arms (reported, not gates) ===")
    for arm in ["none", "r3", "r6", "r9"]:
        v = {p: np.array([r["var"] for r in rows[arm][p]], float) for p in PLANES}
        v["Gpool"] = 0.5 * (v["G1"] + v["G2"])
        fb, f2, f1, fg = (fit(g, mode, v[k]) for k in ("B", "G2", "G1", "Gpool"))
        print(f"  exclusion={arm:>4s}  aB/aG2={fb['alpha_high'] / f2['alpha_high']:.5f}"
              f"  aB/aGp={fb['alpha_high'] / fg['alpha_high']:.5f}"
              f"  aG2/aG1={f2['alpha_high'] / f1['alpha_high']:.5f}"
              f"  dB/dG2={fb['delta_high'] / f2['delta_high']:.5f}")

    vmed = {p: np.array([r["median_var"] for r in rows[ARM][p]], float) for p in PLANES}
    vmed["Gpool"] = 0.5 * (vmed["G1"] + vmed["G2"])
    fb, f2, f1 = (fit(g, mode, vmed[k]) for k in ("B", "G2", "G1"))
    print(f"  median-pixel variance  aB/aG2={fb['alpha_high'] / f2['alpha_high']:.5f}"
          f"  aG2/aG1={f2['alpha_high'] / f1['alpha_high']:.5f}"
          f"  dB/dG2={fb['delta_high'] / f2['delta_high']:.5f}")

    fb, f2 = (fit(g, mode, var[k], shared_delta=False) for k in ("B", "G2"))
    print(f"  delta per mode         aB/aG2={fb['alpha_high'] / f2['alpha_high']:.5f}"
          f"  dB/dG2(high)={fb['delta_high'] / f2['delta_high']:.5f}"
          f"  dB/dG2(low)={fb['delta_low'] / f2['delta_low']:.5f}")

    hi = mode == 1
    fb, f2 = (fit(g[hi], mode[hi], var[k][hi]) for k in ("B", "G2"))
    print(f"  high mode only         aB/aG2={fb['alpha_high'] / f2['alpha_high']:.5f}"
          f"  dB/dG2={fb['delta_high'] / f2['delta_high']:.5f}")

    lo = mode == 0
    fb, f2 = (fit(g[lo], mode[lo], var[k][lo]) for k in ("B", "G2"))
    print(f"  low mode only          aB/aG2={fb['alpha_low'] / f2['alpha_low']:.5f}"
          f"  dB/dG2={fb['delta_low'] / f2['delta_low']:.5f}")

    print("\n=== ISO 50 / ISO 100 replicate pair at fixed gain (repeatability) ===")
    i50 = list(isos.astype(int)).index(50)
    i100 = list(isos.astype(int)).index(100)
    for p in PLANES:
        print(f"  {p:>3s} sigma(50)={sig[p][i50]:.5f} sigma(100)={sig[p][i100]:.5f} "
              f"ratio={sig[p][i50] / sig[p][i100]:.5f}")

    print("\n=== surviving-population dark level (median temporal-mean excess, DN) ===")
    for p in PLANES:
        vals = series(ARM, p, "median_mean_excess")
        print(f"  {p:>3s} " + " ".join(f"{int(i)}:{x:+.4f}" for i, x in zip(isos, vals)))


if __name__ == "__main__":
    main()

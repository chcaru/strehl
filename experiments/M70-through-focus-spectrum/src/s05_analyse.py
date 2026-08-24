"""M70 s05 - score the pre-registered criteria against the corpus measurement.

Reads `out/tfs-<stack>.npz` from s04, subtracts the shipped photon-transfer
noise model, and scores Criteria A-D and VOID conditions 1-3 exactly as
PREREGISTRATION.md (committed 80572ec) fixed them.

Nothing here re-opens a criterion. Where a criterion fails, it is reported as
failing.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
from m70lib import L  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

DYN_GATE = 10.0  # M5's own dynamic-range gate
HALF_WINDOW = 5
SEED = 705


def load(stack: str, tag: str = ""):
    z = np.load(os.path.join(OUT, f"tfs-{stack}{tag}.npz"), allow_pickle=False)
    return {
        "power": z["power"],  # (K, P, B)
        "level": z["level"],  # (K, P)
        "bands": [str(b) for b in z["bands"]],
        "iso": float(z["iso"]),
        "patch": int(z["patch"]),
        "tile": int(z["tile"]),
        "centres": z["centres"],
    }


def signal(d, sigma_scale: float = 1.0):
    """S = P - sigma^2, with sigma^2 from the shipped photon-transfer model at
    the w^2-weighted patch level of the SAME frame and patch."""
    nvar = M.noise_var_dn2(d["level"], d["iso"]) * sigma_scale  # (K, P)
    return d["power"] - nvar[:, :, None], nvar


def classify(d, s, nvar):
    """Textured vs flat, by peak-frame low-band SNR against M5's DYN_GATE.

    The low band (0.025-0.050 cyc/px) is the least focus-sensitive band
    available, so this classification is close to orthogonal to the mid-band
    statistic under test (rule 17)."""
    j = d["bands"].index("b1_low")
    snr = s[:, :, j].max(axis=0) / np.median(nvar, axis=0)
    return snr >= DYN_GATE, snr


def per_patch_stats(s, band_idx, half_window=HALF_WINDOW):
    rows = []
    for p in range(s.shape[1]):
        rows.append(M.through_focus_stats(s[:, p, band_idx], half_window=half_window))
    return rows


def synthetic_floor(k: int, iso: float, level: float, patch: int, tile: int, rng):
    """Negative control at THIS stack's K, ISO and level: a flat latent with
    calibrated noise, pushed through the identical estimator. Whatever this
    returns is the value `n_eff_MF` takes when there is no signal at all."""
    var = float(M.noise_var_dn2(level, iso))
    acc = {b: [] for b in M.MID_BANDS}
    frames = []
    for _ in range(k):
        img = level + rng.normal(0.0, np.sqrt(var), (patch, patch))
        f, p, c = L.spectrum(img, "GQ", tile=tile, window="hann", sector="iso")
        ba = M.band_average(f, p, c)
        lvl = M.w2_weighted_mean(np.clip(img, 0.0, None), tile)
        nv = float(M.noise_var_dn2(lvl, iso))
        frames.append({b: ba[b][0] - nv for b in M.MID_BANDS})
    out = {}
    for b in M.MID_BANDS:
        st = M.through_focus_stats(np.array([fr[b] for fr in frames]))
        out[b] = st["n_eff_mf_raw"]
    return out, float(np.mean(list(out.values())))


def med(x):
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    return float(np.median(x)) if x.size else np.nan


def analyse(stack: str, tag: str = "", sigma_scale: float = 1.0, rng=None):
    d = load(stack, tag)
    s, nvar = signal(d, sigma_scale)
    tex, snr = classify(d, s, nvar)
    k = s.shape[0]
    res = {
        "stack": stack,
        "K": k,
        "iso": d["iso"],
        "patch": d["patch"],
        "n_textured": int(tex.sum()),
        "n_flat": int((~tex).sum()),
        "sigma_scale": sigma_scale,
    }
    for b in M.MID_BANDS + ("b6_above_f11_cut", "b1_low"):
        j = d["bands"].index(b)
        st = per_patch_stats(s, j)
        g = {}
        for key in ("n_eff_mf_raw", "n_eff_mf_smoothed", "n_eff_mf_window", "pr",
                    "rel_amp_1", "rel_amp_2", "rel_amp_3", "rel_amp_5"):
            g[key] = med([st[p][key] for p in range(len(st)) if tex[p]])
            g[key + "_flat"] = med([st[p][key] for p in range(len(st)) if not tex[p]])
        for m in (1, 2, 3, 5):
            g[f"mf_gain_top{m}"] = med(
                [M.mf_gain_over_top_m(s[:, p, j], m) for p in range(len(st)) if tex[p]]
            )
        g["n_eff_mf_raw_iqr"] = [
            float(np.percentile([st[p]["n_eff_mf_raw"] for p in range(len(st)) if tex[p]], q))
            for q in (25, 75)
        ] if tex.any() else [np.nan, np.nan]
        res[b] = g

    mid = [res[b]["n_eff_mf_raw"] for b in M.MID_BANDS]
    res["mid_n_eff_mf"] = float(np.mean(mid))
    res["mid_sqrt_gain"] = float(np.mean([np.sqrt(max(v, 0.0)) for v in mid]))
    res["mid_n_eff_mf_flat"] = float(
        np.mean([res[b]["n_eff_mf_raw_flat"] for b in M.MID_BANDS])
    )
    res["mid_rel_amp_1"] = float(np.mean([res[b]["rel_amp_1"] for b in M.MID_BANDS]))
    res["mid_rel_amp_2"] = float(np.mean([res[b]["rel_amp_2"] for b in M.MID_BANDS]))
    res["mid_gain_top3"] = float(np.mean([res[b]["mf_gain_top3"] for b in M.MID_BANDS]))

    if rng is not None:
        lvl = float(np.median(d["level"]))
        _, syn = synthetic_floor(k, d["iso"], lvl, d["patch"], d["tile"], rng)
        res["synthetic_floor_mid"] = syn
    return res


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    stacks = [
        "coffee-bubbles", "109MSDCF", "119MSDCF", "113MSDCF", "112MSDCF", "foam",
        "coffee-bean", "wrapped-text-2", "wrapped-text-1", "bee-1", "bee-2", "bee-3",
    ]
    stacks = [s for s in stacks if os.path.exists(os.path.join(OUT, f"tfs-{s}{tag}.npz"))]
    rng = np.random.default_rng(SEED)
    rows = [analyse(s, tag, 1.0, rng) for s in stacks]

    print("=" * 118)
    print(f"M70 through-focus response, patch={rows[0]['patch']} GQ samples, "
          f"mid bands 0.100-0.2762 sensor cyc/px, textured patches")
    print("=" * 118)
    hdr = (f"{'stack':16s} {'K':>4s} {'ISO':>5s} {'tex':>4s} {'flat':>4s} "
           f"{'n_eff':>7s} {'flat':>7s} {'synth':>7s} {'sqrt':>6s} "
           f"{'relA1':>6s} {'relA2':>6s} {'relA3':>6s} {'gain1':>6s} {'gain2':>6s} "
           f"{'gain3':>6s} {'gain5':>6s} {'b6':>6s}")
    print(hdr)
    for r in rows:
        print(f"{r['stack']:16s} {r['K']:4d} {r['iso']:5.0f} {r['n_textured']:4d} "
              f"{r['n_flat']:4d} {r['mid_n_eff_mf']:7.3f} {r['mid_n_eff_mf_flat']:7.3f} "
              f"{r.get('synthetic_floor_mid', np.nan):7.3f} {r['mid_sqrt_gain']:6.3f} "
              f"{r['mid_rel_amp_1']:6.3f} {r['mid_rel_amp_2']:6.3f} "
              f"{float(np.mean([r[b]['rel_amp_3'] for b in M.MID_BANDS])):6.3f} "
              f"{float(np.mean([r[b]['mf_gain_top1'] for b in M.MID_BANDS])):6.3f} "
              f"{float(np.mean([r[b]['mf_gain_top2'] for b in M.MID_BANDS])):6.3f} "
              f"{r['mid_gain_top3']:6.3f} "
              f"{float(np.mean([r[b]['mf_gain_top5'] for b in M.MID_BANDS])):6.3f} "
              f"{r['b6_above_f11_cut']['n_eff_mf_raw']:6.3f}")

    print()
    print("per-band detail (textured medians)")
    print(f"{'stack':16s} {'band':>18s} {'n_eff':>7s} {'flat':>7s} {'window':>7s} "
          f"{'pr':>7s} {'relA1':>6s} {'relA2':>6s} {'gain3':>6s} {'IQR':>18s}")
    for r in rows:
        for b in M.MID_BANDS + ("b6_above_f11_cut",):
            g = r[b]
            iqr = f"[{g['n_eff_mf_raw_iqr'][0]:.2f},{g['n_eff_mf_raw_iqr'][1]:.2f}]"
            print(f"{r['stack']:16s} {b:>18s} {g['n_eff_mf_raw']:7.3f} "
                  f"{g['n_eff_mf_raw_flat']:7.3f} {g['n_eff_mf_window']:7.3f} "
                  f"{g['pr']:7.3f} {g['rel_amp_1']:6.3f} {g['rel_amp_2']:6.3f} "
                  f"{g['mf_gain_top3']:6.3f} {iqr:>18s}")

    # ---------------- pre-registered scoring ----------------
    n = len(rows)
    print()
    print("=" * 118)
    print("PRE-REGISTERED CRITERIA")
    print("=" * 118)

    a_sup = sum(1 for r in rows if r["mid_rel_amp_2"] >= 0.30)
    a_ref = sum(1 for r in rows if r["mid_rel_amp_2"] < 0.30)
    a = "SUPPORTS" if a_sup >= 6 else ("REFUTES" if a_ref >= 9 else "INDETERMINATE")
    print(f"A  rel_amp_2 >= 0.30 on {a_sup}/{n} stacks; < 0.30 on {a_ref}/{n}  ->  {a}")

    b_core = sum(1 for r in rows
                 if r["mid_sqrt_gain"] >= 1.50
                 and r["mid_n_eff_mf"] >= 2.0 * r["mid_n_eff_mf_flat"])
    b_plug = sum(1 for r in rows if r["mid_sqrt_gain"] <= 1.25)
    b = "CORE" if b_core >= 7 else ("PLUGIN" if b_plug >= 7 else "INDETERMINATE")
    print(f"B  sqrt(n_eff) >= 1.50 and 2x flat on {b_core}/{n}; <= 1.25 on {b_plug}/{n}  ->  {b}")

    c_core = sum(1 for r in rows if r["mid_gain_top3"] >= 1.30)
    c_plug = sum(1 for r in rows if r["mid_gain_top3"] <= 1.10)
    c = "CORE" if c_core >= 7 else ("PLUGIN" if c_plug >= 7 else "INDETERMINATE")
    print(f"C  gain over top-3 >= 1.30 on {c_core}/{n}; <= 1.10 on {c_plug}/{n}  ->  {c}")

    lk = np.log(np.array([r["K"] for r in rows], dtype=float))
    ln = np.log(np.clip([r["mid_n_eff_mf"] for r in rows], 1e-6, None))
    slope, icept = np.polyfit(lk, ln, 1)
    rr = np.corrcoef(lk, ln)[0, 1] ** 2
    spread = max(r["mid_n_eff_mf"] for r in rows) / max(
        min(r["mid_n_eff_mf"] for r in rows), 1e-9)
    a1 = [r["mid_rel_amp_1"] for r in rows]
    a1_spread = max(a1) - min(a1)
    d_phys = spread < 3.0 or a1_spread <= 0.30
    d_habit = 0.7 <= slope <= 1.3
    dv = "HABIT" if d_habit else ("PHYSICS" if d_phys else "INDETERMINATE")
    print(f"D  log n_eff vs log K: slope {slope:+.3f} (R2 {rr:.3f}); n_eff spread {spread:.2f}x; "
          f"rel_amp_1 range {a1_spread:.3f}  ->  {dv}")

    print()
    print("VOID conditions")
    v1 = [r["stack"] for r in rows if r["mid_n_eff_mf_flat"] > 0.5 * r["mid_n_eff_mf"]]
    print(f"  1 floor swamp (flat > 50% of textured): {v1 if v1 else 'none'}")
    f11 = [r for r in rows if r["stack"] in ("109MSDCF", "112MSDCF", "113MSDCF")]
    v2 = [r["stack"] for r in f11
          if r["b6_above_f11_cut"]["n_eff_mf_raw"] >= r["mid_n_eff_mf"]]
    for r in f11:
        print(f"  2 f/11 {r['stack']:12s} b6 n_eff {r['b6_above_f11_cut']['n_eff_mf_raw']:.3f} "
              f"vs mid {r['mid_n_eff_mf']:.3f}")
    print(f"  2 broken subtraction: {v2 if v2 else 'none'}")

    print()
    print("VOID condition 3 - sigma sensitivity (+-25%)")
    sens = {}
    for sc in (0.75, 1.25):
        rr2 = [analyse(r["stack"], tag, sc, None) for r in rows]
        a_s = sum(1 for x in rr2 if x["mid_rel_amp_2"] >= 0.30)
        b_c = sum(1 for x in rr2 if x["mid_sqrt_gain"] >= 1.50
                  and x["mid_n_eff_mf"] >= 2.0 * x["mid_n_eff_mf_flat"])
        b_p = sum(1 for x in rr2 if x["mid_sqrt_gain"] <= 1.25)
        c_c = sum(1 for x in rr2 if x["mid_gain_top3"] >= 1.30)
        c_p = sum(1 for x in rr2 if x["mid_gain_top3"] <= 1.10)
        va = "SUPPORTS" if a_s >= 6 else ("REFUTES" if (n - a_s) >= 9 else "INDET")
        vb = "CORE" if b_c >= 7 else ("PLUGIN" if b_p >= 7 else "INDET")
        vc = "CORE" if c_c >= 7 else ("PLUGIN" if c_p >= 7 else "INDET")
        sens[sc] = (va, vb, vc)
        print(f"  sigma x{sc:.2f}: A {va:9s} ({a_s}/{n})   B {vb:6s} "
              f"(core {b_c}, plugin {b_p})   C {vc:6s} (core {c_c}, plugin {c_p})   "
              f"median mid n_eff {np.median([x['mid_n_eff_mf'] for x in rr2]):.3f}")
    stable = all(v == (a, b, c) for v in sens.values())
    print(f"  point estimate A/B/C = {a}/{b}/{c}; stable under +-25% sigma: {stable}")

    with open(os.path.join(OUT, f"s05_analysis{tag}.json"), "w", encoding="utf-8") as fh:
        json.dump({"rows": rows,
                   "criteria": {"A": a, "B": b, "C": c, "D": dv,
                                "slope": float(slope), "r2": float(rr)},
                   "sigma_sensitivity": {str(k2): v for k2, v in sens.items()}},
                  fh, indent=1)
    print(f"\nwrote out/s05_analysis{tag}.json")


if __name__ == "__main__":
    main()

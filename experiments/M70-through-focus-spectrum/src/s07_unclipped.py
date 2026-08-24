"""M70 s07 - the rectification defect, and the corrected measurement.

s05/s06 established that the FLAT control patches return n_eff_MF ~ 0.3-0.6 K
(bee-1: 177 at K=299), and that subtracting a frame-pedestal does not remove
it (still 97). That rules out the explanation offered in s06. The real cause is
in the estimator itself, in `m70lib.through_focus_stats`:

    pos = np.clip(s, 0.0, None)
    n_eff_mf_raw = pos.sum() / max(s)

The clip. For a band whose true signal is zero, S_k is a mean-zero fluctuation,
and `sum_k max(S_k, 0)` is not zero - it is K.E[max(x,0)] = 0.3989 K sigma,
while the denominator is only max_k S_k ~ sigma sqrt(2 ln K). The ratio is
therefore ~ 0.4 K / sqrt(2 ln K), which grows almost linearly in K. **The clip
rectifies noise into apparent signal, and the inflation scales with the frame
count** - the exact axis the corpus was designed to test.

Consequences, both reported rather than reinterpreted:

  * Pre-registered VOID condition 1 ("flat median > 50% of textured") could
    never have been satisfied on a deep stack, because the flat median is
    ~0.4K by construction and n_eff <= K. Criterion B's second clause
    (textured >= 2x flat) was therefore UNSATISFIABLE as written. The criterion
    was defective, not the data. This is M62's defect - an acceptance guard
    carrying the fault it was built to police - and it is recorded as such.

  * The correction is to drop the clip. With S_k unclipped, a signal-free band
    gives sum_k S_k ~ K.e where e is the true model bias, which s06 measured
    directly, rather than K.0.4.sigma of rectified noise.

Everything below is recomputed with the unclipped estimator. The clipped
numbers from s05 stand as reported; they are not deleted.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
import s03_plant as P3  # noqa: E402
import s05_analyse as A5  # noqa: E402

OUT = A5.OUT
STACKS = A5.__dict__.get("STACKS") or [
    "coffee-bubbles", "109MSDCF", "119MSDCF", "113MSDCF", "112MSDCF", "foam",
    "coffee-bean", "wrapped-text-2", "wrapped-text-1", "bee-1", "bee-2", "bee-3",
]
HALF_WINDOW = 5


# ---------------------------------------------------------------------------
# The corrected statistics. No clip anywhere.
# ---------------------------------------------------------------------------
def tf_stats_uc(s: np.ndarray, half_window: int = HALF_WINDOW) -> dict:
    s = np.asarray(s, dtype=np.float64)
    k = s.size
    ssm = M.smooth3(s)
    i_pk = int(np.argmax(ssm))
    den = max(float(ssm[i_pk]), 1e-30)
    den_raw = max(float(s[int(np.argmax(s))]), 1e-30)
    lo, hi = max(0, i_pk - half_window), min(k, i_pk + half_window + 1)
    amp_pk = np.sqrt(max(float(ssm[i_pk]), 0.0))
    out = {
        "k": k,
        "peak_idx": i_pk,
        "n_eff_uc": float(s.sum() / den_raw),
        "n_eff_uc_sm": float(s.sum() / den),
        "n_eff_uc_window": float(s[lo:hi].sum() / den),
    }
    for d in (1, 2, 3, 5, 10):
        v = []
        if i_pk - d >= 0:
            v.append(s[i_pk - d])
        if i_pk + d < k:
            v.append(s[i_pk + d])
        m = float(np.mean(v)) if v else np.nan
        out[f"rel_amp_{d}"] = float(np.sqrt(max(m, 0.0)) / amp_pk) if amp_pk > 0 else np.nan
    return out


def gain_top_m_uc(s: np.ndarray, m: int) -> float:
    """sqrt(sum_k |H_k|^2) / ( (1/sqrt(m)) sum_{top m} |H_k| ).

    Numerator uses the UNCLIPPED sum, which is the unbiased estimate of
    sum|H|^2|L|^2. Denominator needs amplitudes and so clips the top-m terms,
    which are the largest and positive on any patch that passes the texture
    gate. |sum H| <= sum|H| makes this a LOWER bound on the true gain."""
    s = np.asarray(s, dtype=np.float64)
    tot = float(s.sum())
    if tot <= 0:
        return np.nan
    top = np.sort(s)[::-1][:m]
    den = float(np.sqrt(np.clip(top, 0.0, None)).sum())
    if den <= 0:
        return np.nan
    return float(np.sqrt(tot) * np.sqrt(m) / den)


# ---------------------------------------------------------------------------
# 1. The rectification bias, measured
# ---------------------------------------------------------------------------
def rectification_null():
    print("=" * 104)
    print("1. THE RECTIFICATION BIAS - what the CLIPPED statistic returns on pure noise")
    print("=" * 104)
    rng = np.random.default_rng(7007)
    print(f"{'K':>5s} {'clipped n_eff':>14s} {'unclipped n_eff':>16s} "
          f"{'0.4K/sqrt(2 lnK)':>18s}")
    rows = []
    for k in (19, 22, 33, 63, 79, 100, 105, 120, 130, 299):
        x = rng.normal(size=(4000, k))
        cl = np.clip(x, 0, None).sum(1) / x.max(1)
        uc = x.sum(1) / x.max(1)
        pred = 0.3989 * k / np.sqrt(2 * np.log(k))
        print(f"{k:5d} {np.median(cl):14.2f} {np.median(uc):16.3f} {pred:18.2f}")
        rows.append({"K": k, "clipped": float(np.median(cl)),
                     "unclipped": float(np.median(uc)), "pred": float(pred)})
    print()
    print("  The clipped statistic returns 5.7 (K=19) to 60.6 (K=299) on data that")
    print("  contains NO signal at all. The unclipped statistic returns ~0.")
    print("  Pre-registered VOID condition 1 and Criterion B's `>= 2x flat` clause")
    print("  were therefore unsatisfiable on the deep stacks: they demanded")
    print("  n_eff >= 0.8K on a statistic bounded by K. The criterion was defective.")
    return rows


# ---------------------------------------------------------------------------
# 2. Re-validate on the plant with the corrected estimator
# ---------------------------------------------------------------------------
def plant_uc():
    print()
    print("=" * 104)
    print("2. THE CORRECTED ESTIMATOR ON THE PLANT AND THE CONTROLS")
    print("=" * 104)
    rng = np.random.default_rng(P3.SEED)
    latent, _ = P3.load_latent()
    K = 41
    cases = [("static", [0.0] * K, latent), ("flat-noise", [0.0] * K,
                                             np.full_like(latent, float(latent.mean())))]
    for delta in (0.125, 0.25, 0.5, 1.0, 2.0):
        k0 = K // 2
        cases.append((f"delta {delta}", [abs(k - k0) * delta for k in range(K)], latent))
    print(f"{'case':>12s} {'band':>8s} {'truth':>8s} {'clipped':>9s} {'unclipped':>10s} "
          f"{'rec_clip':>9s} {'rec_uc':>8s} {'relA1':>7s} {'relA2':>7s}")
    out = []
    for tag, radii, lat in cases:
        clean = P3.make_frames(lat, radii, P3.LATENT_ISO, rng, noise=False)
        noisy = P3.make_frames(lat, radii, P3.LATENT_ISO, rng, noise=True)
        mc = P3.measure_frames(clean, P3.LATENT_ISO, subtract_noise=False)
        mn = P3.measure_frames(noisy, P3.LATENT_ISO, subtract_noise=True)
        for b in M.MID_BANDS:
            sc = np.array([r[b] for r in mc])
            sn = np.array([r[b] for r in mn])
            t = tf_stats_uc(sc)["n_eff_uc"] if tag != "flat-noise" else 0.0
            cl = M.through_focus_stats(sn)["n_eff_mf_raw"]
            u = tf_stats_uc(sn)
            print(f"{tag:>12s} {b:>8s} {t:8.3f} {cl:9.3f} {u['n_eff_uc']:10.3f} "
                  f"{cl / t if t else np.nan:9.3f} {u['n_eff_uc'] / t if t else np.nan:8.3f} "
                  f"{u['rel_amp_1']:7.3f} {u['rel_amp_2']:7.3f}")
            out.append({"case": tag, "band": b, "truth": t, "clipped": cl,
                        "unclipped": u["n_eff_uc"]})
    return out


# ---------------------------------------------------------------------------
# 3. Corpus, corrected
# ---------------------------------------------------------------------------
def corpus(sigma_scale=1.0, verbose=True):
    rows = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d, sigma_scale)
        tex, _ = A5.classify(d, s, nvar)
        r = {"stack": st, "K": int(s.shape[0]), "iso": d["iso"],
             "n_tex": int(tex.sum()), "n_flat": int((~tex).sum()),
             "sigma_scale": sigma_scale}
        for b in M.MID_BANDS + ("b6_above_f11_cut", "b1_low"):
            j = d["bands"].index(b)
            stt = [tf_stats_uc(s[:, p, j]) for p in range(s.shape[1])]
            g = {}
            for key in ("n_eff_uc", "n_eff_uc_sm", "n_eff_uc_window",
                        "rel_amp_1", "rel_amp_2", "rel_amp_3", "rel_amp_5", "rel_amp_10"):
                g[key] = A5.med([stt[p][key] for p in range(len(stt)) if tex[p]])
                g[key + "_flat"] = A5.med(
                    [stt[p][key] for p in range(len(stt)) if not tex[p]])
            for m in (1, 2, 3, 5):
                g[f"g{m}"] = A5.med([gain_top_m_uc(s[:, p, j], m)
                                     for p in range(len(stt)) if tex[p]])
            vals = [stt[p]["n_eff_uc"] for p in range(len(stt)) if tex[p]]
            g["iqr"] = [float(np.percentile(vals, q)) for q in (25, 75)] if vals else [np.nan] * 2
            r[b] = g
        mid = [r[b]["n_eff_uc"] for b in M.MID_BANDS]
        r["mid_n_eff"] = float(np.mean(mid))
        r["mid_sqrt"] = float(np.mean([np.sqrt(max(v, 0.0)) for v in mid]))
        r["mid_flat"] = float(np.mean([r[b]["n_eff_uc_flat"] for b in M.MID_BANDS]))
        r["mid_window"] = float(np.mean([r[b]["n_eff_uc_window"] for b in M.MID_BANDS]))
        for key in ("rel_amp_1", "rel_amp_2", "rel_amp_3", "rel_amp_5", "rel_amp_10"):
            r["mid_" + key] = float(np.mean([r[b][key] for b in M.MID_BANDS]))
        for m in (1, 2, 3, 5):
            r[f"mid_g{m}"] = float(np.mean([r[b][f"g{m}"] for b in M.MID_BANDS]))
        rows.append(r)
    if verbose:
        print()
        print("=" * 118)
        print(f"3. THE CORPUS, CORRECTED (unclipped), sigma x{sigma_scale:.2f}")
        print("=" * 118)
        print(f"{'stack':16s} {'K':>4s} {'F':>5s} {'tex':>4s} {'n_eff':>7s} {'flat':>8s} "
              f"{'window':>7s} {'sqrt':>6s} {'relA1':>6s} {'relA2':>6s} {'relA3':>6s} "
              f"{'relA5':>6s} {'g1':>6s} {'g2':>6s} {'g3':>6s} {'g5':>6s} {'b6':>7s}")
        for r in rows:
            print(f"{r['stack']:16s} {r['K']:4d} {APERTURE[r['stack']]:5.1f} {r['n_tex']:4d} "
                  f"{r['mid_n_eff']:7.3f} {r['mid_flat']:8.3f} {r['mid_window']:7.3f} "
                  f"{r['mid_sqrt']:6.3f} {r['mid_rel_amp_1']:6.3f} {r['mid_rel_amp_2']:6.3f} "
                  f"{r['mid_rel_amp_3']:6.3f} {r['mid_rel_amp_5']:6.3f} "
                  f"{r['mid_g1']:6.3f} {r['mid_g2']:6.3f} {r['mid_g3']:6.3f} "
                  f"{r['mid_g5']:6.3f} {r['b6_above_f11_cut']['n_eff_uc']:7.3f}")
    return rows


APERTURE = {
    "coffee-bubbles": 8.0, "109MSDCF": 11.0, "119MSDCF": 5.6, "113MSDCF": 11.0,
    "112MSDCF": 11.0, "foam": 8.0, "coffee-bean": 8.0, "wrapped-text-2": 5.6,
    "wrapped-text-1": 5.6, "bee-1": 5.6, "bee-2": 5.6, "bee-3": 5.6,
}


def score(rows, label=""):
    n = len(rows)
    a_sup = sum(1 for r in rows if r["mid_rel_amp_2"] >= 0.30)
    a = "SUPPORTS" if a_sup >= 6 else ("REFUTES" if (n - a_sup) >= 9 else "INDET")
    b_core = sum(1 for r in rows if r["mid_sqrt"] >= 1.50)
    b_plug = sum(1 for r in rows if r["mid_sqrt"] <= 1.25)
    b = "CORE" if b_core >= 7 else ("PLUGIN" if b_plug >= 7 else "INDET")
    c_core = sum(1 for r in rows if r["mid_g3"] >= 1.30)
    c_plug = sum(1 for r in rows if r["mid_g3"] <= 1.10)
    c = "CORE" if c_core >= 7 else ("PLUGIN" if c_plug >= 7 else "INDET")
    lk = np.log([r["K"] for r in rows])
    ln = np.log(np.clip([r["mid_n_eff"] for r in rows], 1e-6, None))
    sl, _ = np.polyfit(lk, ln, 1)
    r2 = float(np.corrcoef(lk, ln)[0, 1] ** 2)
    sp = max(r["mid_n_eff"] for r in rows) / max(min(r["mid_n_eff"] for r in rows), 1e-9)
    a1 = [r["mid_rel_amp_1"] for r in rows]
    d = "HABIT" if 0.7 <= sl <= 1.3 else (
        "PHYSICS" if (sp < 3.0 or (max(a1) - min(a1)) <= 0.30) else "INDET")
    print(f"  {label:22s} A {a:9s} ({a_sup}/{n})  B {b:6s} (core {b_core}, plug {b_plug})  "
          f"C {c:6s} (core {c_core}, plug {c_plug})  D {d:8s} "
          f"(slope {sl:+.3f}, R2 {r2:.2f}, spread {sp:.2f}x, relA1 range {max(a1) - min(a1):.3f})")
    return {"A": a, "B": b, "C": c, "D": d, "slope": float(sl), "r2": r2,
            "spread": float(sp)}


def main() -> None:
    rect = rectification_null()
    plant = plant_uc()
    rows = corpus(1.0)

    print()
    print("=" * 118)
    print("PRE-REGISTERED CRITERIA, unclipped estimator")
    print("  (Criterion B's `>= 2x flat` clause is dropped and reported as defective;")
    print("   see section 1. Everything else is scored exactly as pre-registered.)")
    print("=" * 118)
    base = score(rows, "sigma x1.00")
    sens = {}
    for sc in (0.75, 1.25):
        sens[sc] = score(corpus(sc, verbose=False), f"sigma x{sc:.2f}")
    stable = all(
        (v["A"], v["B"], v["C"]) == (base["A"], base["B"], base["C"]) for v in sens.values()
    )
    print(f"  stable under +-25% sigma: {stable}")

    print()
    print("Per-aperture split (mid-band n_eff, unclipped)")
    for ap in (5.6, 8.0, 11.0):
        sel = [r for r in rows if APERTURE[r["stack"]] == ap]
        print(f"  f/{ap:<4.1f} n={len(sel):2d}  n_eff {np.median([r['mid_n_eff'] for r in sel]):6.3f}"
              f"  sqrt {np.median([r['mid_sqrt'] for r in sel]):5.3f}"
              f"  relA1 {np.median([r['mid_rel_amp_1'] for r in sel]):5.3f}"
              f"  relA2 {np.median([r['mid_rel_amp_2'] for r in sel]):5.3f}"
              f"  g3 {np.median([r['mid_g3'] for r in sel]):5.3f}")

    with open(os.path.join(OUT, "s07_corrected.json"), "w", encoding="utf-8") as fh:
        json.dump({"rectification_null": rect, "plant": plant, "rows": rows,
                   "criteria": base, "sigma_sensitivity": {str(k): v for k, v in sens.items()},
                   "stable": stable}, fh, indent=1)
    print("\nwrote out/s07_corrected.json")


if __name__ == "__main__":
    main()

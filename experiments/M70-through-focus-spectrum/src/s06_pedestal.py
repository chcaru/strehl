"""M70 s06 - the pedestal: diagnosis, and a bracketed re-score.

s05 fired two pre-registered VOID conditions:

  VOID 1 (floor swamp): on 6 of 12 stacks the FLAT control patches return a
  LARGER n_eff_MF than the textured ones - bee-1 flat 177.4 against textured
  11.7 at K=299. A patch with no signal is reading as "all 299 frames carry
  mid-band signal".

  VOID 3 (sigma sensitivity): scaling the modelled sigma^2 by 0.75x and 1.25x
  moves the corpus-median mid-band n_eff_MF from 12.84 to 5.40, a 2.4x swing,
  and flips Criterion C's count from 12/12 to 8/12.

Both have one cause, and it is the input named in PREREGISTRATION.md section 6
rows 2 and 3: a *frame-invariant positive residual* left behind by the noise
subtraction. Write S_k = |H_k|^2|L|^2 + e where e is that residual. Then

    n_eff_MF = (sum_k |H_k|^2|L|^2 + K.e) / (max_k |H_k|^2|L|^2 + e)

so the residual adds K.e to the numerator and almost nothing to the
denominator. It inflates n_eff_MF additively by about K.e / max_k S_k, which is
why the inflation grows with K and why it is unbounded on a patch with no
signal. It is GENEROUS TO THE PROPOSAL, and it scales with exactly the axis the
corpus was supposed to test.

This script does three things:

 1. MEASURES the residual e per stack, per band, per patch, and tests whether
    it is frame-invariant and whether it scales with signal level (PRNU) or
    sits at a constant offset (noise-model error).
 2. Defines a pedestal-free estimator - subtract a low frame-quantile of S per
    patch per band - and MEASURES its bias on the s03 plant, where truth is
    known. It over-subtracts when the true response is wide, so it is biased
    DOWN: conservative against the proposal.
 3. Re-scores the pre-registered criteria with both estimators, giving a
    BRACKET: raw is biased up, pedestal-free is biased down, truth is between.
    A verdict is only reported as decided if both ends of the bracket agree.

The bracket is a post-hoc refinement. It is declared as such. The
pre-registered point estimates from s05 stand as reported.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
from m70lib import L  # noqa: E402
import s03_plant as P3  # noqa: E402
import s05_analyse as A5  # noqa: E402

OUT = A5.OUT
PED_Q = 5.0  # percentile over frames
STACKS = [
    "coffee-bubbles", "109MSDCF", "119MSDCF", "113MSDCF", "112MSDCF", "foam",
    "coffee-bean", "wrapped-text-2", "wrapped-text-1", "bee-1", "bee-2", "bee-3",
]


def pedestal_free(s, q=PED_Q):
    """s: (K,) or (K,P) or (K,P,B). Subtract the q-th frame percentile."""
    ped = np.percentile(s, q, axis=0)
    return np.clip(s - ped, 0.0, None), ped


# ---------------------------------------------------------------------------
# 1. Diagnose the residual
# ---------------------------------------------------------------------------
def diagnose():
    print("=" * 112)
    print("1. THE RESIDUAL - is it frame-invariant, and does it scale with signal?")
    print("=" * 112)
    print(f"{'stack':16s} {'K':>4s} {'ISO':>5s} {'level':>7s} {'sigma2':>8s} "
          f"{'e_flat':>9s} {'e/sig2':>7s} {'e_ped':>9s} {'ped/sig2':>8s} {'cv_tail':>7s}")
    rows = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d)
        tex, _ = A5.classify(d, s, nvar)
        lvl = float(np.median(d["level"]))
        sig2 = float(np.median(nvar))
        j = [d["bands"].index(b) for b in M.MID_BANDS]
        # residual on the flat control patches, averaged over frames and bands
        if (~tex).any():
            e_flat = float(np.mean(s[:, ~tex, :][:, :, j]))
        else:
            e_flat = np.nan
        # residual from the low frame-quantile on the TEXTURED patches
        _, ped = pedestal_free(s[:, tex, :][:, :, j])
        e_ped = float(np.median(ped))
        # is it frame-invariant? coefficient of variation of S over the
        # bottom-half frames of each textured patch
        cvs = []
        for pi in range(int(tex.sum())):
            for jj in range(len(j)):
                v = np.sort(s[:, tex, :][:, pi, j[jj] if False else jj])
                v = v[: max(2, len(v) // 2)]
                if v.mean() > 0:
                    cvs.append(v.std() / v.mean())
        cv = float(np.median(cvs)) if cvs else np.nan
        print(f"{st:16s} {s.shape[0]:4d} {d['iso']:5.0f} {lvl:7.1f} {sig2:8.1f} "
              f"{e_flat:9.2f} {e_flat / sig2 if np.isfinite(e_flat) else np.nan:7.4f} "
              f"{e_ped:9.2f} {e_ped / sig2:8.4f} {cv:7.3f}")
        rows.append({"stack": st, "K": int(s.shape[0]), "iso": d["iso"], "level": lvl,
                     "sigma2": sig2, "e_flat": e_flat, "e_ped": e_ped, "cv_tail": cv})
    print()
    print("  e_flat  mean residual (P - modelled sigma^2) on FLAT patches, DN^2")
    print("  e_ped   the 5th frame-percentile of the residual on TEXTURED patches, DN^2")
    print("  cv_tail coefficient of variation of S over the least-sharp half of the")
    print("          frames: near 0 means the residual really is frame-invariant.")

    # does the residual scale with signal (PRNU) or sit flat (model error)?
    ok = [r for r in rows if np.isfinite(r["e_flat"])]
    if len(ok) >= 3:
        lv = np.log(np.array([r["level"] for r in ok]))
        le = np.log(np.clip([r["e_flat"] for r in ok], 1e-9, None))
        sl = np.polyfit(lv, le, 1)[0]
        r2 = np.corrcoef(lv, le)[0, 1] ** 2
        print(f"\n  log e_flat vs log level: slope {sl:+.2f} (R2 {r2:.2f}) over {len(ok)} stacks.")
        print("  slope ~2 would indicate PRNU (fixed-pattern, variance ~ (frac.S)^2);")
        print("  slope ~1 would indicate a gain error in the photon-transfer model;")
        print("  slope ~0 would indicate a read-noise offset.")
    return rows


# ---------------------------------------------------------------------------
# 2. What the pedestal-free estimator does to KNOWN truth
# ---------------------------------------------------------------------------
def validate_on_plant():
    print()
    print("=" * 112)
    print("2. THE PEDESTAL-FREE ESTIMATOR ON THE PLANT - measured bias, known truth")
    print("=" * 112)
    rng = np.random.default_rng(P3.SEED)
    latent, mean_dn = P3.load_latent()
    K = 41
    print(f"{'case':>16s} {'band':>8s} {'truth':>8s} {'raw':>8s} {'ped-free':>9s} "
          f"{'rec_raw':>8s} {'rec_ped':>8s}")
    out = []
    cases = [("static", [0.0] * K)]
    for delta in (0.125, 0.25, 0.5, 1.0, 2.0):
        k0 = K // 2
        cases.append((f"delta {delta}", [abs(k - k0) * delta for k in range(K)]))
    for tag, radii in cases:
        clean = P3.make_frames(latent, radii, P3.LATENT_ISO, rng, noise=False)
        noisy = P3.make_frames(latent, radii, P3.LATENT_ISO, rng, noise=True)
        mc = P3.measure_frames(clean, P3.LATENT_ISO, subtract_noise=False)
        mn = P3.measure_frames(noisy, P3.LATENT_ISO, subtract_noise=True)
        for b in M.MID_BANDS:
            sc = np.array([r[b] for r in mc])
            sn = np.array([r[b] for r in mn])
            t = M.through_focus_stats(sc)["n_eff_mf_raw"]
            raw = M.through_focus_stats(sn)["n_eff_mf_raw"]
            spf, _ = pedestal_free(sn)
            pf = M.through_focus_stats(spf)["n_eff_mf_raw"]
            print(f"{tag:>16s} {b:>8s} {t:8.3f} {raw:8.3f} {pf:9.3f} "
                  f"{raw / t:8.3f} {pf / t:8.3f}")
            out.append({"case": tag, "band": b, "truth": t, "raw": raw, "ped_free": pf})
    print()
    print("  The pedestal-free estimator subtracts a low frame-quantile, which on a")
    print("  WIDE true response removes genuine off-peak signal. Its recovery ratio")
    print("  is therefore <= 1 by construction and it is CONSERVATIVE against the")
    print("  deconvolution proposal. The raw estimator is generous. Truth is between.")
    return out


# ---------------------------------------------------------------------------
# 3. Bracketed re-score
# ---------------------------------------------------------------------------
def rescore():
    print()
    print("=" * 112)
    print("3. BRACKETED RE-SCORE - raw (generous) and pedestal-free (conservative)")
    print("=" * 112)
    print(f"{'stack':16s} {'K':>4s} {'n_eff_raw':>10s} {'n_eff_pf':>9s} {'flat_pf':>8s} "
          f"{'sqrt_pf':>8s} {'relA1_pf':>9s} {'relA2_pf':>9s} {'g3_pf':>7s} {'b6_pf':>7s}")
    rows = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d)
        tex, _ = A5.classify(d, s, nvar)
        spf, _ = pedestal_free(s)
        r = {"stack": st, "K": int(s.shape[0]), "iso": d["iso"],
             "n_tex": int(tex.sum()), "n_flat": int((~tex).sum())}
        for b in M.MID_BANDS + ("b6_above_f11_cut",):
            j = d["bands"].index(b)
            stt = [M.through_focus_stats(spf[:, p, j]) for p in range(spf.shape[1])]
            r[b] = {
                "n_eff": A5.med([stt[p]["n_eff_mf_raw"] for p in range(len(stt)) if tex[p]]),
                "n_eff_flat": A5.med(
                    [stt[p]["n_eff_mf_raw"] for p in range(len(stt)) if not tex[p]]),
                "rel_amp_1": A5.med(
                    [stt[p]["rel_amp_1"] for p in range(len(stt)) if tex[p]]),
                "rel_amp_2": A5.med(
                    [stt[p]["rel_amp_2"] for p in range(len(stt)) if tex[p]]),
                "gain3": A5.med([M.mf_gain_over_top_m(spf[:, p, j], 3)
                                 for p in range(len(stt)) if tex[p]]),
                "gain1": A5.med([M.mf_gain_over_top_m(spf[:, p, j], 1)
                                 for p in range(len(stt)) if tex[p]]),
                "gain2": A5.med([M.mf_gain_over_top_m(spf[:, p, j], 2)
                                 for p in range(len(stt)) if tex[p]]),
                "gain5": A5.med([M.mf_gain_over_top_m(spf[:, p, j], 5)
                                 for p in range(len(stt)) if tex[p]]),
            }
        mid = [r[b]["n_eff"] for b in M.MID_BANDS]
        r["mid_n_eff"] = float(np.mean(mid))
        r["mid_sqrt"] = float(np.mean([np.sqrt(max(v, 0.0)) for v in mid]))
        r["mid_flat"] = float(np.mean([r[b]["n_eff_flat"] for b in M.MID_BANDS]))
        r["mid_relA1"] = float(np.mean([r[b]["rel_amp_1"] for b in M.MID_BANDS]))
        r["mid_relA2"] = float(np.mean([r[b]["rel_amp_2"] for b in M.MID_BANDS]))
        for m in (1, 2, 3, 5):
            r[f"mid_g{m}"] = float(np.mean([r[b][f"gain{m}"] for b in M.MID_BANDS]))
        raw = A5.analyse(st)
        r["mid_n_eff_raw"] = raw["mid_n_eff_mf"]
        r["mid_sqrt_raw"] = raw["mid_sqrt_gain"]
        r["mid_relA1_raw"] = raw["mid_rel_amp_1"]
        r["mid_relA2_raw"] = raw["mid_rel_amp_2"]
        r["mid_g3_raw"] = raw["mid_gain_top3"]
        rows.append(r)
        print(f"{st:16s} {r['K']:4d} {r['mid_n_eff_raw']:10.3f} {r['mid_n_eff']:9.3f} "
              f"{r['mid_flat']:8.3f} {r['mid_sqrt']:8.3f} {r['mid_relA1']:9.3f} "
              f"{r['mid_relA2']:9.3f} {r['mid_g3']:7.3f} "
              f"{r['b6_above_f11_cut']['n_eff']:7.3f}")

    n = len(rows)
    print()
    print("Criteria, scored at BOTH ends of the bracket")
    for label, key_sqrt, key_a2, key_g3, key_neff, key_flat in (
        ("raw       (biased UP, generous)", "mid_sqrt_raw", "mid_relA2_raw",
         "mid_g3_raw", "mid_n_eff_raw", None),
        ("ped-free  (biased DOWN, strict)", "mid_sqrt", "mid_relA2", "mid_g3",
         "mid_n_eff", "mid_flat"),
    ):
        a_sup = sum(1 for r in rows if r[key_a2] >= 0.30)
        a = "SUPPORTS" if a_sup >= 6 else ("REFUTES" if (n - a_sup) >= 9 else "INDET")
        if key_flat:
            b_core = sum(1 for r in rows if r[key_sqrt] >= 1.50
                         and r[key_neff] >= 2.0 * r[key_flat])
        else:
            b_core = sum(1 for r in rows if r[key_sqrt] >= 1.50)
        b_plug = sum(1 for r in rows if r[key_sqrt] <= 1.25)
        b = "CORE" if b_core >= 7 else ("PLUGIN" if b_plug >= 7 else "INDET")
        c_core = sum(1 for r in rows if r[key_g3] >= 1.30)
        c_plug = sum(1 for r in rows if r[key_g3] <= 1.10)
        c = "CORE" if c_core >= 7 else ("PLUGIN" if c_plug >= 7 else "INDET")
        print(f"  {label:34s} A {a:9s} ({a_sup}/{n})   B {b:6s} "
              f"(core {b_core}, plug {b_plug})   C {c:6s} (core {c_core}, plug {c_plug})")

    lk = np.log([r["K"] for r in rows])
    for key, lab in (("mid_n_eff_raw", "raw"), ("mid_n_eff", "ped-free")):
        ln = np.log(np.clip([r[key] for r in rows], 1e-6, None))
        sl, _ = np.polyfit(lk, ln, 1)
        r2 = np.corrcoef(lk, ln)[0, 1] ** 2
        sp = max(r[key] for r in rows) / max(min(r[key] for r in rows), 1e-9)
        print(f"  D  {lab:9s} log n_eff vs log K slope {sl:+.3f} (R2 {r2:.3f}), spread {sp:.2f}x")

    with open(os.path.join(OUT, "s06_bracket.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print(f"\nwrote out/s06_bracket.json")
    return rows


def main() -> None:
    diag = diagnose()
    plant = validate_on_plant()
    rows = rescore()
    with open(os.path.join(OUT, "s06_diagnosis.json"), "w", encoding="utf-8") as fh:
        json.dump({"residual": diag, "plant": plant}, fh, indent=1)


if __name__ == "__main__":
    main()

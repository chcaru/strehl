"""M70 s15 - through-focus SYMMETRY on the real corpus.

Scores Criteria E / F / G and VOID 6 / 8 / 9 / 10 of PREREGISTRATION-B.md.
Pure post-processing of out/tfs-*.npz; no new capture, no Rust.

Commissioned by docs/research/M67-focus-correctness.md 7.3, which withdrew its
own claim that real through-focus curves are "measured asymmetric".
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import m70lib as M  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402
import s14_asym_controls as S14  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
STACKS = list(S7.APERTURE.keys())
SEED = 70

# Pre-registered thresholds, copied from PREREGISTRATION-B.md section 3.
E_SYM = 0.05
E_ASYM = 0.15
E_STACKS = 9
G1_SKEWED = 0.45
G1_UNSKEWED = 0.15
G_AGREE_PSF = 0.75
G_AGREE_SCENE = 0.60
VOID10_CENS = 0.25

# CONFOUND envelope, measured by s14 BEFORE these criteria were written.
CONFOUND_MAX = {"A50": 0.0726, "A25": 0.0999, "A10": 0.1451, "g1": 0.4457}


def stats_with_cens(curve: np.ndarray) -> dict:
    """all_stats plus per-fraction censoring flags (VOID 10)."""
    o = {}
    for f in S14.FALL:
        key = f"A{int(100 * f):02d}"
        wn, wf, cn, cf = S14.half_widths(curve, f)
        o[key] = (
            np.nan
            if (not np.isfinite(wn) or not np.isfinite(wf) or (wn + wf) <= 0)
            else (wf - wn) / (wf + wn)
        )
        o[key + "_cens"] = bool(cn or cf)
    g1, g2, trunc = S14.moments(curve)
    o["g1"], o["g2"], o["trunc"] = g1, g2, trunc
    return o


def stack_rows(stack: str, sigma_scale: float = 1.0, mode: str = "intact", rng=None):
    d = A5.load(stack)
    s, nvar = A5.signal(d, sigma_scale)
    tex, _ = A5.classify(d, s, nvar)
    K = s.shape[0]
    rows = []
    for p in np.where(tex)[0]:
        for bname in M.MID_BANDS:
            j = d["bands"].index(bname)
            c = s[:, p, j].astype(np.float64)
            if mode == "reversed":
                c = c[::-1].copy()
            elif mode == "shuffle":
                c = rng.permutation(c)
            r = stats_with_cens(c)
            r["patch"], r["band"] = int(p), bname
            rows.append(r)
    return rows, K, int(tex.sum())


def med(rows, key):
    v = np.array([r[key] for r in rows], dtype=np.float64)
    v = v[np.isfinite(v)]
    return float(np.median(v)) if v.size else float("nan")


def boot_ci(rows, key, rng, reps=2000):
    v = np.array([r[key] for r in rows], dtype=np.float64)
    v = v[np.isfinite(v)]
    if v.size < 4:
        return float("nan"), float("nan")
    idx = rng.integers(0, v.size, size=(reps, v.size))
    b = np.median(v[idx], axis=1)
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def sign_agree(rows, key):
    v = np.array([r[key] for r in rows], dtype=np.float64)
    v = v[np.isfinite(v) & (v != 0.0)]
    if v.size == 0:
        return float("nan"), 0
    pos = float((v > 0).mean())
    return max(pos, 1.0 - pos), v.size


def cens_frac(rows, key):
    v = [r[key + "_cens"] for r in rows]
    return float(np.mean(v)) if v else float("nan")


def hdr(t):
    print("\n" + "=" * 118)
    print(t)
    print("=" * 118)


def main() -> None:
    rng = np.random.default_rng(SEED)
    res = {"stacks": {}, "criteria": {}, "voids": {}}

    hdr("CORPUS SYMMETRY - stack medians over textured patches x 3 mid bands")
    print(
        f"{'stack':<16}{'f/':>5}{'K':>6}{'tex':>5}{'n':>6}"
        f"{'A50':>9}{'[95% CI]':>18}{'A25':>9}{'A10':>9}{'g1':>9}{'g2':>9}"
    )
    for st in STACKS:
        rows, K, ntex = stack_rows(st)
        lo, hi = boot_ci(rows, "A50", rng)
        e = {
            "aperture": S7.APERTURE[st],
            "K": K,
            "n_tex": ntex,
            "n": len(rows),
            "A50": med(rows, "A50"),
            "A50_ci": [lo, hi],
            "A25": med(rows, "A25"),
            "A10": med(rows, "A10"),
            "g1": med(rows, "g1"),
            "g2": med(rows, "g2"),
            "agree_A50": sign_agree(rows, "A50")[0],
            "agree_A25": sign_agree(rows, "A25")[0],
            "agree_A10": sign_agree(rows, "A10")[0],
            "agree_g1": sign_agree(rows, "g1")[0],
            "cens50": cens_frac(rows, "A50"),
            "cens25": cens_frac(rows, "A25"),
            "cens10": cens_frac(rows, "A10"),
            "trunc": float(np.mean([r["trunc"] for r in rows])),
        }
        res["stacks"][st] = e
        print(
            f"{st:<16}{S7.APERTURE[st]:>5.1f}{K:>6}{ntex:>5}{len(rows):>6}"
            f"{e['A50']:>+9.4f}   [{lo:>+6.4f},{hi:>+6.4f}]"
            f"{e['A25']:>+9.4f}{e['A10']:>+9.4f}{e['g1']:>+9.4f}{e['g2']:>+9.3f}"
        )

    S = res["stacks"]
    hdr("CENSORING (VOID 10: >25% censored at a fraction => that A_f is unusable)")
    print(f"{'stack':<16}{'cens50':>9}{'cens25':>9}{'cens10':>9}{'trunc(g)':>10}")
    for st in STACKS:
        e = S[st]
        print(
            f"{st:<16}{e['cens50']:>9.3f}{e['cens25']:>9.3f}"
            f"{e['cens10']:>9.3f}{e['trunc']:>10.3f}"
        )
    for f in ("50", "25", "10"):
        worst = max(S[st][f"cens{f}"] for st in STACKS)
        n_over = sum(1 for st in STACKS if S[st][f"cens{f}"] > VOID10_CENS)
        res["voids"][f"VOID10_A{f}"] = {"worst": worst, "n_over": n_over}
        v = "FIRES" if n_over > 0 else "does not fire"
        print(f"  A{f}: worst {worst:.3f}, {n_over}/12 stacks over 0.25 -> VOID 10 {v}")

    hdr("PLACEBOS ON REAL DATA (VOID 6 reversal, VOID 9 frame shuffle)")
    print(f"{'stack':<16}{'A50 fwd':>10}{'A50 rev':>10}{'|f+r|':>9}{'A50 shuf':>10}")
    worst_rev, shuf = 0.0, []
    for st in STACKS:
        r_rev, _, _ = stack_rows(st, mode="reversed")
        r_shf, _, _ = stack_rows(st, mode="shuffle", rng=np.random.default_rng(SEED))
        fwd, rev, sh = S[st]["A50"], med(r_rev, "A50"), med(r_shf, "A50")
        d = abs(fwd + rev)
        worst_rev = max(worst_rev, d)
        shuf.append(abs(sh))
        S[st]["A50_rev"], S[st]["A50_shuf"] = rev, sh
        print(f"{st:<16}{fwd:>+10.4f}{rev:>+10.4f}{d:>9.5f}{sh:>+10.4f}")
    med_int = float(np.median([abs(S[st]["A50"]) for st in STACKS]))
    med_shuf = float(np.median(shuf))
    res["voids"]["VOID6"] = {"worst": worst_rev, "fires": worst_rev > 0.02}
    res["voids"]["VOID9"] = {
        "median_abs_intact": med_int,
        "median_abs_shuffled": med_shuf,
        "fires": med_shuf > med_int,
    }
    print(f"\n  VOID 6 worst |fwd+rev| = {worst_rev:.6f} (bar 0.02) -> "
          f"{'FIRES' if worst_rev > 0.02 else 'does not fire'}")
    print(f"  VOID 9 median |A50| intact {med_int:.4f} vs shuffled {med_shuf:.4f} -> "
          f"{'FIRES' if med_shuf > med_int else 'does not fire'}")

    hdr("CRITERION E - symmetric, asymmetric-beyond-confound, or indeterminate")
    for key in ("A50", "A25", "A10"):
        vals = np.array([S[st][key] for st in STACKS])
        n_sym = int((np.abs(vals) < E_SYM).sum())
        n_asym = int((np.abs(vals) >= E_ASYM).sum())
        pos = int((vals > 0).sum())
        n_asym_cons = max(
            int(((vals >= E_ASYM)).sum()), int(((vals <= -E_ASYM)).sum())
        )
        res["criteria"][f"E_{key}"] = {
            "median_of_medians": float(np.median(vals)),
            "n_below_0.05": n_sym,
            "n_at_or_above_0.15": n_asym,
            "n_consistent_sign_asym": n_asym_cons,
            "n_positive": pos,
            "confound_max": CONFOUND_MAX[key],
            "n_inside_confound": int((np.abs(vals) <= CONFOUND_MAX[key]).sum()),
        }
        print(
            f"  {key}: median-of-medians {np.median(vals):+.4f}   "
            f"|A|<0.05 on {n_sym}/12   |A|>=0.15 same sign on {n_asym_cons}/12   "
            f"sign +{pos}/-{12 - pos}   inside confound envelope "
            f"({CONFOUND_MAX[key]:.4f}) {int((np.abs(vals) <= CONFOUND_MAX[key]).sum())}/12"
        )
    sym_all = all(
        res["criteria"][f"E_{k}"]["n_below_0.05"] >= E_STACKS
        for k in ("A50", "A25", "A10")
    )
    asym_any = any(
        res["criteria"][f"E_{k}"]["n_consistent_sign_asym"] >= E_STACKS
        for k in ("A50", "A25", "A10")
    )
    verdict_e = (
        "ASYMMETRIC" if asym_any else ("SYMMETRIC" if sym_all else "INDETERMINATE")
    )
    res["criteria"]["E_verdict"] = verdict_e
    print(f"\n  CRITERION E => {verdict_e}")

    hdr("CRITERION F - skew and kurtosis, SEPARATELY (M67 prerequisite (a))")
    g1v = np.array([S[st]["g1"] for st in STACKS])
    n_unskew = int((np.abs(g1v) < G1_UNSKEWED).sum())
    n_skew = max(int((g1v >= G1_SKEWED).sum()), int((g1v <= -G1_SKEWED).sum()))
    verdict_f1 = (
        "SKEWED" if n_skew >= E_STACKS
        else ("UNSKEWED" if n_unskew >= E_STACKS else "INDETERMINATE")
    )
    print(f"  g1 median-of-medians {np.median(g1v):+.4f}   |g1|<0.15 on {n_unskew}/12   "
          f"|g1|>=0.45 same sign on {n_skew}/12  =>  {verdict_f1}")

    g2v = np.array([S[st]["g2"] for st in STACKS])
    Kv = np.array([S[st]["K"] for st in STACKS], dtype=np.float64)
    rho = float(np.corrcoef(np.log(Kv), g2v)[0, 1])
    print(f"\n  g2 median-of-medians {np.median(g2v):+.3f}   range "
          f"[{g2v.min():+.3f}, {g2v.max():+.3f}]")
    print(f"  corr(log K, g2) = {rho:+.3f}   (K is the step-density proxy)")
    print("  NULL-SYM, a plant SYMMETRIC BY CONSTRUCTION, gave g2 = -0.63 / +0.86 / +6.13")
    print("  at delta = 0.25 / 0.50 / 1.00 px/step. g2 tracks curve width relative to the")
    print("  moment window, not tail weight. Pre-registered as NOT TESTABLE against fact 274.")
    res["criteria"]["F"] = {
        "g1_median": float(np.median(g1v)),
        "g1_verdict": verdict_f1,
        "n_unskewed": n_unskew,
        "n_skewed": n_skew,
        "g2_median": float(np.median(g2v)),
        "g2_min": float(g2v.min()),
        "g2_max": float(g2v.max()),
        "g2_corr_logK": rho,
        "g2_verdict": "NOT TESTABLE (pre-registered)",
    }

    hdr("CRITERION G - PSF-like or scene-like? (M25 question 33)")
    print(f"{'stack':<16}{'agree A50':>11}{'agree A25':>11}{'agree A10':>11}{'agree g1':>10}")
    for st in STACKS:
        e = S[st]
        print(f"{st:<16}{e['agree_A50']:>11.3f}{e['agree_A25']:>11.3f}"
              f"{e['agree_A10']:>11.3f}{e['agree_g1']:>10.3f}")
    ag = np.array([S[st]["agree_A50"] for st in STACKS])
    vals = np.array([S[st]["A50"] for st in STACKS])
    same_sign = max(int((vals > 0).sum()), int((vals < 0).sum()))
    med_ag = float(np.median(ag))
    verdict_g = (
        "PSF-LIKE" if (med_ag >= G_AGREE_PSF and same_sign >= E_STACKS)
        else ("SCENE-LIKE" if med_ag <= G_AGREE_SCENE else "INDETERMINATE")
    )
    print(f"\n  median within-stack sign agreement (A50) {med_ag:.3f}   "
          f"stack medians same sign {same_sign}/12  =>  {verdict_g}")
    void8 = med_int <= CONFOUND_MAX["A50"]
    res["voids"]["VOID8"] = {
        "corpus_median_absA50": med_int,
        "confound_max_A50": CONFOUND_MAX["A50"],
        "fires": bool(void8),
    }
    print(f"  VOID 8: corpus median |A50| {med_int:.4f} vs CONFOUND max "
          f"{CONFOUND_MAX['A50']:.4f} -> {'FIRES' if void8 else 'does not fire'}")
    if void8:
        verdict_g = "INDETERMINATE (VOID 8)"
    res["criteria"]["G_verdict"] = verdict_g
    res["criteria"]["G_median_agreement"] = med_ag

    hdr("STEP-DENSITY AND APERTURE SPLITS")
    print(f"{'group':<22}{'n':>4}{'A50':>10}{'A25':>10}{'A10':>10}{'g1':>10}{'g2':>10}")
    groups = {
        "K <= 33 (sparse)": [s for s in STACKS if S[s]["K"] <= 33],
        "63 <= K <= 130": [s for s in STACKS if 63 <= S[s]["K"] <= 130],
        "K = 299 (dense)": [s for s in STACKS if S[s]["K"] == 299],
        "f/5.6": [s for s in STACKS if S7.APERTURE[s] == 5.6],
        "f/8": [s for s in STACKS if S7.APERTURE[s] == 8.0],
        "f/11": [s for s in STACKS if S7.APERTURE[s] == 11.0],
    }
    res["groups"] = {}
    for g, mem in groups.items():
        row = {k: float(np.median([S[s][k] for s in mem])) for k in
               ("A50", "A25", "A10", "g1", "g2")}
        row["n"] = len(mem)
        res["groups"][g] = row
        print(f"{g:<22}{len(mem):>4}{row['A50']:>+10.4f}{row['A25']:>+10.4f}"
              f"{row['A10']:>+10.4f}{row['g1']:>+10.4f}{row['g2']:>+10.3f}")

    hdr("SIGMA SENSITIVITY (M69 is live on FOCUS_NOISE_SD; this uses the PT model)")
    print(f"{'sigma x':<10}{'med |A50|':>12}{'med A50':>12}{'med g1':>12}{'med g2':>12}")
    res["sigma"] = {}
    for sc in (0.91, 1.00, 1.09, 1.25):
        a50, g1s, g2s = [], [], []
        for st in STACKS:
            rows, _, _ = stack_rows(st, sigma_scale=sc)
            a50.append(med(rows, "A50"))
            g1s.append(med(rows, "g1"))
            g2s.append(med(rows, "g2"))
        e = {
            "median_absA50": float(np.median(np.abs(a50))),
            "median_A50": float(np.median(a50)),
            "median_g1": float(np.median(g1s)),
            "median_g2": float(np.median(g2s)),
        }
        res["sigma"][f"{sc:.2f}"] = e
        print(f"{sc:<10.2f}{e['median_absA50']:>12.4f}{e['median_A50']:>+12.4f}"
              f"{e['median_g1']:>+12.4f}{e['median_g2']:>+12.3f}")

    with open(os.path.join(OUT, "s15_asym_corpus.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s15_asym_corpus.json")


if __name__ == "__main__":
    main()

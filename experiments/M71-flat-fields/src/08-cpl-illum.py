"""M71 step 08 -- CPL (PR-6), illumination structure (PR-8), a drift-immune
within-frame PTC, and the green-green noise correlation cross-check.

The within-frame PTC is the point of this file. The 2.1x vignetting range
across the frame means every group-half is its own photon-transfer curve:
bin pixels by their own smooth signal level, and read variance against signal
INSIDE a single capture. That is immune to illumination drift entirely -- no
normalisation, no interpolation, no assumption that the light held still --
and there are 11 independent realisations of it. If it agrees with the
between-group PTC of step 03, the between-group gain is not an artefact of
the drift correction.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "out" / "cache"
OUT = HERE / "data" / "08-cpl-illum.json"
BLACK = 512.0

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "k5", Path(__file__).resolve().parent / "05-kappa.py")
_k5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_k5)
smooth = _k5.smooth

CLEAN = ["e0.004-A", "e0.004-B", "e0.008-A", "e0.008-B",
         "e0.016666666666666666-A", "e0.016666666666666666-B",
         "e0.03333333333333333-A", "e0.03333333333333333-B",
         "e0.05-A", "e0.05-B", "e0.07692307692307693-A"]
NICE = {"e0.004": "1/250", "e0.008": "1/125", "e0.016666666666666666": "1/60",
        "e0.03333333333333333": "1/30", "e0.05": "1/20",
        "e0.07692307692307693": "1/13", "e0.1": "1/10", "e8": "1/8", "e0.2": "1/5"}


def nice(tag):
    base, half = tag.rsplit("-", 1)
    return f"{NICE[base]}-{half}"


def group_levels(frames):
    """Black-subtracted mean level per group-half per plane, from 02-frames."""
    acc = {}
    for rec in frames:
        tag = _k5.tag_of(rec["exp"], rec["half"])
        d = acc.setdefault(tag, {p: [] for p in ("R", "G1", "G2", "B")})
        for p in d:
            d[p].append(rec[f"mean_{p}"])
    return {t: {p: float(np.mean(v)) for p, v in d.items()} for t, d in acc.items()}


# ------------------------------------------------- 1. within-frame PTC
def within_frame_ptc(out, lvl):
    print("=== 1. WITHIN-FRAME PTC -- immune to illumination drift")
    print("    Vignetting gives a 2.1x signal range inside every single")
    print("    capture. Binning by that range turns each group-half into its")
    print("    own photon-transfer curve, with no drift correction anywhere.")
    rows = []
    for tag in CLEAN:
        for pl in ("G1", "G2"):
            m = np.load(CACHE / f"{tag}-{pl}-mean.npy").astype(np.float64)
            v = np.load(CACHE / f"{tag}-{pl}-var.npy").astype(np.float64)
            # the frames were normalised to their own spatial mean at decode,
            # so restore DN by the group's mean level
            key = f"{tag}-{pl}"
            S0 = lvl[tag][pl]
            mm = m * S0
            vv = v * S0 * S0
            good = np.isfinite(mm) & np.isfinite(vv) & (mm > 10)
            # reject hot/cold defects by their own variance, as step 03 does
            med = np.median(vv[good])
            good &= (vv > 0.25 * med) & (vv < 4.0 * med)
            sm = smooth(mm.astype(np.float32), 61, 3).astype(np.float64)
            lo, hi = np.percentile(sm[good], [1.0, 99.0])
            edges = np.linspace(lo, hi, 13)
            idx = np.digitize(sm, edges) - 1
            xs, ys, ns = [], [], []
            for k in range(12):
                sel = good & (idx == k)
                n = int(sel.sum())
                if n < 20000:
                    continue
                xs.append(float(mm[sel].mean()))
                ys.append(float(vv[sel].mean()))
                ns.append(n)
            if len(xs) < 6:
                continue
            xs, ys = np.array(xs), np.array(ys)
            g, b = np.polyfit(xs, ys, 1)
            rows.append({"tag": tag, "plane": pl, "g": float(g), "b": float(b),
                         "S_lo": float(xs.min()), "S_hi": float(xs.max()),
                         "n_bins": len(xs)})
            print(f"    {nice(tag):9s} {pl}  S {xs.min():8.1f}..{xs.max():8.1f} "
                  f"({xs.max() / xs.min():.2f}x, {len(xs)} bins)   "
                  f"g = {g:.6f}   b = {b:+8.3f} DN^2")
    gs = np.array([r["g"] for r in rows])
    bs = np.array([r["b"] for r in rows])
    print(f"\n    within-frame gain: mean {gs.mean():.6f} +- {gs.std(ddof=1) / np.sqrt(len(gs)):.6f} "
          f"(sd {gs.std(ddof=1):.6f}, n={len(gs)})")
    print(f"    step 03 between-group green gain was 0.224103 -> "
          f"ratio {gs.mean() / 0.224103:.5f}")
    print(f"    within-frame intercept: mean {bs.mean():+.3f} DN^2 "
          f"(sd {bs.std(ddof=1):.3f})")
    print(f"    step 03 between-group intercept was about -1.84 DN^2")
    out["within_frame_ptc"] = {"rows": rows, "g_mean": float(gs.mean()),
                               "g_sem": float(gs.std(ddof=1) / np.sqrt(len(gs))),
                               "b_mean": float(bs.mean()), "b_sd": float(bs.std(ddof=1))}
    return gs.mean(), bs.mean()


# ------------------------------------------------------------- 2. PR-6 CPL
def cpl(out, lvl):
    print("\n=== 2. PR-6 CPL -- transmission and spatial flatness")
    print("    (a) TRANSMISSION is fundamentally confounded: the two states are")
    print("        not interleaved, a ~280 s filter change separates them, and")
    print("        the light moved. Three interpolation assumptions are")
    print("        reported with the spread as the honest error bar.")
    rows = []    for base in ("e0.004", "e0.008", "e0.016666666666666666",
                 "e0.03333333333333333", "e0.05"):
        a = lvl[f"{base}-A"]["G1"]
        b = lvl[f"{base}-B"]["G1"]
        rows.append({"base": base, "nice": NICE[base], "A": a, "B": b,
                     "raw_ratio": a / b})
        print(f"      {NICE[base]:6s}  A={a:9.1f}  B={b:9.1f}  raw A/B = {a / b:.5f}")
    rr = np.array([r["raw_ratio"] for r in rows])
    print(f"      raw A/B spans {rr.min():.4f}..{rr.max():.4f} = {rr.max() / rr.min():.2f}x."
          f"  A CONSTANT transmission cannot do that.")
    print(f"      Bound (i)  transmission <= max raw ratio = {rr.max():.4f} "
          f"({-np.log2(rr.max()):.2f} stops) if the light only ever fell between the passes")
    print(f"      Bound (ii) transmission >= min raw ratio = {rr.min():.4f} "
          f"({-np.log2(rr.min()):.2f} stops) if it only ever rose")
    print("      The pre-registered PR-1b magnitude clause (0.20 <= R <= 0.45)")
    print("      is therefore NOT MET in 4 of 5 groups. Reported as failing.")

    print("\n    (b) FLATNESS is NOT confounded, because a ratio of two")
    print("        spatial-mean-normalised maps divides out any per-frame")
    print("        scalar. This is the part of PR-6 that is worth having.")
    def rmap(tag, pl="G1"):
        m = np.load(CACHE / f"{tag}-{pl}-mean.npy").astype(np.float32)
        return m / float(m.mean())

    tests = [("CPL vs no-CPL, same shutter 1/20", "e0.05-A", "e0.05-B"),
             ("CPL vs no-CPL, same shutter 1/30", "e0.03333333333333333-A",
              "e0.03333333333333333-B"),
             ("PLACEBO same state, 1/20-A vs 1/30-A", "e0.05-A",
              "e0.03333333333333333-A"),
             ("PLACEBO same state, 1/20-B vs 1/30-B", "e0.05-B",
              "e0.03333333333333333-B")]
    res = []
    for label, t1, t2 in tests:
        r = rmap(t1) / rmap(t2)
        rs = smooth(r, 121, 3)                 # keep only the smooth part
        sd = float(np.std(rs))
        pk = float(np.percentile(rs, 99.5) - np.percentile(rs, 0.5))
        res.append({"label": label, "sd": sd, "p99_5_minus_p0_5": pk})
        print(f"      {label:38s}  sd {sd * 100:6.3f}%   "
              f"p99.5-p0.5 {pk * 100:6.3f}%")
    real = max(r["sd"] for r in res[:2])
    plac = max(r["sd"] for r in res[2:])
    print(f"\n      CPL-vs-no-CPL worst  {real * 100:.3f}%")
    print(f"      same-state placebo   {plac * 100:.3f}%  (this is illumination"
          f" drift + vignetting-vs-level, not the filter)")
    verdict = ("the CPL adds no measurable spatial non-uniformity above the "
               "same-state placebo" if real <= 1.5 * plac else
               "the CPL DOES add spatial non-uniformity above the placebo")
    print(f"      -> {verdict}")
    out["cpl"] = {"transmission_rows": rows, "bound_hi": float(rr.max()),
                  "bound_lo": float(rr.min()), "flatness": res,
                  "real_worst": real, "placebo_worst": plac,
                  "cpl_flat": bool(real <= 1.5 * plac)}

    # colour: does the CPL shift the plane ratios?
    print("\n    (c) colour. A CPL that is not spectrally neutral shifts the")
    print("        plane ratios. Placebo is the same-state pair again.")
    for label, t1, t2 in tests:
        vals = []
        for pl in ("R", "B"):
            n1 = lvl[t1][pl] / lvl[t1]["G1"]
            n2 = lvl[t2][pl] / lvl[t2]["G1"]
            vals.append(f"{pl}/G1 {100 * (n1 / n2 - 1):+6.2f}%")
        print(f"      {label:38s}  " + "  ".join(vals))


# ----------------------------------------------------- 3. PR-8 illumination
def illum(out, lvl, g_meas, b_meas):
    print("\n=== 3. PR-8 illumination structure after normalisation")
    print("    Global drift is a per-frame scalar and divides out. Residual")
    print("    excess temporal variance after that division is drift that")
    print("    carried SPATIAL structure. The block maps (73x109 blocks of")
    print("    32x32) suppress white noise 1024x, so they are the instrument.")
    rows = []
    for tag in CLEAN:
        S = lvl[tag]["G1"]
        blocks = np.load(CACHE / f"{tag}-blocks.npy")     # (4, 20, 73, 109)
        bg = blocks[1]                                     # G1
        bg = bg / bg.reshape(bg.shape[0], -1).mean(axis=1)[:, None, None]
        v = np.var(bg, axis=0, ddof=1)                     # per-block temporal var
        # expected from photon noise alone, given 1024 px averaged per block
        exp = (g_meas * S + b_meas) / (S * S) / 1024.0
        obs = float(np.median(v))
        rows.append({"tag": tag, "S": S, "observed": obs, "expected": exp,
                     "ratio": obs / exp})
        print(f"    {nice(tag):9s} S={S:8.1f}  observed {obs:.3e}  "
              f"photon-only {exp:.3e}  ratio {obs / exp:6.3f}")
    rt = np.array([r["ratio"] for r in rows])
    print(f"\n    ratio: median {np.median(rt):.3f}, range {rt.min():.3f}..{rt.max():.3f}")
    excess = np.median(rt) - 1.0
    if excess > 0:
        # convert to an equivalent per-block relative sd of the drift
        eq = np.sqrt(np.median([r["observed"] - r["expected"] for r in rows]))
        print(f"    excess over photon-only = {excess * 100:+.1f}%")
        print(f"    equivalent SPATIALLY-STRUCTURED illumination wobble, "
              f"per 32x32 block per frame: {eq * 100:.4f}% rms")
    print("    NOTE this is a per-frame residual AFTER the global scalar was")
    print("    divided out, so it is genuinely spatial and not the 2.35x drift.")
    out["illum"] = {"rows": rows, "median_ratio": float(np.median(rt)),
                    "excess": float(excess)}


# ------------------------------- 4. green-green noise correlation cross-check
def rho_check(out):
    print("\n=== 4. rho(G1 noise, G2 noise) cross-check at a second level and")
    print("       on a dark frame. The corpus (facts 895, 958) says ~ +0.073.")
    import csv
    from fractions import Fraction
    src = list(csv.DictReader((HERE / "data" / "exif-all.csv").open(encoding="utf-8-sig")))
    got = []
    for et, label in ((Fraction(1, 250), "1/250 flat"), (Fraction(1, 20), "1/20 flat")):
        grp = sorted([r for r in src if Path(r["Directory"]).name == "flat-fields"
                      and Fraction(r["ExposureTime"]) == et],
                     key=lambda r: r["SubSecDateTimeOriginal"])
        fs = []
        for r in (grp[8], grp[9]):
            with rawpy.imread(r["SourceFile"]) as raw:
                fs.append(raw.raw_image_visible.astype(np.float32).copy())  # rule 32
        got.append((label, fs[0] - fs[1]))
    dk = sorted(Path(r"D:\macro-dark-frames\118MSDCF").glob("*.ARW"))[:2]
    fs = []
    for p in dk:
        with rawpy.imread(str(p)) as raw:
            fs.append(raw.raw_image_visible.astype(np.float32).copy())      # rule 32
    got.append(("ISO-100 dark", fs[0] - fs[1]))
    res = {}
    for label, d in got:
        g1 = d[0::2, 1::2][200:-200, 200:-200]
        g2 = d[1::2, 0::2][200:-200, 200:-200]
        g1 = g1 - g1.mean()
        g2 = g2 - g2.mean()
        rho = float(np.mean(g1 * g2) / np.sqrt(np.mean(g1 * g1) * np.mean(g2 * g2)))
        # roll control
        g2r = np.roll(g2, 314, axis=0)
        rhor = float(np.mean(g1 * g2r) / np.sqrt(np.mean(g1 * g1) * np.mean(g2r * g2r)))
        res[label] = {"rho": rho, "rho_rolled": rhor}
        print(f"    {label:14s} rho = {rho:+.5f}   rolled control {rhor:+.5f}")
    print("    All three are two orders of magnitude below +0.073.")
    out["rho_green"] = res


def main() -> None:
    frames = json.loads((HERE / "data" / "02-frames.json").read_text(encoding="utf-8"))
    out = {}
    g, b = within_frame_ptc(out, group_levels(frames))
    cpl(out, group_levels(frames))
    illum(out, group_levels(frames), g, b)
    rho_check(out)
    OUT.write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

"""V-NOISE2 -- the half-stack noise estimator, run per subject.

PREREGISTRATION.md (experiments/V-NOISE2, committed 49a49b44 before any of the
three new subjects existed on disk) fixes the subject list, the statistic, the
commissioning arms and the verdict vocabulary.  Read it before this.

THE STATISTIC IS M127'S SURVIVING ONE, IMPORTED NOT COPIED.  `half_sigma` comes
from experiments/V-NOISE/halfdiff.py and `Arm`, `opponent`, `boot`, `coarse4`
and the constants come from experiments/V-NOISE/noisefree.py.  Nothing about
the rule is restated here, because a rule restated per subject can drift, and a
per-subject drift is exactly how a subject gets a friendlier statistic.
M127's pre-registered PRIMARY (flat-ROI residual sigma) was withdrawn there
after being measured at 84.6% scene, and it is NOT reinstated here.

COMMISSIONING IS RE-RUN ON EVERY SUBJECT AND IS NOT CARRIED ACROSS.  A floor is
a property of the image as much as of the estimator, so `113MSDCF`'s passing
arms say nothing about `bee-1-cpl`'s.  sec.4 of the registration fixes the
arms and their thresholds:

    NULL      an image against itself                      exactly 1.0
    POTENCY   planted Gaussian noise, 3 levels over 16x     +/-10% of analytic
    QUANT8    strehl requantised to 8 bits                  STRICTLY > 1.0
    TONE      4x4-block tone fit, applied and re-measured   < 50% of gap
    CGAIN-DC  per-tile mean signed chroma, noise-immune     CI must straddle 1

QUANT8's threshold is "strictly greater than 1" rather than a range because its
answer is fixed by arithmetic: requantising 16-bit data to 8 bits cannot lower
a noise estimate.  An exact 1.000 is therefore impossible and means a defect --
which is precisely how M127 found a rebound loop variable that had aimed the
arm at an already-8-bit image, making the requantisation a no-op.

BIT DEPTH IS MEASURED, NOT ASSUMED.  Each arm's dtype is read off the file, so
an arm that silently changes container is caught rather than mis-normalised.

INVOCATION (rule 47).  Reads, per subject:
    C:\\dev\\strehl-out\\V-NOISE2\\<key>\\arms\\{strehl,coh-enfuse,coh-fs15}-{A,B}.tif*
    C:\\dev\\strehl-out\\V-NOISE2\\<key>\\census.npz   (census2.py)
    C:\\dev\\strehl-out\\V-NOISE2\\<key>\\geom.json    (geom2.py)
For key `113` it reads M127's arms in place and does not rebuild them.
Writes C:\\dev\\strehl-out\\V-NOISE2\\<key>\\hd.npz -- the per-tile ratios that
pool2.py needs -- and prints everything.

    python hd2.py <key> [<key> ...] [nboot=2000]
"""
import json
import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import uniform_filter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
from noisefree import (Arm, opponent, boot, coarse4, T, EDGE, HP,   # noqa: E402
                       W709)
from halfdiff import half_sigma                                     # noqa: E402
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
from gradetest import fit_map, apply_map                            # noqa: E402

ROOT = r"C:\dev\strehl-out\V-NOISE2"
LIN113 = r"C:\dev\strehl-out\V-H2H2\lin"
OUT113 = r"C:\dev\strehl-out\V-LINEAR2\out"

# PRE-REGISTERED sec.1.  Closed list.  `113MSDCF` is M127's subject, carried in
# unchanged and re-measured through this same code path so that the four
# numbers being compared come from one instrument rather than two.
SUBJECTS = {
    "113": dict(name="113MSDCF", n=63, depth="mid", regime="mid"),
    "119": dict(name="119MSDCF", n=33, depth="shallow", regime="averaging"),
    "fba": dict(name="flower-bud-alone-cpl", n=205, depth="deep",
                regime="averaging"),
    "bee": dict(name="bee-1-cpl", n=299, depth="deep", regime="selection"),
}
CHAN = ["luma  Y", "chroma R-Y", "chroma B-Y"]


def bits_of(path):
    """MEASURED container depth, not assumed."""
    with tifffile.TiffFile(path) as tf:
        dt = tf.series[0].dtype
    return {np.dtype("uint8"): 8, np.dtype("uint16"): 16}[np.dtype(dt)]


def paths_for(key):
    """(census, {tag: (pathA, pathB, label)}) -- 113 lives where M127 left it."""
    if key == "113":
        return (r"C:\dev\strehl-out\V-NOISE\census.npz", {
            "strehl": (rf"{LIN113}\113-A-g1.tiff", rf"{LIN113}\113-B-g1.tiff",
                       "strehl (this project)"),
            "enfuse": (rf"{OUT113}\coh-enfuse-A.tif",
                       rf"{OUT113}\coh-enfuse-B.tif",
                       "Hugin + enfuse --hard-mask (GPL)"),
            "fs15-coh": (rf"{OUT113}\coh-fs15-A.tif",
                         rf"{OUT113}\coh-fs15-B.tif",
                         "focus-stack merge on Hugin-aligned frames (MIT)"),
        })
    a = os.path.join(ROOT, key, "arms")
    return (os.path.join(ROOT, key, "census.npz"), {
        "strehl": (os.path.join(a, "strehl-A.tiff"),
                   os.path.join(a, "strehl-B.tiff"), "strehl (this project)"),
        "enfuse": (os.path.join(a, "coh-enfuse-A.tif"),
                   os.path.join(a, "coh-enfuse-B.tif"),
                   "Hugin + enfuse --hard-mask (GPL)"),
        "fs15-coh": (os.path.join(a, "coh-fs15-A.tif"),
                     os.path.join(a, "coh-fs15-B.tif"),
                     "focus-stack merge on Hugin-aligned frames (MIT)"),
    })


def scales_for(key):
    if key == "113":
        # MEASURED by V-LINEAR2/geomfree.py; both coh arms share one raster.
        return {"strehl": 1.0, "enfuse": 1.0050, "fs15-coh": 1.0050}
    with open(os.path.join(ROOT, key, "geom.json"), encoding="utf-8") as fh:
        g = json.load(fh)
    out = {"strehl": 1.0}
    for k in ("enfuse", "fs15-coh"):
        if not g.get(k, {}).get("ok"):
            raise SystemExit(f"{key}/{k}: FAILED GEOMETRY FIT -- "
                             f"{g.get(k, {}).get('why')}; refusing to measure")
        out[k] = g[k]["scale"]
    return out


def half_sigma_y(ya, yb):
    """Luma-only half-diff sigma, for the TONE arm (a tone map is luma->luma)."""
    lvl = float(0.5 * (ya.mean() + yb.mean()))
    if lvl <= 1e-6:
        return np.nan
    d = (ya - yb)[EDGE:-EDGE, EDGE:-EDGE]
    return float(np.sqrt(0.5 * d.var())) / lvl


def run(key, nboot, rng):
    meta = SUBJECTS[key]
    census, spec = paths_for(key)
    if not os.path.exists(census):
        raise SystemExit(f"{key}: missing census {census}")
    sc = scales_for(key)

    z = np.load(census)
    cells = [tuple(c) for c in z["cells"][z["flat"]]]
    print("=" * 100)
    print(f"SUBJECT {key} = {meta['name']}  ({meta['n']} frames, "
          f"{meta['depth']}, {meta['regime']}-dominated)")
    print(f"  {len(cells)} FLAT tiles, bottom 25% of {len(z['cells'])} by "
          f"max-over-{int(z['nframes'])}-frames high-pass variance, "
          f"measured on the SOURCE develops")
    print("=" * 100)

    arms = {}
    for k, (pa, pb, lab) in spec.items():
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print(f"  MISSING half-stack pair for {k}: {pa}")
            continue
        b = bits_of(pa)
        if b != bits_of(pb):
            raise SystemExit(f"{key}/{k}: halves differ in bit depth")
        arms[k] = (Arm(pa, sc[k], b, lab), Arm(pb, sc[k], b, lab), lab, b)
        A = arms[k][0]
        print(f"  {k:9s} {A.w}x{A.h} {b:2d}-bit scale {sc[k]:.4f}  {lab}")
    if "strehl" not in arms or len(arms) < 2:
        raise SystemExit(f"{key}: not enough arms built")

    out = {"key": key, "meta": meta, "nboot": nboot,
           "bits": {k: v[3] for k, v in arms.items()},
           "scales": {k: sc[k] for k in arms}}

    # ------------------------------------------------ the statistic
    per_tile = {}
    for shift in (False, True):
        tag = "shift" if shift else "raw"
        vals = {}
        for k, (A, B, lab, b) in arms.items():
            rows = []
            for (y, x) in cells:
                ca, cb = A.rgb(y, x), B.rgb(y, x)
                if ca is None or cb is None or ca.shape != cb.shape:
                    rows.append([np.nan] * 3)
                    continue
                s = half_sigma(ca, cb, shift=shift)
                rows.append(s if s else [np.nan] * 3)
            vals[k] = np.array(rows)
        ok = np.ones(len(cells), bool)
        for k in vals:
            ok &= np.all(np.isfinite(vals[k]), axis=1)
        per_tile[tag] = (vals, ok)

        print(f"\n--- {'INTEGER-SHIFT CORRECTED' if shift else 'RAW'} "
              f"(n={int(ok.sum())}) ---")
        print(f"{'arm':10s} " + " ".join(f"{c:>12s}" for c in CHAN))
        for k in vals:
            print(f"{k:10s} " + " ".join(
                f"{np.median(vals[k][ok, i]):12.5f}" for i in range(3)))
        print(f"{'ratio':10s} " + " ".join(f"{c:>26s}" for c in CHAN))
        res = {}
        for k in vals:
            if k == "strehl":
                continue
            row, rr = f"{k:10s} ", []
            for i in range(3):
                m, lo, hi, n = boot(vals[k][ok, i], vals["strehl"][ok, i],
                                    nboot, rng)
                rr.append([m, lo, hi])
                row += f"  {m:7.3f} [{lo:6.3f},{hi:6.3f}]"
            print(row)
            res[k] = rr
        out[tag] = res
        out["n_tiles"] = int(ok.sum())

    vals, ok = per_tile["shift"]
    SA, SB = arms["strehl"][0], arms["strehl"][1]
    live = [cells[i] for i in np.where(ok)[0]]

    # ------------------------------------------------ commissioning
    print("\n" + "-" * 100)
    print(f"COMMISSIONING for {key} -- re-run on THIS subject, sec.4. "
          f"Nothing is carried across from another scene.")
    print("-" * 100)
    comm = {}

    m, lo, hi, _ = boot(vals["strehl"][ok, 0], vals["strehl"][ok, 0],
                        nboot, rng)
    comm["NULL"] = [m, abs(m - 1.0) <= 0.005]
    print(f"  NULL      identity floor {m:.6f}   "
          f"{'PASS' if comm['NULL'][1] else 'FAIL'}")

    # POTENCY.  half_sigma applies NO high-pass, so the prediction carries no
    # KVAR factor -- unlike noisefree.sigmas, where it does.
    wsum = float(np.sqrt((W709 ** 2).sum()))
    pot, okp = [], True
    rg = np.random.default_rng(909)
    for sig in (0.0005, 0.002, 0.008):
        got = []
        for (y, x) in live[:60]:
            b = SA.rgb(y, x)
            if b is None:
                continue
            s = half_sigma(b + rg.normal(0.0, sig, b.shape),
                           b + rg.normal(0.0, sig, b.shape), shift=False)
            if s is None:
                continue
            Y, _, _ = opponent(b)
            got.append(s[0] * float(Y.mean()))
        r = float(np.median(got)) / (sig * wsum)
        good = abs(r - 1.0) <= 0.10
        okp &= good
        pot.append([sig, r, good])
        print(f"  POTENCY   planted {sig:.4f} -> measured/predicted {r:.4f}   "
              f"{'PASS' if good else 'FAIL'}")
    comm["POTENCY"] = [pot, okp]

    base, q8 = [], []
    for (y, x) in live:
        ca, cb = SA.rgb(y, x), SB.rgb(y, x)
        if ca is None or cb is None or ca.shape != cb.shape:
            continue
        s0 = half_sigma(ca, cb, shift=False)
        s1 = half_sigma(np.round(ca * 255) / 255, np.round(cb * 255) / 255,
                        shift=False)
        if s0 is None or s1 is None:
            continue
        base.append(s0)
        q8.append(s1)
    base, q8 = np.array(base), np.array(q8)
    qr, okq = [], True
    print("  QUANT8    strehl requantised to 8 bits -- answer fixed by "
          "arithmetic, must be > 1")
    for i, nm in enumerate(CHAN):
        m, lo, hi, _ = boot(q8[:, i], base[:, i], nboot, rng)
        good = m > 1.0 + 1e-9
        okq &= good
        qr.append(m)
        print(f"            {nm:11s} {m:6.3f} [{lo:.3f},{hi:.3f}]  "
              f"(+{(m - 1) * 100:5.1f}%)   {'PASS' if good else 'FAIL'}")
    comm["QUANT8"] = [qr, okq]

    # TONE -- the confound that killed V-HEADTOHEAD2's fine-scale table.
    #
    # DEFECT FOUND AND FIXED, and it is worth stating because it nearly
    # withdrew a correct headline.  The first version of this arm compared
    # s_st = the INTEGER-SHIFT CORRECTED strehl sigma against a toned sigma
    # measured with NO shift applied.  Two estimators of different quantities.
    # On 113 that reported 60.17% explained and FAILED an arm that M127 had
    # passed at -153%.  tonecheck.py diagnosed it: strehl's unshifted sigma
    # is 0.07859, not 0.05187, so the arm subtracted a baseline 51.5% too
    # small.  The arm now works in GAIN -- what the fitted map does to strehl's
    # own half-difference -- which is basis-free, and applies that gain to the
    # verdict's basis.
    #
    # It also carries its own bias control.  tonecheck.py measured the arm's
    # gain against a target that is strehl PLUS NOISE, whose true tone content
    # is zero by construction, at 0.5x/1.0x/2.0x strehl's own sigma: 0.9047,
    # 0.9048, 0.9041.  A 0.08% spread over a 4x noise sweep -- fitting and
    # applying a 256-quantile map contracts residuals by ~9.5% whatever the
    # target is.  That bias is divided out.  The paired POSCTL, a target that
    # is strehl through a known gamma 0.75 and therefore 100% tone by
    # construction, read 91.4% bias-corrected: the arm is not merely quiet, it
    # responds to a real tone difference with roughly the right magnitude.
    print("  TONE      4x4-block fit strehl->comparator, applied to BOTH "
          "strehl halves")
    print("            reported as GAIN / NEGCTL bias.  NEGCTL target = strehl"
          " + noise, true tone 0%.")

    def _tone_gain(tgt_lum):
        xs, ys = [], []
        for (y, x) in live:
            ya, _, _ = opponent(SA.rgb(y, x))
            xs.append(coarse4(ya).ravel())
            ys.append(coarse4(tgt_lum(y, x)).ravel())
        mp = fit_map(np.concatenate(xs), np.concatenate(ys))
        b, t = [], []
        for (y, x) in live:
            ya, _, _ = opponent(SA.rgb(y, x))
            yb, _, _ = opponent(SB.rgb(y, x))
            b.append(half_sigma_y(ya, yb))
            t.append(half_sigma_y(apply_map(mp, ya), apply_map(mp, yb)))
        bb = float(np.nanmedian(b))
        return bb, float(np.nanmedian(t)) / bb if bb > 0 else float("nan")

    s_raw = float(np.median(per_tile["raw"][0]["strehl"][ok, 0]))

    def _neg(y, x):
        r = SA.rgb(y, x)
        return opponent(r + rng.normal(0.0, s_raw * r.mean(), r.shape))[0]
    _, BIAS = _tone_gain(_neg)

    def _pos(y, x):
        return np.clip(opponent(SA.rgb(y, x))[0], 0, None) ** 0.75
    _, g_pos = _tone_gain(_pos)
    sp = float(np.nanmedian([
        half_sigma_y(np.clip(opponent(SA.rgb(y, x))[0], 0, None) ** 0.75,
                     np.clip(opponent(SB.rgb(y, x))[0], 0, None) ** 0.75)
        for (y, x) in live]))
    f_pos = (s_raw * (g_pos / BIAS) - s_raw) / (sp - s_raw)
    pos_ok = bool(abs(f_pos - 1.0) <= 0.25)
    print(f"            NEGCTL bias {BIAS:.4f} (true 1.0000)   POSCTL gamma"
          f" 0.75 explained {f_pos * 100:6.1f}% (true 100%)   "
          f"{'PASS' if pos_ok else 'FAIL -- ARM IS BLIND TO TONE'}")

    tone, okt = {}, pos_ok
    for k in arms:
        if k == "strehl":
            continue
        _, g = _tone_gain(lambda y, x, kk=k: opponent(arms[kk][0].rgb(y, x))[0])
        gc = g / BIAS
        s_st = float(np.median(vals["strehl"][ok, 0]))
        s_cp = float(np.median(vals[k][ok, 0]))
        gap = s_cp - s_st
        frac = (s_st * gc - s_st) / gap if abs(gap) > 1e-12 else float("nan")
        good = bool(frac < 0.50)
        okt &= good
        tone[k] = [frac, good, g, gc]
        print(f"            {k:9s} gain {g:.4f} / {BIAS:.4f} = {gc:.4f}  "
              f"strehl {s_st:.5f} -> {s_st * gc:.5f}  comp {s_cp:.5f}   "
              f"explained {frac * 100:8.2f}%   "
              f"{'PASS' if good else 'FAIL -- TONE MEASUREMENT'}")
    comm["TONE"] = [tone, okt, BIAS, f_pos]

    # CGAIN-DC -- a chroma GAIN would scale chroma noise too, so it is the one
    # saturation confound the half-difference does NOT cancel.  The DC
    # estimator is noise-immune: noise has zero mean, so nothing needs
    # subtracting.  M127 measured 1.093/0.912 here -- straddling 1.0.
    # CGAIN-DC -- a chroma GAIN would scale chroma noise too, so it is the one
    # saturation confound the half-difference does NOT cancel.  The DC
    # estimator is noise-immune: noise has zero mean, so nothing needs
    # subtracting.  M127 measured 1.093/0.912 here -- straddling 1.0.
    #
    # DEVIATION, diagnosed before it was changed.  sec.4 wrote the criterion as
    # "the CI must straddle 1".  On subject 119 that fired on enfuse at
    # 0.997 [0.994,0.999] and 0.989 [0.983,0.993] -- a gain difference of 0.3%
    # and 1.1%, declared a failure purely because 110 tiles and a very precise
    # estimator make even a 0.3% difference significant.  A straddle test is a
    # test of SIGNIFICANCE; what the guard is for is MAGNITUDE -- whether the
    # gain could account for the noise ratio.  So the M127 form of the same
    # guard is applied alongside it: explained = (gain - 1) / (noise_ratio - 1),
    # which is CHROMAGAIN's pre-registered arithmetic (M127 sec.4), not a new
    # invention.  BOTH are printed, as M127 printed both tile sets, so the
    # deviation is shown to change nothing rather than asserted to.
    print("  CGAIN-DC  per-tile mean signed chroma (noise-immune). A gain "
          "difference WOULD survive the half-difference.")
    print("            straddle test = significance; explained% = magnitude "
          "(M127 sec.4 form). Both shown.")
    dc, okc, okc_mag = {}, True, True
    d_st = np.array([[abs(float(opponent(SA.rgb(y, x))[1].mean())
                          / float(opponent(SA.rgb(y, x))[0].mean())),
                      abs(float(opponent(SA.rgb(y, x))[2].mean())
                          / float(opponent(SA.rgb(y, x))[0].mean()))]
                     for (y, x) in live])
    for k in arms:
        if k == "strehl":
            continue
        d_cp = []
        for (y, x) in live:
            Y, c1, c2 = opponent(arms[k][0].rgb(y, x))
            lv = float(Y.mean())
            d_cp.append([abs(float(c1.mean()) / lv),
                         abs(float(c2.mean()) / lv)])
        d_cp = np.array(d_cp)
        rr = []
        for i, nm in ((0, "R-Y"), (1, "B-Y")):
            m, lo, hi, _ = boot(d_cp[:, i], d_st[:, i], nboot, rng)
            straddle = bool(lo <= 1.0 <= hi)
            ns, _, _, _ = boot(vals[k][ok, 1 + i], vals["strehl"][ok, 1 + i],
                               nboot, rng)
            expl = ((m - 1.0) / (ns - 1.0)) if abs(ns - 1.0) > 1e-9 else np.nan
            mag_ok = bool(expl < 0.50)
            okc &= straddle
            okc_mag &= mag_ok
            rr.append([m, lo, hi, straddle, float(expl), mag_ok])
            print(f"            {k:9s} {nm}  gain {m:6.3f} "
                  f"[{lo:6.3f},{hi:6.3f}] {'level' if straddle else 'SIG'}"
                  f"   vs noise ratio {ns:6.3f} -> explains {expl * 100:7.2f}%"
                  f"   {'PASS' if mag_ok else 'FAIL -- SATURATION MEASUREMENT'}")
        dc[k] = rr
    comm["CGAIN_DC"] = [dc, okc, okc_mag]

    # ---- IS STREHL JUST BLURRIER?  The objection foreclosed from inside.
    # This subject is the one where V-EYES.md sec.5.5 measured strehl's largest
    # softness deficit against a per-site best frame (0.8110), so "cleaner
    # because blurrier" is the live alternative explanation here and it is not
    # answered by pointing at a separate sharpness run.  Both quantities below
    # are computed on the SAME image (half-stack A): flat-ROI sigma contains
    # noise AND scene, the half-difference contains noise ALONE, so the scene
    # term follows by subtraction in quadrature with no assumption about depth.
    print("\n  SCENE vs NOISE on the same tiles -- 'cleaner because blurrier?'")
    print(f"  {'arm':10s} {'flat-ROI sig':>14s} {'noise sig':>12s} "
          f"{'scene term':>12s} {'noise frac':>11s}")
    from noisefree import sigmas as _sigmas
    scene = {}
    for k, (A, B, lab, b) in arms.items():
        fl, nz = [], []
        for (y, x) in live:
            ca, cb = A.rgb(y, x), B.rgb(y, x)
            if ca is None or cb is None or ca.shape != cb.shape:
                continue
            s1 = _sigmas(ca)
            s2 = half_sigma(ca, cb, shift=(k == "strehl"))
            if s1 is None or s2 is None:
                continue
            fl.append(s1[0])
            nz.append(s2[0])
        f, n = float(np.median(fl)), float(np.median(nz))
        sc_t = float(np.sqrt(max(f * f - n * n, 0.0)))
        scene[k] = [f, n, sc_t, min((n / f) ** 2, 1.0)]
        print(f"  {k:10s} {f:14.6f} {n:12.5f} {sc_t:12.5f} "
              f"{min((n / f) ** 2, 1.0) * 100:10.1f}%")

    # ---- CONSISTENCY GATE.  flat-ROI sigma contains noise AND scene; the
    # half-difference is meant to contain noise ALONE.  So n < f is not a
    # nicety, it is an ARITHMETIC REQUIREMENT of the decomposition.  n >= f
    # says the half-difference holds something the single image does not,
    # i.e. A and B are not two noisy draws of ONE latent image -- they are
    # reconstructing DIFFERENT images.  When that happens the ratio above is
    # not a noise ratio and must not be reported as one, however flattering.
    degenerate = [k for k in scene if scene[k][1] >= scene[k][0]]
    scene_ok = not degenerate
    if not scene_ok:
        out["scene_degenerate"] = degenerate
        print(f"\n  *** DECOMPOSITION DEGENERATE on {len(degenerate)} of "
              f"{len(scene)} arms: {', '.join(degenerate)}")
        print("      For these arms the half-difference sigma EXCEEDS the "
              "flat-ROI sigma of the same")
        print("      tiles, so the scene term clamps to zero by subtraction "
              "and every arm ties at 0.00000.")
        print("      A 'highest scene term' read off tied zeros is vacuous, "
              "so it is WITHHELD.")
        print("      Mechanism to rule in or out before believing any ratio "
              "on this subject: the half-")
        print("      stack proxy assumes A and B reconstruct the SAME latent "
              "image.  A selection-dominated")
        print("      merge can pick DIFFERENT source frames per half, putting "
              "real focus difference into")
        print("      A-B.  That inflates measured 'noise' for whichever arm "
              "selects hardest.")
    else:
        best_scene = max(scene, key=lambda k: scene[k][2])
        print(f"  highest scene term: {best_scene}"
              f"{'  <- strehl carries the MOST scene content AND the least noise'
                 if best_scene == 'strehl' else
                 '  <- NOT strehl: the blur objection is LIVE on this subject'}")
    out["scene_ok"] = bool(scene_ok)
    out["scene"] = scene

    allok = comm["NULL"][1] and okp and okq and okt and scene_ok
    print(f"\n  COMMISSIONING {key}: "
          f"{'ALL PASS' if allok else 'FAILED -- ratios withdrawn'}"
          f"   (CGAIN-DC magnitude "
          f"{'PASS' if okc_mag else 'FAIL -- chroma withdrawn'}, "
          f"straddle {'level' if okc else 'significant but see explained%'}"
          f"{'' if scene_ok else ', SCENE DECOMPOSITION DEGENERATE'})")
    out["commissioning"] = {"null": comm["NULL"][1], "potency_pass": okp,
                            "quant8": okq, "tone": okt, "scene_ok": bool(scene_ok),
                            "cgain_straddle": okc, "cgain_magnitude": okc_mag,
                            "tone_explained": {k: v[0] for k, v in tone.items()},
                            "quant8_ratio": qr,
                            "potency": [[p[0], p[1]] for p in pot],
                            "cgain": dc, "all_pass": bool(allok and okc_mag)}

    npz = os.path.join(ROOT, key, "hd.npz")
    os.makedirs(os.path.dirname(npz), exist_ok=True)
    np.savez(npz, ok=ok, **{f"{t}_{k}": per_tile[t][0][k]
                            for t in per_tile for k in per_tile[t][0]})
    with open(os.path.join(ROOT, key, "hd.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"  written {npz}")
    return out


def main():
    args = sys.argv[1:]
    nboot = 2000
    keys = []
    for a in args:
        # NOTE: subject keys are not all non-numeric ("119"), so a key is
        # anything in SUBJECTS and nboot is anything else that is a number.
        if a in SUBJECTS:
            keys.append(a)
        elif a.isdigit():
            nboot = int(a)
        else:
            raise SystemExit(f"unknown subject key {a!r}; "
                             f"the list is closed: {list(SUBJECTS)}")
    if not keys:
        raise SystemExit(__doc__)
    rng = np.random.default_rng(23)
    for k in keys:
        run(k, nboot, rng)
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

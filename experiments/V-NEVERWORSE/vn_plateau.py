"""Measure the plateau structure of the shipping winner field, and run the
counterfactual on the knob that exists.

Deliverables, re-aimed. ORCH asked for absolute-vs-response-relative tolerance.
Neither exists on the shipping path (see `vn_pyr` docstring): the shipping
weight is already a noise-relative SNR ratio. The knob `pyramid.rs` itself
names as the driver of never-worse violations is the SELECTION EXPONENT, so the
counterfactual is run on that.

Every blotch number carries a sharpness number on the same pixels, and both
statistics are commissioned with a planted DEGRADATION and a planted
IMPROVEMENT before any of them is quoted.
"""
import io
import json
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_pyr as VP

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\plateau"
BUNDLE = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"

# From the binary's own self-report in the provenance file. finest -> coarsest.
BETA = [0.8898, 0.0529, 0.0101, 0.0024, 0.0006, 0.0001, 0.0000, 0.0000]
SHIP = {"exponent": 2.0, "sharpen": 1.4, "gate": 2.0, "hull": True}


# ---------------------------------------------------------------- statistics
def blotch(img):
    """band(50-400 px) / mean, on green. The gate's own statistic."""
    g = img[:, :, 1].astype(np.float64)
    lo = ndimage.gaussian_filter(g, 50.0 / 2.355)
    hi = ndimage.gaussian_filter(g, 400.0 / 2.355)
    band = lo - hi
    return float(band.std() / max(g.mean(), 1e-9)), float(band.std())


def sharpness(img):
    """RMS of the finest Laplacian level, relative to mean. Signed both ways.

    Chosen so it can move in BOTH directions: blurring must lower it and
    sharpening must raise it. A magnitude bounded below by zero would only ever
    be able to ignore a loss, never charge for a gain -- that perverse gauge is
    a documented failure in this project and the commissioning arm below is
    what excludes it here.
    """
    g = img[:, :, 1].astype(np.float64)
    lap, _ = VP.lap_pyr(g, 1)
    return float(lap[0].std() / max(g.mean(), 1e-9))


# ---------------------------------------------------------------- fidelity
def self_test():
    """The reimplementation is a claim about the shape of the code.

    NOTE, and it is the reason this function looks paranoid: the first version
    asserted only that `expand` preserved the MEAN of a constant. It did -- and
    its border ring still spanned 300 to 2700 DN around a constant 1200, std
    61.87. A spatially varying error with zero mean passes a mean test. Every
    shape assertion below therefore checks SPREAD as well as level, and the
    sharpness gauge is required to respond to blur here rather than only in
    `commission`, because that is the property the border bug destroyed.
    """
    fails = []
    c = np.full((64, 64), 7.25)
    if abs(VP.smooth5(c).mean() - 7.25) > 1e-9 or VP.smooth5(c).std() > 1e-9:
        fails.append("smooth5 does not preserve a constant")
    r = VP.reduce_(c)
    if abs(r.mean() - 7.25) > 1e-9 or r.std() > 1e-9:
        fails.append("reduce does not preserve a constant")
    e = VP.expand(np.full((100, 100), 1200.0), (200, 200))
    if abs(e.mean() - 1200.0) > 1e-6 or e.std() > 1e-6:
        fails.append("expand distorts a constant: mean %.4f std %.4f "
                     "min %.1f max %.1f" % (e.mean(), e.std(), e.min(), e.max()))

    rng = np.random.default_rng(7)
    a = rng.normal(1000, 60, (96, 96))
    lap, base = VP.lap_pyr(a, 4)
    R = base
    for k in range(3, -1, -1):
        R = VP.expand(R, lap[k].shape) + lap[k]
    err = float(np.abs(R - a).max())
    if err > 1e-6:
        fails.append("pyramid does not reconstruct exactly (%.3e DN)" % err)

    # one frame in, the same frame out: weights cannot matter with n = 1
    f = rng.normal(1200, 80, (64, 64, 3))
    var0 = np.full((64, 64), 400.0)
    rec, _ = VP.merge([f], dict(SHIP, hull=False), BETA, var0, nb=4)
    err1 = float(np.abs(rec - f).max())
    if err1 > 1e-5:
        fails.append("single-frame merge is not the identity (%.3e DN)" % err1)

    # the sharpness gauge must actually see a blur -- the border bug hid this
    g = rng.normal(1200, 25, (256, 256, 3))
    s0 = sharpness(g)
    s5 = sharpness(ndimage.gaussian_filter(g, (5.0, 5.0, 0)))
    if not s5 < s0 * 0.25:
        fails.append("sharpness barely responds to a sigma=5 blur "
                     "(%.5f -> %.5f, %.3fx); the gauge is blind" % (s0, s5, s5 / s0))
    return fails


def commission():
    """Both statistics must move the right way under a planted defect AND a
    planted improvement.

    Design note, recorded because the first version REFUSED and it was the
    plants that were wrong, not the statistics. That version built its base
    from a 56 px sine of amplitude 300 DN -- which sits inside the 50-400 px
    blotch band -- so the base was already maximally mottled and a planted
    mottle could only move it 1.11x. The fix is a stronger, cleaner plant, NOT
    a looser threshold: loosening a threshold until a test passes is how a
    gauge gets certified blind. Structure is now placed OUTSIDE the measured
    band, and each statistic is tested as an ORDERING over three levels of one
    planted quantity, so a monotone response is required rather than a single
    step.
    """
    rng = np.random.default_rng(11)
    h = w = 400
    yy, xx = np.mgrid[0:h, 0:w]
    # coarse illumination well outside the 50-400 px band, plus fine texture
    base = (1200.0 + 120.0 * np.sin(xx / 260.0) + rng.normal(0, 25, (h, w)))
    base = np.repeat(base[:, :, None], 3, axis=2)
    mot = (300.0 * np.sin(xx / 24.0) * np.sin(yy / 24.0))[:, :, None]
    ok, bad = [], []

    def arm(cond, msg):
        (ok if cond else bad).append(msg)

    # --- blotch: monotone in planted mid-scale mottle, both directions ---
    b_lo, _ = blotch(base)
    b_mid, _ = blotch(base + 1.0 * mot)
    b_hi, _ = blotch(base + 2.0 * mot)
    arm(b_hi > b_mid * 1.5,
        "blotch DEGRADE: 2x mottle %.5f > 1x %.5f" % (b_hi, b_mid))
    arm(b_lo < b_mid * 0.5,
        "blotch IMPROVE: mottle removed %.5f < 1x %.5f" % (b_lo, b_mid))
    arm(b_lo < b_mid < b_hi, "blotch is MONOTONE in the planted mottle")

    # --- sharpness: monotone in planted fine detail, both directions ---
    ref = base + 1.0 * mot
    blur = ndimage.gaussian_filter(ref, (3.0, 3.0, 0))
    sh = ref + 1.4 * (ref - ndimage.gaussian_filter(ref, (1.6, 1.6, 0)))
    s_lo, s_mid, s_hi = sharpness(blur), sharpness(ref), sharpness(sh)
    arm(s_lo < s_mid * 0.6,
        "sharp DEGRADE: blurred %.5f < ref %.5f" % (s_lo, s_mid))
    arm(s_hi > s_mid * 1.3,
        "sharp IMPROVE: unsharp %.5f > ref %.5f" % (s_hi, s_mid))
    arm(s_lo < s_mid < s_hi, "sharpness is MONOTONE in planted fine detail")

    # --- specificity: the trade ORCH warned about must be VISIBLE ---
    # A smoothed image reads better on blotch. If blotch improved while
    # sharpness held, the pair could not tell a fix from a smoother. It must.
    b_blur, _ = blotch(blur)
    arm(b_blur <= b_mid * 1.05 and s_lo < s_mid * 0.6,
        "SPECIFICITY: blurring flatters blotch (%.5f vs %.5f) while sharpness "
        "collapses (%.5f vs %.5f) -- the pair can see the trade"
        % (b_blur, b_mid, s_lo, s_mid))
    return ok, bad


# ---------------------------------------------------------------- plateaus
def plateaus(W, level_px):
    """Connected regions of the winner field at one level.

    `level_px` is the native-pixel size of one cell at this level, so region
    areas convert to native pixels and the 20-60 px band ORCH asked about is
    measurable.
    """
    den = W.sum(axis=0)
    win = np.where(den > 0, W.argmax(axis=0), -1)
    n_eff = np.where(den > 0, den ** 2 / np.maximum((W ** 2).sum(axis=0), 1e-30),
                     float(W.shape[0]))
    sizes = []
    for f in np.unique(win):
        lab, n = ndimage.label(win == f)
        if n:
            sizes.append(np.bincount(lab.ravel())[1:])
    sizes = np.concatenate(sizes) if sizes else np.array([0])
    diam = np.sqrt(sizes) * level_px
    tot = float(sizes.sum())
    band = float(sizes[(diam >= 20) & (diam <= 60)].sum()) / max(tot, 1)
    return {
        "n_eff_mean": float(n_eff.mean()),
        "n_eff_median": float(np.median(n_eff)),
        "n_eff_p05": float(np.percentile(n_eff, 5)),
        "frac_single_winner": float((n_eff < 1.5).mean()),
        "regions": int(len(sizes)),
        "median_diam_px": float(np.median(diam)),
        "frac_area_20_60px": band,
        "level_px": level_px,
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"

    fails = self_test()
    if fails:
        print("REFUSED -- the reimplementation failed its own fidelity test:")
        for f in fails:
            print("   " + f)
        return 2
    print("fidelity: constant preserved, pyramid reconstructs exactly, "
          "single-frame merge is the identity")

    ok, bad = commission()
    for line in ok:
        print("  ok      " + line)
    for line in bad:
        print("  FAILED  " + line)
    if bad:
        print("REFUSED -- statistics not commissioned (%d ok, %d failed)"
              % (len(ok), len(bad)))
        return 2
    print("commissioned: %d ok, %d failed (defect AND improvement arms)\n"
          % (len(ok), len(bad)))

    z = np.load(os.path.join(BUNDLE, "%s.npz" % subj))
    keys = sorted(k for k in z.files if k.startswith("b") and k != "bw")
    meta = json.load(io.open(os.path.join(BUNDLE, "%s.json" % subj),
                             encoding="utf-8"))
    ok = {r["frame"] for r in meta["rows"] if r["state"] == "OK"}
    allk = sorted(k for k in z.files if k.startswith("b") and k != "bw")
    keys = [k for k in allk if int(k[1:]) in ok]
    dropped = len(allk) - len(keys)
    frames = [z[k].astype(np.float64) for k in keys]
    master = z["mb"].astype(np.float64)
    print("%s: %d bundled = %d OK source frames + %d not-OK dropped, tile %s"
          % (subj, len(allk), len(frames), dropped, frames[0].shape))

    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1])
    print("noise model FITTED (the one guess): var = %.1f + %.4f*S DN^2"
          % (read2, gph))
    if gph < 0:
        print("REFUSED: fitted photon gain is negative, which is unphysical")
        return 2

    nb = 7
    res = {"subject": subj, "frames": len(frames),
           "noise_fit": {"read2": read2, "gain": gph}}

    rec, W = VP.merge(frames, SHIP, BETA, var0, nb=nb)
    res["plateaus"] = {}
    for k in range(nb):
        res["plateaus"]["L%d" % k] = plateaus(W[k], 2 ** k)
    res["exponents"] = [VP.exponent_at(k, nb, 2.0, 1.4) for k in range(nb)]

    arms = {
        "a_shipping": SHIP,
        "b_plain_mean": dict(SHIP, mode="mean"),
        "c_exponent_1_flat": dict(SHIP, exponent=1.0, sharpen=1.0),
        "d_no_ramp_exp2": dict(SHIP, sharpen=1.0),
    }
    res["arms"] = {}
    srcb = [blotch(f)[0] for f in frames]
    srcs = [sharpness(f) for f in frames]
    # A frame that scores exactly zero is degenerate, not "the best source".
    # Dividing by it would report an infinite excess as a number, so refuse.
    bad = [keys[i] for i, v in enumerate(srcb) if not (v > 0.0)]
    bad += [keys[i] for i, v in enumerate(srcs) if not (v > 0.0)]
    if bad:
        print("REFUSED: %d source frame(s) score zero and cannot bound a "
              "minimum: %s" % (len(bad), ", ".join(sorted(set(bad)))))
        return 2
    res["source"] = {"blotch_min": min(srcb), "blotch_med": float(np.median(srcb)),
                     "sharp_max": max(srcs), "sharp_med": float(np.median(srcs)),
                     "n_ok": len(frames), "n_dropped_not_ok": dropped}
    for name, cfg in arms.items():
        r, Wa = VP.merge(frames, cfg, BETA, var0, nb=nb)
        b, _ = blotch(r)
        s = sharpness(r)
        row = {"blotch": b, "sharpness": s,
               "blotch_vs_best_source": b / min(srcb),
               "sharp_vs_best_source": s / max(srcs)}
        if name != "b_plain_mean":
            row["L5"] = plateaus(Wa[5], 32)
        res["arms"][name] = row
        print("  %-18s blotch %.5f (%.3fx best src)   sharp %.5f (%.3fx)"
              % (name, b, row["blotch_vs_best_source"], s,
                 row["sharp_vs_best_source"]))

    mb, _ = blotch(master)
    res["shipped_master"] = {"blotch": mb, "sharpness": sharpness(master),
                             "blotch_vs_best_source": mb / min(srcb)}
    print("  %-18s blotch %.5f (%.3fx best src)"
          % ("SHIPPED master", mb, mb / min(srcb)))

    # The noise model is guessed, so what depends on it is measured, not
    # assumed. If the ranking of the arms survives a 4x sweep of the fitted
    # variance, the conclusion does not rest on the guess.
    print("\nsensitivity to the guessed noise model:")
    res["varscale"] = {}
    for sc in (0.5, 1.0, 2.0):
        r, _ = VP.merge(frames, SHIP, BETA, var0 * sc, nb=nb)
        rc_, _ = VP.merge(frames, dict(SHIP, exponent=1.0, sharpen=1.0),
                          BETA, var0 * sc, nb=nb)
        bs, be = blotch(r)[0] / min(srcb), blotch(rc_)[0] / min(srcb)
        res["varscale"]["x%.1f" % sc] = {"shipping": bs, "exp1": be}
        print("  var x%.1f   shipping %.3fx   exponent-1 %.3fx   %s"
              % (sc, bs, be, "exp1 lower" if be < bs else "EXP1 NOT LOWER"))

    p = os.path.join(OUT, "%s.json" % subj)
    io.open(p, "w", encoding="utf-8").write(json.dumps(res, indent=1))
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nREFUSED: crashed; no plateau claim is measured")
        sys.exit(2)

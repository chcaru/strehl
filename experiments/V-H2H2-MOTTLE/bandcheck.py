"""Commission the band ladder, then run it: comparator arms, then the mean_coarse dose.

Nothing is reported until commissioning passes. The suite carries a planted DEFECT, a
planted IMPROVEMENT, and the specific trap ORCH evidenced -- `focus-stack` reads 0.077
grain and 0.260 mid on this site, 10-25x below both other arms, which is a smoothed
photograph rather than a clean one. A fix here can trivially "win" the mid band by
blurring, so the blur arm must be REFUSED rather than credited, and a suite that only
plants degradations cannot tell a blind statistic from a perverse one.
"""
import json
import sys

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

from bandlib import (ARMS, BANDS, CROP, MANIFEST, MC_DIR, boxblur, call, display,
                     fit_to, terms, verdict)


def band_plant(shape, rng, lo, hi, gauge_lo, gauge_hi):
    """In-band field with a CLEAN STOPBAND, scaled to unit sigma AS THE GAUGE SEES IT.

    Two defects in this lane forced both halves of that sentence.

    Scale: an earlier plant was normalised to unit sigma before the gauge band-passed
    it a second time. The band-pass is not idempotent, so the delivered amplitude was
    far below the designed one and the defect arm scored x1.023 where x1.118 was
    intended. The plant is therefore normalised by the gauge's own response to it.

    Stopband: an earlier plant was built from a difference of BOX blurs, which have a
    poor stopband and leak 1 px gradient energy. It inflated `sharp` by 1.60x, so
    removing it read as smoothing and the IMPROVEMENT arm was refused for improving.
    A difference of Gaussians is used instead, and purity is then asserted rather than
    assumed.
    """
    w = rng.normal(0.0, 1.0, shape).astype(np.float32)
    p = (gaussian_filter(w, 11.0) - gaussian_filter(w, 24.0)).astype(np.float32)
    seen = float(np.std(boxblur(p, gauge_lo // 2) - boxblur(p, gauge_hi // 2)))
    return p / seen if seen > 0 else p


def commission(ref16, expo, rng):
    """Arms are built in LINEAR 16-bit and routed through fit_to + display, exactly the
    path a real arm takes. The first version compared display-state arms directly and
    never applied the photometric fit, so `gain x1.5` scored x1.500 -- the suite was
    certifying a path the measurement does not use."""
    print("COMMISSIONING the band ladder")
    ref_disp = display(ref16, expo)
    ref = terms(ref_disp)

    lin_mid = float(np.mean([np.std(boxblur(ref16[..., c], 10) - boxblur(ref16[..., c], 30))
                             for c in range(3)]))
    lin_grain = float(np.mean([np.std(ref16[..., c] - boxblur(ref16[..., c], 1))
                               for c in range(3)]))
    plant = band_plant(ref16.shape[:2], rng, 20, 60, 20, 60)[..., None]
    mottled = ref16 + plant * (0.5 * lin_mid)
    # Halo arm: unsharp mask. It RAISES fine detail far more than the mid band, which
    # is the perverse direction. Carried because a suite of degradations plus a repair
    # still never tests whether the guard can fire upward.
    haloed = np.stack([ref16[..., c] + 1.2 * (ref16[..., c] - boxblur(ref16[..., c], 2))
                       for c in range(3)], axis=-1)

    # Uniform-attenuation arm: everything above a coarse scale reduced by the SAME
    # factor. This is `focus-stack`'s measured signature (0.044/0.041/0.042/0.046
    # across the ladder) and it is invisible to a ratio-based selectivity, which is
    # why the real render defeated the first version of the guard. A box blur cannot
    # produce this shape, so no amount of blur-arm tuning would have found it.
    uni = np.stack([boxblur(ref16[..., c], 40)
                    + 0.05 * (ref16[..., c] - boxblur(ref16[..., c], 40))
                    for c in range(3)], axis=-1)

    arms = {
        "clone": ref16.copy(),
        "gain x1.5": ref16 * 1.5,
        "mottle+": mottled,
        "grain+": ref16 + rng.normal(0.0, 0.5 * lin_grain, ref16.shape).astype(np.float32),
        "blur r8": np.stack([boxblur(ref16[..., c], 8) for c in range(3)], axis=-1),
        "uniform -20x": uni,
        "halo": haloed,
    }
    t = {}
    fits = {}
    for k, a16 in arms.items():
        g, o = fit_to(ref16, a16)
        fits[k] = g
        t[k] = terms(display(a16 * g + o, expo))
    v = {k: verdict(ref, x) for k, x in t.items()}
    # The IMPROVEMENT arm: the mottled render repaired, judged against the mottled one.
    v["repair"] = verdict(t["mottle+"], ref)

    d, b, rp = v["mottle+"], v["blur r8"], v["repair"]
    checks = [
        ("clone is inert",
         all(abs(v["clone"][x] - 1.0) < 0.005 for x, _, _ in BANDS)),
        ("photometric gain cancels (fit is exercised)",
         all(abs(v["gain x1.5"][x] - 1.0) < 0.01 for x, _, _ in BANDS)),
        ("FIT is decoupled from the measurand",
         abs(float(np.mean(fits["mottle+"])) - 1.0) < 0.005),
        ("DEFECT: mid-band plant convicted",
         d["20-60"] > 1.05 and not d["smoothed"]),
        ("DEFECT is band-selective, not a level shift",
         (d["20-60"] - 1.0) > 3.0 * abs(d["5-15"] - 1.0)),
        ("IMPROVEMENT: repair credited, not refused",
         rp["20-60"] < 0.95 and not rp["smoothed"] and not rp["traded"]),
        ("TRAP: blur's mid band DOES improve (the trap is real)",
         b["20-60"] < 0.95),
        ("TRAP: blur REFUSED anyway",
         b["smoothed"]),
        ("TRAP: uniform reduction convicted (ratio-blind case)",
         v["uniform -20x"]["smoothed"]),
        ("TRAP: uniform reduction is NOT called traded",
         not v["uniform -20x"]["traded"]),
        ("detail floor separates repair from blur by >1.5x",
         rp["sharp"] / max(b["sharp"], 1e-9) > 1.5),
        ("selectivity separates blur from repair by >1.5x",
         rp["selectivity"] / max(b["selectivity"], 1e-9) > 1.5),
        ("TRADE: upward artifact convicted (guard is two-sided)",
         v["halo"]["traded"] and not v["halo"]["smoothed"]),
        ("grain plant lands in grain, not the mid band",
         v["grain+"]["grain"] > 1.05 and abs(v["grain+"]["20-60"] - 1.0) < 0.03),
    ]
    ok = 0
    for name, good in checks:
        print("  %-46s %s" % (name, "PASS" if good else "FAIL"))
        ok += bool(good)
    for k, x in v.items():
        print("    %-10s %-30s sel %5.2f  grain %6.3f sharp %6.3f  20-60 %6.3f  5-15 %6.3f"
              % (k, call(x), x["selectivity"], x["grain"], x["sharp"], x["20-60"], x["5-15"]))
    print("  commissioned %d/%d" % (ok, len(checks)))
    return ok == len(checks)


def load(path, y, x, dy=0, dx=0):
    a = tifffile.imread(str(path))
    if a.ndim != 3:
        raise SystemExit("not RGB: %s" % path)
    ys, xs = y + dy, x + dx
    if ys < 0 or xs < 0 or ys + CROP > a.shape[0] or xs + CROP > a.shape[1]:
        raise SystemExit("CROP OUT OF BOUNDS for %s: want [%d:%d, %d:%d] of %s. "
                         "A silent clip returns plausible numbers for pixels it never "
                         "read." % (path.name, ys, ys + CROP, xs, xs + CROP, a.shape))
    return a[ys:ys + CROP, xs:xs + CROP, :3].astype(np.float32)


def row(label, v):
    return ("  %-22s %-24s grain %6.3f  sharp %6.3f   "
            % (label, call(v), v["grain"], v["sharp"])
            + " ".join("%s %6.3f" % (b, v[b]) for b, _, _ in BANDS))


def main():
    man = json.loads(MANIFEST.read_text())
    site = next(s for s in man["sites"] if s.get("label") == "worst-on-subject")
    y, x, expo, fits = site["y"], site["x"], site["exposure"], site["fits"]
    print("site worst-on-subject y=%d x=%d exposure x%.4g\n" % (y, x, expo))

    ref16 = load(ARMS / "strehl-A.tiff", y, x, *fits["strehl"]["shift"])
    g = np.array(fits["strehl"]["gain"], np.float32)
    o = np.array(fits["strehl"]["offset"], np.float32)
    ref_disp = display(ref16 * g + o, expo)

    rng = np.random.default_rng(20260827)
    if not commission(ref16 * g + o, expo, rng):
        print("\nREFUSING to report: the gauge is not commissioned")
        return 1

    print("\nCOMPARATORS at the published site (ratio to strehl; <1 = comparator cleaner)")
    ref = terms(ref_disp)
    print("  %-22s %-24s grain %6s  sharp %6s   " % ("strehl (reference)", "-", "1.000", "1.000")
          + " ".join("%s %6.3f" % (b, float(np.mean(ref[b]))) for b, _, _ in BANDS)
          + "   <- absolute codes")
    for k, fn in (("enfuse", "coh-enfuse-A.tif"), ("focus-stack", "coh-fs15-A.tif")):
        a16 = load(ARMS / fn, y, x, *fits[k]["shift"])
        ag = np.array(fits[k]["gain"], np.float32)
        ao = np.array(fits[k]["offset"], np.float32)
        print(row(k, verdict(ref, terms(display(a16 * ag + ao, expo)))))

    print("\nMEAN_COARSE DOSE at the same site (ratio to mc=0; <1 = the dose is cleaner)")
    base = MC_DIR / "119MSDCF--mc0.tiff"
    if not base.exists():
        print("  mc arms absent -- render first")
        return 0
    b16 = load(base, y, x)
    bdisp = display(b16, expo)
    bref = terms(bdisp)
    print("  %-22s %-24s grain %6s  sharp %6s   " % ("mc=0 (reference)", "-", "1.000", "1.000")
          + " ".join("%s %6.3f" % (b, float(np.mean(bref[b]))) for b, _, _ in BANDS)
          + "   <- absolute codes")
    for mc in (3, 5, 7):
        p = MC_DIR / ("119MSDCF--mc%d.tiff" % mc)
        if not p.exists():
            continue
        a16 = load(p, y, x)
        ag, ao = fit_to(b16, a16)
        print(row("mc=%d" % mc, verdict(bref, terms(display(a16 * ag + ao, expo)))))

    # The target: enfuse's absolute mid band on these pixels, which is a real merger's
    # real performance rather than an oracle.
    e16 = load(ARMS / "coh-enfuse-A.tif", y, x, *fits["enfuse"]["shift"])
    eg = np.array(fits["enfuse"]["gain"], np.float32)
    eo = np.array(fits["enfuse"]["offset"], np.float32)
    et = terms(display(e16 * eg + eo, expo))
    print("\nTARGET  enfuse 20-60 absolute %s  (strehl mc=0 %s)"
          % (np.array2string(et["20-60"], precision=3),
             np.array2string(bref["20-60"], precision=3)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

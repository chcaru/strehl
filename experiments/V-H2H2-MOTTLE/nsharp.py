"""Does the merged image actually get softer as N rises, on my own arms?

The softness lane measured 63 frames 0.114 softer than 32 at matched focus range.
This is an independent check of the EFFECT on arms I staged myself, using the
committed section 11 band gauge, so that my refutation of the proposed CAUSE
cannot be mistaken for a denial that the effect exists.

The reference arm is n32 and the test arm is n63, so a sharpness ratio BELOW 1.0
means adding frames cost acuity. bandlib.verdict carries both guards: `smoothed`
fires if a mid-band gain was bought with detail, and `traded` fires in the
opposite direction, because a gauge that can only fire on smoothing is bounded on
one side and this project has already shipped one of those.

SITES are chosen on the n63 render and applied to BOTH arms -- the same pixels,
not the same rule evaluated twice. Both arms render 7032x4688 from the same
subject with the same bracket endpoints, so the grids correspond.

EXPOSURE is not fitted away silently: both arms are --linear-srgb, which refuses
--exposure and applies no gain, so the fitted per-channel gain SHOULD be 1.000
and it is printed. A gain that departs from 1 means the arms differ by more than
N and the numbers below are not an A/B.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\nscale\out"
CROP = 400


def sites(sd, want, n=3, crop=CROP, margin=0.05):
    """The n most extreme non-overlapping crops, excluding a border margin.

    The first version of this took a single most-extreme crop and put the flat
    site at x=0 -- hard against the frame edge, which is where the alignment crop
    lives and where every frame's warp is least constrained. A conclusion about
    noise drawn from that one crop would have been a conclusion about the border.
    A margin and a median over several sites cost nothing and remove the class.
    """
    h, w = sd.shape
    my, mx = int(h * margin), int(w * margin)
    step = crop // 2
    cand = []
    for y in range(my, h - crop - my, step):
        for x in range(mx, w - crop - mx, step):
            cand.append((float(np.mean(sd[y:y + crop, x:x + crop])), y, x))
    cand.sort(reverse=(want == "detail"))
    out = []
    for m, y, x in cand:
        if all(abs(y - yy) >= crop or abs(x - xx) >= crop for _, yy, xx in out):
            out.append((m, y, x))
        if len(out) == n:
            break
    return out


def main():
    a63 = tifffile.imread(os.path.join(OUT, "n63.tiff"))
    a32 = tifffile.imread(os.path.join(OUT, "n32.tiff"))
    if a63.shape != a32.shape:
        raise SystemExit("arms differ in shape: %s vs %s" % (a63.shape, a32.shape))
    print("both arms %dx%d" % (a63.shape[1], a63.shape[0]))

    sd = bandlib.boxblur(a63[..., 1].astype(np.float64), 8)
    sd = np.abs(a63[..., 1].astype(np.float64) - sd)
    sd = bandlib.boxblur(sd, 8)

    g, _ = bandlib.fit_to(a32, a63)
    print("per-channel gain fitted n63 -> n32: %.5f %.5f %.5f" % tuple(g))
    if np.any(np.abs(g - 1.0) > 0.01):
        print("  WARNING: gain departs from 1.000 by more than 1%. The arms differ")
        print("  by more than frame count and these numbers are not an A/B.")

    # bandlib.display(c16, expo) takes a LINEAR GAIN, not stops: it computes
    # srgb(c16/65535 * expo). Passing 0.0 multiplies the image by zero, and the
    # first run of this script did exactly that -- every band read 0.000 and the
    # script printed "n63 SOFTER by 100.00%". The gauge itself was not fooled
    # (it REFUSED both sites as smoothed), but the summary line was, so the gain
    # is now derived and asserted rather than passed as a constant.
    #
    # The rule is the tool's own --auto-exposure rule: put the 99.9th percentile
    # of the reference at 0.90. It is taken from the REFERENCE arm and applied
    # unchanged to both, because a per-arm gain would be exactly the confound
    # that cost the softness lane its first number tonight.
    p999 = float(np.percentile(a32.astype(np.float64) / 65535.0, 99.9))
    expo = 0.90 / max(p999, 1e-9)
    print("display gain %.4f (from n32's 99.9th pct %.5f), applied to BOTH arms"
          % (expo, p999))

    for want in ("detail", "flat"):
        chosen = sites(sd, want)
        print("\n=== %s: %d sites, mean local sd %s ==="
              % (want, len(chosen), " ".join("%.1f" % m for m, _, _ in chosen)))
        acc = {}
        for m, y, x in chosen:
            c63 = a63[y:y + CROP, x:x + CROP].astype(np.float32) * g
            c32 = a32[y:y + CROP, x:x + CROP].astype(np.float32)
            d63 = bandlib.display(c63, expo)
            d32 = bandlib.display(c32, expo)
            t63, t32 = bandlib.terms(d63), bandlib.terms(d32)
            if float(np.mean(t32["sharp"])) < 1e-6 or float(np.mean(t32["20-60"])) < 1e-6:
                raise SystemExit("reference arm measures ZERO at (%d,%d) -- the display "
                                 "transform or the crop is dead, not the image" % (x, y))
            v = bandlib.verdict(t32, t63)
            for key in [lbl for lbl, _, _ in bandlib.BANDS] + ["grain", "sharp"]:
                acc.setdefault(key, []).append(
                    (float(np.mean(t32[key])), float(np.mean(t63[key])), v[key]))
            acc.setdefault("_v", []).append(v)

        print("  %-10s %-9s %-9s %-9s %s" % ("band", "n32", "n63", "n63/n32", "per-site"))
        for key in [lbl for lbl, _, _ in bandlib.BANDS] + ["grain", "sharp"]:
            rows = acc[key]
            name = "SHARPNESS" if key == "sharp" else key
            print("  %-10s %-9.3f %-9.3f %-9.4f %s"
                  % (name,
                     float(np.median([r[0] for r in rows])),
                     float(np.median([r[1] for r in rows])),
                     float(np.median([r[2] for r in rows])),
                     " ".join("%.4f" % r[2] for r in rows)))
        rs = float(np.median([r[2] for r in acc["sharp"]]))
        rg = float(np.median([r[2] for r in acc["grain"]]))
        print("  median sharpness: %s"
              % ("n63 SOFTER by %.2f%%" % (100 * (1 - rs)) if rs < 0.999
                 else ("n63 sharper by %.2f%%" % (100 * (rs - 1)) if rs > 1.001
                       else "level")))
        print("  median grain    : %s"
              % ("n63 CLEANER by %.2f%%" % (100 * (1 - rg)) if rg < 0.999
                 else ("n63 NOISIER by %.2f%%" % (100 * (rg - 1)) if rg > 1.001
                       else "level")))
        if want == "flat":
            print("  NOTE: in a flat region mean |gradient| is not acuity, it is noise.")
            print("  Read the sharpness row here as a second noise number, not a win.")
            # If the merge is winner-take-all on noise here -- and n_eff at band 0
            # in flat regions measures 1.008 at N=63 and 1.004 at N=32, which is
            # winner-take-all at both -- then the surviving coefficient is the
            # largest of N noisy candidates, and for Gaussian draws
            # E[max of N] ~ sigma*sqrt(2 ln N). Deepening the stack should then
            # RAISE flat-field noise by sqrt(ln 63 / ln 32), which is a number,
            # not a direction, and it is printed so the measurement can miss it.
            pred = float(np.sqrt(np.log(63.0) / np.log(32.0)))
            print("  selection-on-noise predicts x%.4f  (sqrt(ln63/ln32));"
                  " measured grain x%.4f" % (pred, rg))
            if rg <= 1.0:
                print("  MEASURED BELOW 1: deepening the stack made flat fields CLEANER.")
                print("  That refutes selection-on-noise at these sites.")


if __name__ == "__main__":
    main()

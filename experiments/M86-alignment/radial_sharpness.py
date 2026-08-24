"""M86b -- does registration sharpen the merged image, and does the gain grow with radius?

The prediction under test is specific and falsifiable. Misregistration from focus
breathing is a scale error about a centre of expansion, so the displacement between
frames is ZERO at the centre and grows LINEARLY with radius. If uncorrected drift is
what is softening these renders, then correcting it must:

  1. raise high-frequency energy overall, and
  2. raise it MORE at large radius than at small radius.

A uniform gain would mean something other than registration changed. A gain that is
flat or negative in the outer annuli refutes the claim outright.

Metric: mean squared gradient magnitude (Tenengrad) of the green channel, in annuli
of normalised radius. Green only, because it carries the luminance detail and avoids
demosaic colour interpolation dominating the statistic.
"""

import sys
import numpy as np
import tifffile

N_ANN = 8


def tenengrad_map(g):
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return gx * gx + gy * gy


def load_green(path):
    a = tifffile.imread(path)
    if a.ndim != 3 or a.shape[2] < 3:
        raise SystemExit(f"{path}: expected an RGB image, got shape {a.shape}")
    return a[:, :, 1].astype(np.float64)


def main(p_before, p_after, label):
    gb = load_green(p_before)
    ga = load_green(p_after)
    if gb.shape != ga.shape:
        raise SystemExit(f"shape mismatch: {gb.shape} vs {ga.shape}")

    h, w = gb.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    # Normalised radius, 1.0 at the corner.
    r = np.sqrt(((yy - cy) / cy) ** 2 + ((xx - cx) / cx) ** 2) / np.sqrt(2.0)

    tb = tenengrad_map(gb)
    ta = tenengrad_map(ga)

    # Trim the border: the warp leaves uncovered pixels at the frame edge and a
    # gradient there is an artefact of the fill, not of the subject.
    m = 96
    core = (slice(m, h - m), slice(m, w - m))
    tb, ta, r = tb[core], ta[core], r[core]

    print(f"=== {label} ===")
    print(f"  image {w}x{h}, green channel, Tenengrad")
    print()
    print("  annulus (norm r)      before          after     ratio")
    edges = np.linspace(0.0, r.max(), N_ANN + 1)
    rows = []
    for i in range(N_ANN):
        lo, hi = edges[i], edges[i + 1]
        sel = (r >= lo) & (r < hi)
        if sel.sum() < 1000:
            continue
        b = tb[sel].mean()
        a = ta[sel].mean()
        rows.append((lo, hi, b, a, a / b if b > 0 else float("nan")))
        print(f"  {lo:5.3f}-{hi:5.3f}   {b:12.1f}   {a:12.1f}   {a/b:7.4f}")

    wb, wa = tb.mean(), ta.mean()
    print()
    print(f"  WHOLE FRAME          {wb:12.1f}   {wa:12.1f}   {wa/wb:7.4f}")

    if len(rows) >= 4:
        inner = rows[0][4]
        outer = rows[-1][4]
        print()
        print(f"  innermost annulus ratio : {inner:.4f}")
        print(f"  outermost annulus ratio : {outer:.4f}")
        print(f"  outer / inner           : {outer/inner:.4f}")
        # The registered prediction: the gain must grow with radius.
        rr = np.array([x[4] for x in rows])
        mid = np.array([0.5 * (x[0] + x[1]) for x in rows])
        slope = np.polyfit(mid, rr, 1)[0]
        print(f"  slope of ratio on radius: {slope:+.4f} per unit normalised radius")
        print()
        if outer > inner and slope > 0:
            print("  VERDICT: gain GROWS with radius -- the signature of a corrected")
            print("           scale error about a centre of expansion. Consistent with")
            print("           misregistration having been the cause.")
        elif wa / wb > 1.0:
            print("  VERDICT: overall gain but NOT radius-dependent. Something improved,")
            print("           but it does not carry the signature of a scale correction.")
        else:
            print("  VERDICT: NO improvement. The claim is refuted on this stack.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit("usage: radial_sharpness.py <before.tif> <after.tif> [label]")
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "sharpness")

"""R10 -- signed residual inter-channel RADIAL displacement, off vs on.

The orchestrator retracted the sqrt(2) steer and made a specific, falsifiable
claim: the shipped correction OVER-corrects by k ~ 1.444, so the right
instrument is the SIGNED residual radial displacement between channels, where
under- and over-correction land on opposite sides of zero. My earlier W3
"keep-sign" bar cannot do this, because a correction that overshoots past zero
and one that does nothing both fail it.

## THE MODEL

Let D(r) be the true lateral-CA radial displacement of R relative to G. The
correction applies k*D. Then:

    residual_off = D
    residual_on  = D - k*D = (1 - k) * D
    ratio        = residual_on / residual_off = 1 - k

    k = 1.000  ->  ratio =  0.000   exact
    k < 1      ->  ratio in (0, 1)  under-corrected
    k > 1      ->  ratio < 0        OVER-corrected, sign inverted
    k = 1.444  ->  ratio = -0.444   the orchestrator's claim
    k = 1.456  ->  ratio = -0.456   its support-restricted mean

## BARS, REGISTERED BEFORE THE RUN

  T1  LATERAL CA IS PRESENT IN THE OFF ARM. The radial R-G displacement in
      the off arm must grow with r and be nonzero. If it does not, this
      estimator is not measuring lateral CA and nothing below means anything.

  T2  THE RATIO. Window-weighted residual_on / residual_off, aggregated over
      annuli inside the measured support (r <= 0.788).
        ratio <  0     -> OVER-corrected, confirms the direction
        ratio in (0,1) -> UNDER-corrected, contradicts the orchestrator
        ratio ~  0     -> correction is about right
      I register the orchestrator's prediction as -0.444 and will report the
      measured value against it WITHOUT adjusting the bar afterwards.
      Implied k = 1 - ratio.

  T3  TANGENTIAL NULL. The identical estimator run along the TANGENTIAL unit
      vector. Lateral CA is radial by construction; a magnification error
      cannot produce tangential displacement. So:
        - tangential must be much smaller than radial in the off arm, and
        - tangential must NOT change materially between arms.
      If tangential moves as much as radial, the estimator is picking up
      generic misregistration and T1/T2 are void. This is the measurement-side
      analogue of the tangentially-rotated placebo.

  T4  SHAPE. The APPLIED displacement (on - off) must be linear in r through
      the origin -- that is what a magnification error is. If the applied
      correction is instead flat in r, the model shape is wrong and a scalar
      will not fix it. Reported as R^2 of a through-origin linear fit.

## ESTIMATOR

Per window, a 1-D Lucas-Kanade along a chosen unit vector u:

    shift = sum(w * gu * (R - G)) / sum(w * gu^2)

with gu the directional derivative of G along u, after standardising R and G
within the window (zero mean, unit variance) so that the cross-channel
intensity difference does not bias the match. Weight = sum(gu^2), i.e. windows
with more structure along u count more. This is signed: +ve means R sits
FARTHER OUT along u than G.
"""
import os
import numpy as np
import tifffile

R7 = r"C:\dev\strehl-out\M107-chroma\r7"
WIN = 64
SUPPORT_R = 0.788
K_CLAIM = 1.444


def load_rg(p):
    a = tifffile.imread(p)
    r = a[..., 0].astype(np.float32)
    g = a[..., 1].astype(np.float32)
    return r, g


def windows(shape):
    h, w = shape
    cy, cx = h / 2.0, w / 2.0
    rmax = np.hypot(cx, cy)
    for y in range(0, h - WIN, WIN):
        for x in range(0, w - WIN, WIN):
            wy, wx = y + WIN / 2.0 - cy, x + WIN / 2.0 - cx
            rr = np.hypot(wx, wy) / rmax
            yield y, x, wx, wy, rr


def estimate(r, g, arm):
    """Return list of (radius, radial_shift, tang_shift, weight_rad, weight_tan)."""
    out = []
    for y, x, wx, wy, rr in windows(r.shape):
        if rr < 1e-6:
            continue
        R = r[y:y + WIN, x:x + WIN]
        G = g[y:y + WIN, x:x + WIN]
        sr, sg = R.std(), G.std()
        if sr < 1e-6 or sg < 1e-6:
            continue
        Rn = (R - R.mean()) / sr
        Gn = (G - G.mean()) / sg
        gy, gx = np.gradient(Gn)
        d = Rn - Gn
        n = np.hypot(wx, wy)
        ux, uy = wx / n, wy / n           # radial (outward)
        tx, ty = -uy, ux                  # tangential
        rec = [rr]
        for vx, vy in ((ux, uy), (tx, ty)):
            gu = vx * gx + vy * gy
            den = float((gu * gu).sum())
            if den < 1e-3:
                rec += [np.nan, 0.0]
                continue
            rec += [float((gu * d).sum()) / den, den]
        out.append(tuple(rec))
    return out


def agg(recs, idx_s, idx_w, lo, hi):
    """Weighted mean shift over an annulus."""
    num = den = 0.0
    n = 0
    for rec in recs:
        if not (lo <= rec[0] < hi):
            continue
        s, w = rec[idx_s], rec[idx_w]
        if not np.isfinite(s) or w <= 0:
            continue
        num += s * w
        den += w
        n += 1
    return (num / den if den > 0 else np.nan), den, n


def main():
    print("=" * 74)
    print("R10 -- signed residual inter-channel radial displacement")
    print(f"      window={WIN}px   support r<={SUPPORT_R}   claim k={K_CLAIM}"
          f" -> predicted ratio {1-K_CLAIM:+.3f}")
    print("=" * 74)

    r0, g0 = load_rg(os.path.join(R7, "off1.tif"))
    r1, g1 = load_rg(os.path.join(R7, "on.tif"))
    print(f"\nimage {r0.shape[1]}x{r0.shape[0]}")

    off = estimate(r0, g0, "off")
    on = estimate(r1, g1, "on")
    print(f"windows: off={len(off)}  on={len(on)}")

    edges = np.linspace(0.0, 1.0, 11)
    print("\n  annulus        n     RADIAL off    RADIAL on      applied"
          "     ratio")
    rows = []
    for i in range(10):
        lo, hi = edges[i], edges[i + 1]
        so, wo, no = agg(off, 1, 2, lo, hi)
        sn, wn, nn = agg(on, 1, 2, lo, hi)
        if not np.isfinite(so) or no < 5:
            print(f"  {lo:.2f}-{hi:.2f}  {no:6d}     -- below floor --")
            continue
        applied = sn - so
        ratio = sn / so if abs(so) > 1e-9 else np.nan
        mark = "" if hi <= SUPPORT_R else "  (outside support)"
        print(f"  {lo:.2f}-{hi:.2f}  {no:6d}   {so:+10.5f}   {sn:+10.5f}"
              f"   {applied:+10.5f}  {ratio:+8.3f}{mark}")
        rows.append((0.5 * (lo + hi), so, sn, applied, wo, hi <= SUPPORT_R))

    print("\nT1  is lateral CA present in the OFF arm?")
    rs = np.array([r[0] for r in rows])
    so = np.array([r[1] for r in rows])
    wts = np.array([r[4] for r in rows])
    slope_off = float(np.sum(wts * rs * so) / np.sum(wts * rs * rs))
    print(f"    through-origin slope of radial displacement vs r: "
          f"{slope_off:+.5f} px per unit r")
    print(f"    T1 {'PASS -- present and radial' if abs(slope_off) > 1e-3 else 'FAIL -- no radial signal'}")

    print("\nT2  THE RATIO (support-restricted, window-weighted)")
    ins = [r for r in rows if r[5]]
    num = sum(r[1] * r[4] for r in ins)
    den = sum(r[2] * r[4] for r in ins)
    ratio = den / num if abs(num) > 1e-12 else np.nan
    k_impl = 1.0 - ratio
    print(f"    annuli inside support: {len(ins)}")
    print(f"    weighted residual_on / residual_off = {ratio:+.4f}")
    print(f"    implied k = 1 - ratio               = {k_impl:.4f}")
    print(f"    orchestrator's claim                 k = {K_CLAIM:.4f} "
          f"(ratio {1-K_CLAIM:+.4f})")
    if ratio < -0.05:
        print(f"    T2 OVER-CORRECTED -- direction CONFIRMED, implied k={k_impl:.3f}")
    elif ratio > 0.05:
        print(f"    T2 UNDER-corrected -- CONTRADICTS the claim, implied k={k_impl:.3f}")
    else:
        print("    T2 correction is approximately exact")

    print("\nT3  TANGENTIAL NULL (physics forbids tangential lateral CA)")
    to, _, _ = agg(off, 3, 4, 0.0, SUPPORT_R)
    tn, _, _ = agg(on, 3, 4, 0.0, SUPPORT_R)
    ro, _, _ = agg(off, 1, 2, 0.0, SUPPORT_R)
    rn, _, _ = agg(on, 1, 2, 0.0, SUPPORT_R)
    print(f"    radial     off={ro:+.5f}  on={rn:+.5f}  applied={rn-ro:+.5f}")
    print(f"    tangential off={to:+.5f}  on={tn:+.5f}  applied={tn-to:+.5f}")
    rat = abs(tn - to) / max(abs(rn - ro), 1e-12)
    print(f"    |applied tangential| / |applied radial| = {rat:.4f}")
    print(f"    T3 {'PASS -- correction is radial, estimator is not seeing generic shift' if rat < 0.25 else 'FAIL -- tangential moves too; T1/T2 VOID'}")

    print("\nT4  SHAPE -- is the APPLIED correction linear in r through origin?")
    ap = np.array([r[3] for r in rows])
    sl = float(np.sum(wts * rs * ap) / np.sum(wts * rs * rs))
    pred = sl * rs
    ss_res = float(np.sum(wts * (ap - pred) ** 2))
    ss_tot = float(np.sum(wts * (ap - np.average(ap, weights=wts)) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else np.nan
    print(f"    slope {sl:+.5f} px per unit r   R^2(through origin) = {r2:.4f}")
    print(f"    T4 {'PASS -- magnification-shaped; a scalar is the right fix' if r2 > 0.8 else 'AMBIGUOUS -- shape may not be a pure magnification'}")
    print("=" * 74)


if __name__ == "__main__":
    main()

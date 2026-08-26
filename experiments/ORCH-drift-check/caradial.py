"""Is the lateral-CA correction a RADIAL SHIFT (real) or a BLUR (harm)?

Two earlier discriminators died and are recorded here so they are not retried:

  1. Amplitude of HF(R).  Dead: removing a fringe and blurring both lower it.
  2. corr(HF_R, HF_G).  Dead by its own potency control: a synthetic blur of R
     RAISED the correlation (0.5637 -> 0.6036), because blurring removes noise
     that is uncorrelated with green.  Both hypotheses predict the same sign.

This one uses physics instead of amplitude.  Lateral chromatic aberration is a
per-channel magnification difference: the displacement between R and G is
strictly RADIAL from the optical centre and grows with field radius.  So:

    real CA correction ->  displacement field is radial, |d| grows with radius,
                           and the TANGENTIAL component is zero.
    blur               ->  no displacement at all; radial and tangential both
                           sit at the noise floor together.

The tangential component is a placebo the physics hands us for free: no
parameter fitting, no second render, and it is measured on the same tiles by
the same estimator as the signal.

Usage:
    python caradial.py <arm_off.tif> <arm_on.tif> [tile] [step]
"""

import sys
import numpy as np
import tifffile


def hf(ch):
    v = np.zeros_like(ch)
    v[1:-1, 1:-1] = (4.0 * ch[1:-1, 1:-1]
                     - ch[:-2, 1:-1] - ch[2:, 1:-1]
                     - ch[1:-1, :-2] - ch[1:-1, 2:])
    return v


def shift_of(a, b):
    """Sub-pixel shift taking a -> b, by FFT cross-correlation + parabola."""
    w = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    A = np.fft.rfft2(a * w)
    B = np.fft.rfft2(b * w)
    d = A.conj() * B
    m = np.abs(d)
    m[m == 0] = 1.0
    c = np.fft.irfft2(d / m, s=a.shape)          # phase correlation
    k = int(np.argmax(c))
    py, px = np.unravel_index(k, c.shape)
    peak = c[py, px]

    def par(vm, v0, vp):
        den = (vm - 2 * v0 + vp)
        return 0.0 if den == 0 else 0.5 * (vm - vp) / den

    dy = py + par(c[(py - 1) % c.shape[0], px], c[py, px], c[(py + 1) % c.shape[0], px])
    dx = px + par(c[py, (px - 1) % c.shape[1]], c[py, px], c[py, (px + 1) % c.shape[1]])
    if dy > a.shape[0] / 2:
        dy -= a.shape[0]
    if dx > a.shape[1] / 2:
        dx -= a.shape[1]
    return float(dy), float(dx), float(peak)


def main():
    p_off, p_on = sys.argv[1], sys.argv[2]
    tile = int(sys.argv[3]) if len(sys.argv) > 3 else 256
    step = int(sys.argv[4]) if len(sys.argv) > 4 else 384
    off = tifffile.imread(p_off).astype(np.float32) / 65535.0
    on = tifffile.imread(p_on).astype(np.float32) / 65535.0
    H, W, _ = off.shape
    cy, cx = H / 2.0, W / 2.0
    print(f"shape {off.shape}  tile={tile} step={step}  centre=({cy:.0f},{cx:.0f})")

    # ---- COMMISSIONING -------------------------------------------------
    # This estimator is not trusted until it is shown to recover a shift it
    # was GIVEN.  The corpus has already been bitten once by a shift estimator
    # that shrank (fact 45: recovery ratio 0.56 on a real pair), so a raw
    # number from an uncommissioned estimator is not evidence.
    #
    # Plant a known pure-radial magnification change on R of arm-OFF, at a
    # size chosen to bracket the quantity being measured, and report the
    # recovery ratio.  Every radial number below is divided by it.
    print("\nCOMMISSIONING  plant a known radial shift, require recovery")
    yy = (np.arange(H, dtype=np.float32) - cy)[:, None]
    xx = (np.arange(W, dtype=np.float32) - cx)[None, :]
    rmax = float(np.hypot(cy, cx))
    ratios = []
    for planted in (0.05, 0.20, 0.50):
        k = planted / rmax                      # magnification delta
        src_y = np.clip(cy + yy * (1.0 - k), 0, H - 1.001)
        src_x = np.clip(cx + xx * (1.0 - k), 0, W - 1.001)
        y0 = src_y.astype(np.int32); x0 = src_x.astype(np.int32)
        fy = (src_y - y0); fx = (src_x - x0)
        R = off[:, :, 0]
        planted_R = ((1 - fy) * ((1 - fx) * R[y0, x0] + fx * R[y0, x0 + 1])
                     + fy * ((1 - fx) * R[y0 + 1, x0] + fx * R[y0 + 1, x0 + 1]))
        pl = off.copy(); pl[:, :, 0] = planted_R
        meas = []
        for y in range(0, H - tile, step * 3):
            for x in range(0, W - tile, step * 3):
                if float(np.std(off[y:y + tile, x:x + tile, 1])) < 0.02:
                    continue
                ry, rx = (y + tile / 2 - cy), (x + tile / 2 - cx)
                r = float(np.hypot(ry, rx))
                if r < 1e-6:
                    continue
                dy, dx, _ = shift_of(hf(off[y:y + tile, x:x + tile, 0]),
                                     hf(pl[y:y + tile, x:x + tile, 0]))
                if abs(dy) > 3 and abs(dx) > 3:
                    continue
                meas.append((dy * ry / r + dx * rx / r) / (r / rmax))
        got = float(np.median(meas)) if meas else float("nan")
        ratios.append(abs(got) / planted)
        print(f"  planted {planted:.2f} px @ corner -> recovered {abs(got):.4f} px  "
              f"ratio {abs(got)/planted:.3f}   (n={len(meas)})")
    recov = float(np.median(ratios))
    if not (0.2 < recov < 3.0):
        print(f"  *** recovery ratio {recov:.3f} is not usable. STOP.")
        return 1
    print(f"  recovery ratio (median) = {recov:.3f}  -- radial numbers below are "
          f"divided by this")
    # --------------------------------------------------------------------

    recs = {"R": [], "G": [], "B": []}
    chans = (("R", 0), ("G", 1), ("B", 2))
    ntile = 0
    for y in range(0, H - tile, step):
        for x in range(0, W - tile, step):
            a0 = off[y:y + tile, x:x + tile, 1]
            # only tiles with real structure can report a shift at all
            if float(np.std(a0)) < 0.02:
                continue
            ntile += 1
            ry, rx = (y + tile / 2 - cy), (x + tile / 2 - cx)
            r = float(np.hypot(ry, rx))
            if r < 1e-6:
                continue
            uy, ux = ry / r, rx / r          # radial unit
            ty, tx = -ux, uy                 # tangential unit
            for nm, c in chans:
                dy, dx, pk = shift_of(hf(off[y:y + tile, x:x + tile, c]),
                                      hf(on[y:y + tile, x:x + tile, c]))
                if abs(dy) > 3 or abs(dx) > 3:
                    continue
                recs[nm].append((r, dy * uy + dx * ux, dy * ty + dx * tx))
    print(f"textured tiles measured: {ntile}\n")

    print(f"{'ch':<3} {'n':>5} {'radial px':>11} {'tangential px':>14} {'|rad|/|tan|':>12}")
    out = {}
    for nm, _ in chans:
        a = np.array(recs[nm])
        if a.size == 0:
            continue
        rad, tan = a[:, 1], a[:, 2]
        mr, mt = float(np.median(np.abs(rad))), float(np.median(np.abs(tan)))
        out[nm] = (a, mr, mt)
        print(f"{nm:<3} {len(a):>5} {mr:>11.4f} {mt:>14.4f} {mr/mt if mt else float('nan'):>12.2f}")

    print("\nPLACEBO  tangential must sit at the noise floor for a lateral-CA fix.")
    print("         green is the second placebo: it is the reference channel.")
    print("\nradial displacement vs field radius (binned medians, px):")
    edges = np.linspace(0, np.hypot(cy, cx), 7)
    hdr = "  ".join(f"{0.5*(edges[i]+edges[i+1]):>7.0f}" for i in range(len(edges) - 1))
    print(f"{'ch':<3} r-> {hdr}")
    for nm in ("R", "G", "B"):
        if nm not in out:
            continue
        a = out[nm][0]
        cells = []
        for i in range(len(edges) - 1):
            m = (a[:, 0] >= edges[i]) & (a[:, 0] < edges[i + 1])
            cells.append(f"{np.median(a[m, 1]):>7.3f}" if m.sum() >= 4 else f"{'-':>7}")
        print(f"{nm:<3}     " + "  ".join(cells))

    print()
    for nm in ("R", "B"):
        if nm not in out:
            continue
        a, mr, mt = out[nm]
        m = a[:, 0] > 0.6 * np.hypot(cy, cx)
        outer = float(np.median(np.abs(a[m, 1]))) if m.sum() >= 4 else float("nan")
        inner = a[:, 0] < 0.3 * np.hypot(cy, cx)
        ctr = float(np.median(np.abs(a[inner, 1]))) if inner.sum() >= 4 else float("nan")
        grow = outer / ctr if ctr else float("nan")
        radial_dominates = mr > 2.0 * mt
        grows = grow > 1.5
        verdict = ("RADIAL SHIFT -- consistent with lateral CA"
                   if (radial_dominates and grows) else
                   "NOT a clean radial shift")
        print(f"{nm}: |radial| centre {ctr:.4f} px -> outer {outer:.4f} px "
              f"(x{grow:.2f}); radial/tangential {mr/mt if mt else float('nan'):.2f}")
        print(f"   -> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

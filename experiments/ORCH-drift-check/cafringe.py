"""Measure lateral-CA fringing between two renders that differ ONLY in STREHL_FIX_CA.

Design notes (house rules this instrument obeys):

  * The tile/pixel selection is made on the MEAN of the two arms, never on one
    arm, so neither arm can choose the ground it is judged on (rule from
    flatcrop.py / SS28).
  * Every measurement is reported beside its DOSE.  The edge set is where
    lateral CA can act at all; the flat set is where a pure geometric channel
    warp must be a near-no-op.  The flat set is therefore the built-in placebo,
    and a "win" that also moves the placebo is not a win.
  * Whole-frame census first, picture second.  The crop is an illustration of a
    number that was already measured everywhere.

Usage:
    python cafringe.py <arm_off.tif> <arm_on.tif> <outdir> [--crop Y X]
"""

import sys
import os
import numpy as np
import tifffile


def srgb_to_linear(a):
    a = a.astype(np.float32) / 65535.0
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def sobel_mag(g):
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return np.hypot(gx, gy)


def robust_sigma(v):
    if v.size == 0:
        return float("nan")
    med = np.median(v)
    return float(1.4826 * np.median(np.abs(v - med)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 3:
        print(__doc__)
        return 2
    p_off, p_on, outdir = args[0], args[1], args[2]
    crop_yx = None
    if "--crop" in sys.argv:
        i = sys.argv.index("--crop")
        crop_yx = (int(sys.argv[i + 1]), int(sys.argv[i + 2]))
    os.makedirs(outdir, exist_ok=True)

    off = tifffile.imread(p_off)
    on = tifffile.imread(p_on)
    if off.shape != on.shape:
        raise SystemExit(f"shape mismatch {off.shape} vs {on.shape}")
    print(f"shape {off.shape}  dtype {off.dtype}")

    # Are they even different?  A no-op arm would make every number below a lie.
    diff_px = int(np.count_nonzero(np.any(off != on, axis=2)))
    total_px = off.shape[0] * off.shape[1]
    print(f"DOSE (frame): pixels differing between arms {diff_px:,} / {total_px:,} "
          f"= {100.0*diff_px/total_px:.3f}%   max |delta| = {int(np.max(np.abs(off.astype(np.int32)-on.astype(np.int32))))} DN")
    if diff_px == 0:
        raise SystemExit("ABORT: the two arms are identical -- the intervention did not land.")

    lo = srgb_to_linear(off)
    ln = srgb_to_linear(on)

    # Selection surface: the MEAN of the arms.  Neither arm picks its own ground.
    gmean = 0.5 * (lo[:, :, 1] + ln[:, :, 1])
    grad = sobel_mag(gmean)

    hi_thr = float(np.quantile(grad, 0.99))
    lo_thr = float(np.quantile(grad, 0.50))
    edge = grad >= hi_thr
    flat = grad <= lo_thr
    print(f"selection (on arm-mean): edge = top 1% grad (>= {hi_thr:.5f}), "
          f"n={int(edge.sum()):,}   flat = bottom 50% (<= {lo_thr:.5f}), n={int(flat.sum()):,}")

    rows = []
    for name, m in (("EDGE (dose set)", edge), ("FLAT (placebo)", flat)):
        for arm, img in (("ca-OFF", lo), ("ca-ON ", ln)):
            rb = (img[:, :, 0] - img[:, :, 2])[m]
            rg = (img[:, :, 0] - img[:, :, 1])[m]
            bg = (img[:, :, 2] - img[:, :, 1])[m]
            rows.append((name, arm,
                         robust_sigma(rb), float(np.quantile(np.abs(rb), 0.999)),
                         robust_sigma(rg), robust_sigma(bg)))

    print()
    print(f"{'set':<17} {'arm':<7} {'sigma(R-B)':>11} {'p99.9|R-B|':>11} {'sigma(R-G)':>11} {'sigma(B-G)':>11}")
    for r in rows:
        print(f"{r[0]:<17} {r[1]:<7} {r[2]:>11.5f} {r[3]:>11.5f} {r[4]:>11.5f} {r[5]:>11.5f}")

    print()
    for i in (0, 2):
        setname = rows[i][0]
        a, b = rows[i], rows[i + 1]
        for j, lbl in ((2, "sigma(R-B)"), (3, "p99.9|R-B|"), (4, "sigma(R-G)"), (5, "sigma(B-G)")):
            ratio = b[j] / a[j] if a[j] else float("nan")
            print(f"{setname:<17} {lbl:<11} ON/OFF = {ratio:6.4f}   ({a[j]:.5f} -> {b[j]:.5f})")
        print()

    if crop_yx:
        try:
            from PIL import Image
        except ImportError:
            return 0
        y, x, s = crop_yx[0], crop_yx[1], 520
        panels = []
        for img in (off, on):
            c = img[y:y + s, x:x + s]
            panels.append((c >> 8).astype(np.uint8))
        gap = np.full((s, 12, 3), 32, np.uint8)
        sheet = np.hstack([panels[0], gap, panels[1]])
        im = Image.fromarray(sheet)
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 170, 13], fill=(0, 0, 0))
        d.text((3, 2), f"ca OFF  y{y} x{x}", fill=(255, 210, 60))
        d.rectangle([s + 12, 0, s + 12 + 150, 13], fill=(0, 0, 0))
        d.text((s + 15, 2), "ca ON (fix-ca)", fill=(255, 210, 60))
        dst = os.path.join(outdir, f"cafringe-y{y}-x{x}-AB.png")
        im.save(dst)
        print(f"  {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

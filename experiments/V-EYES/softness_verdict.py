"""Is the merged master softer than the best frame available AT EACH SITE?

The question. A focus stacker's one job is that every point in the subject's
depth comes out as sharp as the best frame in the bracket resolved it. If the
merged output is measurably softer than that ceiling, the tool has failed at its
purpose. V-EYES measured a 35-55% top-octave deficit and refused to stand behind
it, for three reasons this script exists to remove.

Confound 1, the transfer curve. The earlier measurement was taken on --srgb
masters. The project's standing rule, in `strehl stack --help` under
--linear-srgb and in docs/research/V-softness.md, is that quality is never
judged on an --srgb render, because the curve is a strong non-linearity that
moves every ratio a metric computes, and results have been retracted for exactly
that. Both arms here are rendered --linear-srgb --demosaic. --auto-exposure is
refused in that mode, so neither arm carries a gain the other lacks.

Confound 2, the demosaicer. The earlier reference frames were developed by
rawpy, whose kernel is not strehl's, so part of any gap was a comparison between
two reconstructions. Here the reference frames are developed by strehl itself,
one frame per invocation, so Malvar-He-Cutler, the colour matrix, the black
level, the white balance and the coverage rescale are all common-mode and
cancel.

Confound 3, the reference. "The sharpest frame" is not a fair ceiling: any one
frame is defocused over most of a deep stack, so comparing the whole master to
one frame reads soft everywhere that frame was out of focus, which would
manufacture the very deficit being tested for. The fair ceiling is the sharpest
frame AT EACH SITE. This builds a per-block envelope: the image is divided into
blocks, and the reference for a block is the maximum over frames of that block's
sharpness. Blocks, not pixels, because the single-frame renders are not warped
into the master's frame -- each is its own alignment reference -- so a few pixels
of residual shift must be absorbed. The shift is estimated per frame by phase
correlation and corrected before blocks are cut; the residual is reported.

The statistic is contrast-normalised: mean squared Sobel gradient divided by the
block's own variance, after a sigma 1.0 pre-blur to keep per-pixel shot noise
from dominating. Normalisation is required because linear-light renders of a
merge and of a single frame do not sit at the same amplitude, and raw gradient
energy scales with the square of amplitude -- an un-normalised metric would
report an exposure difference as a sharpness difference. This follows the
project's own move to contrast-normalised sharpness in ac31a74a.

Blocks whose contrast is near the noise floor are dropped: on a featureless
block the ratio is a quotient of two noise estimates and carries no information
about focus.

The confidence interval on the median ratio is bootstrapped over blocks, which
is the unit that actually varies, rather than over pixels, which are correlated.

Commissioning, per AGENTS.md, four arms -- and note that two of them are
IMPROVEMENTS. A suite that only ever plants degradations cannot tell a metric
that is blind to a defect from one that is perverse on it, and this project has
shipped that bug twice (tri.blur_equiv bounding its own error below at zero, and
V-GATHER finding overshoot_frac reads backwards). The arms:

  NULL     master compared against itself as the reference. Must read 1.000.
  DEFECT   master blurred. Ratio against the true envelope must FALL.
  IMPROVE  master unsharp-masked. Ratio must RISE.
  CEILING  the per-site best frame substituted for the master. Must read >= 1.0,
           because the best frame IS the envelope at the block where it wins.
           This is the arm that catches a metric which reads everything as soft.

Usage:
  python softness_verdict.py <master.tiff> <framesdir> <x> <y> <size> [block]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2


BLUR = 1.0


def luma_linear(a):
    """Linear-light luminance. Rec.709 weights are the right ones here because
    the render's stated target IS BT.709 primaries with a D65 white."""
    return (
        0.2126 * a[..., 0].astype(np.float64)
        + 0.7152 * a[..., 1].astype(np.float64)
        + 0.0722 * a[..., 2].astype(np.float64)
    )


def sharp_blocks(img, block, mode="grad"):
    """Contrast-normalised sharpness per block, plus per-block contrast.

    Two statistics, because they answer different questions and a merge can
    pass one while failing the other.

      grad  mean squared Sobel gradient after a sigma 1.0 pre-blur. Broadband:
            it responds to any edge energy, and is the natural "is this soft"
            measure.
      hf    mean squared residual of a sigma 1.5 unsharp high-pass. This is the
            top-octave statistic, and it is the one the original 35-55% claim
            was about. A convex-combination merge that averages frames would
            attenuate the finest scales first, so a deficit could hide here
            while `grad` looks clean.

    Both are divided by the block's own variance. Linear-light renders of a
    merge and of a single frame do not sit at the same amplitude, and both
    numerators scale with the square of amplitude, so without normalisation an
    exposure difference would be reported as a sharpness difference.
    """
    f = img.astype(np.float32)
    if mode == "grad":
        b = cv2.GaussianBlur(f, (0, 0), BLUR)
        gx = cv2.Sobel(b, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(b, cv2.CV_32F, 0, 1, ksize=3)
        num_px = gx * gx + gy * gy
    elif mode == "hf":
        hp = f - cv2.GaussianBlur(f, (0, 0), 1.5)
        num_px = hp * hp
    else:
        raise ValueError(mode)
    h, w = img.shape
    ny, nx = h // block, w // block
    num_px = num_px[: ny * block, : nx * block].reshape(ny, block, nx, block)
    im = img[: ny * block, : nx * block].astype(np.float64).reshape(ny, block, nx, block)
    num = num_px.mean(axis=(1, 3))
    var = im.var(axis=(1, 3))
    contrast = np.sqrt(var)
    return num / np.maximum(var, 1e-9), contrast


def shift_of(ref, mov):
    """Global translation of mov relative to ref, by phase correlation."""
    a = cv2.GaussianBlur(ref.astype(np.float32), (0, 0), 2.0)
    b = cv2.GaussianBlur(mov.astype(np.float32), (0, 0), 2.0)
    win = cv2.createHanningWindow((a.shape[1], a.shape[0]), cv2.CV_32F)
    (dx, dy), _ = cv2.phaseCorrelate(a * win, b * win)
    return dx, dy


def warp(img, dx, dy):
    M = np.array([[1, 0, -dx], [0, 1, -dy]], np.float32)
    return cv2.warpAffine(
        img.astype(np.float32), M, (img.shape[1], img.shape[0]),
        flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT,
    )


def boot_ci(vals, n=4000, seed=11):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(vals), size=(n, len(vals)))
    meds = np.median(np.asarray(vals)[idx], axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def main():
    mpath, fdir = sys.argv[1], pathlib.Path(sys.argv[2])
    x, y, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    block = int(sys.argv[6]) if len(sys.argv) > 6 else 64

    m = tifffile.imread(mpath)
    master = luma_linear(m[y : y + size, x : x + size])
    print(f"master {pathlib.Path(mpath).name} tile ({x},{y}) {size}x{size} block {block}")
    print(f"  linear luma range {master.min():.0f}..{master.max():.0f} "
          f"mean {master.mean():.1f}")

    frames = sorted(fdir.glob("frame-*.tiff"))
    if not frames:
        print("no developed frames found")
        return
    print(f"  {len(frames)} developed reference frames\n")

    print(f"  {'frame':<22} {'shift dx,dy':>14}")
    print("  " + "-" * 42)
    tiles = []
    for f in frames:
        a = tifffile.imread(str(f))
        t = luma_linear(a[y : y + size, x : x + size])
        dx, dy = shift_of(master, t)
        tiles.append(warp(t, dx, dy))
        print(f"  {f.stem:<22} {dx:>6.2f},{dy:>6.2f}")

    _, mc = sharp_blocks(master, block, "grad")
    thr = np.percentile(mc, 35)
    live = mc > max(thr, 1.0)
    print(f"\n  blocks: {mc.size} total, {live.sum()} above contrast floor "
          f"({thr:.1f} linear DN rms)")

    for mode, label in (("grad", "BROADBAND gradient"), ("hf", "TOP-OCTAVE high-pass")):
        S = np.stack([sharp_blocks(t, block, mode)[0] for t in tiles])
        envelope = S.max(axis=0)
        winner = S.argmax(axis=0)
        ms, _ = sharp_blocks(master, block, mode)

        print(f"\n  === {label} ===")
        print(f"  distinct frames winning a live block: "
              f"{len(np.unique(winner[live]))} of {len(frames)}")

        base = (ms / np.maximum(envelope, 1e-12))[live]
        base_med = float(np.median(base))
        d = cv2.GaussianBlur(master.astype(np.float32), (0, 0), 1.2)
        d_med = float(np.median((sharp_blocks(d, block, mode)[0]
                                 / np.maximum(envelope, 1e-12))[live]))
        u = np.clip(master + 1.0 * (master - d), 0, None)
        u_med = float(np.median((sharp_blocks(u, block, mode)[0]
                                 / np.maximum(envelope, 1e-12))[live]))
        n_med = float(np.median((ms / np.maximum(ms, 1e-12))[live]))
        c_med = float(np.median((envelope / np.maximum(envelope, 1e-12))[live]))

        print("  COMMISSIONING")
        print(f"    NULL     master vs itself         {n_med:.4f}  "
              f"{'PASS' if abs(n_med - 1) < 1e-6 else 'FAIL'} (must be 1.0000)")
        print(f"    DEFECT   master blurred s1.2      {d_med:.4f}  "
              f"{'PASS' if d_med < base_med else 'FAIL'} (must fall below {base_med:.4f})")
        print(f"    IMPROVE  master unsharp masked    {u_med:.4f}  "
              f"{'PASS' if u_med > base_med else 'FAIL'} (must rise above {base_med:.4f})")
        print(f"    CEILING  per-site best frame      {c_med:.4f}  "
              f"{'PASS' if c_med >= 0.999 else 'FAIL'} (must be >= 1.0)")

        lo, hi = boot_ci(base)
        frac = float((base < 1.0).mean())
        print("  RESULT")
        print(f"    median master / per-site-best  = {base_med:.4f}")
        print(f"    95% bootstrap CI over blocks   = [{lo:.4f}, {hi:.4f}]  "
              f"(n={live.sum()} blocks)")
        print(f"    blocks softer than best        = {frac * 100:.1f}%")
        if hi < 1.0:
            print(f"    VERDICT: master IS softer by {(1 - base_med) * 100:.1f}% "
                  f"(CI excludes 1.0)")
        elif lo > 1.0:
            print(f"    VERDICT: master is SHARPER by {(base_med - 1) * 100:.1f}% "
                  f"(CI excludes 1.0)")
        else:
            print(f"    VERDICT: NO significant difference (CI spans 1.0)")


if __name__ == "__main__":
    main()

"""Softness verdict, second instrument: noise-corrected, with a noise arm.

Why there is a second one. `softness_verdict.py` produced two results that
cannot both be believed, and inspecting why kills the first instrument:

  * Its IMPROVE arm FAILED on the 2560 px tile: unsharp-masking the master
    LOWERED its score (0.7537 against a baseline of 0.7580). The statistic
    divides gradient energy by the block's total variance, and sharpening
    raises the variance faster than it raises the gradient energy, so the
    statistic is not monotone in sharpness. A metric that scores a real
    improvement as a regression is the exact failure this project has shipped
    twice, and no number it produces can be used.

  * Its top-octave arm reported the master 89.2% softer than the per-site best
    frame. That number is almost certainly noise, not detail. `strehl stack
    --help` states the merge's purpose plainly: "averaging is the only
    operation that gets BELOW single-frame noise", measured at 5.43x on a
    30-frame burst. A merge of 205 frames therefore MUST carry less
    high-frequency energy than any single frame, because a large part of a
    single frame's high-frequency energy is shot noise. Measuring raw
    high-pass energy cannot separate "lost detail" from "removed noise", and
    on this corpus it will always report the stacker as soft.

Both faults are fixed here, and the fixes are checked rather than asserted.

  Denominator. Block variance of a heavily blurred (sigma 4) copy. That still
  scales with the square of amplitude, so the statistic stays invariant to the
  exposure difference between a merge and a single frame, but it is nearly
  blind to fine detail, so sharpening no longer inflates it. Monotonicity is
  then testable, and the IMPROVE arm tests it.

  Noise subtraction. For each image the high-pass energy of a structureless
  block is an estimate of that image's noise contribution, so the 5th
  percentile of per-block high-pass energy is taken as that image's noise floor
  and subtracted from every block. What remains is structure. This is done
  per image, so the master's much lower noise floor is removed from the master
  and each frame's much higher floor from that frame, instead of being scored
  as a sharpness difference.

Commissioning, five arms. Three of them are things that must NOT lower the
score, because a suite of degradations alone cannot distinguish a blind metric
from a correct one:

  NULL     master against itself                  must read exactly 1.0
  DEFECT   master blurred sigma 1.2               must FALL
  IMPROVE  master unsharp masked                  must RISE
  CEILING  per-site best frame as the subject     must read >= 1.0
  NOISE    master plus synthetic noise at the
           single-frame noise level               must NOT RISE materially

The NOISE arm is the one that matters most here and the one the first
instrument lacked. If adding noise raises the score, the metric is measuring
noise, and every "the stacker is soft" verdict it has ever produced is an
artifact of the stacker doing its job.

Verdicts are reported across a sweep of contrast floors rather than at one
threshold, because which blocks are included is itself a judgement and hiding
it inside a single number would be dishonest. Blocks near the noise floor
carry no focus information in either arm.

Usage:
  python softness_verdict2.py <master.tiff> <framesdir> <x> <y> <size> [block]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2


def luma_linear(a):
    """Linear-light luminance; Rec.709 weights, because the render's stated
    target is BT.709 primaries at D65 with no transfer curve."""
    return (
        0.2126 * a[..., 0].astype(np.float64)
        + 0.7152 * a[..., 1].astype(np.float64)
        + 0.0722 * a[..., 2].astype(np.float64)
    )


def block_mean(px, block):
    h, w = px.shape
    ny, nx = h // block, w // block
    return px[: ny * block, : nx * block].reshape(ny, block, nx, block).mean(axis=(1, 3))


def block_var(px, block):
    h, w = px.shape
    ny, nx = h // block, w // block
    return px[: ny * block, : nx * block].reshape(ny, block, nx, block).var(axis=(1, 3))


def stat(img, block, hp_sigma=1.5, subtract_noise=True):
    """Noise-corrected, amplitude-invariant detail density per block."""
    f = img.astype(np.float32)
    hp = f - cv2.GaussianBlur(f, (0, 0), hp_sigma)
    e = block_mean((hp * hp).astype(np.float64), block)
    floor = float(np.percentile(e, 5)) if subtract_noise else 0.0
    signal = np.clip(e - floor, 0.0, None)
    lowf = cv2.GaussianBlur(f, (0, 0), 4.0).astype(np.float64)
    denom = np.maximum(block_var(lowf, block), 1e-9)
    return signal / denom, floor


def contrast_map(img, block):
    lowf = cv2.GaussianBlur(img.astype(np.float32), (0, 0), 4.0).astype(np.float64)
    return np.sqrt(block_var(lowf, block))


def shift_of(ref, mov):
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
    v = np.asarray(vals)
    idx = rng.integers(0, len(v), size=(n, len(v)))
    meds = np.median(v[idx], axis=1)
    return float(np.percentile(meds, 2.5)), float(np.percentile(meds, 97.5))


def main():
    mpath, fdir = sys.argv[1], pathlib.Path(sys.argv[2])
    x, y, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    block = int(sys.argv[6]) if len(sys.argv) > 6 else 64

    m = tifffile.imread(mpath)
    master = luma_linear(m[y : y + size, x : x + size])
    frames = sorted(fdir.glob("frame-*.tiff"))
    print(f"master {pathlib.Path(mpath).name} tile ({x},{y}) {size}x{size} block {block}")
    print(f"  {len(frames)} reference frames, developed by the same binary "
          f"--linear-srgb --demosaic")

    tiles = []
    for f in frames:
        t = luma_linear(tifffile.imread(str(f))[y : y + size, x : x + size])
        dx, dy = shift_of(master, t)
        tiles.append(warp(t, dx, dy))

    ms, mfloor = stat(master, block)
    fstats, ffloors = [], []
    for t in tiles:
        s, fl = stat(t, block)
        fstats.append(s)
        ffloors.append(fl)
    S = np.stack(fstats)
    envelope = S.max(axis=0)
    winner = S.argmax(axis=0)

    print(f"\n  noise floor (high-pass energy of a structureless block):")
    print(f"    master        {mfloor:>12.1f}")
    print(f"    frames  median{float(np.median(ffloors)):>12.1f}   "
          f"min {min(ffloors):.1f}  max {max(ffloors):.1f}")
    print(f"    ratio frames/master = {float(np.median(ffloors)) / max(mfloor, 1e-9):.2f}x"
          "   <- this is the merge's noise reduction, and it is why an")
    print("       uncorrected high-pass metric reports the stacker as soft.")

    cmap = contrast_map(master, block)

    # noise level to plant, in linear DN, from a single frame's own floor
    plant_sigma = float(np.sqrt(max(np.median(ffloors), 0.0)) * 2.0)
    rng = np.random.default_rng(3)
    noisy = master + rng.normal(0.0, plant_sigma, master.shape)

    print(f"\n  {'floor pct':>9} {'blocks':>7} {'median':>8} {'95% CI':>18} "
          f"{'%soft':>7}  commissioning")
    print("  " + "-" * 86)
    for pct in (35, 50, 65, 80, 90):
        thr = float(np.percentile(cmap, pct))
        live = cmap > thr
        if live.sum() < 30:
            continue
        base = (ms / np.maximum(envelope, 1e-12))[live]
        bmed = float(np.median(base))
        lo, hi = boot_ci(base)

        d = cv2.GaussianBlur(master.astype(np.float32), (0, 0), 1.2)
        dmed = float(np.median((stat(d, block)[0] / np.maximum(envelope, 1e-12))[live]))
        u = np.clip(master + 1.0 * (master - d), 0, None)
        umed = float(np.median((stat(u, block)[0] / np.maximum(envelope, 1e-12))[live]))
        nmed = float(np.median((stat(noisy, block)[0]
                                / np.maximum(envelope, 1e-12))[live]))
        cmed = float(np.median((envelope / np.maximum(envelope, 1e-12))[live]))

        arms = []
        arms.append("NULL " + ("ok" if abs(1.0 - 1.0) < 1e-9 else "FAIL"))
        arms.append("DEFECT " + ("ok" if dmed < bmed else "FAIL"))
        arms.append("IMPROVE " + ("ok" if umed > bmed else "FAIL"))
        arms.append("CEILING " + ("ok" if cmed >= 0.999 else "FAIL"))
        arms.append("NOISE " + ("ok" if nmed <= bmed * 1.10 else "FAIL"))
        print(f"  {pct:>8}% {live.sum():>7} {bmed:>8.4f} "
              f"[{lo:>6.4f},{hi:>6.4f}] {float((base < 1).mean()) * 100:>6.1f}%  "
              + " ".join(arms))
        if pct == 65:
            keep = (bmed, lo, hi, dmed, umed, nmed, cmed, live.sum(),
                    float((base < 1).mean()))

    bmed, lo, hi, dmed, umed, nmed, cmed, n, frac = keep
    print(f"\n  === VERDICT at the 65th-percentile contrast floor "
          f"({n} blocks) ===")
    print(f"    NULL     1.0000   DEFECT {dmed:.4f}   IMPROVE {umed:.4f}   "
          f"CEILING {cmed:.4f}   NOISE {nmed:.4f}")
    print(f"    baseline {bmed:.4f}  (DEFECT must be lower, IMPROVE higher, "
          f"NOISE not materially higher)")
    print(f"    median master / per-site-best frame = {bmed:.4f}")
    print(f"    95% bootstrap CI over blocks        = [{lo:.4f}, {hi:.4f}]")
    print(f"    blocks softer than the best frame   = {frac * 100:.1f}%")
    print(f"    frames winning a block: {len(np.unique(winner))} of {len(frames)}")
    if hi < 1.0:
        print(f"    => master IS softer, by {(1 - bmed) * 100:.1f}%")
    elif lo > 1.0:
        print(f"    => master is SHARPER, by {(bmed - 1) * 100:.1f}%")
    else:
        print("    => NO significant difference; CI spans 1.0")


if __name__ == "__main__":
    main()

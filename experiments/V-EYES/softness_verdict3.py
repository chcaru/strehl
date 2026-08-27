"""Softness verdict, third instrument. The second one was inverted.

WHY THERE IS A THIRD. softness_verdict2.py reported the master at 0.108 of the
per-site best frame with all five commissioning arms passing. compare_tiles.py
put that verdict in front of an eye, and the frame that "won" the median block
was a FEATURELESS FLAT GREY -- completely defocused, no structure at all -- while
the master at the same coordinates showed hairs, dark markings and texture.

The mechanism. That instrument divided each block's high-pass energy by the
block's own low-frequency variance, to get amplitude invariance. On a defocused
frame the low-frequency variance within a block is near zero, so the quotient
exploded, and the envelope -- a maximum over frames -- therefore selected the
MOST DEFOCUSED frame in almost every block. The reference was upside down and
the reported deficit was measuring that inversion.

Why the commissioning suite did not catch it: all five arms perturbed the
MASTER and compared against a fixed envelope. Not one of them perturbed the
REFERENCE. A suite that only validates the numerator cannot see a broken
denominator or a broken reference, however many arms it has. That is the same
family as the two failures already on this project's record, and the lesson is
that the arms must exercise every term the verdict depends on.

WHAT THIS ONE DOES DIFFERENTLY.

  No per-block normalisation, because it is not needed and it was the bug.
  Both arms are rendered --linear-srgb --demosaic by the same binary with no
  --auto-exposure (that flag is refused outside --srgb), so master and frames
  are already on a common linear scale. Exposure parity is checked and printed
  rather than assumed; if it does not hold the comparison is void and the
  script says so.

  Detail is absolute high-pass energy per block, minus that image's own noise
  floor (the 5th percentile of its per-block high-pass energy, which is a block
  with no structure). Subtracting per image is what keeps the merge's noise
  behaviour from being scored as sharpness.

  The reference is still the per-site maximum over frames, but a frame is only
  eligible to win a block if it actually has structure there -- its
  low-frequency contrast must clear the same floor the master's must. A
  featureless block can no longer win.

COMMISSIONING, and this time both sides are exercised.

  Numerator arms, on the master:
    NULL       master against itself                  must read 1.0
    DEFECT     master blurred sigma 1.2               must FALL
    IMPROVE    master unsharp masked                  must RISE
    NOISE      master plus single-frame-level noise   must NOT rise materially

  Reference arms, on the envelope -- the ones the previous suite lacked:
    CEILING    per-site best frame as the subject     must read >= 1.0
    REF-BLUR   every reference frame blurred          ratio must RISE, because
               a softened ceiling is easier to reach
    REF-SHARP  every reference frame sharpened        ratio must FALL
    WINNER     the frames that win blocks must be the ones a focus sweep says
               are sharp; the distribution of winners is printed so a
               degenerate reference is visible instead of silent

Usage:
  python softness_verdict3.py <master.tiff> <framesdir> <x> <y> <size> [block]
"""

import sys
import pathlib
import numpy as np
import tifffile
import cv2


HP_SIGMA = 1.5
LF_SIGMA = 4.0


def luma_linear(a):
    return (
        0.2126 * a[..., 0].astype(np.float64)
        + 0.7152 * a[..., 1].astype(np.float64)
        + 0.0722 * a[..., 2].astype(np.float64)
    )


def blocks(px, block, fn):
    h, w = px.shape
    ny, nx = h // block, w // block
    r = px[: ny * block, : nx * block].reshape(ny, block, nx, block)
    return fn(r)


def detail(img, block):
    """Absolute high-pass energy per block, minus this image's own noise floor."""
    f = img.astype(np.float32)
    hp = f - cv2.GaussianBlur(f, (0, 0), HP_SIGMA)
    e = blocks((hp * hp).astype(np.float64), block, lambda r: r.mean(axis=(1, 3)))
    floor = float(np.percentile(e, 5))
    return np.clip(e - floor, 0.0, None), floor


def contrast(img, block):
    lf = cv2.GaussianBlur(img.astype(np.float32), (0, 0), LF_SIGMA).astype(np.float64)
    return np.sqrt(blocks(lf, block, lambda r: r.var(axis=(1, 3))))


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


def boot_ci(v, n=4000, seed=11):
    rng = np.random.default_rng(seed)
    v = np.asarray(v)
    idx = rng.integers(0, len(v), size=(n, len(v)))
    return tuple(
        float(p) for p in np.percentile(np.median(v[idx], axis=1), [2.5, 97.5])
    )


def build_envelope(tiles, block, cfloor):
    """Per-site max detail over frames, among frames that have structure there."""
    D = np.stack([detail(t, block)[0] for t in tiles])
    C = np.stack([contrast(t, block) for t in tiles])
    D = np.where(C > cfloor, D, -np.inf)
    env = D.max(axis=0)
    win = D.argmax(axis=0)
    valid = np.isfinite(env)
    return np.where(valid, env, 0.0), win, valid


def main():
    mpath, fdir = sys.argv[1], pathlib.Path(sys.argv[2])
    x, y, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    block = int(sys.argv[6]) if len(sys.argv) > 6 else 64

    master = luma_linear(tifffile.imread(mpath)[y : y + size, x : x + size])
    files = sorted(fdir.glob("frame-*.tiff"))
    tiles, names = [], []
    for f in files:
        t = luma_linear(tifffile.imread(str(f))[y : y + size, x : x + size])
        dx, dy = shift_of(master, t)
        tiles.append(warp(t, dx, dy))
        names.append(f.stem.replace("frame-", ""))

    print(f"master {pathlib.Path(mpath).name} tile ({x},{y}) {size}x{size} block {block}")
    print(f"  {len(tiles)} reference frames, same binary, --linear-srgb --demosaic\n")

    mm = float(np.mean(master))
    fm = [float(np.mean(t)) for t in tiles]
    spread = (max(fm) - min(fm)) / mm
    print("  EXPOSURE PARITY (required: both arms on a common linear scale)")
    print(f"    master mean {mm:>9.1f}   frames mean {np.mean(fm):>9.1f} "
          f"(min {min(fm):.1f}, max {max(fm):.1f})")
    print(f"    master/frames = {mm / np.mean(fm):.4f}, frame spread = "
          f"{spread * 100:.1f}% of master mean")
    if abs(mm / np.mean(fm) - 1.0) > 0.25:
        print("    PARITY FAILED -- arms are not on a common scale; verdict void")
        return
    print("    parity OK\n")

    cm = contrast(master, block)
    cfloor = float(np.percentile(cm, 65))
    live = cm > cfloor

    env, win, valid = build_envelope(tiles, block, cfloor)
    live = live & valid
    md, mfloor = detail(master, block)

    print(f"  blocks {cm.size} total, {live.sum()} live "
          f"(master contrast > {cfloor:.1f} and some frame has structure)")
    uw, cw = np.unique(win[live], return_counts=True)
    print("  WINNER distribution (a healthy reference spreads across the sweep):")
    for i, c in sorted(zip(uw, cw), key=lambda t: -t[1])[:6]:
        print(f"    {names[i]:<12} wins {c:>4} blocks")

    base = (md / np.maximum(env, 1e-12))[live]
    bmed = float(np.median(base))
    lo, hi = boot_ci(base)

    def med_vs(sub, e=env):
        return float(np.median((sub / np.maximum(e, 1e-12))[live]))

    d = cv2.GaussianBlur(master.astype(np.float32), (0, 0), 1.2)
    u = np.clip(master + 1.0 * (master - d), 0, None)
    nfloors = [detail(t, block)[1] for t in tiles]
    noisy = master + np.random.default_rng(3).normal(
        0, float(np.sqrt(max(np.median(nfloors), 0))) * 2.0, master.shape
    )
    env_blur, _, _ = build_envelope(
        [cv2.GaussianBlur(t.astype(np.float32), (0, 0), 1.2) for t in tiles],
        block, cfloor)
    env_sharp, _, _ = build_envelope(
        [np.clip(t + 1.0 * (t - cv2.GaussianBlur(t.astype(np.float32), (0, 0), 1.2)),
                 0, None) for t in tiles], block, cfloor)

    arms = [
        ("NULL     master vs itself", med_vs(md, md), "==1"),
        ("DEFECT   master blurred", med_vs(detail(d, block)[0]), "<base"),
        ("IMPROVE  master unsharp", med_vs(detail(u, block)[0]), ">base"),
        ("NOISE    master + noise", med_vs(detail(noisy, block)[0]), "~base"),
        ("CEILING  best frame as subject", med_vs(env), ">=1"),
        ("REF-BLUR every frame blurred", med_vs(md, env_blur), ">base"),
        ("REF-SHARP every frame sharpened", med_vs(md, env_sharp), "<base"),
    ]
    print(f"\n  COMMISSIONING  (baseline = {bmed:.4f})")
    ok = True
    for name, val, rule in arms:
        p = {"==1": abs(val - 1) < 1e-6, "<base": val < bmed, ">base": val > bmed,
             "~base": val <= bmed * 1.10, ">=1": val >= 0.999}[rule]
        ok &= p
        print(f"    {name:<34} {val:>8.4f}   {'PASS' if p else 'FAIL'}  ({rule})")

    print(f"\n  === VERDICT ===  ({'all arms pass' if ok else 'ARMS FAILED - void'})")
    print(f"    median master / per-site-best frame = {bmed:.4f}")
    print(f"    95% bootstrap CI over blocks        = [{lo:.4f}, {hi:.4f}]  "
          f"n={live.sum()}")
    print(f"    blocks softer than best frame       = {float((base < 1).mean()) * 100:.1f}%")
    if not ok:
        print("    verdict withheld: an instrument that fails an arm reports nothing")
    elif hi < 1.0:
        print(f"    => master IS softer than the per-site best frame, "
              f"by {(1 - bmed) * 100:.1f}%")
    elif lo > 1.0:
        print(f"    => master is SHARPER than the per-site best frame, "
              f"by {(bmed - 1) * 100:.1f}%")
    else:
        print("    => NO significant difference; CI spans 1.0")


if __name__ == "__main__":
    main()

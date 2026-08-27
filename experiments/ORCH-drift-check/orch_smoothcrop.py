"""Crop the masters where a seam would SHOW, not where the texture is finest.

The gallery picks its 100% crop by maximum high-frequency energy, deliberately, so the
crop lands on the finest detail in the frame. That is the right choice for judging
resolution and the worst possible one for finding blocky election seams: a lattice
discontinuity is buried by texture and stands out in smooth tone. Every 1:1 crop anyone
has looked at tonight was selected to land where this defect is least visible.

So this inverts the selector. For each subject it finds the CROP-sized block with the
*lowest* high-frequency energy that is still real image -- excluding near-black and
near-clipped blocks, which are smooth for the uninteresting reason -- and writes it at
1:1 with a mild linear stretch so that low-amplitude steps are actually visible on a
screen. The stretch is stated on the filename and is linear, so it cannot manufacture an
edge that is not there; it can only make a real one large enough to see.

My spectral seam detector failed to commission at 16 bits, so it certifies nothing.
Tonight an eye at 1:1 beat three of my own statistics on a defect they all reported
absent. This is the instrument that has been working.
"""
import pathlib
import sys

import numpy as np
import tifffile
from PIL import Image

CROP = 900
STEP = 300
FIXED_W = 250.0
# V-POTENCY: an instrument that prints a number nothing conditions on has not
# reported a limit, it has decorated one. These two are the conditions.
CLIP_MAX = 0.05        # above this the fixed window is saturating, not measuring
SMOOTH_MAX = 1.0e14    # min-texture score above this means the master has no smooth field
HP_WIN = 201


def boxblur(a, win):
    """Separable box blur via cumulative sums, edge-replicated. No SciPy dependency."""
    r = win // 2
    pad = np.pad(a, ((r + 1, r), (r + 1, r)), mode="edge")
    c = np.cumsum(pad, axis=0)
    a = (c[win:, :] - c[:-win, :]) / win
    c = np.cumsum(a, axis=1)
    return (c[:, win:] - c[:, :-win]) / win


def hf_energy(blk):
    f = np.fft.fftshift(np.fft.fft2(blk - blk.mean()))
    F = np.abs(f)
    h, w = blk.shape
    fy = (np.arange(h) - h / 2)[:, None] / (h / 2)
    fx = (np.arange(w) - w / 2)[None, :] / (w / 2)
    r = np.sqrt(fy ** 2 + fx ** 2)
    return float((F[(r > 0.20) & (r <= 0.45)] ** 2).sum())


def pick_smooth(lum):
    """Lowest-texture block that is still real image, not black and not clipped.

    V-POTENCY measured that this had NO ABSOLUTE FLOOR: it gated on mean only
    and returned argmin regardless of whether the minimum was smooth. foam's
    "smoothest" block scored 9.117e+16 against coffee-bean's 1.037e+13 -- 8800x
    -- with a 201 px residual RMS of 7366 DN. The tool always emitted a smooth
    crop even for a master that has none, and then asserted comparability on it.

    A search that cannot fail returns its least-bad candidate and calls it a
    find. SMOOTH_MAX is the floor that lets it say no. Returns best=None when
    nothing in the master is actually smooth, and every caller must handle it.
    """
    h, w = lum.shape
    lo_gate, hi_gate = 0.06 * 65535, 0.94 * 65535
    best, by, bx, bmean = None, 0, 0, 0.0
    for y in range(0, max(1, h - CROP), STEP):
        for x in range(0, max(1, w - CROP), STEP):
            blk = lum[y:y + CROP, x:x + CROP]
            if blk.shape != (CROP, CROP):
                continue
            m = float(blk.mean())
            if m < lo_gate or m > hi_gate:
                continue
            e = hf_energy(blk[::3, ::3])
            if best is None or e < best:
                best, by, bx, bmean = e, y, x, m
    if best is not None and best > SMOOTH_MAX:
        return by, bx, None, bmean
    return by, bx, best, bmean


def main(paths, outdir):
    out = pathlib.Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    adaptive = "--adaptive" in sys.argv
    # --window=N exists so CLIP_MAX can be commissioned. A gate never observed to
    # fire is indistinguishable from a gate wired to nothing; this is how it fires.
    global FIXED_W
    for a in sys.argv:
        if a.startswith("--window="):
            FIXED_W = float(a.split("=", 1)[1])
    mode = "ADAPTIVE per-block percentiles" if adaptive else f"FIXED +/-{FIXED_W:.0f} DN"
    print(f"stretch mode: {mode}")
    if adaptive:
        print("  WARNING: per-block gain. Valid WITHIN one master; invalid for ranking "
              "masters against each other, because a flatter -- cleaner -- field is "
              "amplified more and therefore looks dirtiest.")
    print(f"{'subject':30s} {'crop':>16s} {'mean':>8s} {'gain/DN':>9s} {'clipped':>9s}")
    print("-" * 80)
    nok = nclip = nreject = 0
    for p in paths:
        p = pathlib.Path(p)
        a = tifffile.imread(str(p))
        rgb = a[:, :, :3].astype(np.float32)
        lum = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
        y0, x0, e, m = pick_smooth(lum)
        if e is None:
            print(f"{p.stem[:30]:30s} {'NO SMOOTH BLOCK':>16s}  (min texture exceeds "
                  f"SMOOTH_MAX={SMOOTH_MAX:.1e}) -- NOT EXAMINED")
            nreject += 1
            continue
        blk = rgb[y0:y0 + CROP, x0:x0 + CROP]
        if adaptive:
            lo = float(np.percentile(blk, 1.0))
            hi = float(np.percentile(blk, 99.0))
            span = max(hi - lo, 1.0)
            scaled = (blk - lo) * (255.0 / span)
            tag = f"adaptive{65535.0 / span:.0f}x"
        else:
            # Dust is a LOCAL defect; the background gradient is not the thing being
            # judged, and at a fixed gain wide enough not to clip that gradient, the
            # defect is too small to see. Subtracting a heavily blurred copy removes
            # scene-scale tone and leaves anything smaller than HP_WIN intact, so a
            # fixed window on the RESIDUAL is both comparable across masters and
            # actually legible. The high-pass is linear and cannot create an edge.
            res = np.stack([blk[:, :, c] - boxblur(blk[:, :, c], HP_WIN)
                            for c in range(3)], axis=2)
            span = 2 * FIXED_W
            scaled = (res + FIXED_W) * (255.0 / span)
            tag = f"hp{HP_WIN}-fixed{FIXED_W:.0f}DN"
        clipped = float(((scaled < 0) | (scaled > 255)).mean())
        v = np.clip(scaled, 0, 255).astype(np.uint8)
        name = f"{p.stem}--smooth-{x0}x{y0}--{tag}.png"
        Image.fromarray(v).save(out / name)
        flag = ""
        if not adaptive and clipped > CLIP_MAX:
            flag = "  <== CLIPPED, NOT COMPARABLE"
            nclip += 1
        else:
            nok += 1
        print(f"{p.stem[:30]:30s} {f'({x0},{y0})':>16s} {m/65535:8.3f} "
              f"{255.0/span:9.4f} {clipped*100:8.2f}%{flag}")
        del a, rgb, lum, blk, scaled, v
    print(f"\nwrote to {out}")
    print("A blocky seam appears here as straight steps on a regular pitch; dust as "
          "discs, or as dashes where the stack moved under the warp.")
    print(f"\npartition: {nok} comparable, {nclip} clipped over {CLIP_MAX*100:.0f}%, "
          f"{nreject} with no smooth block, {nok+nclip+nreject} total")
    print("A rejected or clipped master was NOT measured and is not a clean reading.")
    if not adaptive:
        if nclip:
            print(f"\n*** {nclip} master(s) exceed {CLIP_MAX*100:.0f}% clipping at "
                  f"+/-{FIXED_W:.0f} DN. Cross-master severity is INVALID for those. ***")
            print("Re-run those with a wider window; the bias collapses to 1.00x as")
            print("clipping goes to zero, which is measured in the commissioning table.")
        else:
            print(f"High-passed at {HP_WIN}px, then a FIXED +/-{FIXED_W:.0f} DN window: "
                  f"gain is {255.0 / (2 * FIXED_W):.4f} levels per DN for every master. "
                  f"Every master above is under {CLIP_MAX*100:.0f}% clipped, so apparent "
                  f"severity IS comparable across them. A 40 DN defect reads as "
                  f"{40 * 255.0 / (2 * FIXED_W):.1f} of 255, and 128 is the zero level.")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sys.exit(main(args[:-1], args[-1]))

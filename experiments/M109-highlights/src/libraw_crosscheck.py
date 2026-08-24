"""B5: cross-check strehl's blown-highlight rendering against LibRaw's.

Independence is the point: `rawpy` wraps LibRaw, a completely separate decoder
and colour pipeline that this project has never read the source of. If strehl
now renders a container-pinned neutral as neutral and LibRaw renders the same
sensels as neutral too, the fix agrees with an implementation it did not copy.

The region is found by the PREDICATE, not by hand (discipline 713): the pixels
where BOTH green sensels of a quad sit at `CONTAINER_MAX_DN` are, by definition,
the ones where green cannot rise and white balance carries red and blue past it.
No ROI is typed in anywhere.

Rule 32: `raw_image_visible` is a view into a buffer LibRaw frees when the
context manager exits. Everything is copied inside the `with`.
"""

import numpy as np
import rawpy

FRAME = r"D:\personal\macro\dry-erase-marker-head-cpl\DSC00150.ARW"
CONTAINER_MAX_DN = 16383  # crates/strehl-core/src/clip.rs


def main() -> None:
    with rawpy.imread(FRAME) as raw:
        cfa = raw.raw_image_visible.astype(np.int32)  # copy inside the `with`
        black = float(np.mean(raw.black_level_per_channel))
        white = int(raw.white_level)
        cam_wb = list(raw.camera_whitebalance)
        # LibRaw's own render, its own highlight logic, its own everything.
        rgb = raw.postprocess(
            use_camera_wb=True,
            output_bps=16,
            no_auto_bright=True,
            gamma=(2.4, 12.92),  # sRGB-ish, matching strehl's transfer curve
        ).astype(np.float32) / 65535.0

    print(f"frame              : {FRAME}")
    print(f"LibRaw black/white : {black} / {white}")
    print(f"camera_whitebalance: {cam_wb}")
    print(f"CFA {cfa.shape}, LibRaw render {rgb.shape}")

    # RGGB quads: R G1 / G2 B.
    h, w = cfa.shape[0] // 2 * 2, cfa.shape[1] // 2 * 2
    q = cfa[:h, :w]
    r_ = q[0::2, 0::2]
    g1 = q[0::2, 1::2]
    g2 = q[1::2, 0::2]
    b_ = q[1::2, 1::2]

    pinned = (g1 >= CONTAINER_MAX_DN) & (g2 >= CONTAINER_MAX_DN)
    n = int(pinned.sum())
    print()
    print(f"quads with BOTH greens pinned at {CONTAINER_MAX_DN}: {n} "
          f"({100.0 * n / pinned.size:.4f} % of {pinned.size})")
    if n == 0:
        raise SystemExit("no pinned quads -- the predicate found nothing to compare")

    print("  raw DN means over those quads:")
    for name, plane in (("R", r_), ("G1", g1), ("B", b_), ("G2", g2)):
        v = plane[pinned]
        sat = 100.0 * float((v >= CONTAINER_MAX_DN).mean())
        print(f"    {name:2s} mean {float(v.mean()):9.1f}   at saturation {sat:6.2f} %")

    # LibRaw's render is full-resolution; a pinned quad covers a 2x2 block.
    # Take the block's mean so the comparison is on the same footing as
    # strehl's demosaiced output.
    rh, rw = rgb.shape[0] // 2 * 2, rgb.shape[1] // 2 * 2
    blocks = rgb[:rh, :rw].reshape(rh // 2, 2, rw // 2, 2, 3).mean(axis=(1, 3))
    ph = min(blocks.shape[0], pinned.shape[0])
    pw = min(blocks.shape[1], pinned.shape[1])
    m = pinned[:ph, :pw]
    sel = blocks[:ph, :pw][m]
    r, g, b = sel[:, 0], sel[:, 1], sel[:, 2]
    print()
    print(f"  LibRaw renders those same quads (n={len(sel)}):")
    print(f"    mean R={r.mean():.4f} G={g.mean():.4f} B={b.mean():.4f}")
    print(f"    mean (R-G) = {float((r - g).mean()):+.4f}   mean (B-G) = {float((b - g).mean()):+.4f}")
    print(f"    max  (R-G) = {float((r - g).max()):+.4f}")
    magenta = ((r - g) > 0.06) & ((b - g) > 0.06)
    print(f"    magenta by strehl's own predicate: {100.0 * float(magenta.mean()):.4f} %")


if __name__ == "__main__":
    main()

"""R8 -- cross-binary null, edge-chroma metric, and crops for the by-eye read.

Bars registered here before the run:

  X1  The CA-OFF render of the WIRED binary must be byte-identical to
      C:\\dev\\strehl-out\\ORCH-kernel\\bee-3-cpl-catmull-rom.tif, which was
      produced by a DIFFERENT, PRE-WIRING binary. If this holds it is a much
      stronger default-path guarantee than an A/A within one binary: it shows
      the wiring changed no bytes across a rebuild and a different commit.
      If the file is missing, X1 is SKIPPED, not passed.

  X2  Edge-chroma, in the orchestrator's registered shape:
      mean(max(|R-Y|,|B-Y|)) over the top-1% gradient pixels, divided by the
      same over the bottom-50% (flat) pixels. Reported for both arms. The
      orchestrator's caution applies: a fix that suppresses chroma globally is
      a regression dressed as a win, so I also report the FLAT-pixel chroma
      separately. If flat chroma drops materially, the correction is
      desaturating rather than de-fringing.
      NO BAR IS SET ON THE DIRECTION of X2, because eps_b is None and a
      red-only correction on a red/cyan fringe has no predicted sign. This is
      a measurement, not a test.

  X3  Crops written for the by-eye read. Chosen automatically at the highest
      edge-chroma density so the choice is not mine, then written 1:1 with no
      resampling and no post-processing.
"""
import os, sys
import numpy as np
import tifffile

R7 = r"C:\dev\strehl-out\M107-chroma\r7"
OFF = os.path.join(R7, "off1.tif")
ON = os.path.join(R7, "on.tif")
PREWIRE = r"C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom.tif"
OUTDIR = R7


def sha256(path):
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def chroma_stats(img):
    a = img.astype(np.float64) / 65535.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    c = np.maximum(np.abs(r - y), np.abs(b - y))
    gy, gx = np.gradient(y)
    gm = np.hypot(gx, gy)
    hi = gm >= np.quantile(gm, 0.99)
    lo = gm <= np.quantile(gm, 0.50)
    return float(c[hi].mean()), float(c[lo].mean()), c, gm


def main():
    print("=" * 66)
    print("R8 -- cross-binary null, chroma metric, crops")
    print("=" * 66)

    print("\nX1  cross-binary byte-identical null")
    h_off = sha256(OFF)
    print(f"    wired binary, CA off : {h_off}")
    if os.path.exists(PREWIRE):
        h_pre = sha256(PREWIRE)
        print(f"    pre-wiring binary    : {h_pre}")
        x1 = h_off == h_pre
        print(f"    X1 {'PASS -- the wiring changed no bytes on the default path' if x1 else 'FAIL -- DIFFERS'}")
    else:
        print(f"    pre-wiring render not found at {PREWIRE}")
        print("    X1 SKIPPED (not passed)")

    off = tifffile.imread(OFF)
    on = tifffile.imread(ON)
    print(f"\n    shapes off={off.shape} on={on.shape} dtype={off.dtype}")

    print("\nX2  edge-chroma (orchestrator's D2 shape)")
    e_off, f_off, c_off, gm = chroma_stats(off)
    e_on, f_on, c_on, _ = chroma_stats(on)
    print(f"    arm    edge-chroma   flat-chroma   ratio")
    print(f"    off    {e_off:.6f}     {f_off:.6f}      {e_off/f_off:.3f}")
    print(f"    on     {e_on:.6f}     {f_on:.6f}      {e_on/f_on:.3f}")
    print(f"    edge chroma change: {100*(e_on-e_off)/e_off:+.2f}%")
    print(f"    flat chroma change: {100*(f_on-f_off)/f_off:+.2f}%   "
          f"(large negative here = global desaturation, a regression)")

    print("\nX3  crops")
    # Pick the window with the highest edge-chroma density, so the choice is
    # made by the data rather than by me.
    hi = gm >= np.quantile(gm, 0.99)
    dens = (c_off * hi)
    W = 320
    h, w = dens.shape
    best, bxy = -1.0, (0, 0)
    for yy in range(0, h - W, W // 2):
        for xx in range(0, w - W, W // 2):
            s = dens[yy:yy + W, xx:xx + W].sum()
            if s > best:
                best, bxy = s, (yy, xx)
    yy, xx = bxy
    r_norm = np.hypot(xx + W / 2 - w / 2, yy + W / 2 - h / 2) / (np.hypot(w, h) / 2)
    print(f"    auto-selected window at (x={xx}, y={yy}) size {W}, "
          f"field height r={r_norm:.3f}")

    def crop8(a):
        c = a[yy:yy + W, xx:xx + W, :3].astype(np.float64) / 65535.0
        return (np.clip(c, 0, 1) * 255).astype(np.uint8)

    pair = np.concatenate([crop8(off), np.zeros((W, 8, 3), np.uint8), crop8(on)], axis=1)
    p = os.path.join(OUTDIR, "crop_off_vs_on.png")
    tifffile.imwrite(p, pair)
    print(f"    wrote {p}   (LEFT = CA off, RIGHT = CA on, 1:1, no post)")

    # Also a corner window, past the measured support radius r=0.788.
    cy, cx = h - W - 8, w - W - 8
    r_corner = np.hypot(cx + W / 2 - w / 2, cy + W / 2 - h / 2) / (np.hypot(w, h) / 2)

    def crop8_at(a, y0, x0):
        c = a[y0:y0 + W, x0:x0 + W, :3].astype(np.float64) / 65535.0
        return (np.clip(c, 0, 1) * 255).astype(np.uint8)

    cpair = np.concatenate(
        [crop8_at(off, cy, cx), np.zeros((W, 8, 3), np.uint8), crop8_at(on, cy, cx)], axis=1)
    pc = os.path.join(OUTDIR, "crop_corner.png")
    tifffile.imwrite(pc, cpair)
    print(f"    wrote {pc}  corner window r={r_corner:.3f} "
          f"(PAST the measured support radius 0.788)")

    # Per-channel displacement actually applied, as a sanity readout.
    d = np.abs(on.astype(np.int32) - off.astype(np.int32))
    print("\n    per-channel max |on-off| (DN):",
          [int(d[..., i].max()) for i in range(3)])
    print("    per-channel mean |on-off| (DN):",
          [round(float(d[..., i].mean()), 4) for i in range(3)])


if __name__ == "__main__":
    main()

"""Is the merge output carrying full sensor resolution, or half of it?

M95 reports the default output is "binned -- 8.2 MP from a 32.9 MP capture".
My own binned_check.py could not settle it: its controls landed but the render
read 6.1x above the upper anchor, breaking the readout (it exits 2 and reports
nothing). The flaw was the negative control -- white noise is not a fair stand-in
for "a full-resolution photograph of this subject". This script uses the right
one: THE ACTUAL RAW FILE, decoded independently of strehl by LibRaw.

THE COMPARISON, and why gate 0 makes it fair.
At `--gate 0` the merge reports mean n_eff = 1.000 with 100.00% of pixels at
n_eff = 1 (fact 1283): every output pixel comes from exactly ONE frame, with no
averaging. So the merge output has the same noise level as a single frame, and
noise -- which is broadband and would otherwise dominate any high-frequency
comparison between an average and a single exposure -- cancels out of the
comparison instead of driving it.

THREE SPECTRA, so the merge is read against two anchors rather than against an
assumption:
  FULL    a single ARW decoded at full resolution by rawpy
  BINNED  that same decode passed through an exact 2x2 bin-and-replicate
  MERGE   strehl's gate-0 render

If MERGE tracks BINNED, M95 is right and the pipeline is discarding half the
linear resolution. If MERGE tracks FULL, it is not, and tonight's leading
explanation for the softness is wrong.

CONFOUNDS, HANDLED
 - Geometry. The render is coverage-cropped to 0.9315 of the field of view and
   scaled back to full dimensions, so a scene point at offset d from the centre
   in the RAW sits at d/0.9315 in the render. Tiles are mapped through that.
   Frame 149 is the merge's own reference frame, so its warp is identity and no
   other correction is needed.
 - Focus. A single frame is sharp only where it is in focus, while the merge is
   sharp everywhere; comparing arbitrary tiles would flatter the merge. Tiles
   are therefore chosen as the SHARPEST tiles of the single frame, which is the
   only region where the comparison is meaningful.
 - Exposure. The render is exposure-scaled ~3x. Every spectrum is normalised by
   its own power in a low band where all three necessarily agree.
 - Demosaic. rawpy's algorithm is not strehl's, which perturbs the top octave.
   That is why the test asks which of two anchors the merge tracks, rather than
   asking for an absolute MTF.
"""
import sys

import numpy as np
import rawpy
import tifffile

TILE = 256
FOV = 0.9315
REF_FRAME = 149
NORM_LO, NORM_HI = 0.04, 0.10     # band where all three must agree
HF_LO, HF_HI = 0.30, 0.48         # band that distinguishes full from binned


def spectrum(tiles):
    f = np.fft.fftfreq(TILE)
    fr = np.sqrt((f[:, None] ** 2) + (f[None, :] ** 2))
    win = np.outer(np.hanning(TILE), np.hanning(TILE))
    acc = np.zeros((TILE, TILE))
    for t in tiles:
        t = t.astype(np.float64)
        acc += np.abs(np.fft.fft2((t - t.mean()) * win)) ** 2
    acc /= max(len(tiles), 1)
    edges = np.linspace(0.02, 0.5, 49)
    mids, vals = [], []
    for i in range(len(edges) - 1):
        m = (fr >= edges[i]) & (fr < edges[i + 1])
        if m.sum() > 4:
            mids.append((edges[i] + edges[i + 1]) / 2)
            vals.append(acc[m].mean())
    mids, vals = np.array(mids), np.array(vals)
    norm = vals[(mids >= NORM_LO) & (mids <= NORM_HI)].mean()
    return mids, vals / norm


def bin2x(y):
    """Bin 2x2, then upsample SMOOTHLY -- what a binned pipeline actually emits.

    An earlier version replicated each binned value over its 2x2 block (np.kron).
    That is idempotent, which made it a good anchor for a ratio test, but it is a
    terrible anchor for a SPECTRAL test: the block edges inject high-frequency
    energy, so the "binned" reference ended up with 9x MORE power at 0.445 cyc/px
    than the full-resolution frame it was built from, and the two anchors crossed
    over instead of bracketing. A pipeline that bins and then scales back up does
    not emit blocks, so the anchor must not either.
    """
    from scipy.ndimage import zoom
    h, w = y.shape
    h2, w2 = h - (h % 2), w - (w % 2)
    b = y[:h2, :w2].reshape(h2 // 2, 2, w2 // 2, 2).mean(axis=(1, 3))
    out = zoom(b.astype(np.float32), (h / b.shape[0], w / b.shape[1]), order=3)
    return out[:h, :w]


def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)


def sharp_tiles(y, n=40, box=2048):
    """The n sharpest tiles inside a central box -- where the single frame is in focus."""
    h, w = y.shape
    cy, cx = h // 2, w // 2
    cand = []
    for ty in range(cy - box, cy + box - TILE, TILE):
        for tx in range(cx - box, cx + box - TILE, TILE):
            if not (0 <= ty < h - TILE and 0 <= tx < w - TILE):
                continue
            t = y[ty:ty + TILE, tx:tx + TILE]
            gy = np.diff(t, axis=0)
            gx = np.diff(t, axis=1)
            s = float(gy.var() + gx.var())
            cand.append((s, ty, tx))
    cand.sort(reverse=True)
    return [(ty, tx) for _, ty, tx in cand[:n]]


def main(raw_dir, render_path):
    import glob
    import os
    files = sorted(glob.glob(os.path.join(raw_dir, "*.ARW")))
    if not files:
        sys.exit(f"no ARW in {raw_dir}")
    src = files[min(REF_FRAME, len(files) - 1)]
    print(f"single frame : {os.path.basename(src)}  ({REF_FRAME} of {len(files)})")
    print(f"render       : {os.path.basename(render_path)}\n")

    with rawpy.imread(src) as r:
        rgb = r.postprocess(output_bps=16, no_auto_bright=True,
                            use_camera_wb=True, gamma=(1, 1))
    y_full = luma(rgb)
    del rgb
    y_binned = bin2x(y_full)

    a = tifffile.imread(render_path)
    y_merge = luma(a)
    del a
    print(f"raw decode {y_full.shape}, render {y_merge.shape}")
    if y_full.shape != y_merge.shape:
        print("NOTE: dimensions differ; tiles are mapped through the coverage scale anyway.")

    keys = sharp_tiles(y_full)
    print(f"selected {len(keys)} sharpest tiles of the single frame\n")

    t_full = [y_full[ty:ty + TILE, tx:tx + TILE] for ty, tx in keys]
    t_bin = [y_binned[ty:ty + TILE, tx:tx + TILE] for ty, tx in keys]

    # Map each tile through the coverage scale into render coordinates.
    fh, fw = y_full.shape
    mh, mw = y_merge.shape
    fcy, fcx = (fh - 1) / 2.0, (fw - 1) / 2.0
    mcy, mcx = (mh - 1) / 2.0, (mw - 1) / 2.0
    t_merge = []
    for ty, tx in keys:
        my = int(round(mcy + (ty + TILE / 2 - fcy) / FOV - TILE / 2))
        mx = int(round(mcx + (tx + TILE / 2 - fcx) / FOV - TILE / 2))
        if 0 <= my < mh - TILE and 0 <= mx < mw - TILE:
            t_merge.append(y_merge[my:my + TILE, mx:mx + TILE])
    print(f"{len(t_merge)} of them land inside the render\n")

    m, s_full = spectrum(t_full)
    _, s_bin = spectrum(t_bin)
    _, s_merge = spectrum(t_merge)

    print(f"{'freq':>7} {'FULL':>10} {'BINNED':>10} {'MERGE':>10}   which anchor")
    for i, f in enumerate(m):
        if f < 0.20:
            continue
        d_full = abs(np.log10(s_merge[i]) - np.log10(s_full[i]))
        d_bin = abs(np.log10(s_merge[i]) - np.log10(s_bin[i]))
        who = "FULL" if d_full < d_bin else "binned"
        print(f"{f:>7.3f} {s_full[i]:>10.4f} {s_bin[i]:>10.4f} "
              f"{s_merge[i]:>10.4f}   {who}")

    hf = (m >= HF_LO) & (m <= HF_HI)
    lf, lb, lm = (np.log10(s[hf]).mean() for s in (s_full, s_bin, s_merge))
    print()
    print(f"mean log10 power in {HF_LO}-{HF_HI} cyc/px:")
    print(f"  FULL   {lf:+.4f}")
    print(f"  BINNED {lb:+.4f}")
    print(f"  MERGE  {lm:+.4f}")
    sep = lf - lb
    if sep < 0.20:
        print("\nANCHORS NOT SEPARATED: full and binned differ by less than 0.2 dex")
        print("in this band, so the test has no resolving power. Report nothing.")
        return 1
    pos = (lm - lb) / sep
    print(f"\nanchor separation {sep:.4f} dex -- the test can resolve them.")
    print(f"On the scale 0 = BINNED, 1 = FULL, the merge sits at {pos:.3f}.")
    print()
    if pos < 0.35:
        print("VERDICT: the merge tracks the BINNED anchor. M95 is right --")
        print("roughly half the linear resolution is being discarded.")
    elif pos > 0.75:
        print("VERDICT: the merge tracks the FULL anchor. It is NOT binned, and")
        print("tonight's leading explanation for the softness is wrong.")
    else:
        print("VERDICT: intermediate. The merge holds some but not all detail")
        print("above the binned Nyquist; neither label is honest on its own.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

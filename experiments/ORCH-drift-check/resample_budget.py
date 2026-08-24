"""Does resampling account for the merge's 2.34x high-frequency deficit?

Fact 1286 measured the gate-0 render 0.3693 dex below a single in-focus frame
over 0.30-0.48 cyc/px, and recorded the cause as ARGUED: resampling. This script
tries to falsify that by pricing the resampling directly. If the interpolation
kernel can be shown to cost the measured amount, the cause is settled and the fix
is an output-path change. If it costs far less, something else is eating the
detail and I have been chasing the wrong thing twice in one night.

THE MODEL UNDER TEST
The pipeline reports the field of view scaled to 0.9315 "then upsampled to keep
the output dimensions", and at gate 0 the frame that wins a given pixel is
usually not the reference frame, so its samples arrive through a warp gather at
an arbitrary sub-pixel offset. Both are Catmull-Rom. Whether they are one fused
gather or two in series I do not know -- `merge_cmd.rs` is contended and I am not
reading 152 KB to find out -- so the script measures BOTH and reports which
bracket the merge falls in.

PRE-REGISTERED, BEFORE RUNNING (per rule 12, these are predictions, not results):

  P1  NULL. A resample at scale 1.0 with zero offset must cost < 0.01 dex.
      It is the same code path doing nothing, so anything larger means the
      harness itself is blurring and every number below is void.

  P2  DOSE. Cost must rise monotonically with sub-pixel offset over
      0.0 -> 0.125 -> 0.25 -> 0.5 px. Catmull-Rom is exact at integer offsets
      and worst at the half-pixel, so a non-monotone ladder means the kernel
      is not implemented correctly.

  P3  THE TEST. If one fused gather explains the deficit, R1s lands within
      0.08 dex of the measured MERGE value. If two gathers are needed, R2 does
      and R1s falls short. If BOTH fall well short of 0.3693 dex, the
      resampling hypothesis is refuted and the cause is still open.

I am registering in advance that I expect R1s to fall SHORT. A single Catmull-Rom
resample is a mild filter and 2.34x of power is a lot to lose to one gather. The
outcome I consider most likely is a partial account, which would mean resampling
is a contributor rather than the explanation.

The demosaic confound of fact 1286 is untouched here and still bounds everything:
rawpy's demosaic is not strehl's, so some unknown part of the 0.3693 dex belongs
to that difference rather than to any resampling.
"""
import os
import sys

import numpy as np
import rawpy
import tifffile

TILE = 256
PAD = 384          # source region extracted per tile, before resampling
FOV = 0.9315
REF_FRAME = 149
NORM_LO, NORM_HI = 0.04, 0.10
HF_LO, HF_HI = 0.30, 0.48


def catmull_rom_weights(t):
    """Catmull-Rom (cubic convolution, a = -0.5) taps for fractional offset t."""
    t2, t3 = t * t, t * t * t
    return np.stack([
        -0.5 * t3 + t2 - 0.5 * t,
        1.5 * t3 - 2.5 * t2 + 1.0,
        -1.5 * t3 + 2.0 * t2 + 0.5 * t,
        0.5 * t3 - 0.5 * t2,
    ])


def resample_1d(a, coords, axis):
    """Separable Catmull-Rom gather along one axis at float coords."""
    a = np.moveaxis(a, axis, 0)
    i0 = np.floor(coords).astype(np.int64)
    t = (coords - i0).astype(np.float64)
    w = catmull_rom_weights(t)
    n = a.shape[0]
    out = np.zeros((len(coords),) + a.shape[1:], dtype=np.float64)
    for k in range(4):
        idx = np.clip(i0 - 1 + k, 0, n - 1)
        out += w[k][:, None] * a[idx]
    return np.moveaxis(out, 0, axis)


def resample(tile_src, scale, shift_y, shift_x, n_out=TILE):
    """One Catmull-Rom gather: upsample by `scale` and offset sub-pixel.

    `scale` > 1 magnifies. Output is n_out square, centred on the source centre,
    so every arm below is looking at the same piece of scene.
    """
    h, w = tile_src.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    co = (n_out - 1) / 2.0
    i = np.arange(n_out, dtype=np.float64) - co
    vy = cy + i / scale + shift_y
    vx = cx + i / scale + shift_x
    out = resample_1d(tile_src.astype(np.float64), vy, 0)
    out = resample_1d(out, vx, 1)
    return out


def spectrum(tiles):
    f = np.fft.fftfreq(TILE)
    fr = np.sqrt((f[:, None] ** 2) + (f[None, :] ** 2))
    win = np.outer(np.hanning(TILE), np.hanning(TILE))
    acc = np.zeros((TILE, TILE))
    for t in tiles:
        t = np.asarray(t, dtype=np.float64)
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


def hf_level(tiles):
    m, s = spectrum(tiles)
    return float(np.log10(s[(m >= HF_LO) & (m <= HF_HI)]).mean())


def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)


def sharp_tiles(y, n=40, box=2048):
    h, w = y.shape
    cy, cx = h // 2, w // 2
    cand = []
    for ty in range(cy - box, cy + box - TILE, TILE):
        for tx in range(cx - box, cx + box - TILE, TILE):
            if not (PAD // 2 <= ty < h - PAD and PAD // 2 <= tx < w - PAD):
                continue
            t = y[ty:ty + TILE, tx:tx + TILE]
            s = float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var())
            cand.append((s, ty, tx))
    cand.sort(reverse=True)
    return [(ty, tx) for _, ty, tx in cand[:n]]


def main(raw_dir, render_path):
    import glob
    files = sorted(glob.glob(os.path.join(raw_dir, "*.ARW")))
    if not files:
        sys.exit(f"no ARW in {raw_dir}")
    src = files[min(REF_FRAME, len(files) - 1)]
    print(f"single frame : {os.path.basename(src)}")
    print(f"render       : {os.path.basename(render_path)}\n")

    with rawpy.imread(src) as r:
        rgb = r.postprocess(output_bps=16, no_auto_bright=True,
                            use_camera_wb=True, gamma=(1, 1))
    y_full = luma(rgb)
    del rgb

    keys = sharp_tiles(y_full)
    print(f"selected {len(keys)} sharpest tiles of the single frame")

    # Padded source regions, centred on each tile, resampled once per arm.
    src_regions = []
    for ty, tx in keys:
        cy, cx = ty + TILE // 2, tx + TILE // 2
        src_regions.append(y_full[cy - PAD // 2:cy + PAD // 2,
                                  cx - PAD // 2:cx + PAD // 2])

    def arm(scale, sy, sx):
        return [resample(r, scale, sy, sx) for r in src_regions]

    # The FULL baseline is the same centred crop with no resampling at all.
    base = [r[PAD // 2 - TILE // 2:PAD // 2 + TILE // 2,
              PAD // 2 - TILE // 2:PAD // 2 + TILE // 2] for r in src_regions]
    L_full = hf_level(base)

    print("\n--- CONTROLS ---")
    L_null = hf_level(arm(1.0, 0.0, 0.0))
    d_null = L_full - L_null
    ok_null = abs(d_null) < 0.01
    print(f"P1 NULL    scale 1.0, offset 0      cost {d_null:+.4f} dex   "
          f"{'PASS' if ok_null else 'FAIL'}")

    ladder = []
    for off in (0.0, 0.125, 0.25, 0.5):
        ladder.append(L_full - hf_level(arm(1.0, off, off)))
    ok_dose = all(ladder[i] < ladder[i + 1] + 1e-9 for i in range(len(ladder) - 1))
    print("P2 DOSE    offset 0/0.125/0.25/0.5   cost " +
          " / ".join(f"{d:+.4f}" for d in ladder) +
          f"   {'PASS' if ok_dose else 'FAIL'}")

    if not (ok_null and ok_dose):
        print("\nCONTROLS FAILED. The harness cannot be trusted; reporting nothing.")
        return 1

    print("\n--- ARMS ---")
    L_r1 = hf_level(arm(1 / FOV, 0.0, 0.0))
    L_r1s = hf_level(arm(1 / FOV, 0.5, 0.5))
    two = [resample(r, 1 / FOV, 0.0, 0.0, n_out=PAD) for r in src_regions]
    L_r2 = hf_level([resample(t, 1.0, 0.5, 0.5) for t in two])

    a = tifffile.imread(render_path)
    y_merge = luma(a)
    del a
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
    L_merge = hf_level(t_merge)

    print(f"{'arm':<44} {'level':>9} {'cost vs FULL':>14}")
    rows = [
        ("FULL  single frame, no resample", L_full),
        ("R1    one gather, scale only", L_r1),
        ("R1s   one gather, scale + 0.5 px offset", L_r1s),
        ("R2    two gathers, scale then 0.5 px offset", L_r2),
        ("MERGE strehl gate-0 render", L_merge),
    ]
    for name, lv in rows:
        print(f"{name:<44} {lv:>+9.4f} {L_full - lv:>+14.4f}")

    target = L_full - L_merge
    print(f"\nthe deficit to explain: {target:+.4f} dex")
    for name, lv in (("R1s (one fused gather)", L_r1s), ("R2 (two gathers)", L_r2)):
        c = L_full - lv
        print(f"  {name:<26} accounts for {c:+.4f} dex "
              f"= {100 * c / target:5.1f}% of it")

    print()
    best = max(L_full - L_r1s, L_full - L_r2)
    if abs(best - target) < 0.08:
        print("VERDICT: resampling accounts for the deficit. The softness is an")
        print("output-path problem and the fix is to resample less, or better.")
    elif best < 0.5 * target:
        print("VERDICT: resampling is NOT the explanation -- it accounts for less")
        print("than half. P3 is refuted and the cause of the softness is OPEN.")
    else:
        print("VERDICT: resampling is a contributor but not the whole story.")
        print("Something else carries the remainder; the cause stays PARTIAL.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

"""Is the merge's unexplained residual just a demosaic difference?

Fact 1287 left +0.1301 dex of the softness unaccounted for after the coverage
rescale explains 64.2% of it. Fact 1286 named the leading suspect and flagged it
as a confound I could not control: the FULL anchor is decoded by rawpy, whose
demosaic is not strehl's, and demosaic algorithms differ most in exactly the
0.30-0.48 cyc/px band the whole measurement lives in.

I cannot compare against strehl's demosaic from outside the codebase. But I can
bound the effect: if simply CHANGING DEMOSAIC ALGORITHM, with everything else
held identical, moves the high-frequency level by something like 0.1301 dex,
then the residual is comfortably within what demosaic choice alone can produce,
and the softness account is closed. If every algorithm lands within a few
hundredths of a dex of every other, demosaic cannot be the explanation and
something else is eating the detail.

This is a bounding argument, not an identification. A PASS here does not prove
the residual IS demosaic; it proves demosaic is a sufficient explanation and
that no further mechanism needs to be invented to account for the number. That
distinction goes in the fact, not just in this docstring.

PRE-REGISTERED, BEFORE RUNNING:

  P1  CONTROL. Decoding the same file twice with the same algorithm must give
      identical levels to within 0.001 dex. Anything larger and the harness has
      a nondeterminism I do not understand, and no spread below is meaningful.

  P2  ORDERING. LINEAR (plain bilinear) is the crudest algorithm offered and
      must read LOWEST of the set. If it does not, the metric is not measuring
      demosaic quality and the run is void.

  P3  THE TEST. If (max - min) across algorithms >= 0.1301 dex, demosaic choice
      alone spans the residual and the account is closed. If it is < 0.05 dex,
      demosaic is refuted as the explanation and the residual is a real open
      question. Between those, partial.

I register in advance that I expect this to PASS, because the residual is small
and demosaic differences in the top octave are not. If it fails, the far more
interesting possibility is that the focus election is picking a sub-optimal
frame at a meaningful fraction of pixels -- which would be a genuine algorithmic
defect rather than a rendering-path one, and a much bigger prize.
"""
import os
import sys

import numpy as np
import rawpy

TILE = 256
NORM_LO, NORM_HI = 0.04, 0.10
HF_LO, HF_HI = 0.30, 0.48
REF_FRAME = 149
RESIDUAL = 0.1301          # dex left unexplained by fact 1287

ALGOS = [
    ("LINEAR", rawpy.DemosaicAlgorithm.LINEAR),
    ("VNG", rawpy.DemosaicAlgorithm.VNG),
    ("PPG", rawpy.DemosaicAlgorithm.PPG),
    ("AHD", rawpy.DemosaicAlgorithm.AHD),
    ("DHT", rawpy.DemosaicAlgorithm.DHT),
    ("AAHD", rawpy.DemosaicAlgorithm.AAHD),
]


def luma(a):
    return (0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]).astype(np.float32)


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


def hf_level(y, keys):
    tiles = [y[ty:ty + TILE, tx:tx + TILE] for ty, tx in keys]
    m, s = spectrum(tiles)
    return float(np.log10(s[(m >= HF_LO) & (m <= HF_HI)]).mean())


def sharp_tiles(y, n=40, box=2048):
    h, w = y.shape
    cy, cx = h // 2, w // 2
    cand = []
    for ty in range(cy - box, cy + box - TILE, TILE):
        for tx in range(cx - box, cx + box - TILE, TILE):
            if not (0 <= ty < h - TILE and 0 <= tx < w - TILE):
                continue
            t = y[ty:ty + TILE, tx:tx + TILE]
            s = float(np.diff(t, axis=0).var() + np.diff(t, axis=1).var())
            cand.append((s, ty, tx))
    cand.sort(reverse=True)
    return [(ty, tx) for _, ty, tx in cand[:n]]


def decode(src, algo):
    with rawpy.imread(src) as r:
        rgb = r.postprocess(output_bps=16, no_auto_bright=True, use_camera_wb=True,
                            gamma=(1, 1), demosaic_algorithm=algo)
    return luma(rgb)


def main(raw_dir):
    import glob
    files = sorted(glob.glob(os.path.join(raw_dir, "*.ARW")))
    if not files:
        sys.exit(f"no ARW in {raw_dir}")
    src = files[min(REF_FRAME, len(files) - 1)]
    print(f"single frame : {os.path.basename(src)}")
    print(f"band         : {HF_LO}-{HF_HI} cyc/px")
    print(f"residual to span : {RESIDUAL:+.4f} dex\n")

    base = decode(src, rawpy.DemosaicAlgorithm.AHD)
    keys = sharp_tiles(base)
    print(f"tile set fixed on the AHD decode: {len(keys)} tiles\n")

    print("--- CONTROL ---")
    l1 = hf_level(base, keys)
    l2 = hf_level(decode(src, rawpy.DemosaicAlgorithm.AHD), keys)
    ok_det = abs(l1 - l2) < 0.001
    print(f"P1 determinism  AHD twice   {l1:+.4f} vs {l2:+.4f}   "
          f"delta {abs(l1 - l2):.6f}   {'PASS' if ok_det else 'FAIL'}\n")
    if not ok_det:
        print("CONTROL FAILED. Decode is not deterministic; reporting nothing.")
        return 1

    print("--- ALGORITHMS ---")
    levels = {}
    for name, algo in ALGOS:
        try:
            levels[name] = hf_level(decode(src, algo), keys)
        except Exception as e:
            print(f"{name:<8} unavailable ({type(e).__name__})")
            continue
        print(f"{name:<8} {levels[name]:>+9.4f}")

    if len(levels) < 3:
        print("\nToo few algorithms decoded; reporting nothing.")
        return 1

    lo_name = min(levels, key=levels.get)
    ok_order = lo_name == "LINEAR"
    print(f"\nP2 ordering   lowest is {lo_name}   "
          f"{'PASS' if ok_order else 'FAIL -- metric is not tracking demosaic quality'}")
    if not ok_order:
        print("\nORDERING CONTROL FAILED. Reporting nothing.")
        return 1

    spread = max(levels.values()) - min(levels.values())
    hi_name = max(levels, key=levels.get)
    print(f"\nspread {spread:.4f} dex  ({lo_name} -> {hi_name})")
    print(f"residual to explain {RESIDUAL:.4f} dex  "
          f"= {100 * RESIDUAL / spread:.1f}% of the spread\n")

    if spread >= RESIDUAL:
        print("VERDICT: demosaic choice ALONE spans the residual. It is a")
        print("sufficient explanation, so no further mechanism need be invented")
        print("to account for it. This does NOT prove the residual IS demosaic.")
    elif spread < 0.05:
        print("VERDICT: demosaic is REFUTED as the explanation -- every algorithm")
        print("lands within a few hundredths of a dex. Something else is eating")
        print("the remaining detail, and focus election is the next suspect.")
    else:
        print("VERDICT: partial. Demosaic covers some of the residual but not")
        print("all of it; a second mechanism is still required.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))

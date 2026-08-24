"""How hard does the real capture actually drive the demosaic?

Arm 6's ladder mosaics a 2x-downsampled truth, so the band it measures --
0.30-0.48 cyc/px of the TRUTH grid -- is 0.15-0.24 cyc/px of the SENSOR grid.
The real demosaic runs on the sensor grid, where its aliasing lives at
0.30-0.48 cyc/px of *that* lattice: a physically higher spatial frequency, where
diffraction has attenuated the scene far more.

So the synthetic ladder feeds MHC more in-band content than the real capture
ever contains, and its 31% artifact share is an UPPER bound on the real one.
This file turns that caveat into a number instead of leaving it as a hedge.

It measures, on the real full-resolution decode, the ratio of luma band power at
0.30-0.48 cyc/px (where real demosaic aliasing lives) to that at 0.15-0.24
cyc/px (what the synthetic ladder actually tested). A small ratio means the real
capture drives the demosaic much more gently than arm 6's ladder does.

Reads D:\\personal\\macro read-only. Writes nothing outside out/.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import rawpy

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import m95dem  # noqa: E402

ARW = pathlib.Path(r"D:\personal\macro\bee-3-cpl\DSC00150.ARW")
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M95-demosaic\scratch")
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"

N = 64
COUNT = 400
TESTED = (0.15, 0.24)   # what the synthetic ladder tested, in sensor-grid units
ALIAS = (0.30, 0.48)    # where the real demosaic's aliasing lives


def band_power(L, tiles, lo, hi):
    win, msk = m95dem.hann2(N), m95dem.band_mask(N, lo, hi)
    tot = 0.0
    for (y, x) in tiles:
        F = np.fft.rfft2(L[y:y + N, x:x + N] * win)
        tot += float((np.abs(F[msk]) ** 2).sum())
    return tot / int(msk.sum())     # per-bin, so the two bands are comparable


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    with rawpy.imread(str(ARW)) as raw:
        rgb = raw.postprocess(
            demosaic_algorithm=rawpy.DemosaicAlgorithm.AHD, output_bps=16,
            gamma=(1, 1), no_auto_bright=True, use_camera_wb=True,
            output_color=rawpy.ColorSpace.raw, user_flip=0)
    L = m95dem.luma(rgb.astype(np.float32) / 65535.0)
    print(f"sensor-grid decode {L.shape}")

    # Tiles ranked on the ALIAS band, i.e. the most favourable possible case for
    # there being real content up there. If the ratio is small even here, it is
    # small everywhere.
    tiles = m95dem.pick_tiles(L, N, COUNT, *ALIAS)
    p_alias = band_power(L, tiles, *ALIAS)
    p_tested = band_power(L, tiles, *TESTED)
    ratio = p_alias / p_tested

    # Same measurement on the synthetic truth, for the contrast.
    T = np.load(SCRATCH / "truth_AHD.npy")
    TL = m95dem.luma(T)
    ttiles = m95dem.pick_tiles(TL, N, COUNT, *ALIAS)
    t_alias = band_power(TL, ttiles, *ALIAS)
    t_tested = band_power(TL, ttiles, *TESTED)
    t_ratio = t_alias / t_tested

    print()
    print(f"  real sensor grid   per-bin power {ALIAS[0]}-{ALIAS[1]} : {p_alias:.6e}")
    print(f"  real sensor grid   per-bin power {TESTED[0]}-{TESTED[1]} : {p_tested:.6e}")
    print(f"  ratio alias/tested                        : {ratio:.5f}"
          f"   ({np.log10(ratio):+.4f} dex)")
    print()
    print(f"  synthetic truth    per-bin power {ALIAS[0]}-{ALIAS[1]} : {t_alias:.6e}")
    print(f"  synthetic truth    per-bin power {TESTED[0]}-{TESTED[1]} : {t_tested:.6e}")
    print(f"  ratio alias/tested                        : {t_ratio:.5f}"
          f"   ({np.log10(t_ratio):+.4f} dex)")
    print()
    print(f"  the synthetic ladder drives the demosaic {t_ratio / ratio:.2f}x harder"
          f" than the real capture does")

    res = {
        "alias_band": list(ALIAS), "tested_band": list(TESTED), "n_tiles": COUNT,
        "real": {"alias": p_alias, "tested": p_tested, "ratio": ratio,
                 "ratio_dex": float(np.log10(ratio))},
        "truth": {"alias": t_alias, "tested": t_tested, "ratio": t_ratio,
                  "ratio_dex": float(np.log10(t_ratio))},
        "overdrive": float(t_ratio / ratio),
    }
    (OUT / "d3_scale.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

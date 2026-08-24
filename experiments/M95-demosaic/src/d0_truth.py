"""Build ground truth `T` for arm 6, three ways.

`T` must be full-colour at every pixel with no CFA hole, so that mosaicking it
gives a demosaic problem whose answer is known exactly. There is no such image
lying around: every photograph this project owns came off a Bayer sensor.

The construction is a 2x box-downsample of a full-resolution decode. Demosaic
error lives at the top octave of the decode grid; averaging over a 2x2 quad
attenuates it heavily, and what survives is common to the whole ladder rather
than favouring one arm.

That construction is not free of its decoder, which is why three truths are
built here from three different LibRaw algorithms. K5 in `d2_ladder.py` runs the
whole ladder against all three: if the ranking of the arms depends on which
decoder made the truth, the truth is contaminated and arm 6 reports nothing.

Camera-native colour on purpose (`output_color=raw`): a colour matrix mixes the
channels, and demosaic artifacts are largely chromatic, so applying one before
the measurement would smear the thing being measured across channels. strehl
demosaics before the matrix for the same reason.

Writes only under C:\\dev\\strehl-out\\M95-demosaic\\. Reads D:\\personal\\macro
read-only.
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

TRUTHS = ["AHD", "VNG", "LINEAR"]


def decode(alg: str) -> np.ndarray:
    with rawpy.imread(str(ARW)) as raw:
        rgb = raw.postprocess(
            demosaic_algorithm=getattr(rawpy.DemosaicAlgorithm, alg),
            output_bps=16,
            gamma=(1, 1),
            no_auto_bright=True,
            use_camera_wb=True,
            output_color=rawpy.ColorSpace.raw,
            user_flip=0,
        )
    return rgb.astype(np.float32) / 65535.0


def main() -> int:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"source": str(ARW), "truths": {}}
    for alg in TRUTHS:
        full = decode(alg)
        T = m95dem.box2(full)
        # even extent both ways, else the RGGB parity of the last row/col is
        # ambiguous and the mosaic phase would differ from the interior
        T = T[: T.shape[0] // 2 * 2, : T.shape[1] // 2 * 2]
        p = SCRATCH / f"truth_{alg}.npy"
        np.save(p, T)
        meta["truths"][alg] = {
            "decode_shape": list(full.shape),
            "truth_shape": list(T.shape),
            "mean": float(T.mean()),
            "path": str(p),
        }
        print(f"  {alg:7s} decode {full.shape} -> truth {T.shape}  mean {T.mean():.5f}")
        del full, T

    (OUT / "d0_truth.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("\ntruths written to", SCRATCH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Round-trip probe: does the shipped CLI decode a hand-written CFA DNG?

Writes one small synthetic frame, then leaves it for `strehl probe` to read.
Everything downstream depends on this, so it is checked first and alone.
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from dngwrite import write_cfa_dng  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[1] / "data" / "probe"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    h, w = 64, 96
    rng = np.random.default_rng(0)
    cfa = np.zeros((h, w), np.uint16)
    # A distinct constant per CFA plane so a mis-read phase is visible.
    cfa[0::2, 0::2] = 4000  # R
    cfa[0::2, 1::2] = 6000  # G1
    cfa[1::2, 0::2] = 6500  # G2
    cfa[1::2, 1::2] = 3000  # B
    cfa = (cfa + rng.integers(0, 40, size=cfa.shape)).astype(np.uint16)
    path = OUT / "probe0001.arw"
    write_cfa_dng(path, cfa, iso=160, exposure_s=1.0)
    print(f"wrote {path} ({path.stat().st_size} bytes) shape={cfa.shape}")
    np.save(OUT / "probe-truth.npy", cfa)


if __name__ == "__main__":
    main()

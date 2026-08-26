"""Commission `bandtrade.py` before any of its numbers are believed.

A metric that has never been shown to move is not an instrument, it is a
formatting routine. This runs the two controls that make its readings mean
something, on the SAME real frames the report uses:

* NULL -- the control TIFF against ITSELF. Every band ratio must be exactly
  1.0000. If a null does not read exactly flat, nothing else it prints is
  interpretable.

* POSITIVE CONTROL -- the control TIFF against a deliberately softened copy of
  itself, with a known-potent one-octave blur. The finest band MUST collapse.
  A softening detector that cannot see a real blur cannot certify do-no-harm,
  and "no softening detected" from an inert detector looks exactly like a pass.

Both must pass or the do-no-harm number in the report is withdrawn.

    python commission_bandtrade.py <control.tiff>
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from bandtrade import blur, laplacian_bands, luma, read16

LEVELS = 6
FINE_MUST_DROP_BELOW = 0.60   # a one-octave blur must cost >=40% of band 0


def ratios(a: np.ndarray, b: np.ndarray) -> list[float]:
    ba, bb = laplacian_bands(a, LEVELS), laplacian_bands(b, LEVELS)
    out = []
    for x, y in zip(ba, bb):
        rx = float(np.sqrt(np.mean(x * x)))
        ry = float(np.sqrt(np.mean(y * y)))
        out.append(ry / rx if rx > 0 else float("nan"))
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    l = luma(read16(src))
    print(f"commissioning bandtrade.py on {src.name}  ({l.shape[1]} x {l.shape[0]} px)")
    print()

    ok = True

    null = ratios(l, l)
    flat = all(abs(r - 1.0) < 1e-6 for r in null)
    print("NULL  (control vs itself) -- every ratio must be 1.000000")
    print("      " + "  ".join(f"{r:.6f}" for r in null))
    print(f"      {'PASS' if flat else '*** FAIL -- the null is not flat'}")
    ok &= flat
    print()

    soft = blur(l)
    pos = ratios(l, soft)
    fine_ok = pos[0] < FINE_MUST_DROP_BELOW
    print("POSITIVE CONTROL  (control vs a one-octave blur of itself)")
    print("      " + "  ".join(f"{r:.4f}" for r in pos))
    print(f"      band 0 ratio {pos[0]:.4f}, must be < {FINE_MUST_DROP_BELOW}")
    print(f"      {'PASS -- the detector responds to a real blur' if fine_ok else '*** FAIL -- detector is inert'}")
    ok &= fine_ok
    print()

    print("COMMISSIONED -- bandtrade readings are admissible" if ok
          else "*** NOT COMMISSIONED -- withdraw every bandtrade number")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

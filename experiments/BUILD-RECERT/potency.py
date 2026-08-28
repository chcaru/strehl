"""Potency control for the pyramid-exponent arms.

ORCH's guard, verbatim: "An arm that silently rendered the default is
indistinguishable from an arm that made no difference." Both read as a null.
So before any arm is interpreted, this asks a question with only one honest
answer: do the decoded pixels differ, and by how much?

Three arms, deliberately:

  default   the shipping ladder, `per-band exp : 2 3 4 5 8 8 8` read from the
            run's own banner rather than from the brief.
  flat-1    --pyramid-exponent 1.0 --pyramid-sharpen 1.0, the candidate.
  exp-4     --pyramid-exponent 4.0, the KNOWN-POTENT positive control. ORCH
            measured it moving 90.98% of samples. It is here so that a null on
            flat-1 can be distinguished from an instrument that cannot see any
            exponent change at all. Without it, "flat-1 == default" would be
            unfalsifiable: it would be equally consistent with a flag that does
            nothing and with a comparison that reads nothing.

A file hash is NOT a pixel gauge and is not used. This project overturned a
correct finding tonight by comparing SHA-1s of TIFFs that differed only in an
ImageDescription tag while np.array_equal was True across 98,898,048 samples.
Everything below reads decoded arrays.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import tifffile

POT = r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\potency"

# The positive control must move at least this fraction of samples for the
# comparison itself to be considered awake. 0.9098 is ORCH's measured figure for
# --pyramid-exponent 4.0; the bar is set well under it so that a legitimately
# smaller move on a different subject does not read as a broken instrument,
# while a truly inert flag (which would read ~0) still fails.
CONTROL_MIN_MOVED = 0.20


def moved(a: np.ndarray, b: np.ndarray) -> tuple[float, int, float]:
    """Fraction of samples differing, max |difference|, and mean |difference|."""
    if a.shape != b.shape:
        raise SystemExit(f"shape mismatch {a.shape} vs {b.shape}")
    d = np.abs(a.astype(np.int64) - b.astype(np.int64))
    nz = d != 0
    return float(nz.mean()), int(d.max()), float(d[nz].mean()) if nz.any() else 0.0


def main() -> int:
    paths = {
        "default": os.path.join(POT, "cb--default.tiff"),
        "flat-1": os.path.join(POT, "cb--flat1.tiff"),
        "exp-4": os.path.join(POT, "cb--exp4.tiff"),
    }
    for name, p in paths.items():
        if not os.path.exists(p):
            raise SystemExit(f"missing arm {name}: {p}")

    arr = {k: tifffile.imread(v) for k, v in paths.items()}
    base = arr["default"]
    print(f"subject coffee-bubbles (19 frames), shape {base.shape} {base.dtype}")
    print(f"{'arm vs default':<16} {'moved%':>9} {'max|d|':>8} {'mean|d| on moved':>18}")

    results = {}
    for name in ("flat-1", "exp-4"):
        frac, mx, mean = moved(base, arr[name])
        results[name] = frac
        print(f"{name:<16} {frac*100:>8.4f}% {mx:>8d} {mean:>18.1f}")

    print()
    ctrl = results["exp-4"]
    cand = results["flat-1"]

    # Two-sided and NaN-guarded. `NaN > x` is False, so a NaN would read as a
    # pass on a naive one-sided test; ORCH had exactly that reach cert.json
    # tonight. Test for finiteness explicitly rather than relying on comparison.
    if not (np.isfinite(ctrl) and np.isfinite(cand)):
        print("REFUSED: non-finite move fraction; the comparison did not run")
        return 2

    if ctrl < CONTROL_MIN_MOVED:
        print(f"REFUSED: positive control --pyramid-exponent 4.0 moved only "
              f"{ctrl*100:.4f}% of samples (< {CONTROL_MIN_MOVED*100:.0f}%).")
        print("The instrument cannot see an exponent change, so a null on the")
        print("candidate arm would carry no information. Fix the harness first.")
        return 2

    print(f"CONTROL AWAKE: --pyramid-exponent 4.0 moved {ctrl*100:.4f}% of samples.")
    if cand == 0.0:
        print("CANDIDATE INERT: flat-1 is bit-identical to default. The flags")
        print("parsed but changed no pixel. Do not render 26 subjects.")
        return 1

    print(f"CANDIDATE POTENT: flat-1 moved {cand*100:.4f}% of samples.")
    print("The arms genuinely differ; a comparison between them is meaningful.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

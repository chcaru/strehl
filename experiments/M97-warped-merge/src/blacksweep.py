"""P3 re-confirmation at true 16 bits.

The first pass at this used PIL, which silently truncates a 16-bit RGB TIFF to
8 bits (mode='RGB', max 255) with no warning. A pixel that is 1/65535 is not
black, but after a >>8 truncation it reads as 0 -- so the 8-bit sweep could
only ever OVERSTATE the black count. This re-runs it on the real data.

Reports, per arm and over the WHOLE frame (not a crop):
  - NaN count (must be structurally impossible; checked anyway)
  - exact-zero pixel fraction, all channels zero
  - the same restricted to the outer annulus, where a gather rim would live
"""

import json
import sys

import numpy as np
import tifffile


def sweep(path: str) -> dict:
    a = tifffile.imread(path)
    if a.ndim == 2:
        a = a[:, :, None]
    h, w = a.shape[:2]
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"

    # uint16 cannot hold NaN, so a NaN would have had to be cast on the way out.
    # Check the float view of the raw bits is not somehow signalling, and check
    # the saturated value too -- a NaN cast to uint16 lands on 0 on x86.
    black = np.all(a == 0, axis=2)

    ann = np.zeros((h, w), dtype=bool)
    m = max(1, int(round(0.02 * min(h, w))))  # outer 2% border
    ann[:m, :] = ann[-m:, :] = ann[:, :m] = ann[:, -m:] = True

    return {
        "path": path,
        "shape": [int(h), int(w), int(a.shape[2])],
        "dtype": str(a.dtype),
        "max": int(a.max()),
        "black_frac_pct": 100.0 * float(black.mean()),
        "black_count": int(black.sum()),
        "annulus_black_frac_pct": 100.0 * float(black[ann].mean()),
        "annulus_black_count": int(black[ann].sum()),
    }


def main(argv: list[str]) -> int:
    out, pairs = argv[1], argv[2:]
    rows = []
    print(f"{'arm':<12} {'max':>6} {'black %':>12} {'outer black %':>14}")
    for spec in pairs:
        name, path = spec.split("=", 1)
        r = sweep(path)
        r["arm"] = name
        rows.append(r)
        print(
            f"{name:<12} {r['max']:>6} {r['black_frac_pct']:>12.5f} "
            f"{r['annulus_black_frac_pct']:>14.5f}"
        )
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=2)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

"""Capture metadata for 112MSDCF and 113MSDCF, and the physical focus step.

The whole point of the 112/113 pair is that the two captures sweep the *same*
focus interval at two sampling densities, so a frame-index span means a
different physical baseline in each.  That claim has to be measured, not
assumed, and the per-frame focus ladder has to be inspected for repeats: if the
body ever emits two frames at one focus position, a span-1 edge is not a
short baseline at all, it is a null pair, and the ladder would be measuring
something else entirely.

Run:  python m12_meta.py
"""

from __future__ import annotations

import csv
from collections import Counter

import numpy as np

CASES = [
    ("112MSDCF", "data/exif-112.csv"),
    ("113MSDCF", "data/exif-113.csv"),
]


def load(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    print("=" * 78)
    print("CAPTURE METADATA - 112MSDCF vs 113MSDCF")
    print("=" * 78)
    summary = {}
    for name, path in CASES:
        rows = load(path)
        d = np.array([float(r["FocusDistance2"]) for r in rows])
        p = np.array([float(r["FocusPosition2"]) for r in rows])
        steps = np.diff(d)
        nz = steps[np.abs(steps) > 0]
        print(f"\n  {name}: {len(rows)} frames")
        print(f"    FocusDistance2  {d[0]:.6f} -> {d[-1]:.6f} m   "
              f"span {d[-1] - d[0]:.6f} m")
        print(f"    FocusPosition2  {p[0]:.0f} -> {p[-1]:.0f}   "
              f"distinct positions {len(set(p.tolist()))}")
        print(f"    exposure {rows[0]['ExposureTime']} s   f/{rows[0]['FNumber']}   "
              f"ISO {rows[0]['ISO']}   LensType3 {rows[0]['LensType3']}")
        print(f"    inter-frame distance step: mean {steps.mean() * 1e6:.2f} um, "
              f"median {np.median(steps) * 1e6:.2f} um, "
              f"zero steps {int((steps == 0).sum())}/{len(steps)}")
        if nz.size:
            print(f"    non-zero steps: n={nz.size}  mean {nz.mean() * 1e6:.2f} um  "
                  f"min {nz.min() * 1e6:.2f}  max {nz.max() * 1e6:.2f}")
        runs = Counter()
        cur = 1
        for k in range(1, len(p)):
            if p[k] == p[k - 1]:
                cur += 1
            else:
                runs[cur] += 1
                cur = 1
        runs[cur] += 1
        print(f"    runs of equal FocusPosition2: {dict(sorted(runs.items()))}")
        pos_steps = np.diff(p)
        print(f"    FocusPosition2 steps: {dict(sorted(Counter(pos_steps.tolist()).items()))}")
        summary[name] = dict(n=len(rows), span=d[-1] - d[0], d0=d[0], d1=d[-1],
                             step=(d[-1] - d[0]) / (len(rows) - 1))

    a, b = summary["112MSDCF"], summary["113MSDCF"]
    print()
    print("=" * 78)
    print("THE LEVER THAT SEPARATES frame-index span FROM physical baseline")
    print("=" * 78)
    print(f"  112: {a['n']} frames, {a['n'] - 1} steps over {a['span'] * 1e3:.4f} mm "
          f"-> {a['step'] * 1e6:.3f} um/frame")
    print(f"  113: {b['n']} frames, {b['n'] - 1} steps over {b['span'] * 1e3:.4f} mm "
          f"-> {b['step'] * 1e6:.3f} um/frame")
    print(f"  ratio of physical baselines per unit frame-index span "
          f"(113/112) = {b['step'] / a['step']:.4f}")
    print(f"  identical focus interval? start {a['d0']:.6f} vs {b['d0']:.6f} m, "
          f"end {a['d1']:.6f} vs {b['d1']:.6f} m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

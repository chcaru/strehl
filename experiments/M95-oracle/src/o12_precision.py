"""O12 -- precision provenance of the inputs pick_tiles ranks in M95's trees.

o11 answered ORCH's structural question. This answers the second one: what was
the input, and was it already narrowed? Fact 1712 says a differencing dispersion
statistic under-reports noise by 16x on narrowed input, so the level count of the
array handed to pick_tiles is the thing that decides exposure.

Measured, not inferred. For every array actually loaded by the two flagged
scripts, and for a sample of the shared scratch the pinned call sites rank, this
prints dtype, range, and the number of DISTINCT LEVELS in a large sample -- which
is the direct observable behind "narrowed", where dtype alone is not (a float32
array holding 256 distinct values is narrowed and its dtype does not say so).

BAR, stated before the numbers: an array is NARROWED if a 4M-pixel sample of one
channel holds fewer than 4096 distinct values. Native 16-bit RAW clears that by
a wide margin; anything that has passed through an 8-bit stage cannot.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

OUTD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
OUT_ROOT = pathlib.Path(r"C:\dev\strehl-out")
NARROW_BAR = 4096
SAMPLE = 4_000_000


def probe(a, label):
    a = np.asarray(a)
    flat = a.reshape(-1) if a.ndim <= 2 else a[..., 0].reshape(-1)
    if flat.size > SAMPLE:
        step = flat.size // SAMPLE
        flat = flat[::step]
    lv = int(np.unique(flat).size)
    row = dict(label=label, dtype=str(a.dtype), shape=list(a.shape),
               min=float(np.min(a)), max=float(np.max(a)),
               levels=lv, sampled=int(flat.size),
               narrowed=bool(lv < NARROW_BAR))
    print(f"  {label:44s} {str(a.dtype):8s} {str(list(a.shape)):20s} "
          f"range [{row['min']:.5g}, {row['max']:.5g}]  "
          f"levels {lv:7d}/{flat.size}  "
          f"{'NARROWED' if row['narrowed'] else 'native'}")
    return row


def main() -> int:
    res = []
    print("BAR: fewer than 4096 distinct values in a 4M sample = NARROWED\n")

    print("the two call sites o11 flagged, M95-demosaic:")
    d = OUT_ROOT / "M95-demosaic" / "scratch"
    for alg in ["AHD", "VNG", "LINEAR"]:
        p = d / f"truth_{alg}.npy"
        if p.exists():
            res.append(probe(np.load(p, mmap_mode="r"), f"truth_{alg}.npy"))

    print("\nshared scratch ranked by the 31 pinned call sites:")
    for sub in ["M95-resample", "M95-coverage", "M95-kernel", "M95-cdiff",
                "M95-dose"]:
        base = OUT_ROOT / sub
        if not base.exists():
            continue
        found = sorted(base.rglob("*.npy"))[:3]
        if not found:
            print(f"  {sub:44s} no .npy scratch on disk")
            continue
        for p in found:
            try:
                res.append(probe(np.load(p, mmap_mode="r"),
                                 f"{sub}/{p.name}"))
            except Exception as e:
                print(f"  {sub}/{p.name}: unreadable ({e})")

    print("\n" + "=" * 78)
    nar = [r for r in res if r["narrowed"]]
    print(f"arrays probed: {len(res)}   NARROWED: {len(nar)}")
    for r in nar:
        print(f"  NARROWED  {r['label']}  {r['levels']} levels")
    if not res:
        raise SystemExit("COVERAGE FAILURE: probed nothing")
    with open(os.path.join(OUTD, "o12_precision.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"\nwrote {os.path.join(OUTD, 'o12_precision.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

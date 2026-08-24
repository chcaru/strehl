"""K17b -- why does the re-derived k disagree with the tool's printed 0.9315?

K17's K0 control failed: bisection on the pinned 299-frame solve returns
k = 0.997438, while the tool printed 0.9315 for bee-3-cpl. One of the two is
wrong and this script finds out which, before any arm number is reported.

Three things are checked.

1. SELF-CONSISTENCY of the bisection. covers(k) must be True at the returned k
   and False just above it. If the bracket is not tight the search is broken
   regardless of what the tool says.

2. WHICH SOLVE. k is a property of the placements, and the placements depend on
   the reference frame: a reference at 0 must accept the full end-to-end drift
   while a reference in the middle accepts only half of it. Every available
   bee-3-cpl sidecar is scanned and its own k derived, so a sidecar matching
   0.9315 identifies the solve the tool was describing.

3. GEOMETRY. The corner excursion at k = 1 is reported in plane pixels, so the
   crop can be checked by hand against the measured drift instead of trusted.
"""
import struct
import sys
from pathlib import Path

import numpy as np

MARGIN = 3.0
CANDIDATES = [
    r"C:\dev\strehl-out\M95-pin\experiments\M86-alignment\out\warpmap-bee-3-cpl.txt",
    r"C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-catmull-rom-warpmap.txt",
    r"C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-nearest-warpmap.txt",
    r"C:\dev\strehl-out\ORCH-kernel\bee-3-cpl-bilinear-warpmap.txt",
    r"C:\dev\strehl-out\ORCH-gallery3\bee-3-cpl-warpmap.txt",
    r"C:\dev\strehl-out\M106\warpmap-corpus-snapshot.txt",
    r"C:\dev\strehl-out\M107-chroma\renders\bee-3-cpl-warpmap.txt",
    r"C:\dev\strehl-out\ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt",
    r"C:\dev\strehl-out\M97\cache\bee-3-cpl-ea1d38ea5c9523c5.warpmap.txt",
    r"C:\dev\strehl-out\M113\cache\bee-3-cpl-ea1d38ea5c9523c5.warpmap.txt",
]


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def read_map(path):
    meta = {}
    rows = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("plane "):
            meta["plane"] = tuple(int(v) for v in s.split()[1].split("x"))
        elif s.startswith("stack-digest "):
            meta["digest"] = s.split()[1]
        elif s.startswith("frames "):
            meta["frames"] = int(s.split()[1])
        elif s.startswith("reference "):
            meta["reference"] = int(s.split()[1])
        elif s.startswith("resampler "):
            meta["resampler"] = s.split()[1]
        elif not s or s.startswith("#") or s.startswith("end"):
            continue
        else:
            p = s.split()
            if len(p) >= 6 and p[1] == "placed":
                rows.append((int(p[0]), f64(p[2]), f64(p[3]), f64(p[4]), f64(p[5])))
    return meta, rows


def geometry(plane):
    w, h = float(plane[0]), float(plane[1])
    corners = np.array(
        [complex(0.0, 0.0), complex(w - 1.0, 0.0),
         complex(0.0, h - 1.0), complex(w - 1.0, h - 1.0)]
    )
    return w, h, complex(w * 0.5, h * 0.5), corners


def covers(k, a, b, w, h, c, corners, margin=MARGIN):
    q = k * a[:, None] * (corners[None, :] - c) + b[:, None] + c
    return bool(
        np.all(
            (q.real >= margin) & (q.imag >= margin)
            & (q.real <= w - 1.0 - margin) & (q.imag <= h - 1.0 - margin)
        )
    )


def derive_k(plane, rows, margin=MARGIN):
    w, h, c, corners = geometry(plane)
    a = np.array([complex(r[1], r[2]) for r in rows])
    b = np.array([complex(r[3], r[4]) for r in rows])
    if covers(1.0, a, b, w, h, c, corners, margin):
        return 1.0, (a, b, w, h, c, corners)
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if covers(mid, a, b, w, h, c, corners, margin):
            lo = mid
        else:
            hi = mid
    return lo, (a, b, w, h, c, corners)


def excursion(a, b, w, h, c, corners):
    """How far outside the plane the worst corner lands at k = 1, plane px."""
    q = a[:, None] * (corners[None, :] - c) + b[:, None] + c
    over = np.maximum.reduce([
        MARGIN - q.real, MARGIN - q.imag,
        q.real - (w - 1.0 - MARGIN), q.imag - (h - 1.0 - MARGIN),
    ])
    return float(over.max())


def main():
    print("=" * 78)
    print("K17b  which solve does k = 0.9315 belong to?")
    print("=" * 78)
    print(f"  margin {MARGIN} px, bisection 60 iterations, same as fit_to_cover")
    print()
    hdr = f"  {'k':>9} {'1/k':>7} {'fr':>4} {'ref':>4} {'over@1':>8} {'tight':>6}  file"
    print(hdr)
    hits = []
    for path in CANDIDATES:
        p = Path(path)
        if not p.exists():
            print(f"  {'-':>9} {'-':>7} {'-':>4} {'-':>4} {'-':>8} {'-':>6}  "
                  f"MISSING {p.name}")
            continue
        meta, rows = read_map(p)
        if not rows:
            print(f"  {'-':>9} {'-':>7} {'-':>4} {'-':>4} {'-':>8} {'-':>6}  "
                  f"NO ROWS {p.name}")
            continue
        k, (a, b, w, h, c, corners) = derive_k(meta["plane"], rows)
        # self-consistency: covered at k, not covered just above it
        tight = covers(k, a, b, w, h, c, corners) and not covers(
            min(k + 1e-6, 1.0), a, b, w, h, c, corners
        )
        over = excursion(a, b, w, h, c, corners)
        print(f"  {k:>9.6f} {1 / k:>7.4f} {len(rows):>4} "
              f"{meta.get('reference', -1):>4} {over:>8.1f} "
              f"{'yes' if tight else 'NO':>6}  {p.name}")
        hits.append((k, meta, len(rows), p, tight, over))
    print()
    print("  over@1 = plane px the worst corner falls outside the source at k=1.")
    print("  tight  = covered at k and NOT covered at k+1e-6 (bracket is exact).")

    print()
    print("--- does any available solve give 0.9315? ---")
    near = [(abs(k - 0.9315), k, p.name) for k, _, _, p, _, _ in hits]
    near.sort()
    for d, k, name in near[:3]:
        print(f"  |k - 0.9315| = {d:.6f}   k = {k:.6f}   {name}")
    if near and near[0][0] < 0.001:
        print("  -> the printed 0.9315 belongs to that solve.")
    else:
        print("  -> NO available bee-3-cpl solve yields 0.9315.")

    print()
    print("--- what crop would 0.9315 require? ---")
    w = 3516.0
    print(f"  k=0.931500 crops {(1 - 0.9315) * w / 2:.1f} plane px per side "
          f"({(1 - 0.9315) * 100:.2f}% of width)")
    ks = [k for k, _, _, _, _, _ in hits if k < 1.0]
    if ks:
        km = max(ks)
        print(f"  k={km:.6f} crops {(1 - km) * w / 2:.1f} plane px per side "
              f"({(1 - km) * 100:.2f}% of width)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

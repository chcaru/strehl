"""V-DILUTE -- ORCH correction #4 re-check: is my verdict band-dependent at all?

ORCH's correction: the signal/noise boundary moves by subject, 0.17-0.48 cyc/px
(V-LINEAR, 31eda43a).  A fixed band-1 acuity gate is therefore illegitimate.

MY POSITION, TO BE TESTED NOT ASSUMED.  My Assignment 2 result is a NULL, and a
null that is FLAT ACROSS THE WHOLE FREQUENCY AXIS cannot be rescued or destroyed
by moving the boundary within that axis.  The fixed-band error bites when there
is a DIFFERENTIAL effect between bands and you read the wrong one.  So the test
is: report the null-normalised ratio in EVERY band, at both site types, for
every subject, and look for any differential.

If max |ratio - 1| over the entire boundary range 0.17-0.50 cyc/px is small on
every subject, the verdict holds for ANY boundary in V-LINEAR's measured range
and needs no per-subject qualification.  If some band moves and others do not,
my verdict IS band-dependent and must be requalified per subject.

Bands (contrast_ms.py placement, f = 1/(2*pi*sigma)):
  band 0  0.250-0.500   spans boundaries 0.25..0.48
  band 1  0.170-0.250   spans boundaries 0.17..0.25
  band 2+ coarser, reported for completeness and as the null
"""
import os
import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter

SIGMAS = [0.6366, 0.9362, 2.0, 4.0, 8.0, 16.0]
EDGES = [1.0 / (2.0 * np.pi * s) for s in SIGMAS]
S, N_SITES = 256, 12

# V-LINEAR 31eda43a, docs/research/V-LINEAR-BANDS.md section 3.
KNOWN = {"113MSDCF": 0.25, "119MSDCF": 0.25, "bee-1-cpl": 0.48,
         "flower-bud-alone-cpl": 0.17, "leaf-2-cpl": 0.20}

SUBJECTS = [("coffee-bubbles", 19), ("109MSDCF", 22), ("119MSDCF", 33),
            ("113MSDCF", 63), ("foam", 100), ("coffee-bean", 105),
            ("bee-3-cpl", 299)]


def lum(p):
    a = tifffile.imread(p)
    if a.ndim == 3:
        a = a[..., :3].astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    return a.astype(np.float64)


def octaves(x):
    out, prev = [], x
    for s in SIGMAS:
        cur = gaussian_filter(x, s)
        out.append(prev - cur)
        prev = cur
    return out


def per_band(pa, pb):
    a, b = lum(pa), lum(pb)
    if a.shape != b.shape:
        return None
    b = b * (np.median(a) / np.median(b))
    mid = gaussian_filter(a, 2.0)
    gy, gx = np.gradient(mid)
    g = np.hypot(gy, gx)
    H, W = a.shape
    ny, nx = H // S, W // S
    tg = g[: ny * S, : nx * S].reshape(ny, S, nx, S).mean(axis=(1, 3))
    order = np.argsort(tg.ravel())
    flat, edge = order[:N_SITES], order[-N_SITES:]
    ba, bb = octaves(a), octaves(b)

    def bs(idx, arr):
        v = []
        for f in idx:
            ty, tx = divmod(int(f), nx)
            v.append(arr[ty * S:ty * S + S, tx * S:tx * S + S].std())
        return float(np.mean(v))

    null = bs(edge, bb[-1]) / bs(edge, ba[-1])
    e = [bs(edge, bb[j]) / bs(edge, ba[j]) / null for j in range(len(SIGMAS))]
    f = [bs(flat, bb[j]) / bs(flat, ba[j]) / null for j in range(len(SIGMAS))]
    return e, f, null


if __name__ == "__main__":
    D = r"C:\dev\strehl-out\V-DILUTE\baseband"
    print("Null-normalised ratio, --pyramid-base weighted vs mean, --pyramid-bands 7.")
    print("Every band reported. A verdict that is flat across all bands does not")
    print("depend on where a subject's signal/noise boundary sits.")
    print()
    hdr = (f"{'subject':<16s} {'N':>4s} {'bnd':>5s} | " +
           " ".join(f"{f'{(0.5 if j == 0 else EDGES[j-1]):.2f}':>7s}" for j in range(len(SIGMAS))) +
           " |  maxdev(0.17-0.50)")
    print(hdr)
    print("-" * len(hdr))
    worst = 0.0
    for subj, n in SUBJECTS:
        pa = os.path.join(D, f"{subj}.b7.mean.tiff")
        pb = os.path.join(D, f"{subj}.b7.weighted.tiff")
        if not (os.path.exists(pa) and os.path.exists(pb)):
            continue
        r = per_band(pa, pb)
        if not r:
            continue
        e, f, null = r
        bnd = KNOWN.get(subj)
        bl = f"{bnd:.2f}" if bnd else ("~0.48?" if subj.startswith("bee") else "  --")
        # bands 0 and 1 together cover the whole measured boundary range
        dev = max(abs(e[0] - 1), abs(e[1] - 1), abs(f[0] - 1), abs(f[1] - 1))
        worst = max(worst, dev)
        print(f"{subj:<16s} {n:4d} {bl:>5s} | " +
              " ".join(f"{v:7.4f}" for v in e) + f" |  EDGE  dev {dev:.4f}")
        print(f"{'':<16s} {'':>4s} {'':>5s} | " +
              " ".join(f"{v:7.4f}" for v in f) + f" |  FLAT")
    print()
    print(f"WORST deviation from 1.0000 anywhere in 0.17-0.50 cyc/px, any subject,")
    print(f"either site type: {worst:.4f}")
    print()
    print("boundary column: value = measured by V-LINEAR (31eda43a); '--' = not measured.")
    print("Bands 0 and 1 together span 0.17-0.50 cyc/px and therefore contain every")
    print("boundary V-LINEAR observed (0.17, 0.20, 0.25, 0.25, 0.48).")

"""What is actually in the master's band field? Measure, do not eyeball.

The 1:1 crop looks like it carries a regular lattice. That is an impression.
This dumps the 2-D power spectrum of the worst tile for the master and for the
19 sources, so the pitch -- if there is one -- is read off rather than guessed,
and so "the frames do not have it" is a number.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_bubbles as B  # noqa: E402
import vn_lib as L  # noqa: E402
from orch_blotch import lum_of  # noqa: E402


def spec_peaks(t, kmin=2, kmax=60, top=8):
    """Strongest spectral peaks above the local radial baseline, as pitches."""
    A = t - t.mean()
    h, w = A.shape
    A = A * (np.hanning(h)[:, None] * np.hanning(w)[None, :])
    P = np.abs(np.fft.fftshift(np.fft.fft2(A))) ** 2
    cy, cx = h // 2, w // 2
    yy, xx = np.mgrid[:h, :w]
    ky, kx = yy - cy, xx - cx
    r = np.hypot(ky, kx)
    ri = np.rint(r).astype(int)
    resid = np.full(P.shape, -np.inf)
    for rr in range(kmin, kmax + 1):
        sel = ri == rr
        if sel.any():
            med = np.median(P[sel])
            resid[sel] = P[sel] / max(med, 1e-30)
    out = []
    flat = resid.ravel()
    for i in np.argsort(flat)[::-1]:
        if not np.isfinite(flat[i]):
            continue
        y, x = divmod(int(i), w)
        if any(abs(y - a) < 3 and abs(x - b) < 3 for a, b, _, _ in out):
            continue
        pitch = h / max(float(np.hypot(ky[y, x], kx[y, x])), 1e-9)
        out.append((y, x, pitch, float(flat[i])))
        if len(out) >= top:
            break
    return out


def edge_profile(t):
    """Mean |column step| as a function of x, then its own spectrum.

    A lattice of block boundaries is a periodic train of steps, so its
    signature is a peak in the SPECTRUM OF THE STEP PROFILE, which survives
    the band filter's smoothing far better than any single step does.
    """
    d = np.abs(np.diff(t, axis=1)).mean(axis=0)
    d = d - d.mean()
    P = np.abs(np.fft.rfft(d * np.hanning(d.size))) ** 2
    k = np.arange(P.size)
    out = []
    for i in range(2, min(P.size, 80)):
        out.append((float(d.size / max(k[i], 1e-9)), float(P[i] / max(np.median(P[2:80]), 1e-30))))
    out.sort(key=lambda r: -r[1])
    return out[:6]


def main():
    res = L.jload(os.path.join(B.OUT, "bubbles.json"))
    mwin, flums, _, bw, mrgb, frgb = B.gather()
    ty, tx = res["worst_tile"]
    T = B.TILE

    def tile(f):
        return f[ty:ty + T, tx:tx + T]

    print("")
    print("SPECTRUM of the BAND field, worst tile")
    for name, f in [("master", mwin)] + [("f%02d" % i, flums[i])
                                         for i in (res["best_frame"],
                                                   res["attr_best_frame"], 5)]:
        pk = spec_peaks(tile(B.nband(f)))
        print("  %-7s %s" % (name, ", ".join("%.1fpx x%.1f" % (p, v)
                                             for _, _, p, v in pk[:5])))

    print("")
    print("SPECTRUM of the LUMINANCE, worst tile (before the band filter)")
    for name, f in [("master", mwin)] + [("f%02d" % i, flums[i])
                                         for i in (res["best_frame"],
                                                   res["attr_best_frame"], 5)]:
        pk = spec_peaks(tile(f))
        print("  %-7s %s" % (name, ", ".join("%.1fpx x%.1f" % (p, v)
                                             for _, _, p, v in pk[:5])))

    print("")
    print("STEP-PROFILE spectrum of the band field (lattice of boundaries)")
    for name, f in [("master", mwin)] + [("f%02d" % i, flums[i])
                                         for i in (res["best_frame"],
                                                   res["attr_best_frame"], 5)]:
        pk = edge_profile(tile(B.nband(f)))
        print("  %-7s %s" % (name, ", ".join("%.1fpx x%.1f" % (p, v)
                                             for p, v in pk[:5])))

    print("")
    print("BAND amplitude, worst tile: is the master simply LARGER?")
    for name, f in [("master", mwin)] + [("f%02d" % i, flums[i])
                                         for i in range(0, 19, 6)]:
        b = tile(B.nband(f))
        print("  %-7s std %.5f   p99|.| %.5f" % (name, float(b.std()),
                                                 float(np.percentile(np.abs(b), 99))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

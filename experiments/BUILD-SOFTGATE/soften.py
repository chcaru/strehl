"""Score depth softening on CLI-rendered masters, using V-NEVERWORSE's instrument.

The statistic is the one facts 1843/1844 report: radially-averaged power in the
0.30-0.35 cyc/px band, normalised by a 0.02-0.05 low band to remove common gain.
Depth softening is the CHANGE in that statistic between adjacent depths -- a
negative delta means the deeper stack is softer.

`spectrum` is imported from experiments/V-NEVERWORSE/vn_ninv.py so this lane
measures with the same instrument that produced the facts, not a re-statement of
it. Which path was used is printed, because "I reused their code" is a claim.

COMMISSIONED BEFORE USE. A planted blur must LOWER the statistic and a planted
sharpening must RAISE it. A metric that does not move under a known change
cannot be trusted to report that a treatment did not move it.
"""
import sys
import os
import numpy as np
import tifffile

VN = r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-NEVERWORSE"
sys.path.insert(0, VN)
try:
    from vn_ninv import spectrum, BANDS, REFBAND
    SRC = "imported from vn_ninv.py (V-NEVERWORSE's own instrument)"
except Exception as e:  # pragma: no cover - fallback path is reported
    SRC = "verbatim restatement (vn_ninv import failed: %s)" % e
    BANDS = ((0.10, 0.15), (0.20, 0.25), (0.30, 0.35), (0.40, 0.45))
    REFBAND = (0.02, 0.05)

    def _hann2(h, w):
        return np.outer(np.hanning(h), np.hanning(w))

    def spectrum(img):
        g = img[:, :, 1].astype(np.float64)
        g = g - g.mean()
        h, w = g.shape
        F = np.fft.rfft2(g * _hann2(h, w))
        p = (F.real ** 2 + F.imag ** 2)
        fy = np.fft.fftfreq(h)[:, None]
        fx = np.fft.rfftfreq(w)[None, :]
        rad = np.sqrt(fy ** 2 + fx ** 2)
        out = {}
        for lo, hi in (REFBAND,) + BANDS:
            m = (rad >= lo) & (rad < hi)
            out["%.2f-%.2f" % (lo, hi)] = float(p[m].mean())
        ref = out["%.2f-%.2f" % REFBAND]
        for lo, hi in BANDS:
            k = "%.2f-%.2f" % (lo, hi)
            out["n_" + k] = out[k] / max(ref, 1e-30)
        return out

KEY = "n_0.30-0.35"


def stat(img):
    return spectrum(img)[KEY]


def flattest_tile(img, size=512):
    """The lowest-detail tile: rule 9's flat-region control. A treatment that
    moves this as much as it moves the whole frame is not moving DETAIL."""
    g = img[:, :, 1].astype(np.float64)
    h, w = g.shape
    best, bxy = None, (0, 0)
    for y in range(0, h - size, max(size, (h - size) // 6 or 1)):
        for x in range(0, w - size, max(size, (w - size) // 6 or 1)):
            v = float(g[y:y + size, x:x + size].var())
            if best is None or v < best:
                best, bxy = v, (y, x)
    y, x = bxy
    return img[y:y + size, x:x + size, :], bxy, best


def commission(img):
    """Plant a blur and a sharpening; the statistic must fall and rise."""
    from numpy.fft import rfft2, irfft2
    g = img[:, :, 1].astype(np.float64)
    h, w = g.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    r2 = fy ** 2 + fx ** 2
    F = rfft2(g)
    blur = irfft2(F * np.exp(-r2 / (2 * 0.12 ** 2)), s=(h, w))
    sharp = g + 0.6 * (g - blur)

    def as_img(plane):
        o = img.astype(np.float64).copy()
        o[:, :, 1] = plane
        return o

    s0 = stat(img.astype(np.float64))
    sb = stat(as_img(blur))
    ss = stat(as_img(sharp))
    print("  COMMISSION reference        %s = %.6f" % (KEY, s0))
    print("  COMMISSION planted BLUR     %s = %.6f  ratio %.4f  %s"
          % (KEY, sb, sb / s0, "PASS (fell)" if sb < s0 else "FAIL (did not fall)"))
    print("  COMMISSION planted SHARPEN  %s = %.6f  ratio %.4f  %s"
          % (KEY, ss, ss / s0, "PASS (rose)" if ss > s0 else "FAIL (did not rise)"))
    return sb < s0 and ss > s0


def main():
    paths = sys.argv[1:]
    print("instrument      : %s" % SRC)
    print("statistic       : %s (0.30-0.35 cyc/px power / 0.02-0.05 low band)" % KEY)
    print()
    first = tifffile.imread(paths[0].split("=", 1)[1])
    print("COMMISSIONING THE METRIC on %s" % os.path.basename(paths[0].split("=", 1)[1]))
    ok = commission(first)
    print("  -> metric %s\n" % ("COMMISSIONED" if ok else "REJECTED -- DO NOT TRUST BELOW"))

    rows = {}
    print("%-22s %14s %14s" % ("arm", KEY, "flatROI"))
    for spec in paths:
        label, p = spec.split("=", 1)
        img = tifffile.imread(p)
        whole = stat(img.astype(np.float64))
        tile, xy, var = flattest_tile(img)
        flat = stat(tile.astype(np.float64))
        rows[label] = (whole, flat)
        print("%-22s %14.6f %14.6f   (flat tile at %s, var %.1f)" % (label, whole, flat, xy, var))

    print()
    print("DEPTH SOFTENING: statistic(N=79) - statistic(N=39). Negative = softer with depth.")
    print("%-22s %14s %14s" % ("arm", "delta", "delta flatROI"))
    for arm in ("unset", "exponential", "gaussian"):
        a, b = rows.get("39-" + arm), rows.get("79-" + arm)
        if a and b:
            print("%-22s %+14.6f %+14.6f" % (arm, b[0] - a[0], b[1] - a[1]))


if __name__ == "__main__":
    main()

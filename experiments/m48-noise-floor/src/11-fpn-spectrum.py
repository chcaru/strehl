r"""M48 script 11 -- is the fixed pattern white to Nyquist?

M46 fact 612 asserts the common-mode FPN is "white to Nyquist", and that claim
is load-bearing: it is what kills the FRC 1/7 crossing as a statistic and
licenses several censoring results downstream. M46 established it on an
illuminated pair. Dark frames test it directly, on the fixed pattern itself.

Estimator. The per-pixel temporal mean of T frames is `mu + (temporal noise)/T`,
and that leaked temporal noise is WHITE -- so the power spectrum of a single
mean image has a flat pedestal that would manufacture exactly the conclusion
under test. The fix is the same one script 09 uses for the variance: split the
frames into two disjoint halves by parity and take the CROSS-power spectrum

    P(f) = < Re{ F_A(f) * conj(F_B(f)) } >_ring

whose expectation contains no temporal term at all, because the two halves'
temporal noise is independent. Any flatness in P(f) is the fixed pattern's own.

Two statistics are reported:
  * the slope of log P against log f, and the ratio of mean power in the top
    decade of frequency to the bottom -- both 0 and 1 respectively if white;
  * a row/column/residual decomposition, because CMOS fixed pattern is usually
    part banding, and banding is NOT white. This is computed by covariance
    between halves too, so it is also free of the temporal pedestal.

D:\macro-dark-frames is read-only source data. This script only reads it.
"""

import json
import os

import numpy as np
import rawpy

ROOT = r"D:\macro-dark-frames"
DROP_STABILISATION = 2
CROP = 2048  # centred square per plane, power of two for the FFT
PLANE = ("G1", 0, 1)  # the plane the merge's green luma is built from

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "fpn-spectrum.json")


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def half_means(d):
    files = sorted(
        os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".arw")
    )
    iso = iso_of(files[0])
    files = files[DROP_STABILISATION:]
    if len(files) % 2:
        files = files[:-1]
    _, dy, dx = PLANE
    a = b = None
    for idx, f in enumerate(files):
        with rawpy.imread(f) as rr:
            raw = rr.raw_image_visible
            p = raw[dy::2, dx::2]
            h, w = p.shape
            y0, x0 = (h - CROP) // 2, (w - CROP) // 2
            crop = p[y0 : y0 + CROP, x0 : x0 + CROP].astype(np.float64)
            del raw
        if a is None:
            a = np.zeros_like(crop)
            b = np.zeros_like(crop)
        if idx % 2 == 0:
            a += crop
        else:
            b += crop
    n = len(files) // 2
    return iso, a / n, b / n, len(files)


def radial_cross_spectrum(a, b):
    """Ring-averaged cross-power of two images, in cycles/pixel."""
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    fa = np.fft.fft2((a - a.mean()) * win)
    fb = np.fft.fft2((b - b.mean()) * win)
    cross = np.real(fa * np.conj(fb))

    n = a.shape[0]
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    fr = np.sqrt(fy**2 + fx**2)

    nb = 64
    edges = np.linspace(0.0, 0.5, nb + 1)
    idx = np.digitize(fr.ravel(), edges) - 1
    flat = cross.ravel()
    centres, power = [], []
    for k in range(nb):
        m = idx == k
        if m.sum() < 32:
            continue
        centres.append(0.5 * (edges[k] + edges[k + 1]))
        power.append(float(flat[m].mean()))
    return np.array(centres), np.array(power)


def rowcol_split(a, b):
    """Share of fixed-pattern variance in row, column and residual structure.

    Every term is a cross-covariance between the two halves, so none of it
    contains the temporal pedestal.
    """
    ac, bc = a - a.mean(), b - b.mean()
    ar, br = ac.mean(axis=1), bc.mean(axis=1)  # row profiles
    acol, bcol = ac.mean(axis=0), bc.mean(axis=0)  # column profiles
    res_a = ac - ar[:, None] - acol[None, :]
    res_b = bc - br[:, None] - bcol[None, :]

    v_row = float(np.mean(ar * br))
    v_col = float(np.mean(acol * bcol))
    v_res = float(np.mean(res_a * res_b))
    v_tot = float(np.mean(ac * bc))
    return {
        "v_total": v_tot,
        "v_row": v_row,
        "v_col": v_col,
        "v_residual": v_res,
        "row_share": v_row / v_tot if v_tot else None,
        "col_share": v_col / v_tot if v_tot else None,
        "residual_share": v_res / v_tot if v_tot else None,
    }


def main():
    dirs = sorted(
        os.path.join(ROOT, d)
        for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d))
    )
    out = []
    for d in dirs:
        iso, a, b, t = half_means(d)
        f, p = radial_cross_spectrum(a, b)
        ok = (f > 0.02) & (p > 0)
        slope = float(np.polyfit(np.log(f[ok]), np.log(p[ok]), 1)[0]) if ok.sum() > 8 else None
        lo = p[(f >= 0.05) & (f < 0.15)].mean()
        hi = p[(f >= 0.40) & (f <= 0.50)].mean()
        rc = rowcol_split(a, b)
        rec = {
            "iso": iso,
            "dir": os.path.basename(d),
            "frames": t,
            "loglog_slope": slope,
            "power_low_0.05_0.15": float(lo),
            "power_high_0.40_0.50": float(hi),
            "high_over_low": float(hi / lo) if lo else None,
            "rowcol": rc,
            "freq": f.tolist(),
            "power": p.tolist(),
        }
        out.append(rec)
        print(
            f"ISO {iso:5d}  slope {slope:+.3f}  hi/lo {hi/lo:6.3f}  "
            f"row {rc['row_share']*100:5.1f}%  col {rc['col_share']*100:5.1f}%  "
            f"resid {rc['residual_share']*100:5.1f}%"
        )
    out.sort(key=lambda r: r["iso"])
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "_meta": {
                    "script": "11-fpn-spectrum.py",
                    "claim_under_test": "M46 fact 612 -- common-mode FPN is white to Nyquist",
                    "estimator": "ring-averaged cross-power of two disjoint "
                    "half-means, which carries no temporal pedestal",
                    "plane": PLANE[0],
                    "crop": CROP,
                    "white_would_give": "slope 0, high/low ratio 1, "
                    "row+col shares near 0",
                },
                "sets": out,
            },
            fh,
            indent=2,
        )
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

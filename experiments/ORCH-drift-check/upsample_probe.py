"""Does the aligned render carry a resampling cutoff at 0.9315 x Nyquist?

CLAIM UNDER TEST (from the tool's own output, not yet independently confirmed):
  "coverage : field of view scaled to 0.9315 so that EVERY frame covers every
   pixel (6.9% of width dropped, then upsampled to keep the output dimensions)"
and from --help: "the field of view shrinks ~7-10% so that every frame covers
every output pixel."

If true, the 7032x4688 output carries only ~6547x4365 of real sampling. The
source grid's Nyquist then maps to 0.9315 of the OUTPUT grid's Nyquist, and
there should be a distinct break in the radial power spectrum at f = 0.9315,
above which only interpolation-kernel leakage survives.

WHY THIS TEST AND NOT A SHARPNESS METRIC. A resampling cutoff is a STRUCTURAL
signature at a PREDICTED frequency, so it can be falsified: the break must land
at 0.9315, not merely "somewhere high". Optical rolloff (diffraction, defocus)
is smooth and has no reason to knee at that particular frequency. This is the
difference between measuring a mechanism and scoring an impression.

CONTROL. The same measurement is run on the gate-0.00 arm. The gate provably
does not change detailed regions (fact 1393, 1.00x), but it changes noise
enormously in flat ones -- and NOISE IS BROADBAND, so it fills the band above
any resampling cutoff. If the break is a real resampling cutoff it must sit at
the SAME frequency in both arms; if it moves with the gate it is not one.
"""
import os

import numpy as np
import tifffile

OUT = r"C:\dev\strehl-out\ORCH-gate"
PREDICTED = 0.9315


def region(g, y, x, s):
    a = tifffile.imread(os.path.join(OUT, f"pin-bee-3-cpl-gate-{g}.tif"))
    return a[y:y + s, x:x + s, 1].astype(np.float64)


def radial_spectrum(img):
    n = img.shape[0]
    w = np.hanning(n)
    img = (img - img.mean()) * w[:, None] * w[None, :]
    F = np.abs(np.fft.fftshift(np.fft.fft2(img))) ** 2
    c = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    r = np.sqrt((yy - c) ** 2 + (xx - c) ** 2)
    nyq = c
    bins = np.linspace(0, 1.05, 106)
    rn = r / nyq
    prof = np.array([F[(rn >= bins[i]) & (rn < bins[i + 1])].mean() if ((rn >= bins[i]) & (rn < bins[i + 1])).sum() > 8
                     else np.nan for i in range(len(bins) - 1)])
    return bins[:-1] + np.diff(bins) / 2, prof


def main():
    S = 1024
    sites = [("eye/ommatidia", 3200, 4352), ("hair mass", 3150, 700)]

    for label, y, x in sites:
        print(f"\n=== {label}  {S}x{S} at ({x},{y}) ===")
        print(f"{'f/Nyq':>7} " + "".join(f"{'gate '+g:>14}" for g in ("4.00", "0.00")) + "   slope4")
        curves = {}
        for g in ("4.00", "0.00"):
            f, p = radial_spectrum(region(g, y, x, S))
            curves[g] = (f, p / np.nanmax(p))
        f = curves["4.00"][0]
        prev = None
        for i in range(len(f)):
            if f[i] < 0.80 or f[i] > 1.02:
                continue
            a = curves["4.00"][1][i]
            b = curves["0.00"][1][i]
            sl = "" if prev is None or not np.isfinite(a) or a <= 0 or prev <= 0 else f"{np.log10(a/prev):+7.3f}"
            mark = "  <-- predicted" if abs(f[i] - PREDICTED) < 0.006 else ""
            print(f"{f[i]:>7.3f} {a:>14.3e} {b:>14.3e}   {sl}{mark}")
            prev = a if np.isfinite(a) else prev

        # where is the steepest log-drop between 0.85 and 1.0?
        for g in ("4.00", "0.00"):
            fq, p = curves[g]
            m = (fq >= 0.85) & (fq <= 1.00) & np.isfinite(p) & (p > 0)
            lf, lp = fq[m], np.log10(p[m])
            d = np.diff(lp) / np.diff(lf)
            k = int(np.argmin(d))
            print(f"  gate {g:>5}: steepest log-slope {d[k]:8.2f} dex/Nyq at f = {lf[k]:.3f}"
                  f"   (predicted {PREDICTED})")


if __name__ == "__main__":
    main()

"""V-KILLB0 per-subject QUALIFIED-band re-check (ORCH correction #4).

My earlier tables used a fixed high-pass and, worse, I had mislabelled its
passband.  This replaces both problems at once:

 * bands are ideal FFT radial bands with EXACT edges, so there is no gaussian
   cutoff convention to get wrong;
 * each subject is scored in ITS OWN qualified band, taken from
   docs/research/V-LINEAR-BANDS.md, never a corpus-wide band;
 * only within-subject arm ratios are reported, never a cross-subject ratio.

For a subject with boundary b, the band scored is [0.7b, b] -- the TOP slice
that subject actually qualifies, which is where a softening shows first and
where a claim of "no acuity loss" has to be earned.  A second row scores
[0.3b, 0.7b] to show the damage is not confined to the band edge.

Structured pixels are selected at 0.030-0.085 cyc/px, which is below every
boundary in the document, so the selector is qualified signal on all subjects.

CONTROLS: NULL (arm against itself) must read exactly 1.000000; a planted
gaussian blur must read clearly below 1 in the qualified band.
"""
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp

BOUNDARY = {"bee-1-cpl": 0.48, "113MSDCF": 0.25, "119MSDCF": 0.25,
            "leaf-2-cpl": 0.20, "flower-bud-alone-cpl": 0.17}


def radial_band(img, f0, f1):
    a = np.fft.rfft2(img.astype(np.float32))
    h, w = img.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    r = np.sqrt(fy * fy + fx * fx)
    a *= ((r >= f0) & (r < f1))
    return np.fft.irfft2(a, s=img.shape)


def score(la, lb, f0, f1, mask):
    pa, pb = radial_band(la, f0, f1), radial_band(lb, f0, f1)
    a, b = pa[mask].astype(np.float64), pb[mask].astype(np.float64)
    a -= a.mean(); b -= b.mean()
    ea, eb = np.sqrt((a * a).mean()), np.sqrt((b * b).mean())
    rho = (a * b).mean() / (ea * eb)
    return eb / ea, rho, ea, eb


def main():
    A, B, label = sys.argv[1], sys.argv[2], sys.argv[3]
    b = BOUNDARY[label]
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    sel = np.abs(radial_band(la, 0.030, 0.085))
    sel = gaussian_filter(sel, 3.0)
    struct = sel >= np.percentile(sel, 75)
    flat = sel < np.percentile(sel, 25)

    h, w = la.shape
    sub = la[h//2-768:h//2+768, w//2-768:w//2+768]
    ms = np.ones(sub.shape, bool)
    r_null = score(sub, sub.copy(), 0.7*b, b, ms)[0]
    r_blur = score(sub, gaussian_filter(sub, 0.8), 0.7*b, b, ms)[0]
    print(f"== QUALIFIED {label}   V-LINEAR boundary = {b:.2f} cyc/px")
    print(f"   [C0 NULL] {r_null:.6f}  {'PASS' if abs(r_null-1) < 1e-9 else 'FAIL'}"
          f"    [C1 BLUR sigma 0.8] {r_blur:.4f}  {'PASS' if r_blur < 0.9 else 'FAIL'}")
    print(f"   median={np.median(la):.0f} clip%={100*(la>=65000).mean():.3f} "
          f"black%={100*(la<=200).mean():.3f}")
    print(f"   {'band (cyc/px)':<18} {'site':<8} {'B/A':>8} {'rho':>8} {'A rms DN':>10} {'B rms DN':>10}")
    for nm, f0, f1 in ((f"{0.7*b:.3f}-{b:.3f}", 0.7*b, b),
                       (f"{0.3*b:.3f}-{0.7*b:.3f}", 0.3*b, 0.7*b)):
        for sname, m in (("STRUCT", struct), ("FLAT", flat)):
            ratio, rho, ea, eb = score(la, lb, f0, f1, m)
            print(f"   {nm:<18} {sname:<8} {ratio:8.4f} {rho:8.4f} {ea:10.1f} {eb:10.1f}")


if __name__ == "__main__":
    main()

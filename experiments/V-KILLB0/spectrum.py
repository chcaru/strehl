"""V-KILLB0 spectrum.py -- overlay WHERE THE KNOB ACTS onto WHERE THE SIGNAL IS.

flatanalyze.py answers "is band X at flat/structured sites signal or noise?"
using V-LINEAR's imported rule on linear develops.  This answers the other half
on the SAME band edges and the SAME site definitions: "what does the knob do to
band X at flat/structured sites?"  Laying the two tables side by side is the
only honest way to say whether the knob is self-targeting, because
self-targeting is a claim about the JOINT distribution of the two.

Bands are V-LINEAR's FINE list, imported, and realised as ideal FFT radial
bands so there is no gaussian-cutoff convention left to get wrong.

CONTROLS (run every invocation, printed before any result):
  C0 NULL   A vs A                 -> must be 1.000000 in EVERY band
  C1 BLUR   B := blur(A, sigma)    -> must be <1, monotone worse with freq
  C2 NOISE  B := A + white noise   -> must be >1, worst at high freq
An instrument that reads "no change" is indistinguishable from a dead one.
"""
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp

sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-LINEAR2")
from bandsignal import FINE          # noqa: E402  imported UNMODIFIED

SEL_LO, SEL_HI = 0.030, 0.085        # below every boundary in V-LINEAR-BANDS.md


def radial(img, f0, f1):
    a = np.fft.rfft2(img.astype(np.float32))
    h, w = img.shape
    r = np.hypot(np.fft.fftfreq(h)[:, None], np.fft.rfftfreq(w)[None, :])
    a *= ((r >= f0) & (r < f1))
    return np.fft.irfft2(a, s=img.shape)


def score(la, lb, f0, f1, mask):
    a = radial(la, f0, f1)[mask].astype(np.float64)
    b = radial(lb, f0, f1)[mask].astype(np.float64)
    a -= a.mean(); b -= b.mean()
    ea, eb = np.sqrt((a * a).mean()), np.sqrt((b * b).mean())
    if ea == 0:
        return float("nan"), float("nan"), ea, eb
    return eb / ea, (a * b).mean() / (ea * eb), ea, eb


def table(la, lb, struct, flat, title):
    print(f"\n  {title}")
    print(f"    {'band':<12} {'STRUCT B/A':>11} {'rho':>7} {'A rms':>9} "
          f"{'FLAT B/A':>10} {'rho':>7} {'A rms':>9}")
    for f0, f1 in FINE:
        rs, hs, eas, _ = score(la, lb, f0, f1, struct)
        rf, hf, eaf, _ = score(la, lb, f0, f1, flat)
        print(f"    {f0:.2f}-{f1:.2f}    {rs:11.4f} {hs:7.4f} {eas:9.1f} "
              f"{rf:10.4f} {hf:7.4f} {eaf:9.1f}")


def main():
    A, B, label = sys.argv[1], sys.argv[2], sys.argv[3]
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    if la.shape != lb.shape:
        raise SystemExit(f"shape mismatch {la.shape} {lb.shape}")

    sel = gaussian_filter(np.abs(radial(la, SEL_LO, SEL_HI)), 3.0)
    struct = sel >= np.percentile(sel, 75)
    flat = sel < np.percentile(sel, 25)

    print(f"== SPECTRUM {label}")
    print(f"   A={A}\n   B={B}")
    print(f"   median={np.median(la):.0f}  clip%={100*(la>=65000).mean():.3f}  "
          f"black%={100*(la<=200).mean():.3f}  "
          f"struct px={struct.sum()/struct.size:.3f} flat px={flat.sum()/flat.size:.3f}")

    h, w = la.shape
    c = la[h//2-1024:h//2+1024, w//2-1024:w//2+1024]
    ms = np.ones(c.shape, bool)
    rng = np.random.default_rng(7)
    print("   -- CONTROLS --")
    bad = []
    for f0, f1 in FINE:
        n = score(c, c.copy(), f0, f1, ms)[0]
        if abs(n - 1.0) > 1e-9:
            bad.append((f0, n))
    print(f"   C0 NULL   max|R-1| over 10 bands = "
          f"{max(abs(score(c, c.copy(), f0, f1, ms)[0]-1) for f0, f1 in FINE):.2e}  "
          f"{'PASS' if not bad else 'FAIL ' + str(bad)}")
    cb = gaussian_filter(c, 1.0)
    rb = [score(c, cb, f0, f1, ms)[0] for f0, f1 in FINE]
    ok = rb[-1] < rb[4] < 1.0
    print(f"   C1 BLUR   sigma 1.0: " + " ".join(f"{x:.3f}" for x in rb) +
          f"   {'PASS' if ok else 'FAIL'} (must fall, worse with freq)")
    cn = c + rng.normal(0, 200, c.shape).astype(np.float32)
    rn = [score(c, cn, f0, f1, ms)[0] for f0, f1 in FINE]
    ok2 = rn[-1] > rn[4] > 1.0
    print(f"   C2 NOISE  sd 200 DN: " + " ".join(f"{x:.3f}" for x in rn) +
          f"   {'PASS' if ok2 else 'FAIL'} (must rise, worse with freq)")

    table(la, lb, struct, flat, "B / A  by band and site")


if __name__ == "__main__":
    main()

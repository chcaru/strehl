"""V-KILLB0 decile probe -- the direct test of the SELF-TARGETING claim.

The claim is that the knob is inert where real structure dominates and active
where noise dominates, "because coefficients sit far above the floor when
signal is present and just above it when it is not".

That is a claim about a CONTINUUM, and it makes a sharp prediction: the
fine-band ratio must be a MONOTONE INCREASING function of how structured the
pixel is, running from strongly < 1 at the noise end to ~1 at the structure
end, and it must never dip BELOW the flat-region value in between.  If real
low-contrast texture is being eaten, the middle deciles fall below 1 while the
top decile does not, and the top-decile-only test the orchestrator ran cannot
see it.

Pixels are ranked by a structure selector taken from the DEFAULT arm at
0.05-0.17 cyc/px -- a band both arms agree on to within a few per cent on every
subject measured, so the ranking is very nearly arm-independent, and in any
case identical pixels are scored in both arms.

CONTROLS (run on every invocation):
  C0 NULL  arm against itself -> every decile exactly 1.000000
  C1 BLUR  planted gaussian sigma 0.55 -> EVERY decile must fall, including the
           top one.  This is the shape a real softening makes: uniform.
  C2 NOISE planted white noise removal -> the LOW deciles fall and the top
           decile does not.  This is the shape a real grain win makes.
  The two planted shapes are printed beside the measured one, so the reader can
  see which of them the arm resembles instead of taking a verdict on trust.
"""
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

import bandprobe as bp

NDEC = 10


def deciles(la, lb, sel=None):
    if sel is None:
        sel = gaussian_filter(np.abs(gaussian_filter(la, 1.5)
                                     - gaussian_filter(la, 4.0)), 2.0)
    fa = la - gaussian_filter(la, 0.6366)
    fb = lb - gaussian_filter(lb, 0.6366)
    edges = np.percentile(sel, np.linspace(0, 100, NDEC + 1))
    out = []
    for i in range(NDEC):
        m = (sel >= edges[i]) & (sel < edges[i + 1]) if i < NDEC - 1 else (sel >= edges[i])
        if m.sum() < 1000:
            out.append(np.nan)
            continue
        ra = np.sqrt((fa[m] ** 2).mean())
        rb = np.sqrt((fb[m] ** 2).mean())
        out.append(rb / ra if ra > 0 else np.nan)
    return np.array(out), sel


def main():
    A, B, label = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "")
    la = bp.channels(bp.load(A))["L"]
    lb = bp.channels(bp.load(B))["L"]
    assert la.shape == lb.shape
    h, w = la.shape
    sub = la[h // 2 - 1024:h // 2 + 1024, w // 2 - 1024:w // 2 + 1024]

    rng = np.random.default_rng(23)
    nul, _ = deciles(sub, sub.copy())
    blur, _ = deciles(sub, gaussian_filter(sub, 0.55))
    dn, _ = deciles(sub + rng.normal(0, 300.0, sub.shape), sub)
    c0 = np.all(nul == 1.0)
    c1 = np.all(blur < 0.97)
    c2 = dn[-1] > 0.97 and dn[0] < 0.95
    print(f"== DECILES {label}")
    print(f"  [C0 NULL   ] all deciles 1.000000: {'PASS' if c0 else 'FAIL'}")
    print(f"  [C1 BLUR   ] planted sigma 0.55 -- shape of a real softening:")
    print("               " + " ".join(f"{v:6.3f}" for v in blur)
          + f"   {'PASS' if c1 else 'FAIL'} (every decile must fall)")
    print(f"  [C2 DENOISE] planted noise removal -- shape of a real grain win:")
    print("               " + " ".join(f"{v:6.3f}" for v in dn)
          + f"   {'PASS' if c2 else 'FAIL'} (top decile must not fall)")
    if not (c0 and c1 and c2):
        print("  INSTRUMENT NOT COMMISSIONED -- results below are void")

    meas, sel = deciles(la, lb)
    print("  decile:      " + " ".join(f"{i+1:>6d}" for i in range(NDEC))
          + "   <- 1 = least structured")
    print("  MEASURED:    " + " ".join(f"{v:6.3f}" for v in meas))
    mono = np.all(np.diff(meas) > -0.02)
    dip = np.nanmin(meas[3:])
    print(f"  monotone increasing (tol 0.02): {mono};  min of deciles 4-10 = {dip:.4f}"
          f";  top decile = {meas[-1]:.4f}")


if __name__ == "__main__":
    main()

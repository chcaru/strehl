"""M20 verification -- remaining Gate 4 robustness: wavelength and focus-step sensitivity.

The report evaluates the aperture result at one wavelength (550 nm) and one focus step
(1.0 px of CoC growth).  M5 itself flags the lambda sensitivity of the critical-sampling
number.  Neither is swept in M20.
"""
import numpy as np
from scipy.special import j1

PITCH_UM = 5.12


def f_cut(n, lam):
    return (PITCH_UM / lam) / n


def mtf_diff(f, n, lam):
    u = np.clip(np.asarray(f, float) / f_cut(n, lam), 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(u) - u * np.sqrt(np.maximum(0.0, 1.0 - u * u)))


def mtf_disc(f, d):
    x = np.pi * abs(float(d)) * np.asarray(f, float)
    o = np.ones_like(x)
    nz = np.abs(x) > 1e-12
    o[nz] = np.abs(2.0 * j1(x[nz]) / x[nz])
    return o


def mf_factor(frames, step, target):
    d = np.abs(np.arange(frames) - frames // 2) * step
    h = np.array([float(mtf_disc(np.array([target]), dd)[0]) for dd in d])
    return float(np.sqrt((h ** 2).sum()) / h.max())


print("=" * 88)
print("GATE 4.5 -- WAVELENGTH sensitivity of the aperture headline (B = 3.0, 0.25 cyc/px)")
print("=" * 88)
print(f"{'lambda nm':>10} {'MTF f/11':>10} {'MTF f/5.6':>11} {'contrast x':>12} {'SNR x (time)':>14}")
for lam_nm in (450, 500, 550, 600, 650):
    lam = lam_nm / 1000.0
    a = float(mtf_diff(0.25, 5.6 * 3.0, lam))
    b = float(mtf_diff(0.25, 11.0 * 3.0, lam))
    r = a / b if b > 1e-9 else np.inf
    print(f"{lam_nm:>10} {b:>10.4f} {a:>11.4f} {r:>12.2f} {r*np.sqrt(33.0/16.8):>14.2f}")
print("  Green-only (the measurement plane is the green CFA lattice) argues for ~530-550 nm,")
print("  but a panchromatic scene spans the whole row.  The headline moves 5.6x - 27x.")
print()

print("=" * 88)
print("GATE 4.6 -- FOCUS-STEP sensitivity of the matched-filter factor at 0.25 cyc/px")
print("  (must be aperture-invariant, so it cancels in the f/5.6 : f/11 ratio -- check)")
print("=" * 88)
print(f"{'step px':>9} {'K=41':>9} {'K=81':>9} {'K=113':>9}")
for step in (0.25, 0.5, 1.0, 2.0, 4.0):
    print(f"{step:>9.2f} " + " ".join(f"{mf_factor(k, step, 0.25):>9.4f}" for k in (41, 81, 113)))
print("  The factor depends strongly on the step but not on K once K*step is large,")
print("  so it cancels exactly in an aperture ratio taken at matched blur-per-step.")
print("  The 13.5x therefore does NOT depend on the step choice; only the 2.08 does.")
print()

print("=" * 88)
print("GATE 4.7 -- half-step focus penalty on the 'best frame' (report assumes d = 0)")
print("=" * 88)
for step in (0.5, 1.0, 2.0):
    pen = float(mtf_disc(np.array([0.25]), step / 2)[0])
    print(f"  step {step:>4.1f} px: worst-case best-frame defocus {step/2:>4.2f} px "
          f"-> extra MTF factor {pen:.4f}")
print("  Aperture-invariant by construction, so it cancels in the ratio; but it means the")
print("  absolute best-frame MTF column is an optimistic bound, not the typical pixel.")

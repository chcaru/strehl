"""Isolate why fit_shift is biased and why the cross arm broke the knee estimator.

Deliberately separates the two failures instead of patching both at once:
  A. is the phase-ramp fit biased, and by what?
  B. why does m5_lib.knee misbehave on a zero-mean floor?
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
M5 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "m5-diffraction")
sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402
import xspec as X  # noqa: E402

rng = np.random.default_rng(3)
n, tile = 256, 128

print("A. phase-ramp fit\n" + "-" * 60)

# A1: exact integer shift of a broadband field. No decimation, no band limit.
a = rng.normal(0, 100, (n + 8, n + 8))
p1 = a[0:n, 0:n]
p2 = a[1:n + 1, 2:n + 2]          # b[i,j] = a[i+1, j+2] -> shift (+1, +2)
cx = X.cross_psd2(p1, p2, tile, "hann")
print(f"A1 integer shift        fit {X.fit_shift(cx)}  planted (+1, +2)")

# A2: same, no window, to see whether the Hann window is responsible.
cx = X.cross_psd2(p1, p2, tile, "none")
print(f"A2 integer, no window   fit {X.fit_shift(cx)}  planted (+1, +2)")

# A3: half-sample shift of a properly band-limited field, built by construction
# in the Fourier domain so the shift is exact rather than approximated.
m = n
fu = np.fft.fftfreq(m)[:, None]
fv = np.fft.fftfreq(m)[None, :]
r = np.hypot(fu, fv)
amp = np.zeros((m, m))
amp[r > 0] = r[r > 0] ** -1.0
amp[r > 0.20] = 0.0                       # hard band limit well inside Nyquist
F = np.fft.fft2(rng.normal(size=(m, m))) * amp
s1 = np.real(np.fft.ifft2(F))
s2 = np.real(np.fft.ifft2(F * np.exp(2j * np.pi * (fu * 0.5 + fv * -0.5))))
cx = X.cross_psd2(s1, s2, tile, "hann")
print(f"A3 half shift, exact    fit {X.fit_shift(cx)}  planted (+0.5, -0.5)")

# A4: how much does the power-weighting cut-in matter?
for pf in (0.5, 0.1, 0.02, 0.001):
    print(f"   power_frac {pf:<6} -> {X.fit_shift(cx, power_frac=pf)}")

# A5: reproduce the original failing construction to confirm it is the TEST
# that was wrong, not the estimator.
def scene_old(nn, alpha, fc_lat, rr, oversample=2):
    mm = nn * oversample
    fu2 = np.fft.fftfreq(mm)[:, None]
    fv2 = np.fft.fftfreq(mm)[None, :]
    rr2 = np.hypot(fu2, fv2)
    a2 = np.zeros((mm, mm))
    a2[rr2 > 0] = rr2[rr2 > 0] ** (-alpha / 2.0)
    mtf = L.mtf_diffraction(rr2 * oversample, fc_lat)
    return np.real(np.fft.ifft2(np.fft.fft2(rr.normal(size=(mm, mm))) * a2 * mtf))

fine = scene_old(n, 2.0, 0.30, rng)
cx = X.cross_psd2(fine[0::2, 0::2], fine[1::2, 1::2], tile, "hann")
print(f"A5 old construction     fit {X.fit_shift(cx)}  planted (+0.5, +0.5)")

print("\nB. the knee estimator on a zero-mean floor\n" + "-" * 60)
sig = 300.0
nz = 60.0
s = np.real(np.fft.ifft2(np.fft.fft2(rng.normal(size=(n, n))) * amp))
s = s / s.std() * sig
v1 = s + rng.normal(0, nz, (n, n))
v2 = s + rng.normal(0, nz, (n, n))

fa, pa, ca = L.spectrum(v1, "G1", tile=tile, window="hann")
fx, px, cxo = X.cross_spectrum(v1, v2, tile=tile, window="hann")
top = fa >= 0.8 * fa[-1]
print(f"auto  floor band: mean {pa[top].mean():12.2f}  sd {pa[top].std():10.2f}")
print(f"cross floor band: mean {px[top].mean():12.2f}  sd {px[top].std():10.2f}")
print(f"cross negative bins in floor band: "
      f"{int((px[top] < 0).sum())}/{int(top.sum())}")
print("\nthe crossing rule tests p - N > z*sqrt(kappa)*N/sqrt(n): the threshold is")
print("PROPORTIONAL TO N, so a floor with mean near zero gives a threshold near")
print("zero and every bin is 'detected'. The rule needs a floor, and the cross")
print("spectrum's whole purpose is not to have one.")
ka = L.knee(fa, pa, ca, tile, n, "G1")
kx = L.knee(fx, px, cxo, tile, n, "G1")
print(f"\nauto  f_c {ka.get('f_c')}   floor {ka.get('floor')}")
print(f"cross f_c {kx.get('f_c')}   floor {kx.get('floor')}")

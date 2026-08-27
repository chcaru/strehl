"""What band does my statistic actually integrate over?

Do NOT trust the analytic DoG peak: selftest.py already proved that
scipy.ndimage.gaussian_filter's sampled, truncated kernel departs badly from
the continuous Gaussian at small sigma (2.64x in energy at sigma=0.35).  So
measure the REAL transfer function of dog() by its impulse response, and
report the measured peak and half-power edges.

Frequency is reported per OUTPUT pixel of the gauge, and then converted to
per SENSOR PHOTOSITE.  The linear gauge is 3516x2344 and the sensor is
7032x4688, exactly 2x2 binning (one output pixel = one Bayer quad), so
cyc/photosite = cyc/output-px / 2.  The sRGB gauge is 7032x4688, i.e. 1:1
with the photosite grid, which is why its sigmas are doubled.
"""
import numpy as np, softcheck as S

def transfer(sig, n=256):
    d = np.zeros((n, n), np.float32); d[n//2, n//2] = 1.0
    h = S.dog(d, sig)
    H = np.abs(np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(h))))**2
    fy = np.fft.fftshift(np.fft.fftfreq(n)); fx = fy
    R = np.hypot(*np.meshgrid(fy, fx, indexing="ij"))
    edges = np.linspace(0, 0.5, 129); ctr = 0.5*(edges[1:]+edges[:-1])
    prof = np.array([H[(R>=a)&(R<b)].mean() if ((R>=a)&(R<b)).any() else 0
                     for a, b in zip(edges[:-1], edges[1:])])
    pk = prof.argmax(); half = prof[pk]/2.0
    lo = next((ctr[i] for i in range(pk, -1, -1) if prof[i] < half), ctr[0])
    hi = next((ctr[i] for i in range(pk, len(prof)) if prof[i] < half), ctr[-1])
    ana2 = np.log(sig[1]**2/sig[0]**2)/(2*np.pi**2*(sig[1]**2-sig[0]**2))
    return ctr[pk], lo, hi, np.sqrt(ana2), float((prof*ctr).sum()/prof.sum())

for gauge, binf, probes in (
        ("linear gauge (3516x2344, 2x2 binned, 1 px = 1 Bayer quad)", 2.0,
         [("E_mid  STATISTIC", S.S_MID), ("E_hi   noise proxy", S.S_HI), ("E_lo   tile selector", S.S_LOW)]),
        ("sRGB gauge (7032x4688, 1:1 with photosites)", 1.0,
         [("E_mid  STATISTIC", (1.4,2.8)), ("E_hi   noise proxy", (0.7,1.4)), ("E_lo   tile selector", (6.0,12.0))])):
    print(f"\n{gauge}")
    print(f"  {'probe':22s} {'sigma':>12s} {'peak c/opx':>11s} {'half-power band c/opx':>23s}"
          f" {'peak c/photosite':>17s} {'analytic peak':>14s}")
    for name, sg in probes:
        pk, lo, hi, ana, cen = transfer(sg)
        print(f"  {name:22s} {str(sg):>12s} {pk:11.4f} {'['+format(lo,'.4f')+', '+format(hi,'.4f')+']':>23s}"
              f" {pk/binf:17.4f} {ana:14.4f}")
print("\nNyquist is 0.5 cyc/output-px (= 0.25 cyc/photosite on the binned linear gauge).")
print("The statistic IS band-limited: E_mid is a difference of two Gaussians, so it is")
print("zero at DC and rolls off above its peak.  It is not a full-buffer variance.")

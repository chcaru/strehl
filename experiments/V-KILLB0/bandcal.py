"""V-KILLB0 band-label commissioning.

ORCH correction #4 was itself a frequency-arithmetic error (0.5/sigma used
where 1/(2*pi*sigma) was correct).  So before re-qualifying anything against
V-LINEAR's per-subject boundaries I measure what MY OWN filters actually pass,
by feeding in sinusoids of known frequency and reading the response, rather
than trusting the closed form or the labels I wrote in the source.

Any label that disagrees with the measured half-power edges by more than 15% is
reported as WRONG, and every number I derived from that filter is suspect.
"""
import numpy as np
from scipy.ndimage import gaussian_filter

N = 512
FILTERS = {
    "fine  (hp sigma 0.6366)  labelled 0.25-0.50": lambda x: x - gaussian_filter(x, 0.6366),
    "band  (1.2732,2.0)       labelled 0.17-0.25": lambda x: gaussian_filter(x, 1.2732) - gaussian_filter(x, 2.0),
    "band  (2.0,8.0)          labelled 0.05-0.17": lambda x: gaussian_filter(x, 2.0) - gaussian_filter(x, 8.0),
    "band  (8.0,16.0)         labelled 0.02-0.05": lambda x: gaussian_filter(x, 8.0) - gaussian_filter(x, 16.0),
    "sel   (1.5,4.0)          structure selector": lambda x: gaussian_filter(x, 1.5) - gaussian_filter(x, 4.0),
}
freqs = np.concatenate([np.linspace(0.005, 0.10, 20), np.linspace(0.105, 0.50, 40)])
yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)

print(f"{'filter':<46} {'peak':>7} {'f_lo(half-pow)':>15} {'f_hi(half-pow)':>15}")
for name, f in FILTERS.items():
    resp = []
    for fr in freqs:
        img = np.sin(2 * np.pi * fr * xx)
        resp.append(np.sqrt((f(img)[64:-64, 64:-64] ** 2).mean()) * np.sqrt(2))
    resp = np.array(resp)
    pk = resp.max()
    half = resp >= pk / np.sqrt(2)
    lo, hi = freqs[half][0], freqs[half][-1]
    print(f"{name:<46} {pk:7.3f} {lo:15.3f} {hi:15.3f}")

print()
print("closed form for reference, cutoff of a gaussian blur = 1/(2*pi*sigma):")
for s in (0.6366, 1.2732, 2.0, 4.0, 8.0, 16.0):
    print(f"   sigma {s:7.4f} -> {1/(2*np.pi*s):.4f} cyc/px")

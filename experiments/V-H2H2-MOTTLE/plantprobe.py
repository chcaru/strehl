"""Probe the plant's OWN spectrum before using it to certify anything.

The commissioning arm is only a probe of the gauge if the plant is where I claim it
is. Twice in this lane a plant has been believed rather than measured: once built at
radii 90/360 while the gauge measured 25/200, and once normalised before the gauge
band-passed it a second time. So the plant gets measured on its own, with no image
under it, and the numbers printed are the gauge's response to the plant alone.

`atten` is the ratio of the field's raw sigma to the sigma the gauge actually sees.
A large value means the plant must be scaled up hard to register, and that inflated
field is what leaks into neighbouring bands and into the gradient statistic.
"""
import numpy as np
from scipy.ndimage import gaussian_filter

from bandlib import BANDS, boxblur

rng = np.random.default_rng(1)
w = rng.normal(0.0, 1.0, (400, 400)).astype(np.float32)

print("%-18s %8s %8s  %s" % ("plant", "raw sd", "atten", "  ".join("%8s" % b for b, _, _ in BANDS)))
for s1, s2 in [(20 / 3, 60 / 3), (11, 24), (8, 16), (14, 28), (11, 40), (16, 32)]:
    p = (gaussian_filter(w, s1) - gaussian_filter(w, s2)).astype(np.float32)
    seen = float(np.std(boxblur(p, 10) - boxblur(p, 30)))
    p = p / seen
    raw = float(np.std(p))
    prof = [float(np.std(boxblur(p, lo // 2) - boxblur(p, hi // 2))) for _, lo, hi in BANDS]
    grad = float(np.mean(np.abs(np.diff(p, axis=0))[:, :-1] + np.abs(np.diff(p, axis=1))[:-1, :]))
    print("%-18s %8.3f %8.3f  %s   grad %.4f"
          % ("dog %.1f/%.1f" % (s1, s2), raw, raw / 1.0,
             "  ".join("%8.3f" % v for v in prof), grad))

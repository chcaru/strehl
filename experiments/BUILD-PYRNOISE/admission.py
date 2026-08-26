"""Is this ROI actually FLAT? A pre-registered admission test for the noise ROI.

The whole flat-ROI protocol assumes the region carries noise and nothing else.
That assumption is never checked in the corpus -- the ROI is chosen by a
low-high-pass-energy argmin and then trusted. On the 22-frame bracket that
happens to be fine. On a 182-frame focus sweep it is catastrophically false:
a region that looks smooth in every individual frame can be smooth for
DIFFERENT REASONS in each frame (it is out of focus in most of them), so the
merged arm legitimately contains structure the single frame does not, and the
"noise" ratio reads that structure as noise. The arm that recovered the most
real detail then LOSES hardest, which is exactly backwards.

THE TEST. Take the same ROI in every single unstacked frame. For pixel-level
noise and nothing else, two independent estimates of the same quantity must
agree:

  temporal  -- sd across frames at a fixed pixel, averaged over pixels
  spatial   -- sd of (x - box9 x) within one frame, averaged over frames

Both estimate the per-pixel noise sd. Their ratio is 1.00 for a stationary
region. It rises above 1 when the scene at that pixel CHANGES from frame to
frame -- focus breathing, drift, moving content -- which is precisely the
condition that invalidates the flat-ROI statistic.

ADMISSION BAR, fixed here before any subject was scored: temporal/spatial <=
1.30. Chosen because the two estimators differ by construction even on pure
noise (the spatial one is high-passed and de-biased, the temporal one is not),
and 1.30 leaves room for that while still rejecting a region whose content
moves. A subject that fails does not get a published noise row.

DIRECTION OF FAILURE. The test cannot make a bad ROI look good: any real
non-stationarity adds variance to the temporal estimate only. It CAN fail a
good ROI if the frames are misregistered, so a failure is reported as "not
stationary across the bracket", without claiming to separate focus from drift.
"""

import numpy as np

import pyrnoise as pn


BAR = 1.30


def admission(imgs, frames, roi):
    """Returns (ratio, temporal_sd, spatial_sd, passed)."""
    stack = np.stack([pn.crop(imgs[f], roi) for f in frames]).astype(np.float64)
    temporal = float(stack.std(axis=0, ddof=1).mean())
    spatial = float(np.mean([pn.hp_sd(pn.crop(imgs[f], roi, pn.BOX)) for f in frames]))
    ratio = temporal / spatial
    return ratio, temporal, spatial, ratio <= BAR


def report(imgs, frames, roi, label=""):
    r, t, s, ok = admission(imgs, frames, roi)
    print(f"FLAT-ROI ADMISSION {label:<12}: temporal {t:8.3f} DN / spatial {s:8.3f} DN "
          f"= {r:6.3f}   bar {BAR:.2f}   {'PASS' if ok else 'FAIL -- region is not '
          'stationary across the bracket; no noise row for this subject'}")
    return ok, r

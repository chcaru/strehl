"""Band-resolved mottle gauge with a MATCHED ARM, and the blur trap as a commissioning arm.

WHY THIS EXISTS RATHER THAN mottle.py. Section 10's dose-response is measured on
orch_blotch's band, which its own docstring states as 50-400 px. ORCH has since
measured, on the exact 400 px his 1:1 verdict was formed on, that the band we lose
to `enfuse` is 20-60 px, and that we win the 1 px grain band by 2.19x. Those are
different bands. A ceiling measured at 50-400 px does not bound a defect at 20-60 px,
so this re-poses the question on a LADDER of bands and lets the band profile itself
be the evidence.

CONSTRUCTION, and what each piece is defending against.

  MATCHED ARM, ALWAYS. experiments/ORCH-drift-check/orch_mottle_visual.py is a
  refuted instrument that ranked subjects by how much mid-scale CONTENT their
  flattest region held -- it lit up the vein network of a leaf and produced a
  confirming ordering that meant nothing. Its own verdict on itself: "The defence
  is not a better band or a better site rule, it is the RATIO TO SOURCE." So every
  number here is a ratio between two arms on THE SAME PIXELS, and the gauge refuses
  to report an absolute band figure on its own.

  DISPLAY STATE, from ORCH's transform. The comparator target 4.812/4.963/6.488 is
  in 8-bit display codes after exposure and a per-channel gain/offset fit. Measuring
  in a different state would produce a number that cannot be compared to it. The
  transform is copied from orch_eye_check.py deliberately, including its shape
  assertion.

  PHOTOMETRIC FIT. Arms are brought onto the reference's scale by a per-channel
  least-squares gain+offset on the crop, which is what the published manifest's
  `fits` do. Without it a brighter arm reads as a noisier one.

  INTEGER-ONLY SHIFTS. Registration between arms is integer, never sub-pixel:
  resampling adds blur to the very quantity being measured.

  SHARPNESS ON THE SAME PIXELS AS EVERY BAND NUMBER. `focus-stack` reads 0.077
  grain and 0.260 mid on this site, 10-25x below both other arms -- that is not a
  clean photograph, it is a smoothed one, and it is consistent with our resolving
  1.326x more than it does. Any fix can therefore "win" the mid band by blurring.
  So `blur` is a commissioning ARM, and it must be REFUSED rather than credited.

  A DEFECT ARM AND AN IMPROVEMENT ARM. A suite of degradations cannot distinguish a
  statistic that is blind to a defect from one that is perverse on it. This project
  shipped a sharpness statistic bounded below by zero, which could never charge for
  a halo, precisely because every commissioning arm had been a degradation.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "ORCH-drift-check"))

CROP = 400
MC_DIR = pathlib.Path(r"C:\dev\strehl-out\V-H2H2\mottle")
ARMS = pathlib.Path(r"C:\dev\strehl-out\V-NOISE2\119\arms")
MANIFEST = pathlib.Path(r"C:\dev\strehl-out\DELIVER-V5\vs-the-field\manifest-119MSDCF.json")

# (label, lo_px, hi_px). 20-60 is ORCH's measured band; 50-400 is section 10's.
BANDS = [("5-15", 5, 15), ("10-30", 10, 30), ("20-60", 20, 60),
         ("40-120", 40, 120), ("100-300", 100, 300), ("50-400", 50, 400)]

# A band gain is only credited if the FINE detail survives it. `focus-stack` improves
# the mid band by 0.879 while taking the 5-15 band to 0.434 and sharpness to 0.468 --
# that is smoothing, not cleaning. A genuine mid-band repair moves the mid band and
# leaves fine detail alone.
#
# TWO tests are needed, not one, and the second was added only after the real
# `focus-stack` render defeated the first. Selectivity is a RATIO of bands, so an arm
# that attenuates EVERY band by the same factor cancels in it: focus-stack reads
# 0.044/0.041/0.042/0.046 across the ladder, a uniform 23x reduction, and scored
# selectivity 1.05 -- comfortably "not smoothed" -- while being the most smoothed
# render in the corpus. The commissioning blur arm never caught it because a box blur
# leaves the mid band at 0.852 and crushes only the fine bands, which is a different
# shape of damage. An absolute detail floor is therefore carried alongside the ratio.
SMOOTH_TOL = 0.75
DETAIL_TOL = 0.80
TRADE_TOL = 1.30


def verdict(ref, arm):
    """Compare arm to ref on the SAME pixels. Returns ratios, selectivity and flags.

    smoothed  the arm bought its mid-band number with detail. Fires on EITHER an
              absolute collapse of 1 px sharpness (catches a uniform reduction) or a
              low selectivity (catches damage concentrated in the fine bands).
    traded    the arm's fine-scale energy is far above the reference's relative to its
              mid band. This is the upward direction, carried because a guard that can
              only fire on smoothing is bounded on one side, and this project has
              already shipped a sharpness statistic that could never charge for a halo.
              It fires on an unsharp mask and it fires on `enfuse`, which wins the mid
              band while carrying 2.19x our fine grain -- both are real trades, and
              neither is a free win.
    """
    rs = float(np.mean(arm["sharp"] / np.maximum(ref["sharp"], 1e-9)))
    out = {"sharp": rs}
    for label, _, _ in BANDS:
        out[label] = float(np.mean(arm[label] / np.maximum(ref[label], 1e-9)))
    out["grain"] = float(np.mean(arm["grain"] / np.maximum(ref["grain"], 1e-9)))
    mid = max(out["20-60"], 1e-9)
    fine = max(out["5-15"], rs)
    out["selectivity"] = min(out["5-15"], rs) / mid
    out["lost_detail"] = rs < DETAIL_TOL
    out["smoothed"] = out["lost_detail"] or out["selectivity"] < SMOOTH_TOL
    out["fine_excess"] = fine / mid
    out["traded"] = out["fine_excess"] > TRADE_TOL and fine > 1.1
    return out


def call(v, band="20-60"):
    r = v[band]
    if v["smoothed"]:
        return "REFUSED smoothed (sharp %.3f, sel %.2f)" % (v["sharp"], v["selectivity"])
    if v["traded"]:
        return "traded x%.3f (fine %.2fx the mid gain)" % (r, v["fine_excess"])
    if r < 0.98:
        return "improved x%.3f" % r
    if r > 1.02:
        return "worse x%.3f" % r
    return "level x%.3f" % r


def boxblur(a, r):
    """Separable running-sum box mean. Copied from orch_eye_check.py WITH its shape
    assertion: ORCH's earlier copy returned an array one row and one column short,
    silently, and only broke when two blurs of different radius were differenced
    against the original -- which is exactly what the band term does here."""
    if r < 1:
        return a
    k = 2 * r + 1
    p = np.pad(a, ((r, r), (0, 0)), mode="reflect")
    c = np.concatenate([np.zeros((1, p.shape[1]), a.dtype), np.cumsum(p, axis=0)], axis=0)
    o = (c[k:] - c[:-k]) / k
    p = np.pad(o, ((0, 0), (r, r)), mode="reflect")
    c = np.concatenate([np.zeros((p.shape[0], 1), a.dtype), np.cumsum(p, axis=1)], axis=1)
    o = (c[:, k:] - c[:, :-k]) / k
    assert o.shape == a.shape, f"boxblur changed shape {a.shape} -> {o.shape}"
    return o


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def display(c16, expo):
    """16-bit linear -> 8-bit display codes. ORCH's display(): the pixels that reach an eye."""
    return srgb(np.clip(c16 / 65535.0 * expo, 0.0, 1.0)) * 255.0


def fit_to(ref16, arm16):
    """Per-channel gain matching the arm's MEAN to the reference's. No offset term.

    Two fits were tried and both were functions of the thing being measured:

      least squares  gain = cov(a,r)/var(a), so uncorrelated energy shrinks the arm.
                     The mid-band plant arrived reading 0.972 in the 5-15 band.
      percentiles    p5/p95 spread widens with added variance, so it shrank harder --
                     the DEFECT arm scored 0.967 and was reported as an IMPROVEMENT.
                     A photometric normaliser that turns a planted defect into a win
                     is the most dangerous single component this gauge could have had.

    Every disturbance this gauge must survive -- mottle, grain, blur, unsharp halo --
    is zero-mean, so it cannot move a mean-ratio gain at all. That is decoupling by
    construction rather than by tolerance, and commissioning still asserts it.

    Assumes arms differ by gain and not by an additive black-level offset, which holds
    for arms from one binary on one subject where only --auto-exposure's per-image gain
    varies. It is NOT assumed for the comparator arms: those use the published
    manifest's own gain and offset.
    """
    g = np.ones(3, np.float32)
    for ch in range(3):
        ma = float(np.mean(arm16[..., ch]))
        mr = float(np.mean(ref16[..., ch]))
        if ma > 0:
            g[ch] = mr / ma
    return g, np.zeros(3, np.float32)


def terms(disp):
    """Per-channel band sigmas + grain + sharpness, all in display codes.

    Sharpness is mean |gradient|, which a blur lowers. It is reported for EVERY band
    number so that a band improvement bought by smoothing is visible as one.
    """
    out = {}
    for label, lo, hi in BANDS:
        v = [float(np.std(boxblur(disp[..., ch], lo // 2) - boxblur(disp[..., ch], hi // 2)))
             for ch in range(3)]
        out[label] = np.array(v)
    out["grain"] = np.array([float(np.std(disp[..., ch] - boxblur(disp[..., ch], 1)))
                             for ch in range(3)])
    sh = []
    for ch in range(3):
        p = disp[..., ch]
        sh.append(float(np.mean(np.abs(np.diff(p, axis=0))[:, :-1]
                                + np.abs(np.diff(p, axis=1))[:-1, :])))
    out["sharp"] = np.array(sh)
    return out

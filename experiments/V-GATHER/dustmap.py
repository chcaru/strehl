r"""Build the sensor defect map from dark frames. READ-ONLY on D:\.

A hot pixel is a property of the SENSOR, not of any one exposure. It is
therefore defined here by CONSISTENCY across independent darks rather than by
amplitude in any single one: a cosmic-ray hit, a read-noise outlier and a hot
pixel all look identical in one frame, and only the hot pixel recurs at the same
photosite in the next. `n_hit` counts the darks in which a site exceeds the
local threshold, and only sites hitting in nearly all of them are kept.

The comparison is WITHIN A BAYER PHASE. The mosaic means a site's four nearest
neighbours are different colour channels with different black levels and
different dark current, so a plain 3x3 median mixes phases and manufactures
excess at every site. Each phase is extracted on its own 2-strided lattice and
compared only against its own kind.
"""
import glob
import io
import json
import os

import numpy as np
import rawpy
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
DARKS = r"D:\macro-dark-frames"
OUT = os.path.join(HERE, "defectmap.json")
NDARK = 48
EXCESS_DN = 48.0
HIT_FRAC = 0.90
TOPN = 600
MAD_K = 8.0


def phase_planes(a):
    return {(dy, dx): a[dy::2, dx::2] for dy in (0, 1) for dx in (0, 1)}


def main():
    dk = sorted(glob.glob(os.path.join(DARKS, "**", "*.ARW"), recursive=True))
    if not dk:
        raise SystemExit("POSITIVE CONTROL FAILED: no darks found under " + DARKS)
    print("%d darks available; using %d" % (len(dk), NDARK))
    step = max(1, len(dk) // NDARK)
    use = dk[::step][:NDARK]

    hits = None
    amp = None
    shape = None
    for i, f in enumerate(use):
        with rawpy.imread(f) as r:
            a = r.raw_image_visible.astype(np.float32)
        if hits is None:
            shape = a.shape
            hits = np.zeros(shape, np.int16)
            amp = np.zeros(shape, np.float32)
        for (dy, dx), pl in phase_planes(a).items():
            med = ndimage.median_filter(pl, size=3, mode="nearest")
            ex = pl - med
            hits[dy::2, dx::2] += (ex > EXCESS_DN).astype(np.int16)
            amp[dy::2, dx::2] += ex
        if (i + 1) % 8 == 0:
            print("  %d/%d" % (i + 1, len(use)))
    amp /= len(use)

    # SELECT ON MEAN EXCESS, NOT ON A PER-FRAME HIT COUNT.
    # The per-frame criterion (excess > 48 DN in >= 90% of darks) returned ZERO
    # sites, and zero is ambiguous between "this sensor is clean" and "this
    # threshold is unreachable". dustreach.py measured the query's reach and
    # settled it: at 48 DN the answer really is 0, but at 16 DN it is 2, and the
    # single-frame excess distribution tops out at 78 DN at the 99.99th
    # percentile. The sensor is genuinely very clean, and a per-frame threshold
    # high enough to beat read noise in ONE dark is therefore too high to find
    # what little is there.
    #
    # The mean over N darks suppresses read noise by sqrt(N) while leaving a
    # fixed offset untouched, which is exactly the discrimination wanted. The cut
    # is placed at MAD_K robust sigmas of the mean-excess map itself, so it is
    # derived from the measured noise of this statistic on this sensor rather
    # than typed.
    need = int(round(HIT_FRAC * len(use)))
    med = float(np.median(amp))
    mad = float(np.median(np.abs(amp - med)))
    sig = 1.4826 * mad
    cut = med + MAD_K * sig
    print("per-frame criterion (excess>%.0fDN in >=%d/%d darks) finds %d sites"
          % (EXCESS_DN, need, len(use), int((hits >= need).sum())))
    print("mean-excess map: median %.3f DN, robust sigma %.3f DN, cut %.3f DN"
          % (med, sig, cut))
    ys, xs = np.nonzero(amp > cut)
    print("sites above %.1f sigma of mean excess: %d" % (MAD_K, len(ys)))
    if len(ys) == 0:
        raise SystemExit("NO DEFECTS FOUND -- the map would be vacuous; refusing "
                         "to write a defect map with nothing in it")
    order = np.argsort(-amp[ys, xs])
    ys, xs = ys[order][:TOPN], xs[order][:TOPN]
    doc = {"n_darks": len(use), "raw_shape": list(shape), "excess_dn": EXCESS_DN,
           "hit_frac": HIT_FRAC, "need_hits": need, "mad_k": MAD_K,
           "cut_dn": cut, "robust_sigma_dn": sig,
           "n_perframe_sites": int((hits >= need).sum()),
           "n_sites_total": int((amp > cut).sum()),
           "y": ys.tolist(), "x": xs.tolist(),
           "amp": [float(v) for v in amp[ys, xs]]}
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
    print("kept top %d by mean excess: %.1f .. %.1f DN"
          % (len(ys), doc["amp"][-1], doc["amp"][0]))
    print("wrote " + OUT)


if __name__ == "__main__":
    main()

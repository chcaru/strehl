r"""Build the DUST map from flat fields. READ-ONLY on D:\.

WHY NOT FROM THE DARKS. The darks were the right asset for hot pixels and they
answered: this sensor has ~3 persistent hot photosites, at an amplitude whose
99.99th percentile is 78 DN. Three sites cannot support a statistical detector,
so the dust axis speaks from flats instead -- which is the correct asset anyway,
because dust sits on the sensor stack rather than in the photosites and is
therefore MULTIPLICATIVE and invisible in a dark frame.

A dust mote is a localised ATTENUATION. Dividing each flat by a heavily smoothed
copy of itself removes vignetting and any illumination gradient, both of which
are smooth by construction, and leaves the localised part. As with the hot
pixels, a mote is defined by RECURRENCE across independent flats -- a shadow in
one flat could be anything; a shadow at the same coordinate in every flat is on
the glass.

Phases are kept separate for the same reason as in `dustmap.py`: a smoothing
kernel that crosses the Bayer mosaic mixes channels and manufactures structure.
"""
import glob
import io
import json
import os

import numpy as np
import rawpy
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
FLATS = r"D:\personal\macro\flat-fields\flat-fields"
OUT = os.path.join(HERE, "dustmap.json")
NFLAT = 24
SMOOTH = 64.0
DEPTH = 0.01
# A flat is only a flat at a level where the measurement is above its own shot
# noise. The first build of this map drew every 15th file, landed on flats
# sitting 171 DN above black, and found 178 "motes" of which 174 were 1-3 px --
# single photosites, i.e. PRNU, not dust. At 171 DN shot noise alone is ~7.6%,
# seven times the depth cut, so the cut was measuring noise that happened to
# recur at fixed sites. The campaign does contain usable flats: levels run to
# 15871 DN, which is the clipping ceiling, so the window excludes both the dim
# end and the saturated end and is applied by MEASURING each candidate rather
# than by trusting filename order.
LEVEL_LO, LEVEL_HI = 3000.0, 14000.0
MIN_MOTE_PX = 12
HIT_FRAC = 0.90
TOPN = 400


def main():
    ff = sorted(glob.glob(os.path.join(FLATS, "*.ARW")))
    if not ff:
        raise SystemExit("POSITIVE CONTROL FAILED: no flats under " + FLATS)
    use, levels = [], []
    for f in ff:
        with rawpy.imread(f) as r:
            lv = float(np.median(r.raw_image_visible[1000:1400, 2000:2400])) - 512.0
        if LEVEL_LO <= lv <= LEVEL_HI:
            use.append(f)
            levels.append(lv)
        if len(use) >= NFLAT:
            break
    if len(use) < 8:
        raise SystemExit("ONLY %d FLATS IN [%.0f,%.0f] DN -- refusing to build a "
                         "dust map on flats that cannot beat their own shot noise"
                         % (len(use), LEVEL_LO, LEVEL_HI))
    print("%d flats available; using %d at %.0f..%.0f DN above black"
          % (len(ff), len(use), min(levels), max(levels)))

    hits = None
    depth = None
    for i, f in enumerate(use):
        with rawpy.imread(f) as r:
            a = r.raw_image_visible.astype(np.float32) - 512.0
        if hits is None:
            hits = np.zeros(a.shape, np.int16)
            depth = np.zeros(a.shape, np.float32)
            print("flat median level %.0f DN above black" % np.median(a))
        for dy in (0, 1):
            for dx in (0, 1):
                pl = a[dy::2, dx::2]
                sm = ndimage.gaussian_filter(pl, SMOOTH, mode="nearest")
                rel = pl / np.maximum(sm, 1.0)
                hits[dy::2, dx::2] += (rel < 1.0 - DEPTH).astype(np.int16)
                depth[dy::2, dx::2] += 1.0 - rel
        if (i + 1) % 8 == 0:
            print("  %d/%d" % (i + 1, len(use)))
    depth /= len(use)

    need = int(round(HIT_FRAC * len(use)))
    mask = hits >= need
    print("sites attenuated >%.0f%% in >=%d/%d flats: %d"
          % (100 * DEPTH, need, len(use), int(mask.sum())))
    if not mask.any():
        raise SystemExit("NO DUST FOUND -- refusing to write a vacuous map")

    lab, n = ndimage.label(mask)
    print("connected motes: %d" % n)
    cy, cx, dp, sz = [], [], [], []
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        m = lab[sl] == i
        if m.sum() < MIN_MOTE_PX:
            continue
        yy, xx = np.nonzero(m)
        cy.append(int(sl[0].start + yy.mean()))
        cx.append(int(sl[1].start + xx.mean()))
        dp.append(float(depth[sl][m].mean()))
        sz.append(int(m.sum()))
    order = np.argsort(-np.array(dp))[:TOPN]
    doc = {"n_flats": len(use), "raw_shape": list(hits.shape), "depth_cut": DEPTH,
           "need_hits": need, "smooth": SMOOTH, "n_motes_total": int(n),
           "y": [cy[i] for i in order], "x": [cx[i] for i in order],
           "depth": [dp[i] for i in order], "size": [sz[i] for i in order]}
    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
    if not doc["y"]:
        raise SystemExit("NO MOTE >= %d px -- what recurs on this sensor is "
                         "single-photosite PRNU, not dust" % MIN_MOTE_PX)
    print("kept %d motes >=%dpx: depth %.3f..%.3f, size %d..%d px"
          % (len(doc["y"]), MIN_MOTE_PX, min(doc["depth"]), max(doc["depth"]),
             min(doc["size"]), max(doc["size"])))
    print("SUPPRESSED "
          % ()) if False else None
    print("wrote " + OUT)
    return


def _unused():
    print("kept %d motes >=4px: depth %.3f..%.3f, size %d..%d px"
          % (len(doc["y"]), min(doc["depth"]), max(doc["depth"]),
             min(doc["size"]), max(doc["size"])))
    print("wrote " + OUT)


if __name__ == "__main__":
    main()

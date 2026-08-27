r"""Does the master's ELEVATED RELATIVE CHROMA survive being made as soft as the
frames it is compared against?

The gate's chroma statistic band-passes a/Y and b/Y at 50-300 px.  A Gaussian
blur of sigma <= 8 px cannot remove 50-300 px structure -- so anything it does
to the reading comes through the DENOMINATOR, Y, which blur raises (it fills
shadows, and the sRGB encode is concave).

EXPERIMENT, entirely inside one image, no registration, no strehl code: blur the
MASTER's own chroma window by sigma = 0..10 px and watch (mean Y, relative,
absolute).  Then read off the sigma at which the blurred master's mean Y equals
the source frames' median mean Y -- i.e. the point where it is as soft as they
are -- and compare relative chroma THERE.

  ACQUIT if, at matched mean Y, the master reads at or below the frames.
  CONVICT if it still reads above them: then the excess is not the 1/Y term.

  python vr_blurtest.py SUBJECT
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from vr_chroma2 import stats                                  # noqa: E402


def srgb_decode(v):
    """16-bit sRGB -> linear.  Blurring an ALREADY ENCODED image is mean-preserving
    and reproduces nothing: optical defocus happens in LINEAR light and the
    concave encode is applied afterwards.  The first version of this test blurred
    in the encoded domain, moved the window mean by 0.003%, and proved nothing;
    it is kept in the record as a failed control."""
    x = np.asarray(v, np.float32) / 65535.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def srgb_encode(l):
    l = np.clip(np.asarray(l, np.float32), 0, None)
    v = np.where(l <= 0.0031308, 12.92 * l, 1.055 * np.power(l, 1 / 2.4) - 0.055)
    return (np.clip(v, 0, 1) * 65535.0).astype(np.float32)


def srgb_decode(v):
    """16-bit sRGB -> linear.  Blurring an ALREADY ENCODED image is mean-preserving
    and reproduces nothing: optical defocus happens in LINEAR light and the
    concave encode is applied afterwards.  The first version of this test blurred
    in the encoded domain, moved the window mean by 0.003%, and proved nothing;
    it is kept in the record as a failed control."""
    x = np.asarray(v, np.float32) / 65535.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4).astype(np.float32)


def srgb_encode(l):
    l = np.clip(np.asarray(l, np.float32), 0, None)
    v = np.where(l <= 0.0031308, 12.92 * l, 1.055 * np.power(l, 1 / 2.4) - 0.055)
    return (np.clip(v, 0, 1) * 65535.0).astype(np.float32)


def main():
    subj = sys.argv[1]
    cache = os.path.join(V.OUT, "cache_%s" % subj)
    ks = sorted(int(f[1:5]) for f in os.listdir(cache) if f.startswith("c"))
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    cw = (S["master"]["chroma"]["y"], S["master"]["chroma"]["x"])
    mrgb = V.read_rgb(V.master_path(subj))[cw[0]:cw[0] + V.CWIN,
                                           cw[1]:cw[1] + V.CWIN].astype(np.float32)
    fr = [stats(np.load(os.path.join(cache, "c%04d.npy" % k))) for k in ks]
    fy = float(np.median([r["meanY"] for r in fr]))
    frel = [r["rel"] for r in fr]
    print("SUBJECT %s  chroma window %r   %d source frames" % (subj, cw, len(fr)))
    print("frames: mean Y median %.1f (%.1f..%.1f)   relative %.6f..%.6f (med %.6f)"
          % (fy, min(r["meanY"] for r in fr), max(r["meanY"] for r in fr),
             min(frel), max(frel), float(np.median(frel))))
    print("%8s %10s %10s %10s" % ("sigma", "meanY", "relative", "absDN"))
    prev = None
    hit = None
    for sg in [0, 1, 2, 3, 4, 5, 6, 8, 10]:
        img = mrgb if sg == 0 else srgb_encode(cv2.GaussianBlur(srgb_decode(mrgb), (0, 0), sg))
        r = stats(img)
        print("%8.1f %10.1f %10.6f %10.2f%s"
              % (sg, r["meanY"], r["rel"], r["abs"],
                 "   <- master as shipped" if sg == 0 else ""))
        if prev and hit is None and prev[1]["meanY"] <= fy <= r["meanY"]:
            t = (fy - prev[1]["meanY"]) / max(r["meanY"] - prev[1]["meanY"], 1e-9)
            hit = (prev[0] + t * (sg - prev[0]), prev[1]["rel"] + t * (r["rel"] - prev[1]["rel"]))
        prev = (sg, r)
    if hit:
        print("AT MATCHED MEAN Y (sigma %.2f): master relative %.6f   vs frames median "
              "%.6f  max %.6f  ->  %.3fx median, %.3fx max"
              % (hit[0], hit[1], float(np.median(frel)), max(frel),
                 hit[1] / float(np.median(frel)), hit[1] / max(frel)))
    else:
        print("mean Y never reached the frames' median within sigma<=10: INCONCLUSIVE")


if __name__ == "__main__":
    main()

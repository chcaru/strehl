r"""Chroma, with the 1/Y amplification separated out.

The gate's chroma statistic is band-pass energy of RELATIVE chroma, (R-Y)/Y and
(B-Y)/Y.  Dividing by Y is what makes it survive a tone SCALE (section 99's
lesson).  It does not make it survive a change in SHARPNESS: an all-in-focus
master has deeper darks than a defocused frame (blur fills shadows), and 1/Y is
convex, so the same colour error in DN reads larger in the master.

So measure both, on the same cached windows, in the same tone domain (same
binary, same flags, same exposure, same sRGB encode -- that is what the
single-frame source arm is for):

  RELATIVE  the gate's own number, hypot(rms a/Y, rms b/Y)          [gate units]
  ABSOLUTE  the same band-pass on (R-Y) and (B-Y) in DN, no division  [DN]
  and the window's mean and 5th-percentile Y, which is the term that differs.

  python vr_chroma2.py SUBJECT
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from orch_chroma import boxblur, relative_chroma, LO_R, HI_R  # noqa: E402


def stats(rgb):
    a, b, y = relative_chroma(rgb)
    m = HI_R
    out = {}
    ba = boxblur(a, LO_R) - boxblur(a, HI_R)
    bb = boxblur(b, LO_R) - boxblur(b, HI_R)
    out["rel"] = float(np.hypot(np.sqrt(np.mean(ba[m:-m, m:-m] ** 2)),
                                np.sqrt(np.mean(bb[m:-m, m:-m] ** 2))))
    A = np.asarray(rgb, np.float64)[..., 0] - y
    B = np.asarray(rgb, np.float64)[..., 2] - y
    ca = boxblur(A, LO_R) - boxblur(A, HI_R)
    cb = boxblur(B, LO_R) - boxblur(B, HI_R)
    out["abs"] = float(np.hypot(np.sqrt(np.mean(ca[m:-m, m:-m] ** 2)),
                                np.sqrt(np.mean(cb[m:-m, m:-m] ** 2))))
    out["meanY"] = float(np.mean(y))
    out["p5Y"] = float(np.percentile(y, 5))
    out["invY"] = float(np.mean(1.0 / y))
    return out


def main():
    subj = sys.argv[1]
    cache = os.path.join(V.OUT, "cache_%s" % subj)
    ks = sorted(int(f[1:5]) for f in os.listdir(cache) if f.startswith("c"))
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    cw = (S["master"]["chroma"]["y"], S["master"]["chroma"]["x"])
    mrgb = V.read_rgb(V.master_path(subj))[cw[0]:cw[0] + V.CWIN, cw[1]:cw[1] + V.CWIN]
    print("SUBJECT %s  chroma window %r" % (subj, cw))
    print("%-22s %10s %10s %10s %10s %11s" % ("ARM", "relative", "absDN", "meanY",
                                              "p5 Y", "mean 1/Y"))
    m = stats(mrgb)
    print("%-22s %10.6f %10.2f %10.1f %10.1f %11.3e"
          % ("MASTER", m["rel"], m["abs"], m["meanY"], m["p5Y"], m["invY"]))
    rows = []
    for k in ks:
        r = stats(np.load(os.path.join(cache, "c%04d.npy" % k)))
        rows.append((k, r))
    for k, r in rows:
        print("%-22s %10.6f %10.2f %10.1f %10.1f %11.3e"
              % ("  frame %d" % k, r["rel"], r["abs"], r["meanY"], r["p5Y"], r["invY"]))
    for nm, f in (("max", max), ("median", lambda v: float(np.median(v))), ("min", min)):
        print("%-22s %10.6f %10.2f %10.1f %10.1f %11.3e"
              % ("frames " + nm, f([r["rel"] for _, r in rows]), f([r["abs"] for _, r in rows]),
                 f([r["meanY"] for _, r in rows]), f([r["p5Y"] for _, r in rows]),
                 f([r["invY"] for _, r in rows])))
    # Does the master sit ON the frames' own line?  If the elevated relative
    # chroma is the 1/Y amplification of a darker (sharper) render, then across
    # the frames themselves relative chroma must track mean(1/Y), and the
    # master must be the darkest point on the SAME line -- not a point above it.
    x = np.array([r["invY"] for _, r in rows])
    yv = np.array([r["rel"] for _, r in rows])
    b1, b0 = np.polyfit(x, yv, 1)
    pred = b0 + b1 * m["invY"]
    resid = yv - (b0 + b1 * x)
    sd = float(np.std(resid))
    print("frames' own line   relative = %.6f + %.4g * mean(1/Y)   r=%.3f  scatter %.6f"
          % (b0, b1, float(np.corrcoef(x, yv)[0, 1]), sd))
    print("MASTER predicted from ITS OWN mean(1/Y): %.6f   measured %.6f   "
          "miss %+.6f = %+.1f%% = %+.1f frame-scatters"
          % (pred, m["rel"], m["rel"] - pred, 100 * (m["rel"] - pred) / pred,
             (m["rel"] - pred) / max(sd, 1e-12)))
    # Does the master sit ON the frames' own line?  If the elevated relative
    # chroma is the 1/Y amplification of a darker (sharper) render, then across
    # the frames themselves relative chroma must track mean(1/Y), and the
    # master must be the darkest point on the SAME line -- not a point above it.
    x = np.array([r["invY"] for _, r in rows])
    yv = np.array([r["rel"] for _, r in rows])
    b1, b0 = np.polyfit(x, yv, 1)
    pred = b0 + b1 * m["invY"]
    resid = yv - (b0 + b1 * x)
    sd = float(np.std(resid))
    print("frames' own line   relative = %.6f + %.4g * mean(1/Y)   r=%.3f  scatter %.6f"
          % (b0, b1, float(np.corrcoef(x, yv)[0, 1]), sd))
    print("MASTER predicted from ITS OWN mean(1/Y): %.6f   measured %.6f   "
          "miss %+.6f = %+.1f%% = %+.1f frame-scatters"
          % (pred, m["rel"], m["rel"] - pred, 100 * (m["rel"] - pred) / pred,
             (m["rel"] - pred) / max(sd, 1e-12)))
    print("RATIO master/frames-max   relative %.3f   absolute %.3f"
          % (m["rel"] / max(r["rel"] for _, r in rows),
             m["abs"] / max(r["abs"] for _, r in rows)))


if __name__ == "__main__":
    main()

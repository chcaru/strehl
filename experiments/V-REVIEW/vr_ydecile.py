r"""WHERE does the master's extra relative chroma live?

(R-Y)/Y is invariant to a per-pixel gain on all three channels, so "the master is
darker" cannot by itself change it -- that objection kills the naive 1/Y story
and is why the blur control could not close the gap.  What CAN change it is
WEIGHTING: the same colour structure in DN reads larger in a/Y wherever Y is
small, and an all-in-focus master has genuinely deeper shadows than a defocused
frame (measured: 112MSDCF p5 Y master 9166 vs frame 13393).

So bin the window by LOCAL luminance (boxblur(Y,50), master's own deciles, the
same bins for both arms since they are registered) and report the band-passed
a/Y, b/Y rms per bin.

  INHERITED  the excess is concentrated in the darkest bins and vanishes in the
             bright ones -- the merge is not adding colour, the statistic is
             weighting the subject's colour by a deeper shadow.
  MANUFACTURED  a mottle laid down by the merge has no reason to respect the
             subject's luminance; the excess is flat across bins.
The planted control (--plant) is exactly such a mottle and shows what flat looks
like.

  python vr_ydecile.py SUBJECT [--plant=0.17]
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from orch_blotch import boxblur as bb3, NOISE_R               # noqa: E402
from orch_chroma import boxblur, relative_chroma, LO_R, HI_R  # noqa: E402


def bands(rgb):
    a, b, y = relative_chroma(rgb)
    return (boxblur(a, LO_R) - boxblur(a, HI_R),
            boxblur(b, LO_R) - boxblur(b, HI_R), y)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    subj = args[0]
    cache = os.path.join(V.OUT, "cache_%s" % subj)
    ks = sorted(int(f[1:5]) for f in os.listdir(cache) if f.startswith("c"))
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    cw = (S["master"]["chroma"]["y"], S["master"]["chroma"]["x"])
    M = V.read_rgb(V.master_path(subj))[cw[0]:cw[0] + V.CWIN,
                                        cw[1]:cw[1] + V.CWIN].astype(np.float32)
    if "plant" in opts:
        rng = np.random.default_rng(3)
        L = V.lum_of(M)
        sig = float(np.std(L - bb3(L, NOISE_R)))
        c = rng.normal(0, 1, (V.CWIN // 64 + 2, V.CWIN // 64 + 2)).astype(np.float32)
        f = cv2.resize(c, (V.CWIN, V.CWIN), interpolation=cv2.INTER_LINEAR)
        f = (f - f.mean()) / max(float(np.std(f)), 1e-6) * float(opts["plant"]) * sig
        M = M.copy()
        M[..., 0] += f
        M[..., 2] -= f
        print("POSITIVE CONTROL: planted chroma mottle +-%.1f DN" % (float(opts["plant"]) * sig))
    # the frame that reads highest on the gate's chroma, for a like-for-like fight
    best, bestv = None, -1
    for k in ks:
        w = np.load(os.path.join(cache, "c%04d.npy" % k))
        v = V.gate_chroma(w, at=(0, 0))["chroma"]
        if v > bestv:
            best, bestv = k, v
    F = np.load(os.path.join(cache, "c%04d.npy" % best))
    ma, mb, my = bands(M)
    fa, fb, fy = bands(F)
    m = HI_R
    sl = (slice(m, -m), slice(m, -m))
    yl = boxblur(my, 50)[sl]
    yf = boxblur(fy, 50)[sl]
    edges = np.percentile(yl, np.arange(0, 101, 10))
    print("SUBJECT %s   window %r   master vs frame %d (highest-reading frame, %.6f)"
          % (subj, cw, best, bestv))
    print("master p5 Y %.0f  frame p5 Y %.0f   master mean Y %.0f  frame mean Y %.0f"
          % (np.percentile(my, 5), np.percentile(fy, 5), my.mean(), fy.mean()))
    print("%6s %12s %10s %10s %8s %8s" % ("decile", "local Y", "master", "frame",
                                          "ratio", "share%"))
    tm = float(np.mean(ma[sl] ** 2 + mb[sl] ** 2))
    for i in range(10):
        sel = (yl >= edges[i]) & (yl <= edges[i + 1])
        if sel.sum() < 100:
            continue
        vm = float(np.sqrt(np.mean(ma[sl][sel] ** 2 + mb[sl][sel] ** 2)))
        vf = float(np.sqrt(np.mean(fa[sl][sel] ** 2 + fb[sl][sel] ** 2)))
        share = 100 * float(np.mean(ma[sl][sel] ** 2 + mb[sl][sel] ** 2)) * sel.mean() / tm
        ym = float(np.mean(yl[sel]))
        yfm = float(np.mean(yf[sel]))
        print("%6d %9.0f %9.0f %9.6f %9.6f %7.3f %7.3f %7.1f"
              % (i + 1, ym, yfm, vm, vf, vm / max(vf, 1e-12), yfm / max(ym, 1e-9), share))
    print("WHOLE  %12s %10.6f %10.6f %8.3f"
          % ("", float(np.sqrt(np.mean(ma[sl] ** 2 + mb[sl] ** 2))),
             float(np.sqrt(np.mean(fa[sl] ** 2 + fb[sl] ** 2))),
             float(np.sqrt(np.mean(ma[sl] ** 2 + mb[sl] ** 2))
                   / np.sqrt(np.mean(fa[sl] ** 2 + fb[sl] ** 2)))))


if __name__ == "__main__":
    main()

r"""THE ENVELOPE TEST -- the assumption-free version of "did the merge invent it".

A focus stacker chooses, at each site, among the frames it was given.  Whatever
rule it uses, the result at a pixel should lie between the smallest and the
largest value its inputs offered there.  So band-pass every registered frame,
build the per-pixel envelope [min_k, max_k], and ask what fraction of the
master's band field lies OUTSIDE it, and by how much.

This needs no model of the merge, no assumption about focus, and no tone
argument (every arm is the same binary, same flags, same exposure, same encode).

THE NULL IT IS SCORED AGAINST: a real frame is not inside the envelope of the
others either -- its own noise pushes it out.  So the same number is computed
LEAVE-ONE-OUT for every frame, and the master is compared against that
distribution.  A master that sits inside the frames' own spread is not inventing
anything.  --plant lays a mottle into the master as the positive control.

  python vr_envelope.py SUBJECT [--plant=1.0]
"""
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from orch_blotch import boxblur, LO_R, HI_R, NOISE_R          # noqa: E402


def band_rel(rgb):
    blk = V.lum_of(rgb)
    return (boxblur(blk, LO_R // 2) - boxblur(blk, HI_R // 2)) / max(float(np.mean(blk)), 1e-9)


def outside(B, lo, hi, sd):
    over = np.maximum(B - hi, 0)
    under = np.maximum(lo - B, 0)
    d = over + under
    return 100.0 * float(np.mean(d > 0)), float(np.mean(d)) / sd, float(np.max(d)) / sd


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    subj = args[0]
    cache = os.path.join(V.OUT, "cache_%s" % subj)
    ks = sorted(int(f[1:5]) for f in os.listdir(cache) if f.startswith("b"))
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    bw = (S["master"]["blotch"]["y"], S["master"]["blotch"]["x"])
    M = V.read_rgb(V.master_path(subj))[bw[0]:bw[0] + V.BWIN,
                                        bw[1]:bw[1] + V.BWIN].astype(np.float32)
    if "plant" in opts:
        rng = np.random.default_rng(3)
        blk = V.lum_of(M)
        sig = float(np.std(blk - boxblur(blk, NOISE_R)))
        c = rng.normal(0, 1, (V.BWIN // 64 + 2, V.BWIN // 64 + 2)).astype(np.float32)
        f = cv2.resize(c, (V.BWIN, V.BWIN), interpolation=cv2.INTER_LINEAR)
        f = (f - f.mean()) / max(float(np.std(f)), 1e-6) * float(opts["plant"]) * sig
        M = M + f[..., None]
        print("POSITIVE CONTROL: planted %.1f sigma (%.0f DN) blotch" % (float(opts["plant"]), float(opts["plant"]) * sig))
    Bm = band_rel(M)
    Bs = np.stack([band_rel(np.load(os.path.join(cache, "b%04d.npy" % k))) for k in ks])
    sd = float(np.std(Bm))
    lo, hi = Bs.min(axis=0), Bs.max(axis=0)
    print("SUBJECT %s  window %r  %d frames  master band sd %.5f  envelope width "
          "mean %.5f" % (subj, bw, len(ks), sd, float(np.mean(hi - lo))))
    p, mx, wx = outside(Bm, lo, hi, sd)
    print("MASTER            outside %6.2f%% of pixels   mean excess %.4f sd   worst %.3f sd"
          % (p, mx, wx))
    nulls = []
    for i, k in enumerate(ks):
        o = np.delete(np.arange(len(ks)), i)
        l2, h2 = Bs[o].min(axis=0), Bs[o].max(axis=0)
        pp, mm, ww = outside(Bs[i], l2, h2, sd)
        nulls.append((pp, mm, ww))
        print("  frame %4d (LOO)  outside %6.2f%% of pixels   mean excess %.4f sd   "
              "worst %.3f sd" % (k, pp, mm, ww))
    a = np.array(nulls)
    print("LEAVE-ONE-OUT NULL   outside %.2f..%.2f%% (med %.2f)   mean excess med %.4f sd"
          % (a[:, 0].min(), a[:, 0].max(), np.median(a[:, 0]), np.median(a[:, 1])))
    # HOW MUCH OF THIS IS SUBSAMPLING?  The envelope is built from a SUBSET of
    # the bracket; the master was built from all of it.  A thinner envelope is
    # narrower, so this test is biased toward conviction and the bias must be
    # measured, not asserted.  Thin the envelope and watch.
    for step in (4, 2, 1):
        sel = np.arange(0, len(ks), step)
        if len(sel) < 3:
            continue
        l2, h2 = Bs[sel].min(axis=0), Bs[sel].max(axis=0)
        pp, mm, ww = outside(Bm, l2, h2, sd)
        print("  envelope from %2d of %d frames: master outside %6.2f%%  mean excess %.4f sd"
              % (len(sel), len(ks), pp, mm))
    # HOW MUCH OF THIS IS SUBSAMPLING?  The envelope is built from a SUBSET of
    # the bracket; the master was built from all of it.  A thinner envelope is
    # narrower, so this test is biased toward conviction and the bias must be
    # measured, not asserted.  Thin the envelope and watch.
    for step in (4, 2, 1):
        sel = np.arange(0, len(ks), step)
        if len(sel) < 3:
            continue
        l2, h2 = Bs[sel].min(axis=0), Bs[sel].max(axis=0)
        pp, mm, ww = outside(Bm, l2, h2, sd)
        print("  envelope from %2d of %d frames: master outside %6.2f%%  mean excess %.4f sd"
              % (len(sel), len(ks), pp, mm))
    print("VERDICT INPUT: master %.2f%% vs null median %.2f%% -> %.2fx ; "
          "excess %.4f vs %.4f sd"
          % (p, np.median(a[:, 0]), p / max(np.median(a[:, 0]), 1e-9), mx, np.median(a[:, 1])))


if __name__ == "__main__":
    main()

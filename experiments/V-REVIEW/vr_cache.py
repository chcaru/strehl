r"""Recompute the independent-composite arms FROM THE CACHE, printing the two
terms of the gate's ratio separately.

vr_indep.py's hard composites read BELOW every input frame (112MSDCF: hard60
0.0879 against singles 0.110-0.140).  A per-pixel selection among frames cannot
lower the band amplitude below all of them, so the movement must be in the
DENOMINATOR: blotch = std(band)/mean(window), and a per-pixel argmax over N
noisy frames biases the window mean upward (max-of-N).  This prints band_dn and
mean_dn for every arm so the reader can see which term moved, instead of quoting
a ratio whose mechanism I had not established.

  python vr_cache.py SUBJECT
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from vr_indep import compose                                  # noqa: E402


def main():
    subj = sys.argv[1]
    cache = os.path.join(V.OUT, "cache_%s" % subj)
    ks = sorted(int(f[1:5]) for f in os.listdir(cache) if f.startswith("b"))
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    ms = S["master"]
    mrgb = V.read_rgb(V.master_path(subj))
    bw = (ms["blotch"]["y"], ms["blotch"]["x"])
    cw = (ms["chroma"]["y"], ms["chroma"]["x"])
    mb = V.blotch_ratio(V.lum_of(mrgb[bw[0]:bw[0] + V.BWIN, bw[1]:bw[1] + V.BWIN]))
    mc = V.gate_chroma(mrgb[cw[0]:cw[0] + V.CWIN, cw[1]:cw[1] + V.CWIN], at=(0, 0))
    del mrgb
    print("SUBJECT %s  cache frames %s" % (subj, ks))
    print("%-24s %9s %9s %9s   %9s" % ("ARM", "blotch", "band_DN", "mean_DN", "chroma"))
    print("%-24s %9.5f %9.1f %9.1f   %9.6f"
          % ("MASTER", mb[0], mb[1], mb[3], mc["chroma"]))
    sb = [np.load(os.path.join(cache, "b%04d.npy" % k)) for k in ks]
    sc = [np.load(os.path.join(cache, "c%04d.npy" % k)) for k in ks]
    rows = []
    for k, a, c in zip(ks, sb, sc):
        r = V.blotch_ratio(V.lum_of(a))
        rows.append((r[0], r[1], r[3], V.gate_chroma(c, at=(0, 0))["chroma"], k))
    best = max(rows)
    print("%-24s %9.5f %9.1f %9.1f   %9.6f" % ("best single frame", best[0], best[1],
                                               best[2], max(r[3] for r in rows)))
    print("%-24s %9.5f %9.1f %9.1f   %9.6f"
          % ("  (median frame)", float(np.median([r[0] for r in rows])),
             float(np.median([r[1] for r in rows])), float(np.median([r[2] for r in rows])),
             float(np.median([r[3] for r in rows]))))
    for rule in ("mean", "soft60", "hard60", "soft15", "hard15"):
        cb = compose(sb, rule)
        cc = compose(sc, rule)
        r = V.blotch_ratio(V.lum_of(cb))
        print("%-24s %9.5f %9.1f %9.1f   %9.6f"
              % ("INDEPENDENT " + rule, r[0], r[1], r[3],
                 V.gate_chroma(cc, at=(0, 0))["chroma"]))


if __name__ == "__main__":
    main()

r"""Decisive control on the rho(corrected, n_sel) = -0.716 confound.

The five largest rim readings are all on subjects with the fewest isolated
edges. Two explanations are compatible with that and they have opposite
consequences:

  (A) SAMPLE SIZE. The statistic is biased upward when computed over few edges,
      as this project's earlier `min`-over-frames ratio was biased upward when
      computed over few frames. If so the large readings are an artifact and
      must be discarded.

  (B) SUBJECT TYPE. Few isolated edges means few large high-contrast occluding
      features against smooth ground -- which is precisely the geometry where a
      halo forms and is visible. If so the correlation is causal in the honest
      direction and the readings stand.

These are separable by experiment rather than by argument. Take a subject with
many edges and a known reading, draw random subsets of the SAME edges at the
sample sizes of the small-n subjects, and re-measure. Under (A) the reading
climbs as n falls. Under (B) it stays put and only its spread widens.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-H2H2-RIMCLIP")))
import rimv6                                                       # noqa: E402
import rimaxis                                                     # noqa: E402

SIZES = [72, 112, 244, 334, 600, 1200]
REPS = 24


def run(sub):
    p = os.path.join(rimaxis.SEAL_DIR, sub + "--SHIP-V4.tiff")
    a = tifffile.imread(p)
    g = rimaxis.lum_of(a)
    clip = (a.max(axis=2) >= 65535) | (a.min(axis=2) <= 0)
    del a
    rois = rimaxis.pick_rois(g, clip)
    ref, sel, n_all, cut, fl = rimaxis.select_for(g, clip, rois)
    full = rimaxis.measure_arm(g, sel)
    base = full["resid_bright"] - fl["resid_bright"]
    print("\n%s: full n=%d -> corrected %+.3f%%" % (sub, len(sel), 100 * base))
    print("   %6s %10s %10s %10s" % ("n", "mean", "sd", "P(> +5%)"))
    rng = np.random.default_rng(17)
    for n in SIZES:
        if n > len(sel):
            continue
        vals = []
        for _ in range(REPS):
            i = rng.choice(len(sel), n, replace=False)
            sub_sel = [sel[j] for j in i]
            r = rimaxis.measure_arm(g, sub_sel)
            if r is None:
                continue
            nn = rimv6.try_null(rimv6.edge_width(rimv6.measure(g, sub_sel, rimaxis.T)))
            if nn is None:
                continue
            vals.append(r["bright"] - nn[0] - fl["resid_bright"])
        v = np.array(vals)
        print("   %6d %+9.3f%% %9.3f%% %9.0f%%"
              % (n, 100 * v.mean(), 100 * v.std(), 100 * (v > 0.05).mean()))
    return base


for s in sys.argv[1:] or ["bee-1-cpl", "119MSDCF"]:
    run(s)

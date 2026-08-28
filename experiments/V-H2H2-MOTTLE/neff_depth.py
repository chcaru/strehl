# Does participation grow with frame count? The dilution mechanism, measured.
#
# The mechanism relayed to ORCH says the winner's normalised share is
#
#     share = 1 / (1 + SUM_{k != winner} (e_k/e_winner)^p)
#
# and that the sum runs over N-1 terms, so a deeper stack dilutes the winner
# and softens the merge. In fc3f9aa7 I falsified the model's neglect of its own
# zero-clamp: frames under `gate * beta * var` contribute EXACTLY zero, so
# participation is set by depth-of-field over focus step, not by N.
#
# The two make opposite, quantitative predictions about n_eff:
#
#   DILUTION REAL      n_eff grows roughly in proportion to F.
#                      n_eff(182)/n_eff(22) ~ 8.3
#   CLAMP BOUNDS IT    n_eff is roughly constant in absolute terms.
#                      n_eff(182)/n_eff(22) ~ 1
#
# Nobody in this argument has measured it. Both dumps come from ONE binary in
# ONE session with identical flags, so the frame count is the only difference
# that matters.

import glob
import json
import os
import re
import sys

import numpy as np

D = r"C:\dev\strehl-out\V-H2H2\wdump"
ARMS = [("m109", 22), ("leaf2", 182)]


def band_neff(prefix, k):
    """n_eff per coefficient, from the dump if present, else from conc.

    `conc` = max(w)/sum(w) is NOT n_eff and the file warns it has null value
    1/frames. It is used only as a fallback and the caller is told which.
    """
    p = os.path.join(D, "%s-b%d-neff.f32" % (prefix, k))
    if os.path.exists(p):
        return np.fromfile(p, np.float32), "neff"
    p = os.path.join(D, "%s-b%d-conc.f32" % (prefix, k))
    if os.path.exists(p):
        return np.fromfile(p, np.float32), "conc"
    return None, None


def summarise(prefix, frames):
    out = {}
    for k in range(8):
        v, kind = band_neff(prefix, k)
        if v is None:
            continue
        live = np.isfinite(v) & (v > 0)
        if not live.any():
            continue
        out[k] = (float(v[live].mean()), kind, int(live.sum()), int(v.size))
    return out


def main():
    data = {}
    for prefix, frames in ARMS:
        s = summarise(prefix, frames)
        if not s:
            print("no dump for %s in %s" % (prefix, D))
            return 2
        data[prefix] = s
        kinds = {v[1] for v in s.values()}
        print("%-8s F=%-4d bands=%s  statistic=%s"
              % (prefix, frames, sorted(s), ",".join(sorted(kinds))))

    # Refuse to compare two different statistics. `conc` and `neff` are not the
    # same quantity and a ratio across them is meaningless.
    kinds = {v[1] for s in data.values() for v in s.values()}
    if len(kinds) > 1:
        print("\nREFUSED: the two arms dumped different statistics %s." % sorted(kinds))
        print("`conc` is max(w)/sum(w) with null value 1/frames; `n_eff` is")
        print("sum(w)^2/sum(w^2). Comparing them across frame counts is exactly")
        print("the error pyramid.rs:2016-2020 warns about. Re-render the missing arm.")
        return 1

    (pa, fa), (pb, fb) = ARMS
    common = sorted(set(data[pa]) & set(data[pb]))
    print("\n%-6s %12s %12s %10s %10s" % ("band", "n_eff F=%d" % fa,
                                          "n_eff F=%d" % fb, "ratio", "F ratio"))
    fr = fb / fa
    ratios = []
    for k in common:
        a = data[pa][k][0]
        b = data[pb][k][0]
        r = b / a if a else float("nan")
        ratios.append(r)
        print("%-6d %12.2f %12.2f %10.2f %10.2f" % (k, a, b, r, fr))

    fine = [r for k, r in zip(common, ratios) if k <= 3]
    print("\n  frame-count ratio            %.2f" % fr)
    print("  mean n_eff ratio, bands 0-3  %.2f" % (sum(fine) / len(fine)))
    print("""
  DILUTION REAL would predict a ratio near %.1f at every band.
  CLAMP-BOUNDED would predict a ratio near 1.0.
""" % fr)

    m = sum(fine) / len(fine)
    if m > 0.6 * fr:
        verdict = ("SUPPORTS DILUTION: participation grows roughly with the "
                   "frame count.")
    elif m < 2.0:
        verdict = ("REFUTES DILUTION at the fine bands: participation is nearly "
                   "independent of frame count, which is what the zero-clamp "
                   "predicts and what the relayed model omitted.")
    else:
        verdict = ("PARTIAL: participation grows with depth but far more slowly "
                   "than the frame count, so dilution is at most a fraction of "
                   "the effect.")
    print("  %s" % verdict)
    print("""
  CAVEAT, stated because it limits the claim: these are two DIFFERENT
  SUBJECTS, not one subject decimated. 109MSDCF and leaf-2-cpl differ in
  focus travel, texture and contrast, and any of those moves n_eff. The
  clean experiment is one subject rendered at F and at F/8 by decimating
  its own frame list. This measurement is a strong prior, not a proof, and
  it should be repeated that way before anything is built on it.
""")
    json.dump({p: {str(k): v[0] for k, v in s.items()} for p, s in data.items()},
              open(os.path.join(D, "neff_by_frames.json"), "w"), indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

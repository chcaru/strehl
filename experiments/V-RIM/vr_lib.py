r"""V-RIM shared helpers: run the UNMODIFIED rimaxis/rimv6 pipeline on any file,
and add the ONE diagnostic rimv6 does not compute -- coherence.

WHY COHERENCE. rimv6 reports MEDIAN over edges of ( MAX over t in +2..+7 of q ).
A max over 6 samples of a zero-mean fluctuation is positive by construction, so
the statistic has a strictly positive bias whose size is set by how rough the
bright shoulder is, not by whether a rim exists. Reversing the order --
MAX over t of ( MEDIAN over edges of q ) -- averages an incoherent fluctuation
away across hundreds of edges while leaving a real rim, which is coherent along
the edge, untouched. Same pixels, same normalisation, same selection: the only
difference is the order of the two reductions, so a gap between them is a
property of the statistic and not of what was sampled.

Nothing in rimaxis.py or rimv6.py is modified or re-implemented here; both are
imported and called.
"""
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(ROOT, "V-GATHER"))
sys.path.insert(0, os.path.join(ROOT, "V-H2H2-RIMCLIP"))
import rimaxis                                                     # noqa: E402
import rimv6                                                       # noqa: E402

SHIP = r"C:\dev\strehl-out\acceptance\SHIP-V4"
DELIV = r"C:\dev\strehl-out\ORCH-FAITHFUL\faithful"
SCRATCH = r"D:\strehl-out\V-RIM"


def read_lum(path, crop=None):
    a = tifffile.imread(path)
    if crop is not None:
        y, x, h, w = crop
        a = a[y:y + h, x:x + w]
    g = rimaxis.lum_of(a)
    clip = (a.max(axis=2) >= 65535) | (a.min(axis=2) <= 0)
    del a
    return g, clip


def coherence(e):
    """Both reductions on the SAME profile array.

    max_then_median  -- what rimv6 reports.
    median_then_max  -- the same quantity with the reductions swapped.
    shoulder_sd      -- per-edge sd of q over t=+2..+7 about that edge's own
                        mean there; the driver of the max-of-6 bias.
    predicted_bias   -- E[max of 6 iid N(0,s)] = 1.2672*s, evaluated at the
                        median shoulder sd. This is what a rim-FREE edge with
                        this much shoulder roughness reads by construction.
    """
    if e is None or not len(e["prof"]):
        return None
    P = e["prof"]                                    # (n_edges, 25)
    ib = rimv6.IB
    med = np.median(P, axis=0)
    sh = P[:, ib]
    sd = sh.std(axis=1, ddof=1)
    return dict(
        max_then_median=float(np.median(sh.max(axis=1) - 1.0)),
        median_then_max=float(med[ib].max() - 1.0),
        median_profile=[float(v) for v in med],
        shoulder_sd_median=float(np.median(sd)),
        predicted_bias=float(1.2672 * np.median(sd)),
        n=int(P.shape[0]),
    )


def run_pipeline(g, clip, ntile=rimaxis.NTILE):
    """rimaxis.run_subject, but returning the intermediates as well."""
    rois = rimaxis.pick_rois(g, clip, n=ntile)
    ref, sel, n_all, cut, fl = rimaxis.select_for(g, clip, rois)
    out = dict(n_sel=len(sel), n_candidates=n_all, n_rois=len(rois), cut=cut,
               isolated_frac=(len(sel) / n_all) if n_all else 0.0)
    if len(sel) < rimaxis.NMIN or fl is None:
        out["refused"] = "no cut leaves %d isolated edges in range" % rimaxis.NMIN
        return out, sel, ref, None
    if abs(fl["resid_bright"]) > rimaxis.FLOOR_MAX:
        out["floor"] = fl
        out["refused"] = "floor %+.3f%% exceeds %.1f%%" % (
            100 * fl["resid_bright"], 100 * rimaxis.FLOOR_MAX)
        return out, sel, ref, None
    em = rimv6.measure(g, sel, rimaxis.T)
    m = rimaxis.measure_arm(g, sel)
    out["master"], out["floor"] = m, fl
    if m is None:
        out["refused"] = "edge width outside the null table"
        return out, sel, ref, em
    out["corrected_bright"] = m["resid_bright"] - fl["resid_bright"]
    out["corrected_dark"] = m["resid_dark"] - fl["resid_dark"]
    out["coh_master"] = coherence(em)
    out["coh_floor"] = coherence(rimv6.measure(ref, sel, rimaxis.T))
    return out, sel, ref, em


def verdict(rec, smalln_n=200, smalln_allow=0.015):
    """printcert4.rim_verdict, reproduced from its source so this lane can
    score arms printcert4 never saw. Identical arithmetic."""
    if "refused" in rec:
        return "REFUSED", rec["refused"]
    c = rec["corrected_bright"]
    ci = rec["master"].get("ci_bright")
    off = rec["master"]["null_bright"] + rec["floor"]["resid_bright"]
    if ci is None:
        return "REFUSED", "no bootstrap interval"
    lo = ci[0] - off
    thr = rimaxis.RIM_MAX + (smalln_allow if rec["n_sel"] < smalln_n else 0.0)
    if c > thr and lo > thr:
        return "FAIL", "%+.3f%% (CI lo %+.3f%%) > %.1f%%" % (100 * c, 100 * lo,
                                                             100 * thr)
    if c > thr:
        return "REFUSED", "%+.3f%% but CI lo %+.3f%% below %.1f%%" % (
            100 * c, 100 * lo, 100 * thr)
    return "PASS", "%+.3f%%" % (100 * c)

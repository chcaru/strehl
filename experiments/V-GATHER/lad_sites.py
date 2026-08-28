r"""Per-site ladder, and the zero-shift control that settles the e16 flag.

WHY PER SITE. lad_run.py stores a median per arm. A median over 7-14 sites has
sampling error, and a monotone sequence of medians can in principle be produced
by a handful of sites moving while the rest do nothing. The stronger statement
is per site: at how many INDIVIDUAL locations does ceiling excess rise with the
exponent, out of how many. That statement does not depend on the median's
sampling error and it cannot be carried by a few outliers.

WHY THE ZERO-SHIFT CONTROL. lad_audit.py flagged sites as displaced by up to
(350, -356) in the e16 arm. lad_e16diag.py showed those sites have correlation
confidence 2.1-3.6 against 32-58 at the sites that locked, i.e. no peak at all,
and that a low-pass does NOT restore the lock. That rules out a rigid
displacement being FOUND, but it does not by itself rule one out being PRESENT.

This measures the thing directly: the Pearson correlation of heavily blurred
windows AT ZERO SHIFT. A merge cannot translate an image -- every arm folds the
same warped frames into the same reference grid -- so under "no displacement"
the coarse structure must agree at zero shift even where the fine structure has
decorrelated. If it does agree, the frozen window is looking at the same content
in both arms and the band difference is a difference in structure, not in
placement. This is the control that makes the e16 reading interpretable rather
than merely large.

SEPARATE OUTPUT FILE, deliberately. Two writers doing load-modify-write on one
JSON silently drop each other's entries; this project has already paid for that
lesson once. ladder-sites.json is this script's alone.
"""
import io
import json
import os
import sys
import time

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402
import lad_measure as lm                                           # noqa: E402
import lad_run as lr                                               # noqa: E402

OUT = os.path.join(HERE, "ladder-sites.json")
COARSE_SIGMA = 8.0
HALF = 384


def coarse_agree(a_lum, b_lum, sites):
    """Pearson r of blurred windows AT ZERO SHIFT -- no registration applied."""
    out = []
    H, W = a_lum.shape
    for s in sites:
        cy, cx = s["y"] + lm.WIN // 2, s["x"] + lm.WIN // 2
        y0, x0 = max(0, cy - HALF), max(0, cx - HALF)
        y1, x1 = min(H, cy + HALF), min(W, cx + HALF)
        a = ndimage.gaussian_filter(a_lum[y0:y1, x0:x1], COARSE_SIGMA)
        b = ndimage.gaussian_filter(b_lum[y0:y1, x0:x1], COARSE_SIGMA)
        if a.shape != b.shape:
            continue
        a = a - a.mean()
        b = b - b.mean()
        den = float(a.std() * b.std())
        out.append(float(np.mean(a * b) / den) if den > 1e-30 else None)
    return out


def main():
    cm.check_binary()
    doc = {}
    if os.path.exists(OUT):
        doc = json.load(io.open(OUT, encoding="utf-8"))
    subs = sys.argv[1:]
    if not subs:
        raise SystemExit("name the subjects explicitly; this re-renders every arm")
    for sub in subs:
        if sub in doc and len(doc[sub].get("arms", {})) == len(lr.ARMS):
            print("  %-26s already complete" % sub)
            continue
        sites, _ = lm.frozen_sites(sub)
        if not sites:
            doc[sub] = {"refused": "no frozen sites"}
            continue
        print("\n== %s  (%d sites)" % (sub, len(sites)))
        entry = {"n_sites": len(sites), "arms": {}}
        ref = None
        for tag, e, s in lr.ARMS:
            p = os.path.join(lm.LAD, "sites-%s-%s.tiff" % (sub, tag))
            line, err, dt = lr.render(sub, p, e, s)
            if line is None:
                entry["arms"][tag] = {"refused": err}
                print("    %-8s RENDER FAILED :: %s" % (tag, err[:200]))
                continue
            ml, lat = lm.load_lum(p)
            rows = lm.measure_array(ml, sites)
            rec = {"per_band_exp": line, "seconds": round(dt, 1),
                   "excess": [r.get("excess") for r in rows],
                   "master_band": [r.get("master") for r in rows],
                   "ceiling": [s2["ceiling"] for s2 in sites]}
            if tag == "default":
                ref = ml
            else:
                rec["coarse_r_zero_shift"] = coarse_agree(ref, ml, sites)
                del ml
            entry["arms"][tag] = rec
            os.remove(p)
            ex = [v for v in rec["excess"] if lm.finite(v)]
            print("    %-8s n=%2d median %+9.3f%%  %s" % (
                tag, len(ex), 100 * float(np.median(ex)) if ex else float("nan"),
                ("coarse r min %.4f" % min(v for v in rec["coarse_r_zero_shift"]
                                           if v is not None))
                if tag != "default" else ""))
            doc[sub] = entry
            json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        doc[sub] = entry
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()

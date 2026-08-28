r"""Ceiling-excess measurement for the exponent ladder.

THE MEASURAND. At each frozen site, `excess = master_band / ceiling - 1`. It is
positive when the master carries MORE mid-band contrast than the best single
input frame found at that location -- detail that was in no input and was
therefore manufactured by the merge. It is the same quantity the sharpness axis
reports as a negative deficit, sign-flipped so that "more manufactured detail"
reads as a larger number.

WHY THE CEILING IS FROZEN AND NOT RE-DERIVED PER ARM. My own report records the
failure this avoids: an earlier rim instrument reselected its edge population in
every arm, so the arms were scored over different populations and a BLURRED
image read as ringing MORE than the master. Selection must be frozen once and
reused. Here both the sites AND the ceilings come from sharp.json and are
identical in every arm; the only thing that varies down the ladder is the
master. lad_probe.py establishes the licence for that: a source frame rendered
at exponent 1 and at exponent 16 is BYTE-IDENTICAL, so the ceiling is not a
function of the variable under test.

WHAT THE FROZEN CEILING IS AND IS NOT. For the subjects whose sharpness record
refused for non-convergence, the ceiling is a LOWER bound rather than a settled
ceiling, so the absolute excess is overstated. That bias is a property of the
denominator, which is byte-frozen across the ladder, so it shifts every arm by
the same factor and cannot manufacture a trend. Absolute excess from those
subjects is not quotable; the SHAPE of the ladder is.

NAN. Every acceptance comparison here is guarded, because `NaN > x` is False and
an absent measurement would otherwise read as within-ceiling. This is not
hypothetical: a NaN reached cert.json in this same harness and would have read
as a PASS.

REGISTRATION IS VERIFIED, NOT ASSUMED. All arms are merged from one source set
into one reference grid, so site coordinates ought to transfer between arms
unchanged. `arm_shifts` measures it instead of trusting it, and any arm that
moves is reported rather than silently measured at the wrong place.
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
import certmeasure as cm                                           # noqa: E402
import sharpaxis as sa                                             # noqa: E402

LAD = r"C:\dev\strehl-out\V-GATHER\ladder"
WIN = sa.WIN
SIG_LO, SIG_HI = sa.SIG_LO, sa.SIG_HI


def finite(*vals):
    """A comparison is only admissible if every operand is a real number."""
    for v in vals:
        if v is None or not np.isfinite(v):
            return False
    return True


def band(a):
    """Identical statistic to the sharpness axis: DoG contrast over local mean."""
    a = np.asarray(a, dtype=np.float32)
    b = ndimage.gaussian_filter(a, SIG_LO) - ndimage.gaussian_filter(a, SIG_HI)
    m = float(np.mean(a))
    if not np.isfinite(m) or m <= 1e-6:
        return None
    v = float(np.std(b) / m)
    return v if np.isfinite(v) else None


def frozen_sites(subject):
    """Sites AND ceilings, frozen from the sharpness axis. Never re-derived."""
    out = []
    for f in ("sharp.json", "sharp2.json"):
        p = os.path.join(HERE, f)
        if not os.path.exists(p):
            continue
        doc = json.load(io.open(p, encoding="utf-8"))
        rec = doc.get(subject)
        if not rec or "sites" not in rec:
            continue
        for s in rec["sites"]:
            if "ceiling" not in s or "master" not in s:
                continue
            if not finite(s.get("ceiling"), s.get("master")):
                continue
            if s["ceiling"] <= 0:
                continue
            out.append({"y": s["y"], "x": s["x"], "ceiling": float(s["ceiling"]),
                        "master_ref": float(s["master"]),
                        "converged": bool(rec.get("converged", False))})
        if out:
            return out, rec
    return out, None


def measure_array(ml, sites):
    """Excess at each frozen site of an already-loaded master luminance plane."""
    rows = []
    H, W = ml.shape
    for s in sites:
        y, x = s["y"], s["x"]
        if y < 0 or x < 0 or y + WIN > H or x + WIN > W:
            rows.append({"y": y, "x": x, "excess": None, "why": "window off lattice"})
            continue
        v = band(ml[y:y + WIN, x:x + WIN])
        if not finite(v):
            rows.append({"y": y, "x": x, "excess": None, "why": "band non-finite"})
            continue
        rows.append({"y": y, "x": x, "master": v, "ceiling": s["ceiling"],
                     "excess": v / s["ceiling"] - 1.0})
    return rows


def summarise(rows):
    e = [r["excess"] for r in rows if finite(r.get("excess"))]
    if not e:
        return {"n": 0, "n_offered": len(rows), "median": None, "p90": None, "max": None}
    e = np.asarray(e, dtype=np.float64)
    return {"n": int(e.size), "n_offered": len(rows),
            "median": float(np.median(e)), "p90": float(np.percentile(e, 90)),
            "max": float(np.max(e)), "min": float(np.min(e))}


def arm_shifts(ref_lum, arm_lum, sites, half=384):
    """Do the frozen coordinates still point at the same content in this arm?"""
    bad = []
    H, W = arm_lum.shape
    for s in sites:
        cy, cx = s["y"] + WIN // 2, s["x"] + WIN // 2
        y0, x0 = max(0, cy - half), max(0, cx - half)
        y1, x1 = min(H, cy + half), min(W, cx + half)
        a = ref_lum[y0:y1, x0:x1]
        b = arm_lum[y0:y1, x0:x1]
        if a.shape != b.shape:
            continue
        dy, dx, _ = cm.est_shift(a, b)
        if dy != 0 or dx != 0:
            bad.append((s["y"], s["x"], dy, dx))
    return bad


def load_lum(path, expect=None):
    rgb, lat = cm.read_rgb(path, expect=expect)
    ml = sa.lum(rgb)
    del rgb
    return ml, lat

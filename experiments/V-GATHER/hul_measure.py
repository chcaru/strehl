r"""The hull-ladder gauge.

A CONFLICT IN THE BRIEF, AND HOW IT IS RESOLVED. ORCH asked for two things that
cannot both be done: "run your corrected ceiling-excess gauge, unchanged" and
"do not compare a `blend-render` number against a `strehl stack` number". The
ceiling in `sharp.json` was produced by `strehl.exe` single-frame renders under
`STREHL_ONLY_FRAME`. That env var lives in `merge_cmd.rs`, which `blend-render`
does NOT include -- it pulls in `align_cmd.rs` and `image_out.rs` only. So the
frozen ceiling is a strehl-stack number and the masters here are blend-render
numbers, and dividing one by the other is exactly the comparison forbidden.

So the PRIMARY measurand is not excess. It is the paired ARM RATIO

    ratio = band(arm) / band(inputrange)

at frozen sites, entirely within `blend-render`. It needs no ceiling, so it
cannot make the forbidden comparison, and it is strictly more sensitive than an
excess difference because the ceiling's own noise is absent from it. All three
of ORCH's predictions are statements about a change between arms, so all three
are expressible in it:

    P1  PerLevel reduces manufactured detail   ->  ratio < 1 on the excess subjects
    P2  PerLevel is inert where frames agree   ->  ratio == 1 on the controls
    P3  Unclamped raises it (the potency arm)  ->  ratio > 1

A SECOND STATISTIC ON THE SAME PIXELS, because ORCH required that a sharpness
cost be quoted with any reduction and never one without the other. `acuity` is
the p99.5 of the gradient magnitude over the same window, normalised by the same
local mean. `band` and `acuity` respond alike to a real edge and differently to
a clamp: pinning a run of pixels flat at `lo`/`hi` squares off an edge, which
RAISES gradient while it may not raise mid-band contrast at all.

P2 IS THE DANGEROUS PREDICTION AND IT IS GUARDED. "Inert on the controls" and
"the flag does nothing" produce the same reading. `pyramid.rs:3256` records that
`hull_lambda` shipped WIRED AND INERT -- plumbed correctly, plausible, and
moving the output by 0.008%. Nothing here may report inertness until
`hul_potency.py` has shown the flag moves bytes on some subject. A conclusion of
"no change" is only meaningful once the probe is known non-trivial.

NAN. Every acceptance comparison is two-sided or guarded. `NaN > x` is False, so
an absent measurement would read as "no manufactured detail" -- a silent pass.
"""
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm                                           # noqa: E402
import sharpaxis as sa                                             # noqa: E402
from lad_measure import band, finite, WIN                          # noqa: E402

HULL = r"C:\dev\strehl-out\V-GATHER\hull"
ARMS = ("inputrange", "perlevel", "unclamped")


def acuity(a):
    """Edge acutance: p99.5 of |grad|, over local mean so it is gain-invariant.

    Quoted beside `band` on the same pixels and never instead of it. A level-0
    clamp that squares an edge off RAISES this while flattening the overshoot
    that `band` sees, so the pair can separate "sharper" from "clamped".
    """
    a = np.asarray(a, dtype=np.float32)
    m = float(np.mean(a))
    if not np.isfinite(m) or m <= 1e-6:
        return None
    gy, gx = np.gradient(a)
    g = np.hypot(gy, gx)
    v = float(np.percentile(g, 99.5) / m)
    return v if np.isfinite(v) else None


def site_grid(shape, step=768, margin=256):
    """A fixed lattice, chosen from geometry alone and identical in every arm.

    Deliberately NOT chosen from image content: reselecting a population per arm
    is the defect that made an earlier rim instrument in this lane read a
    blurred image as ringing more than the master.
    """
    H, W = shape
    ys = range(margin, H - WIN - margin, step)
    xs = range(margin, W - WIN - margin, step)
    return [{"y": y, "x": x} for y in ys for x in xs]


def pick_sites(ref, n=64, step=768, margin=256):
    """Rank the fixed lattice by contrast in the REFERENCE arm only, once."""
    cand = site_grid(ref.shape, step=step, margin=margin)
    scored = []
    for s in cand:
        w = ref[s["y"]:s["y"] + WIN, s["x"]:s["x"] + WIN]
        v = band(w)
        if finite(v):
            scored.append((v, s))
    scored.sort(key=lambda t: -t[0])
    return [s for _, s in scored[:n]]


def measure(lum, sites):
    rows = []
    H, W = lum.shape
    for s in sites:
        y, x = s["y"], s["x"]
        if y < 0 or x < 0 or y + WIN > H or x + WIN > W:
            rows.append({"y": y, "x": x, "band": None, "acuity": None,
                         "why": "off lattice"})
            continue
        w = lum[y:y + WIN, x:x + WIN]
        rows.append({"y": y, "x": x, "band": band(w), "acuity": acuity(w)})
    return rows


def ratios(ref_rows, arm_rows, key):
    """Paired per-site ratio, guarded. Returns (values, n_refused)."""
    out, refused = [], 0
    for a, b in zip(ref_rows, arm_rows):
        va, vb = a.get(key), b.get(key)
        if not finite(va, vb) or va <= 0:
            refused += 1
            continue
        out.append(vb / va)
    return np.asarray(out, dtype=np.float64), refused


def summarise(v):
    if v.size == 0:
        return {"n": 0, "median": None, "p90": None, "max": None, "min": None}
    return {"n": int(v.size), "median": float(np.median(v)),
            "p90": float(np.percentile(v, 90)), "max": float(np.max(v)),
            "min": float(np.min(v))}


def arm_path(subject, arm):
    return os.path.join(HULL, "%s-%s.tiff" % (subject, arm))


def load_lum(path, expect=None):
    rgb, lat = cm.read_rgb(path, expect=expect)
    ml = sa.lum(rgb)
    del rgb
    return ml, lat

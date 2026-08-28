r"""Paired rim A/B on two arbitrary files, on the committed rimv6 core.

WHY NOT MY OWN GAUGE. bg_lib.py was written from scratch for this task and is
INADMISSIBLE on this subject: at no isolation cut leaving >=30 edges could it
recover a planted blur of 1.2 px (it read -0.045, +0.016, -0.089 px of sigma
where +0.455 was planted), and it read base rim +0.277 -- the textured-band
pathology rimindep.py already documents at +27%. It is kept only for the
coupling calibration it did produce. This is the third rim instrument I have
had to rule inadmissible in this campaign.

WHAT rimv6 HAS THAT MINE DID NOT, and both matter for ORCH's trap:

  STRUCTURAL NULL. A monotone edge of finite width reads BELOW zero by
  construction, more so the wider it is. So a softened arm reads a LOWER rim
  with nothing removed. rimv6 subtracts the null AT EACH ARM'S OWN MEASURED
  WIDTH, which removes exactly the part of a rim "improvement" that is only
  geometry. Comparing raw overshoots would credit softening as a fix.

  edge_width FROM THE CENTRAL SLOPE, 0.8/slope at t=0, outside the aura band on
  both sides. My own 10-90 rise was coupled to the rim at -3.85 px per unit
  (R^2 0.96, fitted here in bg_commission.py), which runs the wrong way: an arm
  that removes an aura would be reported as softening.

WHAT IS CHANGED FROM rimaxis.py, stated plainly as ORCH asked:
  1. Inputs are two explicit paths, not the SHIP-V4 seal directory.
  2. Selection happens ONCE, on the smoothed CONTROL arm, and BOTH arms are
     measured at those identical pixel locations. rimaxis measures one image.
     rimv6.boot_diff defaults to UNPAIRED because different comparators carry a
     1.005x raster scale; that does not apply here -- both arms come from one
     binary, one registration, one subject, and the integer shift is asserted
     to be (0,0) below. Paired is therefore valid and far tighter.
  3. The bootstrap is over the PAIRED per-edge difference.
Nothing else. The floor rule, the isolation rule, the null table and the
refusal conditions are rimv6's own and are not relaxed.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "V-H2H2-RIMCLIP")))
import rimv6                                                       # noqa: E402

T = 256
NTILE = 40
SMOOTH = 3.0
NMIN = 30
FLOOR_MAX = 0.02


def lum(path):
    a = tifffile.imread(path)
    g = (0.2126 * a[..., 0] + 0.7152 * a[..., 1] +
         0.0722 * a[..., 2]).astype(np.float32) / 65535.0
    clip = (a.max(axis=2) >= 65535) | (a.min(axis=2) <= 0)
    del a
    return g, clip


def pick_rois(g, clip, n=NTILE):
    h, w = g.shape
    cand = []
    for y in range(0, h - T, T):
        for x in range(0, w - T, T):
            if clip[y:y + T, x:x + T].any():
                continue
            t = g[y:y + T, x:x + T]
            gy, gx = np.gradient(ndimage.uniform_filter(t, 3))
            cand.append((float(np.percentile(np.hypot(gx, gy), 99.5)), y, x))
    cand.sort(reverse=True)
    return [(y, x) for _, y, x in cand[:n]]


def arm_stats(g, sel):
    """Corrected rim and edge width for one arm at the frozen locations."""
    e = rimv6.measure(g, sel, T)
    r = rimv6.stats(e, nmin=NMIN)
    if r is None:
        return None, None
    w = rimv6.edge_width(e)
    nn = rimv6.try_null(w) if w else None
    if nn is None:
        return None, e
    r["width"] = w
    r["null_bright"], r["null_dark"] = nn[0], nn[1]
    r["corr_bright"] = r["bright"] - nn[0]
    r["corr_dark"] = r["dark"] - nn[1]
    return r, e


def paired_ci(ea, eb, nboot=4000, seed=23):
    """Bootstrap the PAIRED per-edge difference, B minus A, on both axes."""
    if ea is None or eb is None:
        return None
    n = min(len(ea["ov"]), len(eb["ov"]))
    if n < NMIN:
        return None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, n, size=(nboot, n))
    out = {}
    for axis, ka, kb in (("bright", ea["ov"][:n], eb["ov"][:n]),
                         ("dark", ea["un"][:n], eb["un"][:n])):
        d = np.median(kb[idx], axis=1) - np.median(ka[idx], axis=1)
        out[axis] = (float(np.median(d)), float(np.percentile(d, 2.5)),
                     float(np.percentile(d, 97.5)))
    return out


def int_shift(a, b, search=4):
    h, w = a.shape
    cy, cx = h // 2, w // 2
    pa = a[cy - 256:cy + 256, cx - 256:cx + 256]
    best, bs = None, (0, 0)
    for dy in range(-search, search + 1):
        for dx in range(-search, search + 1):
            pb = b[cy - 256 + dy:cy + 256 + dy, cx - 256 + dx:cx + 256 + dx]
            if pb.shape != pa.shape:
                continue
            e = float(np.mean((pa - pb) ** 2))
            if best is None or e < best:
                best, bs = e, (dy, dx)
    return bs


def run(a_path, arms, label, out_json):
    ga, clip = lum(a_path)
    rois = pick_rois(ga, clip)
    # rimaxis.py's select_for, not rimv6.choose_cut. choose_cut requires >=1000
    # edges and is therefore forced onto a loose cut; on this subject that left
    # the floor at +2.641% and the instrument refused. rimaxis sweeps every
    # candidate at >=NMIN edges and takes whichever drives the floor CLOSEST TO
    # ZERO. The 2% floor rule below is unchanged -- the sweep chooses the cut,
    # it does not choose the verdict, and the arm comparison is never consulted.
    ctrl0 = ndimage.gaussian_filter(ga, SMOOTH).astype(np.float32)
    cut, fl, best = None, None, None
    for c in rimv6.FLAT_CANDIDATES:
        s = rimv6.select(ctrl0, clip, rois, T, c)
        if len(s) < NMIN:
            continue
        r, _e = arm_stats(ctrl0, s)
        if r is None:
            continue
        score = abs(r["corr_bright"])
        if best is None or score < best:
            best, cut = score, c
            fl = {"bright_residual": r["corr_bright"], "width": r["width"],
                  "n": r["n"]}
    del ctrl0
    if cut is None or fl is None:
        print("REFUSED: no flatness cut reaches the instrument's null")
        return
    print("  chosen cut %.2f   floor %+.3f%%   width %.2f px   n=%d"
          % (cut, 100 * fl["bright_residual"], fl["width"], fl["n"]))
    if abs(fl["bright_residual"]) > FLOOR_MAX:
        print("REFUSED: instrument floor %+.3f%% exceeds %.1f%% -- a rim-free "
              "image does not read its null on this subject"
              % (100 * fl["bright_residual"], 100 * FLOOR_MAX))
        return
    ctrl = ndimage.gaussian_filter(ga, SMOOTH).astype(np.float32)
    sel = rimv6.select(ctrl, clip, rois, T, cut)
    del ctrl
    print("  frozen selection: %d edge locations, reused by every arm\n" % len(sel))
    ra, ea = arm_stats(ga, sel)
    if ra is None:
        print("REFUSED: control arm outside the null table's covered range")
        return
    print("  %-30s %10s %10s %9s %8s %7s"
          % ("arm", "rim corr", "d rim", "width", "d width", "n"))
    print("  " + "-" * 78)
    print("  %-30s %+9.3f%% %10s %8.2fpx %8s %7d"
          % ("A (control)", 100 * ra["corr_bright"], "--", ra["width"], "--",
             ra["n"]))
    doc = {"control": {k: ra[k] for k in
                       ("corr_bright", "corr_dark", "width", "n", "bright")},
           "cut": cut, "floor": fl["bright_residual"], "n_sel": len(sel),
           "arms": {}}
    for nm, gb in arms:
        if callable(gb):
            gb = gb(ga)
        if isinstance(gb, str):
            gb, _c2 = lum(gb)
            sh = int_shift(ga, gb)
            if sh != (0, 0):
                print("  %-30s REFUSED: integer shift %s, not (0,0)" % (nm, sh))
                continue
        rb, eb = arm_stats(gb, sel)
        if rb is None:
            print("  %-30s REFUSED: outside the null table's covered range" % nm)
            continue
        ci = paired_ci(ea, eb)
        d = rb["corr_bright"] - ra["corr_bright"]
        dw = rb["width"] - ra["width"]
        print("  %-30s %+9.3f%% %+9.3f%% %8.2fpx %+7.2fpx %7d"
              % (nm, 100 * rb["corr_bright"], 100 * d, rb["width"], dw, rb["n"]))
        if ci:
            print("  %-30s   paired 95%% CI on raw bright delta "
                  "[%+.3f%%, %+.3f%%]" % ("", 100 * ci["bright"][1],
                                          100 * ci["bright"][2]))
        doc["arms"][nm] = {"corr_bright": rb["corr_bright"],
                           "corr_dark": rb["corr_dark"], "width": rb["width"],
                           "d_corr_bright": d, "d_width": dw, "n": rb["n"],
                           "ci_bright": ci["bright"] if ci else None,
                           "ci_dark": ci["dark"] if ci else None}
        del gb
    json.dump(doc, io.open(out_json, "w", encoding="utf-8"), indent=1)
    print("\n  wrote %s" % out_json)


if __name__ == "__main__":
    print(__doc__)
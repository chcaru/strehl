r"""V-NEVERWORSE / THE WARP NULL AT REAL MAGNITUDE -- extending W1.

W1 (in `vn_commission.py`) tested this instrument's resampler at a scale of
1 + 1.66e-2 and found `band/mean` stable to 0.94%. That number certified a
magnitude the real measurement never uses.

The shipped masters carry a coverage fit -- `bee-1-cpl`'s provenance says
"field of view scaled to 0.9236 so that EVERY frame covers every pixel (7.6% of
width dropped, then upsampled to keep the output dimensions)". A single-frame
render has almost nothing to intersect and covers 0.9974. So master content is
magnified by 1/cover_master and source content by 1/cover_src, and the source
window must be scaled by roughly cover_master/cover_src to land on it. Measured
across the corpus that factor runs 0.8451 .. 1.0000, and the fitted per-frame
scale runs 0.775 .. 1.000 -- a magnification of up to 1.29x, SEVENTEEN TIMES the
1.7% W1 certified.

Two things could go wrong at that magnitude and only one of them is obvious:

  RESAMPLER LOSS. An interpolating kernel attenuates structure near its own
  footprint. W1 already shows this is severe for the 3 px `relhf` term
  (x0.710) and mild for `band/mean`. Untested at 1.29x.

  BAND SHIFT. `orch_blotch` filters a FIXED 50-400 px band in master pixels.
  Magnifying a source window by 1.18x means the band is sampling that frame's
  own 42-339 px structure. The two arms are not looking at the same physical
  scales. This one cannot be seen by staring at the code.

Both are measured here the only way that answers the question: push the MASTER
-- the one image whose statistics are known unresampled -- through the exact
`warp_window` path a source goes through, at each subject's own real scale, and
read the statistics back.

DIRECTION THAT WOULD INVALIDATE THIS LANE: if the warp LOWERS blotch, then every
source frame reads low, the min reads low, and `vs_min` is inflated -- the
violations in RESULT.md section 6 would be an artefact of the resampler rather
than a property of the merge. That is the hypothesis under test.

  python vn_warpnull.py [subject ...]
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402
from orch_blotch import lum_of                                # noqa: E402

SUBJ = None     # default: every subject that has a measurement record


def affine(scale, cy, cx, dy=0.0, dx=0.0, rot_deg=0.0):
    """A similarity that fixes the WINDOW CENTRE.

    The first version of this file built `[[s,0,dx],[0,s,dy]]`, which scales
    about the image origin and therefore translates a window at x=5840 by
    5840*(1-s) -- nearly 900 px at s=0.849. That does not resample the window,
    it fetches a different part of the picture, and it made three of four
    subjects report "window falls outside". `warp_window` was doing its job.

    Fixing the centre is what isolates the quantity under test: identical
    physical content, resampled at the real magnification, so any movement in
    the statistic is the resampler and the band shift and nothing else.
    """
    th = np.deg2rad(rot_deg)
    c, s = np.cos(th) * scale, np.sin(th) * scale
    return np.array([[c, -s, cx - c * cx + s * cy + dx],
                     [s, c, cy - s * cx - c * cy + dy]], dtype=np.float64)


def real_scale(subj):
    """The scales the REAL frames were registered at, not ones I chose.

    Returns (record, median, least-warped, MOST-warped). The third value was
    originally the only non-median arm and was labelled "worst scale" while
    being `min(|s-1|)` -- the scale CLOSEST to unity, i.e. the LEAST warped
    frame. That is a weaker test, not a worse one, and the label was wrong.
    The fourth value is the real worst case: the single most magnified frame
    the subject actually contributed.
    """
    rec = L.jload(os.path.join(L.OUT, "ratio", "%s.json" % subj))
    ok = [r for r in rec["rows"] if r.get("state") == "OK"]
    sc = [r["scale"] for r in ok if r.get("scale")]
    return (rec, float(np.median(sc)),
            float(min(sc, key=lambda x: abs(x - 1.0))),
            float(min(sc, key=lambda x: -abs(x - 1.0))))


def nudge(y0, x0, win, h, w, want=160):
    """Clamp a window inward by an INTEGER, moving it only as far as needed.

    A synthetic transform carries none of the translation a real registration
    matrix does, so an edge-hugging window has no margin for the interpolation
    footprint and `warp_window` refuses it -- which killed the identity control
    on three of four subjects. Scaling a 900 px window about its centre by
    0.849 reaches ~80 px past each edge, so `want` must exceed that. Clamping
    (rather than always adding an offset) keeps the ACTUAL measured window on
    every subject that already has room.
    """
    def one(v, n, lim):
        return int(max(want, min(v, lim - n - want)))
    return one(y0, win, h), one(x0, win, w)


def roundtrip(rgb, scale, y0, x0, win, pad=420):
    """Resample to the frame's scale and back again, then crop the window.

    THE SINGLE-APPLICATION ARM CONFLATES TWO MECHANISMS AND ONLY ONE IS REAL.
    Warping the master once by the fitted affine leaves its content at the
    FRAME's scale while `orch_blotch` still filters a fixed 50-400 px band in
    MASTER pixels, so the statistic reads different spatial frequencies. That
    band shift is an artefact of the null: in the real pipeline the affine maps
    master -> frame and `warp_window` pulls with WARP_INVERSE_MAP, so a source
    frame's content arrives IN MASTER SPACE and the band is applied at the
    scale it was designed for.

    A round trip restores the geometry exactly and leaves only the interpolator
    behind. It applies TWO interpolations where the pipeline applies one, so it
    OVERSTATES resampler loss -- the conservative direction for a null whose
    failure mode is under-reporting.
    """
    h, w = rgb.shape[:2]
    p = int(min(pad, y0, x0, h - y0 - win, w - x0 - win))
    n = win + 2 * p
    sub = np.ascontiguousarray(rgb[y0 - p:y0 - p + n, x0 - p:x0 - p + n])
    cy = cx = (n - 1) / 2.0
    a1 = affine(scale, cy, cx)
    a2 = affine(1.0 / scale, cy, cx)
    for A in (a1, a2):
        sub = cv2.warpAffine(sub, A.astype(np.float32), (n, n),
                             flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                             borderMode=cv2.BORDER_REPLICATE)
    return sub[p:p + win, p:p + win]


def stats_of(wb, wc):
    return L.window_stats(wb, wc)


def main(argv):
    subs = argv or SUBJ or [s for s in L.subjects()
                            if os.path.exists(os.path.join(L.OUT, "ratio",
                                                           "%s.json" % s))]
    print("W2 -- RESAMPLING NULL AT THE MAGNITUDE ACTUALLY USED")
    print("the master is pushed through the source arm's own warp_window path;")
    print("a sound instrument returns 1.0000x. blotch falling below 1 is the")
    print("failure direction: it would mean source frames read artificially low.\n")
    print("%-24s %7s | %8s %8s %8s | %8s"
          % ("subject / warp", "scale", "blotch", "band", "chroma", "relhf"))
    worst_b, worst_c, res = 1.0, 1.0, {}
    for s in subs:
        rec, smed, sleast, sext = real_scale(s)
        bw, cw = tuple(rec["bw"]), tuple(rec["cw"])
        rgb = L.read_rgb(L.lin_master_path(s))
        res[s] = dict(base=None, arms=[], scale_median=smed,
                      scale_least=sleast, scale_extreme=sext)
        # These windows sit 14-38 px from the image edge. A REAL registration
        # matrix carries a translation that lands them well inside the source
        # frame; a synthetic one does not, so `warp_window` correctly refuses
        # and the identity control cannot run. An integer inward offset, applied
        # identically to the baseline and to every arm, restores the control
        # without adding any interpolation of its own (memory: register a
        # paired comparison with an integer-only shift).
        off = 160
        h, w = rgb.shape[0], rgb.shape[1]
        b0, b1 = nudge(bw[0], bw[1], L.BWIN, h, w, off)
        c0, c1 = nudge(cw[0], cw[1], L.CWIN, h, w, off)
        moved = (b0, b1, c0, c1) != (bw[0], bw[1], cw[0], cw[1])
        base = L.stats_at(rgb, (b0, b1), (c0, c1))
        res[s]["base"] = base
        print("%-24s %7s | %8.5f %8.3f %8.5f | %8.5f   <- unwarped, b(%d,%d) "
              "c(%d,%d)%s"
              % (s, "-", base["blotch"], base["band"], base["chroma"],
                 base["relhf"], b0, b1, c0, c1,
                 "  [clamped inward]" if moved else ""))
        by, bx = b0 + L.BWIN / 2.0, b1 + L.BWIN / 2.0
        cy, cx = c0 + L.CWIN / 2.0, c1 + L.CWIN / 2.0
        for tag, sc, rot in (
                ("identity", 1.0, 0.0),
                ("RT identity", 1.0, 0.0),
                ("RT median scale", smed, 0.0),
                ("RT extreme scale", sext, 0.0),
                ("RT least-warped", sleast, 0.0),
                ("median scale", smed, 0.0),
                ("extreme scale", sext, 0.0),
                ("extreme + 0.05 deg", sext, 0.05)):
            if tag.startswith("RT "):
                wb = roundtrip(rgb, sc, b0, b1, L.BWIN)
                wc = roundtrip(rgb, sc, c0, c1, L.CWIN)
            else:
                dy, dx = (0.0, 0.0) if tag == "identity" else (0.31, 0.57)
                wb = L.warp_window(rgb, affine(sc, by, bx, dy, dx, rot),
                                   b0, b1, L.BWIN)
                wc = L.warp_window(rgb, affine(sc, cy, cx, dy, dx, rot),
                                   c0, c1, L.CWIN)
            if wb is None or wc is None:
                print("   %-21s %7.4f | window falls outside -- not measurable"
                      % (tag, sc))
                continue
            st = stats_of(wb, wc)
            rb = st["blotch"] / base["blotch"]
            rc = st["chroma"] / base["chroma"]
            print("   %-21s %7.4f | %7.4fx %7.4fx %7.4fx | %7.4fx"
                  % (tag, sc, rb, st["band"] / base["band"], rc,
                     st["relhf"] / base["relhf"]))
            res[s]["arms"].append(dict(tag=tag, scale=float(sc),
                                       blotch=rb, chroma=rc,
                                       relhf=st["relhf"] / base["relhf"]))
            if tag in ("identity", "RT identity") and (abs(rb - 1) > 1e-6
                                                       or abs(rc - 1) > 1e-6):
                raise RuntimeError("%s arm moved on %s: blotch %.6fx "
                                   "chroma %.6fx -- the null is broken"
                                   % (tag, s, rb, rc))
            if tag not in ("identity", "RT identity"):
                worst_b = max(worst_b, rb, 1.0 / rb)
                worst_c = max(worst_c, rc, 1.0 / rc)
        if not any(a["tag"] == "identity" for a in res[s]["arms"]):
            raise RuntimeError("no identity control ran on %s -- a null without "
                               "its own control is not a null" % s)
        del rgb

    print("\nW2 VERDICT")
    print("  Two arms, and only ONE of them is a fair model of the pipeline.")
    print("  RT = round trip: geometry restored, resampler only. It applies TWO")
    print("       interpolations where the pipeline applies one, so it")
    print("       OVERSTATES the loss -- the conservative direction here.")
    print("  1x = single application: leaves the content at the FRAME's scale")
    print("       while the band filter still runs in MASTER pixels, so it")
    print("       charges for a band shift the real pipeline never incurs.")
    print("  'extreme' is the single MOST magnified frame the subject actually")
    print("  contributed, so the RT-extreme column is the true worst case.")
    print("  %-36s %6s %8s %8s %8s | %8s"
          % ("subject", "s_ext", "RTmed b", "RText b", "RText c", "1x blot"))

    def arm(s, t, k):
        a = next((x for x in res[s]["arms"] if x["tag"] == t), None)
        return a[k] if a else float("nan")

    for s in sorted(res):
        res[s]["factor_b"] = min(arm(s, "RT median scale", "blotch"),
                                 arm(s, "RT extreme scale", "blotch"))
        res[s]["factor_c"] = min(arm(s, "RT median scale", "chroma"),
                                 arm(s, "RT extreme scale", "chroma"))
        print("  %-36s %6.4f %8.4f %8.4f %8.4f | %8.4f"
              % (s, res[s]["scale_extreme"],
                 arm(s, "RT median scale", "blotch"),
                 arm(s, "RT extreme scale", "blotch"),
                 arm(s, "RT extreme scale", "chroma"),
                 arm(s, "median scale", "blotch")))

    sc_all = [res[s]["scale_extreme"] for s in res]
    print("\n  most magnified frame in the corpus: %.4f = %.2fx magnification"
          % (min(sc_all), 1.0 / min(sc_all)))
    for k, lab in (("factor_b", "blotch"), ("factor_c", "chroma")):
        v = [d[k] for d in res.values() if d[k] == d[k]]
        print("  round-trip %s factor, worst arm per subject, %d subjects:"
              "  min %.4f  median %.4f  max %.4f"
              % (lab, len(v), min(v), float(np.median(v)), max(v)))
    allf = [(s, d["factor_b"], d["factor_c"]) for s, d in res.items()]
    dev = max(max(abs(b - 1), abs(c - 1)) for _, b, c in allf)
    low = sorted([(s, min(b, c)) for s, b, c in allf if min(b, c) < 0.97],
                 key=lambda t: t[1])
    if low:
        print("\n  FAILURE DIRECTION PRESENT on %d of %d subjects: the resampler"
              % (len(low), len(allf)))
        print("  ALONE lowers a statistic below 0.97x, so those source frames")
        print("  read low and their vs_min is inflated by 1/factor:")
        for s, v in low:
            print("      %-36s %.4fx  -> vs_min inflated %5.1f%%"
                  % (s, v, 100 * (1.0 / v - 1.0)))
    else:
        print("\n  FAILURE DIRECTION ABSENT on all %d subjects. Worst departure"
              % len(allf))
        print("  from unity in either statistic: %.2f%%. The resampler cannot"
              % (100 * dev))
        print("  account for the excursions reported in RESULT.md section 6.")
    rl = [arm(s, "RT extreme scale", "relhf") for s in res]
    print("\n  POSITIVE CONTROL -- the same arms move a 3 px statistic, which is")
    print("  where bilinear interpolation actually does its damage:")
    print("      relhf over 26 subjects: %.4f .. %.4f" % (min(rl), max(rl)))
    print("\n  worst departure over the contaminated 1x arms, for the record:")
    print("      blotch %.2f%%   chroma %.2f%%"
          % (100 * (worst_b - 1.0), 100 * (worst_c - 1.0)))
    L.jdump(res, os.path.join(L.OUT, "report", "warpnull.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

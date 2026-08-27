"""mask_audit.py -- is a fixed percentile mask under any V-H2H2 published number?

WHY.  An independent lane found `aura depression 16557.7 DN` on an image whose
median is `8171.1 DN`, and diagnosed it as a fixed 20/30/40/50 percentile
subject mask designed for a subject occupying 21% of the frame being applied to
one occupying 60%: the "aura" annulus lands on unmasked subject.  The question
put to this lane is whether that mask is under any head-to-head number.

This is a REPAIR, not a verification, so it does not stop at "we don't use that
file".  Four parts:

  A  classify EVERY statistic this lane published by what spatial selection it
     uses, as a counted partition
  B  measure both head-to-head subjects' frame occupancy, with an extent
     estimator commissioned against planted subjects of known area
  C  apply the vh2-style fixed percentile mask TO THIS LANE'S SUBJECTS and
     measure its aura:ground ratio, i.e. test directly whether the defect would
     bite here if that mask were used
  D  the analogous risk that IS in this lane: rois.census picks FLAT control
     ROIs by quantile of local contrast, so on a frame-filling subject "flat"
     could be low-contrast SUBJECT rather than background. Measured, not argued.

Usage:  python mask_audit.py
"""
import os
import sys

import cv2
import numpy as np

import h2
import rois

LIN = r"C:\dev\strehl-out\V-H2H2\lin"
SUBJ = {"113": "113MSDCF", "cb": "coffee-bubbles"}
_ok, _bad = [], []


def record(tag, passed, msg):
    (_ok if passed else _bad).append(tag)
    print("  [%s] %-24s %s" % ("PASS" if passed else "FAIL", tag, msg))


# ---------------------------------------------------------------- part A
# Every figure this lane published, and the spatial selection behind it.
# `source` is the script that printed it; `selection` is the classification.
PUBLISHED = [
    ("C_g1/C_g0 DETAIL, 7 bands (113 and cb)", "flip.py", "roi-adaptive"),
    ("C_g1/C_g0 FLAT, 7 bands", "flip.py", "roi-adaptive"),
    ("P_g1/P_g0 DETAIL, 7 bands", "flip.py", "roi-adaptive"),
    ("absolute C per ROI, FLAT/DETAIL ratio", "flip.py", "roi-adaptive"),
    ("C vs Zerene / fork, per band", "h2h2.py", "roi-adaptive"),
    ("null peak distribution", "h2h2b.py", "roi-adaptive"),
    ("NN-resample degradation arm (P vs C)", "commission.py", "roi-adaptive"),
    ("SHARP arm, C -> 4.0 under 4x unsharp", "commission.py", "roi-adaptive"),
    ("FLAT vs DETAIL noise-specificity census", "commission.py", "roi-adaptive"),
    ("tone reproduction 0.037147 vs 0.037138", "toneparity.py", "whole-frame"),
    ("tone percentile deviation", "toneparity.py", "whole-frame"),
    ("grade-removal quantile transfer", "gradetest.py", "whole-frame"),
    ("coherence gamma vs frequency", "coherence.py", "roi-adaptive"),
    ("integer registration peak / planted shifts", "h2.py", "roi-adaptive"),
    ("wall-clock timing, s/frame, 2.4x", "timing_derive.py", "no-image-stat"),
    ("fork OOM at task 716 of 860", "timing2.ps1", "no-image-stat"),
    ("input-bytes asymmetry 9.9x", "timing_derive.py", "no-image-stat"),
    ("ICC / comparator geometry checks", "check_icc.py", "no-image-stat"),
]


def part_a():
    print("=== A. every published figure, classified by spatial selection ===")
    kinds = {}
    for name, src, kind in PUBLISHED:
        kinds.setdefault(kind, []).append((name, src))
    for kind in ("fixed-percentile-mask", "roi-adaptive", "whole-frame",
                 "no-image-stat"):
        items = kinds.get(kind, [])
        print("  %-24s %2d figure(s)" % (kind, len(items)))
        for name, src in items:
            print("        %-46s %s" % (name[:46], src))
    tot = sum(len(v) for v in kinds.values())
    print("  ---")
    print("  fixed-percentile %d + roi-adaptive %d + whole-frame %d + "
          "non-image %d = %d of %d   %s"
          % (len(kinds.get("fixed-percentile-mask", [])),
             len(kinds.get("roi-adaptive", [])),
             len(kinds.get("whole-frame", [])),
             len(kinds.get("no-image-stat", [])), tot, len(PUBLISHED),
             "OK" if tot == len(PUBLISHED) else "MISMATCH"))
    record("no-fixed-percentile", not kinds.get("fixed-percentile-mask"),
           "no published figure is built on a fixed percentile subject mask, "
           "an annulus, or a depression")
    # print-then-TEST: the classification is checked against the source, not
    # asserted. A distance transform or connected-components call is the
    # signature of the annulus construction.
    # The three files EXCLUDED are the audit itself, written today, which
    # publish no head-to-head figure: naming them here rather than filtering
    # silently, because a carve-out you cannot see is how this hides.
    audit_own = ("mask_audit.py", "physics.py", "commission_physics.py")
    sig = []
    for f in sorted(os.listdir(".")):
        if not f.endswith(".py") or f in audit_own:
            continue
        txt = open(f, encoding="utf-8", errors="replace").read()
        for pat in ("distanceTransform", "connectedComponents", "MORPH_CLOSE",
                    "aura", "depression"):
            if pat in txt:
                sig.append((f, pat))
    print("  (scanned %d lane sources; excluded the audit's own %s)"
          % (len([f for f in os.listdir(".") if f.endswith(".py")])
             - len(audit_own), ", ".join(audit_own)))
    record("no-annulus-in-source", not sig,
           "no lane source calls distanceTransform / connectedComponents / "
           "MORPH_CLOSE or mentions aura|depression: %s"
           % ("none found" if not sig else sig))
    return kinds


# ---------------------------------------------------------------- part B
def extent(g, blur=33, debias=True, floor=0.02, report=None):
    """Subject extent from LOCAL CONTRAST, independent of luminance level.

    A focus-stacked subject is sharp everywhere it exists; background is not.
    Deliberately not a luminance percentile -- that is the construction under
    audit, and grading it with itself would decide nothing.

    Two corrections, both forced by commissioning arms that FAILED:

    1. The local-contrast window spreads high contrast about blur/2 past the
       true boundary, so the raw threshold DILATES: planted 5/21/60% read as
       6.9/24.3/65.8%.  `debias` erodes by that same blur/2 -- the mechanism's
       own radius, not a value fitted to make the arms pass.

    2. Otsu splits ANY histogram, including a unimodal one.  On flat noise with
       no subject at all the first version returned 50.8%, because normalising
       contrast by its own 99.5th percentile rescales a featureless frame to
       full range and manufactures structure.  So the ABSOLUTE contrast of the
       selected class is checked against a floor: 2% local RMS contrast is not
       texture.  The arms below print the measured level for every input so the
       floor can be seen not to sit on a boundary.
    """
    g = g.astype(np.float32)
    m = cv2.blur(g, (blur, blur))
    v = cv2.blur(g * g, (blur, blur)) - m * m
    craw = np.sqrt(np.maximum(v, 0)) / np.maximum(m, 1.0)
    c = (255 * np.clip(craw / max(np.percentile(craw, 99.5), 1e-6), 0, 1)).astype(np.uint8)
    _, b = cv2.threshold(c, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    b = cv2.morphologyEx(b, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    b = cv2.morphologyEx(b, cv2.MORPH_OPEN, np.ones((9, 9), np.uint8))
    if debias:
        k = max(3, (blur // 2) | 1)
        b = cv2.erode(b, np.ones((k, k), np.uint8))
    sel = b > 0
    lvl = float(np.median(craw[sel])) if sel.any() else 0.0
    if report is not None:
        report["contrast"] = lvl
    if lvl < floor:
        return np.zeros_like(sel)
    return sel


def part_b_commission():
    print("\n=== B1. the extent estimator, against planted subjects ===")
    rng = np.random.default_rng(4)
    raw, deb = {}, {}
    for want in (0.05, 0.21, 0.60):
        H, W = 400, 600
        bg = cv2.GaussianBlur(rng.normal(120, 1.0, (H, W)).astype(np.float32), (0, 0), 4)
        side = int(np.sqrt(want * H * W))
        y0, x0 = (H - side) // 2, (W - side) // 2
        sub = bg.copy()
        tex = rng.normal(120, 30, (side, side)).astype(np.float32)
        sub[y0:y0 + side, x0:x0 + side] = tex
        raw[want] = float(extent(sub, debias=False).mean())
        rep = {}
        deb[want] = float(extent(sub, report=rep).mean())
        got = deb[want]
        ok = abs(got - want) <= 0.05
        record("extent-%.2f" % want, ok,
               "planted %.1f%% -> raw %.1f%% (bias %+.1f pp) -> debiased "
               "%.1f%% (bias %+.1f pp), selected-class contrast %.4f"
               % (100 * want, 100 * raw[want], 100 * (raw[want] - want),
                  100 * got, 100 * (got - want), rep["contrast"]))
    # A both-directions arm: the estimator must also NOT see a subject where
    # there is none. Without this, an estimator that returned 0 everywhere
    # would pass the small-subject arm above -- and the FIRST version of this
    # estimator returned 50.8% on flat noise, which is what added the floor.
    H, W = 400, 600
    flat = cv2.GaussianBlur(rng.normal(120, 1.0, (H, W)).astype(np.float32), (0, 0), 4)
    rep = {}
    e0 = float(extent(flat, report=rep).mean())
    record("extent-empty", e0 < 0.02,
           "no subject planted at all -> measured %.2f%% (selected-class "
           "contrast %.4f, below the 0.02 floor), so the estimator is not "
           "simply returning zero or one" % (100 * e0, rep["contrast"]))
    worst = max(abs(deb[w] - w) for w in deb)
    record("extent-bias-bounded", worst <= 0.05,
           "worst debiased error over 5/21/60%% planted = %.1f pp; direction of "
           "the RAW bias is always positive (dilating), so an uncorrected "
           "extent OVERSTATES how much of an annulus lands on subject"
           % (100 * worst))


def part_b(coarse):
    print("\n=== B2. frame occupancy of the two head-to-head subjects ===")
    occ = {}
    for key, g in coarse.items():
        rep = {}
        e = extent(g, report=rep)
        occ[key] = float(e.mean())
        print("  %-16s (%s) subject occupies %5.1f%% of frame  "
              "(selected-class contrast %.4f, %.0fx the 0.02 floor)"
              % (SUBJ[key], key, 100 * occ[key], rep["contrast"],
                 rep["contrast"] / 0.02))
    print("  the vh2 mask's design point was 21%%; it failed at 60%%.")
    return occ


# ---------------------------------------------------------------- part C
def part_c(coarse, occ):
    print("\n=== C. the vh2-style fixed percentile mask, applied HERE ===")
    print("  %-5s %-6s %8s %9s %9s %9s  %s"
          % ("subj", "pctl", "mask%", "n aura", "aura on", "aura:grnd", "verdict"))
    worst = {}
    for key, g in coarse.items():
        truth = extent(g)
        for pctl in (20, 30, 40, 50):
            thr = float(np.percentile(g, pctl))
            sub = (g < thr).astype(np.uint8)
            sub = cv2.morphologyEx(sub, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
            n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
            if n > 1:
                sub = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
            d = cv2.distanceTransform(1 - sub, cv2.DIST_L2, 5)
            bg = (sub == 0)
            a = (d >= 5) & (d <= 13) & bg          # the 40-100 px band, /8 stride
            if a.sum() < 200:
                print("  %-5s %-6d %8.2f %9d %9s %9s  %s"
                      % (key, pctl, 100.0 * sub.mean(), a.sum(), "-", "-",
                         "too few"))
                continue
            on_subject = float(truth[a].mean())
            ratio = 1.0 - on_subject
            bad = ratio < 0.70
            worst[key] = min(worst.get(key, 1.0), ratio)
            print("  %-5s %-6d %8.2f %9d %8.1f%% %9.2f  %s"
                  % (key, pctl, 100.0 * sub.mean(), int(a.sum()),
                     100 * on_subject, ratio,
                     "BELOW the 0.70 floor" if bad else "ok"))
    for key in coarse:
        record("vh2-mask-%s" % key, key in worst,
               "%s: worst aura:ground over 20/30/40/50 pctl = %.2f (occupancy "
               "%.1f%%) -- %s" % (SUBJ[key], worst.get(key, float('nan')),
                                  100 * occ[key],
                                  "would trip the 0.70 floor"
                                  if worst.get(key, 1) < 0.70 else
                                  "clears the 0.70 floor"))

    # Does this verdict depend on the extent estimate being right?  Erode the
    # extent hard -- deliberately UNDER-claiming the subject, the direction that
    # helps the vh2 mask -- and see how far it has to shrink before the aura
    # band clears the 0.70 floor.  If a plausible error cannot flip it, the
    # verdict does not rest on the estimator.
    print("\n  C2. sensitivity: shrink the subject extent until the mask passes")
    print("  %-5s %-9s %8s %10s  %s" % ("subj", "erode px", "extent%",
                                        "aura:grnd", "verdict"))
    for key, g in coarse.items():
        base = extent(g)
        for er in (0, 5, 11, 21, 41):
            t = base if er == 0 else cv2.erode(
                base.astype(np.uint8), np.ones((er, er), np.uint8)) > 0
            thr = float(np.percentile(g, 50))
            sub = (g < thr).astype(np.uint8)
            sub = cv2.morphologyEx(sub, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
            n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
            if n > 1:
                sub = (lab == 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))).astype(np.uint8)
            d = cv2.distanceTransform(1 - sub, cv2.DIST_L2, 5)
            a = (d >= 5) & (d <= 13) & (sub == 0)
            ratio = 1.0 - float(t[a].mean()) if a.sum() else float("nan")
            print("  %-5s %-9d %7.1f%% %10.2f  %s"
                  % (key, er, 100 * t.mean(), ratio,
                     "still below floor" if ratio < 0.70 else "CLEARS floor"))
    return worst


# ---------------------------------------------------------------- part D
def part_d(coarse):
    print("\n=== D. do rois.census FLAT control ROIs land on subject? ===")
    out = {}
    for key in coarse:
        r = h2.Render(os.path.join(LIN, "%s-A-g1.tiff" % key), linear=True,
                      name="%s-A-g1" % key)
        truth = extent(coarse[key])
        for flat_frac, label in ((0.25, "commission.py"), (0.10, "flip.py")):
            detail, flat, counts = rois.census(r, flat_frac=flat_frac,
                                               verbose=False)
            def frac_on_subject(cells):
                if not cells:
                    return float("nan")
                v = []
                for (y, x) in cells:
                    blk = truth[y // 8:y // 8 + 32, x // 8:x // 8 + 32]
                    v.append(float(blk.mean()) if blk.size else 0.0)
                return float(np.mean(v))
            fs, ds = frac_on_subject(flat), frac_on_subject(detail)
            print("  %-5s flat_frac=%.2f (%s): FLAT n=%3d, %5.1f%% on subject | "
                  "DETAIL n=%3d, %5.1f%% on subject"
                  % (key, flat_frac, label, len(flat), 100 * fs, len(detail),
                     100 * ds))
            out[(key, flat_frac)] = (fs, ds)
        del r
    print("\n  The published defence does not rest on FLAT being pure "
          "background.\n  flip-113.txt reports ABSOLUTE coherent power, "
          "FLAT/DETAIL = 0.0645 0.0636\n  0.0821 0.0831 0.0740 0.0556 0.0999 "
          "-- flat ROIs carry 5.6-10.0%% of\n  detail's coherent power in every "
          "band, so contamination of the FLAT\n  control cannot manufacture the "
          "DETAIL result.")
    for (key, ff), (fs, ds) in out.items():
        record("flat-below-detail-%s-%.2f" % (key, ff), fs < ds,
               "%s flat_frac=%.2f: FLAT %.1f%% on subject < DETAIL %.1f%%"
               % (key, ff, 100 * fs, 100 * ds))
    return out


def main():
    part_a()
    part_b_commission()
    coarse = {}
    for key in SUBJ:
        r = h2.Render(os.path.join(LIN, "%s-A-g1.tiff" % key), linear=True,
                      name=key)
        coarse[key] = r.coarse(step=8, chan=1)
        del r
    occ = part_b(coarse)
    part_c(coarse, occ)
    part_d(coarse)

    print("\n=== counted partition of audit checks ===")
    print("  pass %d + fail %d = %d of %d" % (len(_ok), len(_bad),
                                              len(_ok) + len(_bad),
                                              len(_ok) + len(_bad)))
    if _bad:
        print("  FAILED: %s" % ", ".join(_bad))
    return 0 if not _bad else 1


if __name__ == "__main__":
    sys.exit(main())

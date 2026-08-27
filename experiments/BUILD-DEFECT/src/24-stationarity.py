"""Stationarity: does a mote separate from real dark subject detail at the same site?

THE GAP THE ORCHESTRATOR IDENTIFIED

Controls at 0/40 establish specificity across LOCATION -- the check does not fire
at other places in the same frames. It says nothing about specificity against
CONTENT: an eye, a dark hair or a shadow edge that happens to land on
(3434, 2305) reads as a local darkening, fires the check correctly by its own
definition, and the correction then brightens real image detail.

THE DISCRIMINATOR, AND WHY IT SHOULD BE STRONG HERE

Dust is fixed in raw sensor coordinates. The subject is not: the bracket breathes,
and another lane fitted a 1.070 scale between a middle frame and its master on
bee-3-cpl. Both motes sit far off-axis -- mote2 is ~2024 quads from the frame
centre -- so a 7% magnification change moves subject content there by roughly
142 quads, against a mote core radius of ~14. Ten to one. If stationarity is ever
going to separate them, it separates them here.

WHY THIS IS A CONTROLLED EXPERIMENT AND NOT AN OBSERVATIONAL ONE

Looking for a naturally-occurring dark subject feature at the mote coordinates
across the corpus would be a search that cannot fail: whatever the darkest
impostor turns out to be, I would report it. Instead I PLANT both arms with
IDENTICAL depth and radius and vary only whether they move:

  FIXED   -8% disc pinned in raw sensor coords          -> must fire  (a mote)
  MOVING  -8% disc following the bracket's own drift    -> must NOT fire (subject)

Same depth, same size, same stack, same site. The only difference is motion, so
anything that separates them is motion and nothing else.

Plus, per standing policy after two instruments in this project read backwards:

  IMPROVE  a real firing mote divided out    -> presence must COLLAPSE
  PERVERSE a +8% BRIGHT fixed disc           -> must NOT fire as a mote

THE STATISTIC

presence = fraction of individual frames whose depth at the site clears the
floor. Dust is multiplicatively present in every frame, so presence -> 1.0.
A feature that translates through the site is absent from most frames, so
presence falls. This is the cheaper of the two guards the orchestrator allowed
(consistency across a sample of frames rather than in the aggregate), and it
needs no registration, no warp and no second pass -- the per-frame residuals are
already computed to form the pooled median.
"""
import glob
import os
import sys

import numpy as np
import rawpy
from scipy import ndimage

SRC_ROOT = r"D:\personal\macro"
HP_RADIUS, HP_PASS, BP_RADIUS = 64, 2, 3
CORE_RADIUS, ANNULUS_IN, ANNULUS_OUT = 8, 60, 400
N_LOCAL_NULL, P_BAR, DEPTH_FLOOR = 400, 0.0025, 0.015
PRESENCE_BAR = 0.75            # >= this fraction of frames must show the darkening
FRAME_FLOOR = 0.010            # a frame "shows" it at >= 1.0% depth
MOTE2 = (2305, 3434)
PLANT_DEPTH, PLANT_R = 0.08, 14
DRIFT_SCALE = 1.070            # measured on bee-3-cpl by another lane


def box_smooth(a, radius, npass):
    cur = a.astype(np.float64); win = 2 * radius + 1
    for _ in range(npass):
        cur = ndimage.uniform_filter1d(cur, win, axis=1, mode="nearest")
        cur = ndimage.uniform_filter1d(cur, win, axis=0, mode="nearest")
    return cur


def quad_mean(raw, black):
    v = raw.astype(np.float64) - black
    return 0.25 * (v[0::2, 0::2] + v[0::2, 1::2] + v[1::2, 0::2] + v[1::2, 1::2])


def residual(q):
    lo = box_smooth(q, HP_RADIUS, HP_PASS)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(lo > 1.0, q / lo - 1.0, np.nan)
    return box_smooth(np.nan_to_num(r), BP_RADIUS, 1)


def disc(D, cy, cx, r):
    h, w = D.shape
    y0, y1 = max(0, cy - r), min(h, cy + r + 1)
    x0, x1 = max(0, cx - r), min(w, cx + r + 1)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    return D[y0:y1, x0:x1][(yy - cy) ** 2 + (xx - cx) ** 2 <= r * r]


def null_p(D, cy, cx, v, rng):
    h, w = D.shape
    out, got, tries = np.empty(N_LOCAL_NULL), 0, 0
    while got < N_LOCAL_NULL and tries < 40 * N_LOCAL_NULL:
        tries += 1
        a = rng.uniform(0, 2 * np.pi); d = rng.uniform(ANNULUS_IN, ANNULUS_OUT)
        oy, ox = int(cy + d * np.sin(a)), int(cx + d * np.cos(a))
        if not (CORE_RADIUS < oy < h - CORE_RADIUS and CORE_RADIUS < ox < w - CORE_RADIUS):
            continue
        out[got] = np.median(disc(D, oy, ox, CORE_RADIUS)); got += 1
    return (1.0 + float((out[:got] <= v).sum())) / (1.0 + got)


def plant_at(q, cy, cx, depth, r=PLANT_R):
    h, w = q.shape
    yy, xx = np.ogrid[0:h, 0:w]
    return q * np.where((yy - cy) ** 2 + (xx - cx) ** 2 <= r * r, 1.0 - depth, 1.0)


def drift_positions(shape, cy, cx, n):
    """Where a SUBJECT feature at (cy,cx) sits in each frame, under the bracket's
    own magnification drift about the frame centre."""
    h, w = shape
    fy, fx = h / 2.0, w / 2.0
    out = []
    for s in np.linspace(1.0, DRIFT_SCALE, n):
        out.append((int(fy + s * (cy - fy)), int(fx + s * (cx - fx))))
    return out


def assess(qs, cy, cx, rng, label):
    """Return (pooled_depth, p, presence, fires). All three bars must clear."""
    Rs = [residual(q) for q in qs]
    per = [float(np.median(disc(R, cy, cx, CORE_RADIUS))) for R in Rs]
    R = np.median(np.stack(Rs), axis=0)
    v = float(np.median(disc(R, cy, cx, CORE_RADIUS)))
    p = null_p(R, cy, cx, v, rng)
    presence = float(np.mean([d <= -FRAME_FLOOR for d in per]))
    fires = bool(p <= P_BAR and v <= -DEPTH_FLOOR and presence >= PRESENCE_BAR)
    return v, p, presence, fires, per


def main():
    subs = sys.argv[1:] or ["highly-angled-ruler-mm-cpl", "lavendar-cpl",
                            "couch-fibers-cpl", "leaf-2-cpl"]
    rng = np.random.default_rng(2718281)
    cy, cx = MOTE2
    print("STATIONARITY.  presence = fraction of individual frames showing >= %.1f%% depth"
          % (FRAME_FLOOR * 100))
    print("bars: p <= %.4f  AND  pooled depth <= -%.1f%%  AND  presence >= %.2f\n"
          % (P_BAR, DEPTH_FLOOR * 100, PRESENCE_BAR))
    print("%-25s %-22s %9s %8s %9s %6s" % ("subject", "arm", "depth", "p", "presence", "fires"))
    print("-" * 84)
    fails, seen = [], 0
    for sub in subs:
        arw = sorted(glob.glob(os.path.join(SRC_ROOT, sub, "*.ARW")))
        if not arw:
            print("%-25s (no frames)" % sub[:25]); continue
        idx = np.linspace(0, len(arw) - 1, 8).astype(int)
        qs = []
        for i in idx:
            with rawpy.imread(arw[i]) as r:
                qs.append(quad_mean(r.raw_image_visible,
                                    float(np.mean(r.black_level_per_channel))))
        seen += 1
        # REAL: the committed mote, untouched
        v, p, pr, f, per = assess(qs, cy, cx, rng, "REAL")
        print("%-25s %-22s %8.3f%% %8.4f %9.2f %6s" % (sub[:25], "REAL mote2", v * 100, p, pr, f))
        if not f:
            print("%-25s %-22s (stack does not fire; planted arms still valid)" % ("", ""))

        # Use a clean site for the planted pair so the real mote cannot contaminate them
        py, px = 1500, 3250
        # FIXED planted mote -> must fire
        qf = [plant_at(q, py, px, PLANT_DEPTH) for q in qs]
        v, p, pr, f, _ = assess(qf, py, px, rng, "FIXED")
        print("%-25s %-22s %8.3f%% %8.4f %9.2f %6s" % ("", "FIXED planted -8%", v * 100, p, pr, f))
        if not f:
            fails.append("%s FIXED planted mote did not fire" % sub)
        # MOVING planted feature, same depth and radius -> must NOT fire
        pos = drift_positions(qs[0].shape, py, px, len(qs))
        qm = [plant_at(q, y, x, PLANT_DEPTH) for q, (y, x) in zip(qs, pos)]
        v, p, pr, f, _ = assess(qm, py, px, rng, "MOVING")
        print("%-25s %-22s %8.3f%% %8.4f %9.2f %6s   (moved %d quads)"
              % ("", "MOVING planted -8%", v * 100, p, pr, f,
                 abs(pos[-1][0] - pos[0][0]) + abs(pos[-1][1] - pos[0][1])))
        if f:
            fails.append("%s MOVING subject feature FIRED -- would brighten real detail" % sub)
        # PERVERSE: +8% bright fixed disc -> must not fire
        qb = [plant_at(q, py, px, -PLANT_DEPTH) for q in qs]
        v, p, pr, f, _ = assess(qb, py, px, rng, "PERVERSE")
        print("%-25s %-22s %8.3f%% %8.4f %9.2f %6s" % ("", "PERVERSE planted +8%", v * 100, p, pr, f))
        if f:
            fails.append("%s PERVERSE bright disc fired" % sub)
        # IMPROVE: divide the FIXED planted mote back out -> presence must collapse
        qi = [plant_at(plant_at(q, py, px, PLANT_DEPTH), py, px, -PLANT_DEPTH / (1 - PLANT_DEPTH))
              for q in qs]
        v, p, pr, f, _ = assess(qi, py, px, rng, "IMPROVE")
        print("%-25s %-22s %8.3f%% %8.4f %9.2f %6s" % ("", "IMPROVE mote removed", v * 100, p, pr, f))
        if f:
            fails.append("%s IMPROVE arm still fired" % sub)
        print()
    print("=" * 84)
    print("examined %d stacks" % seen)
    if fails:
        print("FAILURES (%d):" % len(fails))
        for x in fails:
            print("   " + x)
        return 1
    print("all arms PASS -- stationarity separates a mote from moving subject detail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

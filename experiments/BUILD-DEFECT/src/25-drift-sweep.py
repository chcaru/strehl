"""Does the `presence` bar earn its place, and where does stationarity stop separating?

WHAT 24 LEFT UNANSWERED

Script 24 put a MOVING planted feature through the check and it did not fire, on
4 of 4 stacks. Good -- but look at WHICH bar rejected it. Pooled depth came out
at -0.044%, -0.033%, -0.423%, -1.141%, all of which fail the -1.5% depth bar on
their own. So on that evidence the depth bar alone was sufficient and `presence`
never did any work. A gate condition that nothing has ever been shown to decide
is dead weight, and dead weight in a gate is not neutral: it can only cause false
SKIPs. Either presence is load-bearing or it should not ship.

The reason 24 could not answer this is that it tested a single drift, 1.070, the
largest breathing scale anyone here has measured. At that drift the feature
leaves the site entirely and every statistic collapses together. The question is
what happens on a SHALLOWER bracket, where a real dark feature moves only a
little and stays partly over the site in every frame.

THE EXPERIMENT

Sweep the drift scale from 1.000 (perfectly stationary) to 1.070 (the measured
maximum) and record where each bar crosses. The plant is at (1500, 3250), 1528
quads off the frame centre, so scale s displaces it by (s-1)*1528 quads against a
plant radius of 14.

  If presence crosses at LOWER drift than depth, presence is load-bearing: there
  is a band of motion where a moving feature still reads deep enough to fire and
  only per-frame consistency rejects it.

  If depth crosses first, presence is redundant on this evidence and I should say
  so rather than ship a bar I cannot show doing anything.

THE ARM THAT MUST FIRE, AND THE LIMIT IT STATES

At s = 1.000 the "moving" feature does not move, and it MUST fire. That is not a
failure -- it is the honest boundary of the whole approach. A dark subject
feature that is genuinely motionless in raw sensor coordinates across an entire
bracket is, by construction, doing exactly what dust does, and no test built on
motion can tell them apart. Reporting the drift at which separation begins is
reporting the instrument's domain of validity, which is the point.
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
PRESENCE_BAR, FRAME_FLOOR = 0.75, 0.010
PLANT_DEPTH, PLANT_R = 0.08, 14
PLANT_SITE = (1500, 3250)
SCALES = [1.000, 1.004, 1.008, 1.012, 1.016, 1.020, 1.030, 1.050, 1.070]


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


def drift_positions(shape, cy, cx, n, scale):
    h, w = shape
    fy, fx = h / 2.0, w / 2.0
    return [(int(fy + s * (cy - fy)), int(fx + s * (cx - fx)))
            for s in np.linspace(1.0, scale, n)]


def assess(qs, cy, cx, rng):
    Rs = [residual(q) for q in qs]
    per = [float(np.median(disc(R, cy, cx, CORE_RADIUS))) for R in Rs]
    R = np.median(np.stack(Rs), axis=0)
    v = float(np.median(disc(R, cy, cx, CORE_RADIUS)))
    p = null_p(R, cy, cx, v, rng)
    presence = float(np.mean([d <= -FRAME_FLOOR for d in per]))
    return v, p, presence


def main():
    subs = sys.argv[1:] or ["lavendar-cpl", "leaf-2-cpl"]
    rng = np.random.default_rng(31415926)
    py, px = PLANT_SITE
    print("DRIFT SWEEP.  planted -%.0f%% disc, radius %d quads, at quad (%d,%d)"
          % (PLANT_DEPTH * 100, PLANT_R, py, px))
    print("bars: p <= %.4f  AND  depth <= -%.1f%%  AND  presence >= %.2f"
          % (P_BAR, DEPTH_FLOOR * 100, PRESENCE_BAR))
    print("question: which bar rejects first as the feature starts to move?\n")

    crossings = []
    for sub in subs:
        arw = sorted(glob.glob(os.path.join(SRC_ROOT, sub, "*.ARW")))
        if not arw:
            print("%s: no frames" % sub); continue
        idx = np.linspace(0, len(arw) - 1, 8).astype(int)
        qs = []
        for i in idx:
            with rawpy.imread(arw[i]) as r:
                qs.append(quad_mean(r.raw_image_visible,
                                    float(np.mean(r.black_level_per_channel))))
        h, w = qs[0].shape
        off = float(np.hypot(py - h / 2.0, px - w / 2.0))
        print("%s  (site is %.0f quads off centre)" % (sub, off))
        print("  %-7s %8s %9s %8s %9s   %-7s %-7s %-9s %s"
              % ("scale", "shift", "depth", "p", "presence",
                 "p ok", "dep ok", "pres ok", "FIRES"))
        dep_cross = pres_cross = None
        for s in SCALES:
            pos = drift_positions(qs[0].shape, py, px, len(qs), s)
            qm = [plant_at(q, y, x, PLANT_DEPTH) for q, (y, x) in zip(qs, pos)]
            v, p, pr = assess(qm, py, px, rng)
            shift = float(np.hypot(pos[-1][0] - pos[0][0], pos[-1][1] - pos[0][1]))
            ok_p, ok_d, ok_r = p <= P_BAR, v <= -DEPTH_FLOOR, pr >= PRESENCE_BAR
            fires = ok_p and ok_d and ok_r
            print("  %-7.3f %7.1fq %8.3f%% %8.4f %9.2f   %-7s %-7s %-9s %s"
                  % (s, shift, v * 100, p, pr, ok_p, ok_d, ok_r, fires))
            if dep_cross is None and not ok_d:
                dep_cross = (s, shift)
            if pres_cross is None and not ok_r:
                pres_cross = (s, shift)
        crossings.append((sub, dep_cross, pres_cross))
        print()

    print("=" * 92)
    print("WHERE EACH BAR FIRST REJECTS")
    verdict = []
    for sub, dc, pc in crossings:
        ds = "never in range" if dc is None else "scale %.3f (%.0f quads)" % dc
        ps = "never in range" if pc is None else "scale %.3f (%.0f quads)" % pc
        print("  %-20s depth bar: %-28s presence bar: %s" % (sub, ds, ps))
        if pc is not None and (dc is None or pc[1] < dc[1]):
            verdict.append("load-bearing")
        elif pc is not None and dc is not None and pc[1] == dc[1]:
            verdict.append("simultaneous")
        else:
            verdict.append("redundant")
    print()
    if all(v == "load-bearing" for v in verdict):
        print("VERDICT: presence is LOAD-BEARING -- it rejects moving content at drifts")
        print("         where the depth bar alone would still have fired. Ship all three.")
    elif all(v == "redundant" for v in verdict):
        print("VERDICT: presence is REDUNDANT on this evidence -- the depth bar rejects")
        print("         at or before every drift presence does. Report it as such.")
    else:
        print("VERDICT: MIXED across stacks -- %s. Report per-stack, claim nothing global."
              % ", ".join("%s=%s" % (s, v) for (s, _, _), v in zip(crossings, verdict)))
    print()
    print("NOTE: scale 1.000 is the stationary control. It MUST fire -- a dark subject")
    print("      feature that never moves is doing exactly what dust does, and that is")
    print("      the stated limit of a motion-based discriminator, not a defect in it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

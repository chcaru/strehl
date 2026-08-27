"""Depth varies 1.8x across stacks. Is it aperture? And what does the check cost?

Script 20, once the raw_image/raw_image_visible coordinate bug was fixed, gave a
usable per-stack detector: mote2 fires in 8 of 10 stacks, mote1 in 6 of 10, and
zero of 40 control sites fire. But the measured depth at the SAME sensor site
ranges from -5.7% to -14.8% against a map that records -8.24%, and coffee-bean
reads -14.758% -- 1.8x the map's nominal.

That matters more than it looks. If the correction applies the MAP's gain, then
on coffee-bean it removes 8.2 points of a 14.8 point defect and leaves a 6.6
point mote behind, while on tweezers-cpl (-5.7%) it would remove 8.2 points from
a 5.7 point defect and OVERSHOOT into a bright spot -- manufacturing the inverse
defect. That is the same failure the orchestrator's staleness objection is about,
arriving through amplitude instead of through position.

My own BUILD-DEFECT report predicted this and left it open as Q2/Q4:
"a smaller aperture makes a mote smaller and deeper. Untested." A dust mote is
an out-of-focus shadow of a particle sitting above the sensor, so its shadow
sharpens and deepens as the aperture closes. If the depth spread tracks
aperture, Q2 is answered and the design consequence is immediate: the map may
nominate the LOCATION but must not dictate the AMPLITUDE.

Also measures the two costs the orchestrator asked for:
  (a) full-frame residual, as script 20 ran it
  (b) cropped residual -- the null only draws out to 400 quads, so a window
      around each site is sufficient and should be ~10x cheaper
"""
import glob
import os
import subprocess
import sys
import time

import numpy as np
import rawpy
from scipy import ndimage

SRC_ROOT = r"D:\personal\macro"
EXIFTOOL = r"C:\Users\chris\AppData\Local\Programs\ExifTool\ExifTool.exe"

HP_RADIUS, HP_PASS, BP_RADIUS = 64, 2, 3
CORE_RADIUS, ANNULUS_IN, ANNULUS_OUT = 8, 60, 400
N_LOCAL_NULL, P_BAR, DEPTH_FLOOR = 400, 0.0025, 0.015
MOTES = {"mote1": (121, 3202), "mote2": (2305, 3434)}
MAP_NOMINAL = {"mote1": -0.036303, "mote2": -0.082359}
WIN = 560          # half-window for the cropped residual: > ANNULUS_OUT + support


def box_smooth(a, radius, npass):
    cur = a.astype(np.float64)
    win = 2 * radius + 1
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


def local_null(D, cy, cx, rng, n=N_LOCAL_NULL, r=CORE_RADIUS):
    h, w = D.shape
    out, got = np.empty(n), 0
    tries = 0
    while got < n and tries < 40 * n:
        tries += 1
        a = rng.uniform(0, 2 * np.pi)
        d = rng.uniform(ANNULUS_IN, ANNULUS_OUT)
        oy, ox = int(cy + d * np.sin(a)), int(cx + d * np.cos(a))
        if not (r < oy < h - r and r < ox < w - r):
            continue
        out[got] = np.median(disc(D, oy, ox, r)); got += 1
    return out[:got]


def score(D, cy, cx, rng):
    v = float(np.median(disc(D, cy, cx, CORE_RADIUS)))
    null = local_null(D, cy, cx, rng)
    p = (1.0 + float((null <= v).sum())) / (1.0 + len(null))
    return v, p, bool(p <= P_BAR and v <= -DEPTH_FLOOR)


def plant(q, cy, cx, depth, r=14):
    h, w = q.shape
    yy, xx = np.ogrid[0:h, 0:w]
    return q * np.where((yy - cy) ** 2 + (xx - cx) ** 2 <= r * r, 1.0 - depth, 1.0)


def aperture(path):
    try:
        o = subprocess.run([EXIFTOOL, "-s3", "-FNumber", path], capture_output=True,
                           text=True, timeout=30).stdout.strip()
        return float(o) if o else float("nan")
    except Exception:
        return float("nan")


def main():
    subs = sys.argv[1:] or [
        "highly-angled-ruler-mm-cpl", "pencil-steep-angle-cpl", "coffee-bean",
        "tweezers-cpl", "couch-fibers-cpl", "flower-bud-alone-cpl",
        "bee-3-cpl", "wrapped-text-1", "lavendar-cpl", "leaf-2-cpl",
    ]
    rng = np.random.default_rng(31415)
    print("A. MEASURED DEPTH vs APERTURE.  map nominal mote2 = %.3f%%"
          % (MAP_NOMINAL["mote2"] * 100))
    print("%-27s %6s %10s %8s %10s %9s" % ("subject", "f/", "mote2 %", "p", "vs map", "mote1 %"))
    print("-" * 76)
    rows = []
    for sub in subs:
        arw = sorted(glob.glob(os.path.join(SRC_ROOT, sub, "*.ARW")))
        if not arw:
            continue
        idx = np.linspace(0, len(arw) - 1, min(8, len(arw))).astype(int)
        qs = []
        for i in idx:
            with rawpy.imread(arw[i]) as r:
                qs.append(quad_mean(r.raw_image_visible,
                                    float(np.mean(r.black_level_per_channel))))
        R = np.median(np.stack([residual(q) for q in qs]), axis=0)
        d2, p2, f2 = score(R, *MOTES["mote2"], rng)
        d1, p1, f1 = score(R, *MOTES["mote1"], rng)
        fn = aperture(arw[idx[0]])
        rows.append((sub, fn, d2, p2, f2, d1, p1, f1, qs, R))
        print("%-27s %6.1f %9.3f%% %8.4f %9.2fx %8.3f%%"
              % (sub[:27], fn, d2 * 100, p2, d2 / MAP_NOMINAL["mote2"], d1 * 100))

    fires = [r for r in rows if r[4]]
    if len(fires) >= 3:
        f_ = np.array([r[1] for r in fires]); d_ = np.array([r[2] for r in fires])
        print("\namong the %d stacks where mote2 FIRES:" % len(fires))
        print("  apertures present: %s" % sorted(set(f_.tolist())))
        print("  depth range %.3f%% .. %.3f%%  (%.2fx spread)"
              % (d_.min() * 100, d_.max() * 100, d_.min() / d_.max()))
        if len(set(f_.tolist())) > 1:
            print("  corr(f-number, depth) = %+.4f" % np.corrcoef(f_, d_)[0, 1])
            for fv in sorted(set(f_.tolist())):
                sel = d_[f_ == fv]
                print("    f/%-5.1f n=%d  mean depth %.3f%%" % (fv, len(sel), sel.mean() * 100))
        else:
            print("  ONE aperture only -- aperture CANNOT be the explanation here.")

    print("\n" + "=" * 88)
    print("B. IMPROVEMENT ARM, corrected: remove the MEASURED depth, not the map's")
    print("%-27s %10s %10s %8s %6s" % ("subject", "before %", "after %", "p", "fires"))
    print("-" * 66)
    fails = []
    for sub, fn, d2, p2, f2, d1, p1, f1, qs, R in rows[:5]:
        if not f2:
            print("%-27s %9.3f%% %10s %8s %6s" % (sub[:27], d2 * 100, "-", "-", "skipped"))
            continue
        cy, cx = MOTES["mote2"]
        Ri = np.median(np.stack([residual(plant(q, cy, cx, d2)) for q in qs]), axis=0)
        da, pa, fa = score(Ri, cy, cx, rng)
        print("%-27s %9.3f%% %9.3f%% %8.4f %6s" % (sub[:27], d2 * 100, da * 100, pa, fa))
        if fa:
            fails.append("%s improvement still fires (%.3f%%)" % (sub, da * 100))

    print("\n" + "=" * 88)
    print("C. COST: full-frame residual vs cropped-window residual")
    q0 = rows[0][8][0]
    t = time.time()
    for _ in range(3):
        residual(q0)
    tfull = (time.time() - t) / 3
    cy, cx = MOTES["mote2"]
    h, w = q0.shape
    y0, y1 = max(0, cy - WIN), min(h, cy + WIN)
    x0, x1 = max(0, cx - WIN), min(w, cx + WIN)
    t = time.time()
    for _ in range(3):
        residual(q0[y0:y1, x0:x1])
    tcrop = (time.time() - t) / 3
    Rc = residual(q0[y0:y1, x0:x1])
    Rf = residual(q0)
    vc = float(np.median(disc(Rc, cy - y0, cx - x0, CORE_RADIUS)))
    vf = float(np.median(disc(Rf, cy, cx, CORE_RADIUS)))
    print("  quad frame %dx%d ; window %dx%d around each site" % (h, w, y1 - y0, x1 - x0))
    print("  full-frame residual  %.3f s/frame" % tfull)
    print("  cropped   residual   %.3f s/frame  (%.1fx cheaper)" % (tcrop, tfull / tcrop))
    print("  two sites            %.3f s/frame" % (2 * tcrop))
    print("  agreement full vs cropped at mote2: %.4f%% vs %.4f%%  (delta %.4f pp)"
          % (vf * 100, vc * 100, abs(vf - vc) * 100))
    if abs(vf - vc) > 0.002:
        fails.append("cropped residual disagrees with full frame by %.4f pp" % (abs(vf - vc) * 100))

    print("\n" + "=" * 88)
    if fails:
        print("FAILURES (%d):" % len(fails))
        for x in fails:
            print("   " + x)
        return 1
    print("all arms PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

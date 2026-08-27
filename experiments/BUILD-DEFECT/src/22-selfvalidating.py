"""The proposed algorithm end to end, with the arm that tests the whole design.

Script 21 settled three things. Depth at a fixed sensor site varies 1.91x across
stacks (-7.737% to -14.758%) and the one f/8 stack reads 1.79x the f/5.6 map
nominal, so the map must not dictate amplitude. The cropped-window residual
agrees with the full-frame one to 0.0000 pp and is 23.5x cheaper. And the
detector fires on 8 of 10 stacks with 0 of 40 controls.

This script runs the algorithm as it would ship, using the map's REAL per-quad
gain profile rather than a flat disc, and commissions it on the arm that decides
whether the orchestrator's design holds:

  STALENESS ARM.  Simulate a CLEANED SENSOR by dividing the real mote out of the
  frames, then run the whole check unmodified. It must SKIP. If it corrects, the
  self-validation does not actually protect against a stale map and the whole
  argument for defaulting ON collapses.

  MANUFACTURE ARM.  Apply the correction at a site where there is no mote and
  measure what it does to a clean image. This quantifies exactly what a stale
  map costs when the guard is absent -- i.e. what default-ON without
  self-validation would have shipped.

  IMPROVEMENT ARM.  Apply the profile-scaled correction where the mote IS real,
  and require the residual to fall below the detection floor.

The correction scales the map profile in log-gain space to hit the measured
depth: g' = exp(ln(g) * s), s = ln(1/(1-|d_meas|)) / ln(1/(1-|d_map|)). Shape
from the map, amplitude from the frames in front of us.
"""
import glob
import os
import sys

import numpy as np
import rawpy
from scipy import ndimage

SRC_ROOT = r"D:\personal\macro"
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAP = os.path.join(HERE, "out", "defect-map-ILCE-7CM2-photo.txt")

HP_RADIUS, HP_PASS, BP_RADIUS = 64, 2, 3
CORE_RADIUS, ANNULUS_IN, ANNULUS_OUT = 8, 60, 400
N_LOCAL_NULL, P_BAR, DEPTH_FLOOR = 400, 0.0025, 0.015
MOTES = {"mote1": (121, 3202), "mote2": (2305, 3434)}
MAP_NOMINAL = {"mote1": 0.036303, "mote2": 0.082359}
WIN = 560


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


def score(D, cy, cx, rng):
    v = float(np.median(disc(D, cy, cx, CORE_RADIUS)))
    h, w = D.shape
    out, got, tries = np.empty(N_LOCAL_NULL), 0, 0
    while got < N_LOCAL_NULL and tries < 40 * N_LOCAL_NULL:
        tries += 1
        a = rng.uniform(0, 2 * np.pi); d = rng.uniform(ANNULUS_IN, ANNULUS_OUT)
        oy, ox = int(cy + d * np.sin(a)), int(cx + d * np.cos(a))
        if not (CORE_RADIUS < oy < h - CORE_RADIUS and CORE_RADIUS < ox < w - CORE_RADIUS):
            continue
        out[got] = np.median(disc(D, oy, ox, CORE_RADIUS)); got += 1
    null = out[:got]
    p = (1.0 + float((null <= v).sum())) / (1.0 + got)
    return v, p, bool(p <= P_BAR and v <= -DEPTH_FLOOR)


def load_map():
    """Return {name: (ys, xs, gains)} grouped by nearest nominated mote."""
    pts = []
    with open(MAP) as f:
        for line in f:
            if line.startswith("d "):
                _, x, y, g = line.split()
                pts.append((int(y), int(x), float(g)))
    out = {}
    for name, (my, mx) in MOTES.items():
        sel = [(y, x, g) for y, x, g in pts if abs(y - my) < 40 and abs(x - mx) < 40]
        if sel:
            ys, xs, gs = zip(*sel)
            out[name] = (np.array(ys), np.array(xs), np.array(gs))
    return out


def apply_corr(q, site, depth_meas, nominal):
    """Shape from the map, amplitude from the frames. Returns a corrected copy."""
    ys, xs, gs = site
    s = np.log(1.0 / (1.0 - abs(depth_meas))) / np.log(1.0 / (1.0 - nominal))
    out = q.copy()
    out[ys, xs] = out[ys, xs] * np.exp(np.log(gs) * s)
    return out


def stack_of(sub, n=8):
    arw = sorted(glob.glob(os.path.join(SRC_ROOT, sub, "*.ARW")))
    if not arw:
        return None
    idx = np.linspace(0, len(arw) - 1, min(n, len(arw))).astype(int)
    qs = []
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            qs.append(quad_mean(r.raw_image_visible,
                                float(np.mean(r.black_level_per_channel))))
    return qs


def pooled(qs):
    return np.median(np.stack([residual(q) for q in qs]), axis=0)


def main():
    subs = sys.argv[1:] or ["highly-angled-ruler-mm-cpl", "pencil-steep-angle-cpl",
                            "coffee-bean", "couch-fibers-cpl", "lavendar-cpl",
                            "tweezers-cpl"]
    rng = np.random.default_rng(16180)
    sites = load_map()
    print("map profile: " + ", ".join("%s %d quads, peak gain %.4f"
                                      % (k, len(v[2]), v[2].max()) for k, v in sites.items()))
    print("\n%-27s %10s %8s %7s %11s %11s %8s"
          % ("subject", "measured", "p", "action", "after corr", "STALE->", "MANUF"))
    print("-" * 92)
    n_corr = n_skip = 0
    fails = []
    for sub in subs:
        qs = stack_of(sub)
        if qs is None:
            print("%-27s (no frames)" % sub[:27]); continue
        cy, cx = MOTES["mote2"]
        R = pooled(qs)
        d, p, fire = score(R, cy, cx, rng)
        if not fire:
            n_skip += 1
            print("%-27s %9.3f%% %8.4f %7s %11s %11s %8s"
                  % (sub[:27], d * 100, p, "SKIP", "-", "-", "-"))
            continue
        n_corr += 1
        # IMPROVEMENT: profile-scaled correction, then re-measure
        qc = [apply_corr(q, sites["mote2"], d, MAP_NOMINAL["mote2"]) for q in qs]
        da, pa, fa = score(pooled(qc), cy, cx, rng)
        if fa:
            fails.append("%s: correction left a still-firing mote (%.3f%%)" % (sub, da * 100))
        # STALENESS: pretend the sensor was cleaned, then run the check unmodified
        qs_clean = [apply_corr(q, sites["mote2"], d, MAP_NOMINAL["mote2"]) for q in qs]
        ds, ps, fs = score(pooled(qs_clean), cy, cx, rng)
        if fs:
            fails.append("%s: STALENESS arm corrected a cleaned sensor" % sub)
        # MANUFACTURE: what the correction does at a site with no mote
        ctrl = (1500, 3250)
        shift = (ctrl[0] - cy, ctrl[1] - cx)
        moved = (sites["mote2"][0] + shift[0], sites["mote2"][1] + shift[1], sites["mote2"][2])
        qm = [apply_corr(q, moved, d, MAP_NOMINAL["mote2"]) for q in qs]
        Rm = pooled(qm)
        dm = float(np.median(disc(Rm, ctrl[0], ctrl[1], CORE_RADIUS)))
        d0 = float(np.median(disc(R, ctrl[0], ctrl[1], CORE_RADIUS)))
        print("%-27s %9.3f%% %8.4f %7s %10.3f%% %10s %+7.2f%%"
              % (sub[:27], d * 100, p, "CORRECT", da * 100,
                 "SKIP" if not fs else "CORRECT!", (dm - d0) * 100))
    print("-" * 92)
    print("examined %d   corrected %d   skipped %d   (sums to total)"
          % (len(subs), n_corr, n_skip))
    print("\nSTALE->  = decision after the mote is divided out (a cleaned sensor). Must be SKIP.")
    print("MANUF    = brightening the correction would inject at a CLEAN site if unguarded.")
    print("\n" + "=" * 92)
    if fails:
        print("FAILURES (%d):" % len(fails))
        for x in fails:
            print("   " + x)
        return 1
    print("all arms PASS -- self-validation blocks the stale-map failure mode")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

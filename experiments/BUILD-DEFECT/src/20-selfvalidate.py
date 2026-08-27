"""Can ONE stack self-validate a nominated mote from its own frames?

THE ORCHESTRATOR'S DESIGN, AND THE ONE THING THAT COULD SINK IT

The proposal is to make the map self-validating at the point of use: before
correcting a nominated site, confirm from the frames in front of us that the
darkening is really there, and skip the site if it is not. That answers the
staleness objection structurally -- a stale map cannot manufacture a defect it
is required to observe first -- and if it holds, the correction can default ON.

The thing that could sink it is statistical power. The committed map established
these two motes at p = 0.0025, but it did so by POOLING 12 subject stacks x 8
frames. A per-stack check has one twelfth of that evidence. If a single stack
cannot clear the bar, the check silently no-ops, the correction never fires, and
we ship a default-on feature that does nothing -- which is worse than opt-in,
because it looks like it works.

So the question is not "is the design elegant", it is "does one stack reach
p <= 0.0025", and it is answerable by measurement on data already on disk.

WHY THIS IS CHEAP, AND WHERE IT READS

quad_mean() reads raw.raw_image -- the Bayer array, black-subtracted and 2x2
averaged. No demosaic, no white balance, no warp. That is the same coordinate
system the correction is applied in and the same one the map is written in, so
the check reads exactly the data it will modify. There is no interaction with
the aligner because the check happens strictly before it.

ARMS, INCLUDING AN IMPROVEMENT ARM

Two instruments in this project have now been caught reading backwards, both
because every arm ever planted made the image worse. So:

  REAL          the two committed motes, per stack        expect FIRE
  CONTROL       clean sites, same geometry, same stacks   expect NO FIRE
  DEFECT        a planted -4% disc at a clean site        expect FIRE
  IMPROVEMENT   the REAL mote divided back out           expect NO FIRE  <-- key
  PERVERSE      a planted +4% BRIGHT disc                 expect NO FIRE

The IMPROVEMENT arm is the one that distinguishes a detector that works from a
detector that fires on any local structure: if dividing the mote out does not
switch it off, it was never measuring the mote.
"""
import os
import sys
import time
import glob

import numpy as np
import rawpy
from scipy import ndimage

SRC_ROOT = r"D:\personal\macro"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

HP_RADIUS, HP_PASS, BP_RADIUS = 64, 2, 3
CORE_RADIUS = 8
ANNULUS_IN, ANNULUS_OUT = 60, 400
N_LOCAL_NULL = 400
P_BAR = 0.0025
DEPTH_FLOOR = 0.015          # absolute floor: a search that cannot fail is not a search

MOTES = {"mote1": (121, 3202), "mote2": (2305, 3434)}      # (cy, cx) in QUADS
CONTROLS = {"ctrlA": (300, 3300), "ctrlB": (1500, 3250),
            "ctrlC": (2000, 3100), "ctrlD": (900, 3400)}


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
    while got < n:
        a = rng.uniform(0, 2 * np.pi)
        d = rng.uniform(ANNULUS_IN, ANNULUS_OUT)
        oy, ox = int(cy + d * np.sin(a)), int(cx + d * np.cos(a))
        if not (r < oy < h - r and r < ox < w - r):
            continue
        out[got] = np.median(disc(D, oy, ox, r))
        got += 1
    return out


def score(D, cy, cx, rng):
    """Return (depth, p, fires). Both bars must be cleared to fire."""
    v = float(np.median(disc(D, cy, cx, CORE_RADIUS)))
    null = local_null(D, cy, cx, rng)
    p = (1.0 + float((null <= v).sum())) / (1.0 + N_LOCAL_NULL)
    fires = bool(p <= P_BAR and v <= -DEPTH_FLOOR)
    return v, p, fires


def plant(q, cy, cx, depth, r=14):
    h, w = q.shape
    yy, xx = np.ogrid[0:h, 0:w]
    m = (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    return q * np.where(m, 1.0 - depth, 1.0)


def load_stack(subject, nframes):
    arw = sorted(glob.glob(os.path.join(SRC_ROOT, subject, "*.ARW")))
    if not arw:
        return None, 0.0, 0
    idx = np.linspace(0, len(arw) - 1, min(nframes, len(arw))).astype(int)
    qs, t0 = [], time.time()
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            qs.append(quad_mean(r.raw_image_visible, float(np.mean(r.black_level_per_channel))))
    return qs, time.time() - t0, len(arw)


def main():
    subs = sys.argv[1:] or [
        "highly-angled-ruler-mm-cpl", "pencil-steep-angle-cpl", "coffee-bean",
        "tweezers-cpl", "couch-fibers-cpl", "flower-bud-alone-cpl",
        "bee-3-cpl", "wrapped-text-1", "lavendar-cpl", "leaf-2-cpl",
    ]
    NF = 8
    rng = np.random.default_rng(271828)
    print("PER-STACK SELF-VALIDATION.  bars: p <= %.4f AND depth <= -%.1f%%"
          % (P_BAR, DEPTH_FLOOR * 100))
    print("reads raw Bayer via quad_mean, sensor coords, BEFORE any warp.  %d frames/stack\n" % NF)
    hdr = ("subject", "n", "mote1 %", "p1", "mote2 %", "p2", "ctrl worst %", "pC", "decode s")
    print("%-27s %3s %9s %7s %9s %7s %13s %7s %9s" % hdr)
    print("-" * 104)
    rows, tsum, nsub = [], 0.0, 0
    for sub in subs:
        qs, dt, navail = load_stack(sub, NF)
        if not qs:
            print("%-27s (no frames)" % sub[:27])
            continue
        tsum += dt; nsub += 1
        t1 = time.time()
        R = np.median(np.stack([residual(q) for q in qs]), axis=0)
        tres = time.time() - t1
        r1 = score(R, *MOTES["mote1"], rng)
        r2 = score(R, *MOTES["mote2"], rng)
        cs = [score(R, cy, cx, rng) for cy, cx in CONTROLS.values()]
        worst = min(cs, key=lambda t: t[0])
        rows.append((sub, r1, r2, cs, R, qs, tres))
        print("%-27s %3d %8.3f%% %7.4f %8.3f%% %7.4f %12.3f%% %7.4f %6.2f+%.2f"
              % (sub[:27], navail, r1[0] * 100, r1[1], r2[0] * 100, r2[1],
                 worst[0] * 100, worst[1], dt, tres))
    if not rows:
        return 1

    n1 = sum(1 for _, r1, _, _, _, _, _ in rows if r1[2])
    n2 = sum(1 for _, _, r2, _, _, _, _ in rows if r2[2])
    ncf = sum(1 for _, _, _, cs, _, _, _ in rows for c in cs if c[2])
    print("\nFIRES  mote1 %d/%d   mote2 %d/%d   CONTROLS %d/%d  (controls must be 0)"
          % (n1, len(rows), n2, len(rows), ncf, len(rows) * len(CONTROLS)))
    print("decode %.2f s/stack mean (%d frames) = %.3f s/frame; residual %.2f s/stack"
          % (tsum / nsub, NF, tsum / nsub / NF, np.mean([r[6] for r in rows])))

    print("\n" + "=" * 104)
    print("COMMISSIONING both directions, on the first 4 stacks")
    print("%-27s %-26s %9s %7s %6s" % ("subject", "arm", "depth", "p", "fires"))
    print("-" * 82)
    fails = []
    for sub, r1, r2, cs, R, qs, _ in rows[:4]:
        cy, cx = CONTROLS["ctrlB"]
        # DEFECT: plant -4% at a clean control site -> must fire
        Rp = np.median(np.stack([residual(plant(q, cy, cx, 0.04)) for q in qs]), axis=0)
        d, p, f = score(Rp, cy, cx, rng)
        print("%-27s %-26s %8.3f%% %7.4f %6s" % (sub[:27], "DEFECT planted -4%", d * 100, p, f))
        if not f:
            fails.append("%s DEFECT did not fire" % sub)
        # PERVERSE: plant +4% BRIGHT -> must not fire
        Rb = np.median(np.stack([residual(plant(q, cy, cx, -0.04)) for q in qs]), axis=0)
        d, p, f = score(Rb, cy, cx, rng)
        print("%-27s %-26s %8.3f%% %7.4f %6s" % ("", "PERVERSE planted +4%", d * 100, p, f))
        if f:
            fails.append("%s PERVERSE fired" % sub)
        # IMPROVEMENT: divide the REAL mote2 back out -> must stop firing
        my, mx = MOTES["mote2"]
        Ri = np.median(np.stack([residual(plant(q, my, mx, -0.0824)) for q in qs]), axis=0)
        d, p, f = score(Ri, my, mx, rng)
        was = r2[2]
        print("%-27s %-26s %8.3f%% %7.4f %6s   (was %s)"
              % ("", "IMPROVE mote2 removed", d * 100, p, f, was))
        if was and f:
            fails.append("%s IMPROVEMENT still fired" % sub)
    print("\n" + "=" * 104)
    if fails:
        print("COMMISSIONING FAILURES (%d):" % len(fails))
        for x in fails:
            print("   " + x)
        return 1
    print("all commissioning arms PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

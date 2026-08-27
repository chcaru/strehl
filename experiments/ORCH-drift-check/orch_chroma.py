"""Chroma blotching and tonal banding — the last declared blind spot.

Every instrument in this tree so far measures LUMA structure: orch_halo.py reads
edge overshoot on a luma profile, orch_blotch.py reads mid-scale luma contrast,
orch_worst.py crops the worst luma edge. A master could carry gross colour noise
in a smooth out-of-focus background, or visible banding in a gradient, and all
three would read clean. Both defects are far more visible in a print than on a
screen, because a print has no backlight to hide a 2 DN step.

TWO STATISTICS, both tone-invariant by construction:

  CHROMA BLOTCH   band-pass energy of the *relative* chroma channels (a/Y, b/Y)
                  at 50-300 px, measured in the window with the flattest chroma.
                  Dimensionless. Immune to the 2.5x-25x tone scaling that
                  invalidated two published numbers in section 99.

  BANDING         fraction of exactly-zero first differences in the smoothest
                  window, against that window's actual range. A smooth gradient
                  rendered continuously has few exact zeros; a quantised one is
                  mostly flat with occasional steps.

THE INNOCENT EXPLANATION, named before the first reading (section 96's lesson):

  For chroma:  real subjects have real colour at 50-300 px. A flower petal, a
               bee's abdomen, an iridescent bubble. A high reading is the
               subject unless the SOURCE arm reads lower on the same window.
               The window is therefore chosen for flat CHROMA, not flat luma,
               and the source control is fitted BEFORE the first master reading.

  For banding: a genuinely flat region (blown highlight, clipped black) is all
               exact zeros and is not banding. The gate requires the window to
               have real range before a zero-fraction means anything.

THE BASELINE RULE (section 96): a stacker selects the sharpest frame at each
site. Benchmarking its output against the MEDIAN input is a strawman that reports
an artifact whenever selection is working. For chroma the relevant comparison is
the MINIMUM over source frames -- the cleanest chroma any input offered -- because
a merge that averages N frames should beat every one of them on colour noise.

Usage:
  python orch_chroma.py masters [--dir=SHIP-V2]
  python orch_chroma.py source SUBJECT [--n=12]
  python orch_chroma.py commission
"""
import os
import sys
import glob

import numpy as np
import tifffile

OUT_ROOT = r"C:\dev\strehl-out"
SRC_ROOT = r"D:\personal\macro"

WIN = 1200          # analysis window, px
LO_R = 50           # band-pass inner radius
HI_R = 300          # band-pass outer radius
GRID = 5            # candidate windows per axis

# Commissioned floors. See ARM COMMISSION; do not edit without re-running it.
CHROMA_FLOOR = 0.000000   # exact null on a neutral scene; ladder linear to 0.1%
BAND_THRESH = 4.0         # median constant-value run, px; a band must be wide
STEP_THRESH = 4.0         # ...AND its step must be big. 1 DN over 12 px is invisible.


def boxblur(a, r):
    """Exact box mean, integral-image, edge-correct (divides by real count)."""
    a = np.asarray(a, dtype=np.float64)
    h, w = a.shape
    ii = np.zeros((h + 1, w + 1), dtype=np.float64)
    ii[1:, 1:] = np.cumsum(np.cumsum(a, axis=0), axis=1)
    y0 = np.clip(np.arange(h) - r, 0, h)
    y1 = np.clip(np.arange(h) + r + 1, 0, h)
    x0 = np.clip(np.arange(w) - r, 0, w)
    x1 = np.clip(np.arange(w) + r + 1, 0, w)
    s = (ii[np.ix_(y1, x1)] - ii[np.ix_(y0, x1)]
         - ii[np.ix_(y1, x0)] + ii[np.ix_(y0, x0)])
    n = ((y1 - y0)[:, None] * (x1 - x0)[None, :]).astype(np.float64)
    return s / n


def relative_chroma(rgb):
    """a/Y and b/Y. Dividing by luma is what makes this survive a tone scale."""
    rgb = np.asarray(rgb, dtype=np.float64)
    y = 0.299 * rgb[..., 0] + 0.587 * rgb[..., 1] + 0.114 * rgb[..., 2]
    y = np.maximum(y, 1.0)
    return (rgb[..., 0] - y) / y, (rgb[..., 2] - y) / y, y


def pick_window(rgb, key):
    """Return (y, x) of the WIN-square window minimising `key`.

    key='chroma' picks flattest colour -- where blotching would show.
    key='luma'   picks flattest tone   -- where banding would show.
    """
    h, w = rgb.shape[:2]
    if h < WIN or w < WIN:
        return None
    a, b, y = relative_chroma(rgb)
    best, best_at = None, None
    for gy in range(GRID):
        for gx in range(GRID):
            oy = (h - WIN) * gy // max(GRID - 1, 1)
            ox = (w - WIN) * gx // max(GRID - 1, 1)
            ya, yb = y[oy:oy + WIN, ox:ox + WIN], b[oy:oy + WIN, ox:ox + WIN]
            aa = a[oy:oy + WIN, ox:ox + WIN]
            if key == "chroma":
                score = float(np.std(aa) + np.std(yb))
            else:
                m = float(np.mean(ya))
                if m <= 0:
                    continue
                score = float(np.std(ya) / m)
            if best is None or score < best:
                best, best_at = score, (oy, ox)
    return best_at


def chroma_blotch(rgb, at=None):
    """Band-pass energy of relative chroma at LO_R..HI_R.

    Returns (blotch, a_rms, b_rms, chroma_std, window). All dimensionless
    except window. Reports every term -- a ratio with one term hidden is how
    section 98 published a defect that was the merge working.
    """
    at = at or pick_window(rgb, "chroma")
    if at is None:
        return None
    oy, ox = at
    a, b, _ = relative_chroma(rgb[oy:oy + WIN, ox:ox + WIN])
    out = []
    for ch in (a, b):
        band = boxblur(ch, LO_R) - boxblur(ch, HI_R)
        m = HI_R  # trim the border where the big box ran short
        out.append(float(np.sqrt(np.mean(band[m:-m, m:-m] ** 2))))
    a_rms, b_rms = out
    return (float(np.hypot(a_rms, b_rms)), a_rms, b_rms,
            float(np.std(a) + np.std(b)), at)


def banding(rgb, at=None):
    """Spatial RUN LENGTH of constant value in the smoothest window.

    Two earlier versions of this statistic died on the commissioning bench and
    both deaths are worth keeping, because each was a faithful ladder measuring
    the wrong quantity -- the section 98 failure mode, twice.

    v1, zero-fraction of first differences: a CONTINUOUS gradient read 0.4996,
    because a 0.5 DN/px slope produces ~50% zero differences by rounding alone.
    It was measuring gradient steepness. The 0.02 threshold built on it would
    have flagged all 26 masters.

    v2, level occupancy: correct in principle -- it tracked the predicted
    N/range to within 0.6% -- but ceilinged at WIN/range on a 1-D ramp, so the
    gate needed to reject it read REJECT-STEEP on 23 of 26 real masters. An
    instrument that declines to examine 88% of its inputs has not measured them.

    v3, this one, measures the thing an eye actually objects to. Banding is
    visible when each value occupies a WIDE spatial band. A smoothly rendered
    gradient moves to a new value every pixel or two whatever its slope; a
    32-step comb across 1200 px holds each value for 37 px. Run length is
    therefore invariant to slope AND to range, which is what defeated v1 and
    v2 respectively, and it is a direct proxy for visibility rather than a
    proxy for a proxy.

    Gated on real range: a clipped black or blown highlight is one run and is
    not banding. Returns (median_run, p90_run, range_dn, window); the first
    element is the string REJECT-FLAT when the gate fires.
    """
    at = at or pick_window(rgb, "luma")
    if at is None:
        return None
    oy, ox = at
    blk = rgb[oy:oy + WIN, ox:ox + WIN]
    y = (0.299 * blk[..., 0] + 0.587 * blk[..., 1]
         + 0.114 * blk[..., 2]).astype(np.float64)
    p1, p99 = np.percentile(y, [1, 99])
    rng = float(p99 - p1)
    if rng < 64.0:
        return ("REJECT-FLAT", 0.0, rng, at, 0.0)
    yi = np.rint(y).astype(np.int64)
    runs, steps = [], []
    for r in np.linspace(0, yi.shape[0] - 1, 200).astype(int):
        row = yi[r]
        d = np.diff(row)
        b = np.nonzero(d)[0]
        if b.size < 8:
            continue                     # a near-constant row says nothing
        runs.append(np.diff(b))
        steps.append(np.abs(d[b]))
    if not runs:
        return ("REJECT-FLAT", 0.0, rng, at, 0.0)
    runs = np.concatenate(runs)
    steps = np.concatenate(steps)
    return (float(np.median(runs)), float(np.percentile(runs, 90)), rng, at,
            float(np.median(steps)))


def read_master(path):
    img = tifffile.imread(path)   # never PIL: it right-shifts 16->8 silently
    if img.ndim != 3 or img.shape[2] < 3:
        raise SystemExit("not RGB: %s %r" % (path, img.shape))
    return img[..., :3].astype(np.float64)


def arm_masters(subdir):
    root = os.path.join(OUT_ROOT, subdir)
    files = [p for p in glob.glob(os.path.join(root, "*.tif*"))
             if os.path.splitext(p)[1].lower() == ".tiff"]
    files.sort()
    print("ARM MASTER  dir=%s  n=%d  WIN=%d LO_R=%d HI_R=%d"
          % (subdir, len(files), WIN, LO_R, HI_R))
    print("%-34s %10s %10s %10s %9s %8s %8s %8s"
          % ("subject", "blotch", "a_rms", "b_rms", "chr_std",
             "med_run", "rangeDN", "medstep"))
    rows = []
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            rgb = read_master(p)
        except Exception as exc:                      # noqa: BLE001
            print("%-34s  READ-FAIL %s" % (name[:34], exc))
            continue
        cb = chroma_blotch(rgb)
        bd = banding(rgb)
        if cb is None:
            print("%-34s  TOO-SMALL" % name[:34])
            continue
        occ = "%.1f" % bd[0] if isinstance(bd[0], float) else bd[0]
        print("%-34s %10.6f %10.6f %10.6f %9.4f %8s %8.0f %8.1f"
              % (name[:34], cb[0], cb[1], cb[2], cb[3], occ, bd[2], bd[4]))
        rows.append((name, cb[0], bd))
    if rows:
        v = sorted(rows, key=lambda r: -r[1])
        print("\nworst chroma blotch:")
        for name, val, _ in v[:6]:
            print("   %-34s %.6f" % (name[:34], val))
        scored = [r for r in rows if isinstance(r[2][0], float)]
        flagged = [r for r in scored if r[2][0] > BAND_THRESH and r[2][4] > STEP_THRESH]
        flat = [r for r in rows if r[2][0] == "REJECT-FLAT"]
        steep = [r for r in rows if r[2][0] == "REJECT-SPARSE"]
        print("\nbanding: median constant-value run > %.1f px is a visible band"
              % BAND_THRESH)
        if flagged:
            for name, _, bd in sorted(flagged, key=lambda r: -r[2][0])[:8]:
                print("   FLAG %-30s median run %.1f px  range %.0f DN"
                      % (name[:30], bd[0], bd[2]))
        else:
            print("   none flagged")
        print("\npartition: %d examined (%d clean, %d flagged)"
              % (len(scored), len(scored) - len(flagged), len(flagged)))
        print("           %d rejected-flat, %d rejected-sparse, %d total"
              % (len(flat), len(steep), len(rows)))
        assert len(scored) + len(flat) + len(steep) == len(rows), "partition leak"
        print("a rejected window was NOT examined and must not be read as a pass.")


def arm_source(subject, n):
    """The control. Fitted before any master reading is believed."""
    import rawpy
    d = os.path.join(SRC_ROOT, subject)
    arw = sorted(glob.glob(os.path.join(d, "*.ARW")))
    if not arw:
        raise SystemExit("no ARW in %s" % d)
    idx = np.linspace(0, len(arw) - 1, min(n, len(arw))).astype(int)
    print("ARM SOURCE  %s  %d of %d frames" % (subject, len(idx), len(arw)))
    print("%-28s %10s %10s %9s %10s" % ("frame", "blotch", "chr_std", "range", "med_run"))
    vals = []
    at = None
    for i in idx:
        with rawpy.imread(arw[i]) as r:
            rgb = r.postprocess(gamma=(1, 1), no_auto_bright=True,
                                use_camera_wb=True, output_bps=16)
        rgb = rgb.astype(np.float64)
        if at is None:
            at = pick_window(rgb, "chroma")      # one window, all frames
        cb = chroma_blotch(rgb, at)
        bd = banding(rgb)
        b0 = "%.1f" % bd[0] if isinstance(bd[0], float) else bd[0]
        print("%-28s %10.6f %9.4f %10.0f %10s"
              % (os.path.basename(arw[i]), cb[0], cb[3], bd[2], b0))
        vals.append(cb[0])
    print("\nsource min %.6f   median %.6f   max %.6f"
          % (min(vals), float(np.median(vals)), max(vals)))
    print("\nBASELINE: compare a master against the MIN, not the median.")
    print("A merge of N frames should beat every input on chroma noise;")
    print("the median is a strawman that flatters the merge (section 96).")
    print("NOTE: window differs between arms (master is warped/cropped);")
    print("relative chroma is tone-invariant but NOT scene-invariant.")


def arm_commission():
    """Prove both statistics respond, monotonically, and that a null is quiet.

    A commissioning that only shows response does not show the instrument can
    say no. Both halves are required.
    """
    rng = np.random.default_rng(20260826)
    h = w = WIN + 2 * HI_R
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)

    print("=== CHROMA BLOTCH ===")
    print("scene: neutral grey ramp + photon-ish noise, no colour structure")
    base = 8000.0 + 2000.0 * (xx / w)
    noise = rng.normal(0, 25.0, size=(h, w))
    flat = np.stack([base + noise, base + noise, base + noise], axis=-1)
    n0 = chroma_blotch(flat)
    print("NULL (no blotch injected)          blotch %.6f" % n0[0])

    print("\nladder: sinusoidal chroma blotch at 150 px, amplitude in %% of luma")
    prev = None
    for amp in (0.0005, 0.001, 0.002, 0.004, 0.008, 0.016):
        blob = np.sin(2 * np.pi * xx / 150.0) * np.sin(2 * np.pi * yy / 150.0)
        img = flat.copy()
        img[..., 0] += base * amp * blob            # push red, pull blue
        img[..., 2] -= base * amp * blob
        v = chroma_blotch(img)[0]
        mono = "" if prev is None else ("  UP" if v > prev else "  ** NOT MONOTONE **")
        print("  amp %.4f   blotch %.6f%s" % (amp, v, mono))
        prev = v
    print("\nCHROMA_FLOOR (null): %.6f" % n0[0])

    print("\n=== BANDING (spatial run length) ===")
    print("scene: smooth gradient, ~900 DN range across the window")
    grad = 8000.0 + 900.0 * (xx / w)
    smooth = np.stack([grad, grad, grad], axis=-1)
    b = banding(smooth)
    print("  continuous (float)   median run %.1f px  p90 %.1f  range %.0f"
          % (b[0], b[1], b[2]))
    print("\nladder: quantise to N levels across that range")
    print("  %6s %11s %11s %10s" % ("levels", "median_run", "predicted", "p90"))
    prev = None
    for levels in (900, 256, 128, 64, 32, 16):
        step = 900.0 / levels
        q = np.rint(grad / step) * step
        v = banding(np.stack([q, q, q], axis=-1))
        if not isinstance(v[0], float):
            print("  %6d  %s" % (levels, v[0]))
            continue
        pred = w / float(levels)
        mono = "" if prev is None else ("  UP" if v[0] >= prev else "  ** NOT MONOTONE **")
        print("  %6d %11.1f %11.1f %10.1f%s" % (levels, v[0], pred, v[1], mono))
        prev = v[0]
    print("\n  ^ run length tracks the predicted width/levels directly, in pixels,")
    print("    which is the unit the defect is actually visible in.")

    print("\nthe control that killed v1 (slope) and v2 (range):")
    print("  %-14s %8s %9s %12s" % ("scene", "slope", "range", "median_run"))
    for span in (150.0, 900.0, 4000.0, 20000.0):
        g1 = 8000.0 + span * (xx / w)
        g2 = g1 + 0.31 * span * (yy / h) + rng.normal(0, 1.5, (h, w))
        for label, g in (("1-D ramp", g1), ("2-D + noise", g2)):
            v = banding(np.stack([g, g, g], axis=-1))
            mr = ("%.1f" % v[0]) if isinstance(v[0], float) else v[0]
            print("  %-14s %8.2f %9.0f %12s" % (label, span / w, v[2], mr))
    print("  ^ CONTINUOUS data reads short runs at every slope and every range.")
    print("    v1 swung 0.92->0.00 across these; v2 rejected the steep ones.")

    print("\nthe REJECT gate, which stops a blown highlight reading as banding:")
    for val in (8000.0, 8000.0 + 30.0 * (xx / w)):
        img = np.stack([np.broadcast_to(val, (h, w))] * 3, axis=-1).astype(np.float64)
        v = banding(img)
        print("  range %.0f DN -> %s" % (v[2], v[0]))

    print("\nnoise breaks up the bands, and that is correct behaviour:")
    for sd in (0.0, 0.5, 2.0, 8.0):
        q = np.rint(grad / (900.0 / 32)) * (900.0 / 32) + rng.normal(0, sd, (h, w))
        v = banding(np.stack([q, q, q], axis=-1))
        print("  32 levels + sigma %.1f DN   median run %.1f px" % (sd, v[0]))
    print("  ^ a dithered gradient is not visibly banded and should not be flagged.")
    print("\nBAND_THRESH in use: median run > %.1f px" % BAND_THRESH)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {a.split("=")[0][2:]: a.split("=", 1)[1]
            for a in sys.argv[1:] if a.startswith("--") and "=" in a}
    if not args:
        raise SystemExit(__doc__)
    if args[0] == "masters":
        arm_masters(opts.get("dir", "SHIP-V2"))
    elif args[0] == "source":
        arm_source(args[1], int(opts.get("n", 12)))
    elif args[0] == "commission":
        arm_commission()
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()

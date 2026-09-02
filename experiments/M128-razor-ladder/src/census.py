r"""M128 / census — the go/no-go. Which stretches of this edge are measurable?

MEASURED on the real blade: the edge locus scatters 1.23 green px RMS about a
straight line, against a photon-noise prediction of 0.044 px. That is 28x
larger, so it is real raggedness of the ground steel, not estimator noise. But
block IQR ranges from 0.18 to 4.0 px ALONG THE SAME EDGE, so clean stretches
exist and the lane is a segment-selection problem.

This walks a window along the edge and scores every position against the
acceptance conditions registered in PREREGISTRATION.md section 6, then reports
the contiguous runs that qualify. It computes no frequency quantity and makes
no measurement; it only decides where a measurement is allowed to be taken.

Why the reported straightness is not a simple pass/fail: section 4.1 of the
pre-registration establishes that registration jitter enters the ladder inside
the aperture-independent term c, and therefore CANCELS -- provided it is the
same at all three apertures. So scatter is ranked and propagated, not
thresholded. What IS thresholded is everything that breaks the estimator
outright: clipping, contrast, crossing yield, phase traversal.

    python src\census.py <frame.ARW> --row0 R --nrow N [--dark-first] --json out\census.json

Exit code is always 0; the verdict is in the output.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

M88 = Path(__file__).resolve().parents[2] / "M88-optical-ceiling" / "src"
sys.path.insert(0, str(M88))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402
import geom  # noqa: E402

# load_active returns the BLACK-SUBTRACTED active area, so the 14-bit container
# ceiling of 15871 DN lands here at 15871 - 512.
CLIP_DN = 15871.0 - 512.0

# Registered in PREREGISTRATION.md section 6.
MIN_TRAVERSAL_SUB_PX = 4.0
MIN_COLUMNS = 200
MIN_CONTRAST_DN = 500.0
MAX_CLIP_FRAC = 0.0
MIN_YIELD = 0.80


HALF_UM_GRID = (192.0, 128.0, 96.0, 64.0, 48.0)
SUB_PITCH_UM = 2.0 * 5.12  # green sublattice pitch


def window_stats(a, xall, yall, hi, lo, c0, c1, gate_half_um):
    """Score one along-edge window. Pure geometry; no frequency quantity."""
    m = (xall >= c0) & (xall < c1)
    x, y = xall[m], yall[m]
    ncol = c1 - c0
    out = {
        "col0": int(c0), "ncol": int(ncol),
        "n_cross": int(len(x)),
        "yield": float(len(x) / ncol),
        "contrast_dn": float(np.median(hi[c0:c1] - lo[c0:c1])),
        "hi_dn": float(np.median(hi[c0:c1])),
        "lo_dn": float(np.median(lo[c0:c1])),
    }
    if len(x) < 32:
        out.update(rms1=None, rms3=None, iqr=None, maxabs=None,
                   slope=None, angle_deg=None, traversal=None,
                   clip=None, clip_frac=1.0)
        return out

    p1 = np.polyfit(x, y, 1)
    keep = np.ones(len(x), bool)
    for _ in range(4):
        r = y - np.polyval(p1, x)
        s = float(np.std(r[keep])) if keep.any() else 0.0
        if s <= 0:
            break
        nk = np.abs(r) <= 3.0 * s
        if nk.sum() < 32:
            break
        keep = nk
        p1 = np.polyfit(x[keep], y[keep], 1)
    r1 = y[keep] - np.polyval(p1, x[keep])

    # A cubic is the pre-registered maximum order. Comparing it to the line
    # separates smooth bow (which a fit removes) from high-frequency raggedness
    # (which it cannot).
    if keep.sum() >= 64:
        xn = (x[keep] - x[keep].mean()) / max(x[keep].std(), 1e-9)
        p3 = np.polyfit(xn, y[keep], 3)
        r3 = y[keep] - np.polyval(p3, xn)
        rms3 = float(np.sqrt(np.mean(r3 ** 2)))
    else:
        rms3 = None

    # Clipping is scoped to the ESF WINDOW, not to the whole band. The blade's
    # bevel carries blown debris specks hundreds of um from the silhouette;
    # those matter only if the half-width reaches them, and the half-width is
    # exactly what commissioning is choosing. So report clipping as a function
    # of half-width and let the choice be made with the numbers in hand.
    rows = np.arange(a.shape[0], dtype=float)[:, None]
    cols = np.arange(c0, c1, dtype=float)[None, :]
    dist_px = np.abs(rows - np.polyval(p1, cols)[None, :])
    patch = a[:, c0:c1]
    clipped = patch >= CLIP_DN
    clip = {}
    for h in HALF_UM_GRID:
        inwin = dist_px <= (h / SUB_PITCH_UM)
        n = int(inwin.sum())
        clip[f"{h:.0f}"] = float((clipped & inwin).sum()) / max(n, 1)

    out.update(
        rms1=float(np.sqrt(np.mean(r1 ** 2))),
        rms3=rms3,
        iqr=float(np.subtract(*np.percentile(r1, [75, 25]))),
        maxabs=float(np.max(np.abs(r1))),
        slope=float(p1[0]),
        angle_deg=float(np.degrees(np.arctan(p1[0]))),
        traversal=float(abs(p1[0]) * ncol),
        n_kept=int(keep.sum()),
        clip=clip,
        clip_frac=clip[f"{gate_half_um:.0f}"],
    )
    return out


def gate(w):
    """Return the list of registered conditions this window FAILS."""
    if w.get("rms1") is None:
        return ["too_few_crossings"]
    bad = []
    if w["traversal"] < MIN_TRAVERSAL_SUB_PX:
        bad.append(f"traversal {w['traversal']:.2f} < {MIN_TRAVERSAL_SUB_PX}")
    if w["ncol"] < MIN_COLUMNS:
        bad.append(f"ncol {w['ncol']} < {MIN_COLUMNS}")
    if w["contrast_dn"] < MIN_CONTRAST_DN:
        bad.append(f"contrast {w['contrast_dn']:.0f} < {MIN_CONTRAST_DN}")
    if w["clip_frac"] > MAX_CLIP_FRAC:
        bad.append(f"clip_frac {w['clip_frac']:.2e} > {MAX_CLIP_FRAC}")
    if w["yield"] < MIN_YIELD:
        bad.append(f"yield {w['yield']:.3f} < {MIN_YIELD}")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--which", default="G1")
    ap.add_argument("--row0", type=int, default=None,
                    help="sublattice row where the across-edge window starts; "
                         "default: located by geom.find_band")
    ap.add_argument("--nrow", type=int, default=None,
                    help="default: whatever find_band returns, typically 440")
    ap.add_argument("--win", type=int, default=400,
                    help="along-edge window width in sublattice columns")
    ap.add_argument("--stride", type=int, default=100)
    ap.add_argument("--band-half", type=int, default=None,
                    help="use +/- this many sublattice rows around the step "
                         "row instead of find_band's default +/-220. A wide "
                         "band drags in debris and glare structure and costs "
                         "crossing yield; a narrow one clips the ESF wings.")
    ap.add_argument("--dark-first", action="store_true")
    ap.add_argument("--gate-half-um", type=float, default=96.0,
                    help="half-width the clipping gate is scoped to; the "
                         "clip fraction is reported for the whole grid "
                         f"{HALF_UM_GRID} regardless")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    active = L.load_active(args.frame)
    sub, xs, ys = L.green_sites(active, args.which)
    bright_first = not args.dark_first
    if args.row0 is None or args.nrow is None:
        b0, b1, row = geom.find_band(sub)
        if args.band_half is not None:
            b0 = max(row - args.band_half, 0)
            b1 = min(row + args.band_half, sub.shape[0])
        r0 = args.row0 if args.row0 is not None else b0
        nr = args.nrow if args.nrow is not None else (b1 - b0)
        print(f"band located by geom.find_band: step row {row}, "
              f"rows {b0}..{b1}")
    else:
        r0, nr = args.row0, args.nrow
    band = sub[r0:r0 + nr, :]

    print(f"{Path(args.frame).name}  sublattice {sub.shape}  plane {args.which}")
    print(f"band rows {r0}..{r0 + nr}  bright_first={bright_first}  "
          f"win={args.win} stride={args.stride}")
    print(f"band max {band.max():.0f} DN  (clip ceiling {CLIP_DN:.0f})  "
          f"samples at ceiling: {int((band >= CLIP_DN).sum())}")

    xall, yall, hi, lo = geom.crossings(band, 0, nr, bright_first)
    xall = xall.astype(float)
    yall = yall.astype(float)
    print(f"crossings found: {len(xall)} of {band.shape[1]} columns "
          f"({100.0 * len(xall) / band.shape[1]:.1f}%)")
    if len(xall) < 64:
        print("\nREFUSE  too few crossings anywhere in this band; the locator "
              "cannot see this edge. Check --row0/--nrow and --dark-first.")
        return

    wins = []
    for c0 in range(0, band.shape[1] - args.win + 1, args.stride):
        w = window_stats(band, xall, yall, hi, lo, c0, c0 + args.win,
                         args.gate_half_um)
        w["fails"] = gate(w)
        w["pass"] = not w["fails"]
        wins.append(w)

    npass = sum(1 for w in wins if w["pass"])
    print(f"\nwindows scored: {len(wins)}   passing the registered gates: "
          f"{npass}   failing: {len(wins) - npass}")

    # A compact yield strip at finer granularity than the windows, because a
    # window-level yield of 0.55 does not say whether the edge is uniformly
    # mediocre or excellent in half its length and destroyed in the other half.
    blk = 64
    nb = band.shape[1] // blk
    ymap, rmap = [], []
    for i in range(nb):
        a0, a1 = i * blk, (i + 1) * blk
        m = (xall >= a0) & (xall < a1)
        y_ = float(m.sum()) / blk
        ymap.append(y_)
        if m.sum() >= 16:
            xb, yb = xall[m], yall[m]
            pb = np.polyfit(xb, yb, 1)
            rmap.append(float(np.sqrt(np.mean((yb - np.polyval(pb, xb)) ** 2))))
        else:
            rmap.append(float("nan"))
    def strip(vals, lo, hi, glyphs=" .:-=+*#%@"):
        out = []
        for v in vals:
            if not np.isfinite(v):
                out.append("?")
                continue
            t = (v - lo) / (hi - lo)
            out.append(glyphs[int(np.clip(t, 0, 1) * (len(glyphs) - 1))])
        return "".join(out)
    print(f"\nper-{blk}-column strip across the whole edge, {nb} blocks, "
          "left to right:")
    print(f"  crossing yield  0->1 : {strip(ymap, 0.0, 1.0)}")
    print(f"  locus RMS 0->1 green px, ? = too few crossings to fit :")
    print(f"                         {strip(rmap, 0.0, 1.0)}")
    fin = [v for v in rmap if np.isfinite(v)]
    if fin:
        print(f"  blocks with RMS < 0.15 px: "
              f"{sum(1 for v in fin if v < 0.15)} of {len(fin)} fitted "
              f"({nb} total); median RMS {np.median(fin):.3f} px, "
              f"best {min(fin):.3f} px")

    reasons = {}
    for w in wins:
        for f in w["fails"]:
            reasons[f.split()[0]] = reasons.get(f.split()[0], 0) + 1
    if reasons:
        print("failure reasons (a window can fail several):")
        for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]):
            print(f"    {k:22s} {v:4d}")

    allw = [w for w in wins if w.get("clip")]
    if allw:
        print("\nclipping inside the ESF window as a function of half-width, "
              "over every scored window. The blade carries blown debris "
              "specks; a half-width that reaches them poisons the ESF, and "
              "this is the evidence for the half-width choice.")
        hdr = "".join(f"{h:>11.0f}" for h in HALF_UM_GRID)
        print(f"  {'half um':>9}{hdr}")
        print(f"  {'mean frac':>9}" + "".join(
            f"{np.mean([w['clip'][f'{h:.0f}'] for w in allw]):11.2e}"
            for h in HALF_UM_GRID))
        print(f"  {'windows0':>9}" + "".join(
            f"{sum(1 for w in allw if w['clip'][f'{h:.0f}'] == 0.0):11d}"
            for h in HALF_UM_GRID)
            + f"   of {len(allw)} with ZERO clipped samples")

    ok = [w for w in wins if w["pass"]]
    if ok:
        ok_sorted = sorted(ok, key=lambda w: w["rms1"])
        print(f"\nthe 20 straightest passing windows, ranked by locus RMS "
              f"(green px):")
        print(f"  {'col0':>6} {'rms1':>7} {'rms3':>7} {'iqr':>7} {'max':>7} "
              f"{'angle':>8} {'trav':>6} {'contr':>7} {'yield':>6}")
        for w in ok_sorted[:20]:
            print(f"  {w['col0']:6d} {w['rms1']:7.3f} "
                  f"{(w['rms3'] if w['rms3'] is not None else float('nan')):7.3f} "
                  f"{w['iqr']:7.3f} {w['maxabs']:7.3f} {w['angle_deg']:+8.4f} "
                  f"{w['traversal']:6.2f} {w['contrast_dn']:7.0f} "
                  f"{w['yield']:6.3f}")
        best = ok_sorted[0]
        print(f"\nstraightest window: col0={best['col0']} rms1="
              f"{best['rms1']:.3f} green px = {best['rms1'] * 10.24:.2f} um")
        print("Compare against the smallest predicted rise, 10.366 um (H3 at "
              "f/5.6). Registration jitter enters the aperture-independent "
              "term c and cancels across the ladder (pre-registration 4.1), "
              "so this is ranked and propagated, not thresholded -- but it "
              "must be constant across apertures, which is control C7.")
        print("\nclipped fraction inside the ESF window, by half-width, for "
              "the 10 straightest passing windows.")
        hdr = "".join(f"{h:>10.0f}" for h in HALF_UM_GRID)
        print(f"  {'col0':>6}{hdr}")
        for w in ok_sorted[:10]:
            print(f"  {w['col0']:6d}" + "".join(
                f"{w['clip'][f'{h:.0f}']:10.2e}" for h in HALF_UM_GRID))
    else:
        print("\nREFUSE  no window passes the registered acceptance "
              "conditions. Per pre-registration section 7 this is a complete "
              "result, not a failure: report the limit and request a capture.")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            {"frame": str(args.frame), "which": args.which, "row0": r0,
             "nrow": nr, "win": args.win, "stride": args.stride,
             "bright_first": bright_first,
             "band_max_dn": float(band.max()),
             "n_at_ceiling": int((band >= CLIP_DN).sum()),
             "n_crossings": int(len(xall)),
             "n_columns": int(band.shape[1]),
             "gates": {"traversal": MIN_TRAVERSAL_SUB_PX,
                       "ncol": MIN_COLUMNS, "contrast": MIN_CONTRAST_DN,
                       "clip_frac": MAX_CLIP_FRAC, "yield": MIN_YIELD},
             "windows": wins}, indent=1, default=float))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()

"""M128 / esfreg -- does the ESF registration reference explain the broken fits?

THE OBSERVATION

The early half-width sweeps returned fits that are not fits. Across nine
settings `amp` sat on its 0.5 lower bound, `sigma` came back at 22-25 um
against a 5.12 um sensor pitch, `fc` pinned at the 400 cy/mm upper bound twice,
and `rms_resid` ran from 0.06 to 2.4 where a good slanted-edge fit is ~0.01.
`success: True` in those records means least_squares converged, not that the
model describes the data.

THE HYPOTHESIS

Both existing reductions register the ESF against a SMOOTH curve:
`m88lib.sfr_from_sites2` bins by distance to a fitted straight line, and
`geom.esf` bins against a fitted cubic. The census measures how far the real
edge departs from those curves -- `rms1` and `rms3`, both about 1.2-1.3
sublattice px on the qualifying windows. A razor's ground edge is ragged at
that scale and no low-order polynomial can follow it.

Binning by distance to a curve the edge does not follow convolves the ESF with
the distribution of that departure. 1.27 sublattice px is 13.0 um, which is the
same order as the 22-25 um the fits reported. So the prediction is specific: the
fitted `sigma` is not optical, it is the raggedness, and the reduction is
measuring the straightness of the blade rather than the resolution of the lens.

THE TEST

Register the ESF four ways on one census-certified window and compare. The
estimator is held fixed throughout: this module never touches `m88lib`, and
changes only the COORDINATES handed to it. Because `sfr_from_sites` computes
`d_px = (X - x0)*nx + (Y - y0)*ny`, displacing a column's samples by `-delta(x)`
in Y moves that column's distance coordinate by exactly `-delta(x)*ny`, which is
the perpendicular departure. So warping Y straightens the edge exactly, and the
validated estimator is reused rather than reimplemented.

  line    delta = 0                       what sfr_run.py does today
  cubic   delta = cubic(x) - line(x)      what geom.esf does today
  self    delta = locus(x) - line(x)      this plane's own 50% crossings
  cross   delta from the OTHER green plane, mean offset removed

`self` and `cross` differ in a way that matters. Registering a plane on its own
crossings aligns each column on a noisy realisation of its own profile, so the
noise in the crossing is correlated with the noise in the samples being binned,
and that correlation sharpens the ESF near the mid level. It is a real bias and
it flatters the answer. Registering G1 on the locus measured in G2 breaks the
correlation by construction: the two sublattices see the same edge through
independent photons. What is left is a genuine blur of exactly the locus
measurement error, which A2 already measured per aperture as 0.267 / 0.289 /
0.356 px and registered a correction for. So `cross` is the mode whose error
budget is known, and the gap between `self` and `cross` is a direct readout of
the self-registration bias.

PREDICTION, recorded before running. If the hypothesis holds, fitted `sigma`
falls steeply from `line` to `cross`, `amp` comes off its 0.5 bound, and
`rms_resid` drops by an order of magnitude. If `sigma` stays near 22-25 um in
every mode then raggedness is not the culprit and this diagnosis is wrong.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
M88 = HERE.parents[1] / "M88-optical-ceiling" / "src"
sys.path.insert(0, str(M88))
sys.path.insert(0, str(HERE))
import m88lib as L  # noqa: E402
import geom  # noqa: E402
import sfr_run  # noqa: E402

MODES = ("line", "cubic", "self", "cross")


def locus_sensor_y(s, yr, bright_first):
    """Per-column 50% crossings of an ROI, in sensor-px Y.

    `geom.crossings` returns the crossing as a fractional sublattice row index
    within the slice it was given. `green_sites` spaces sublattice rows two
    sensor px apart starting at `yr[0]`, so the conversion is exact and needs
    no calibration.
    """
    x, y, hi, lo = geom.crossings(s, 0, s.shape[0], bright_first)
    return x, yr[0] + 2.0 * y, hi, lo


def line_y_at(line, x_sensor):
    """The fitted line's Y at a given sensor X.

    The line is stored as a point and a unit normal. For a near-horizontal edge
    `ny` is close to 1 and the inversion below is well conditioned; it is
    guarded rather than assumed.
    """
    if abs(line["ny"]) < 1e-6:
        raise SystemExit("edge is vertical in this parameterisation")
    return line["y0"] - (x_sensor - line["x0"]) * line["nx"] / line["ny"]


def delta_for_mode(mode, xs_roi, x_idx, y_sen, line, other=None, order=3):
    """Per-column Y displacement that straightens the edge, in sensor px.

    Returns (delta over all ROI columns, mask of columns with a real datum).
    Columns with no clean crossing carry delta by interpolation; the caller
    decides whether to keep or drop them, and both are reported because that
    choice is itself a settings choice this lane has to defend.
    """
    n = len(xs_roi)
    if mode == "line":
        return np.zeros(n), np.ones(n, bool)

    if mode == "cubic":
        xn = (x_idx - x_idx.mean()) / max(x_idx.std(), 1e-9)
        p = np.polyfit(xn, y_sen, order)
        xall = (np.arange(n) - x_idx.mean()) / max(x_idx.std(), 1e-9)
        fit_y = np.polyval(p, xall)
        return fit_y - line_y_at(line, xs_roi), np.ones(n, bool)

    if mode == "self":
        src_x, src_y = x_idx, y_sen
    elif mode == "cross":
        if other is None:
            raise SystemExit("cross mode needs the other plane")
        src_x, src_y = other
    else:
        raise SystemExit(f"unknown mode {mode}")

    have = np.zeros(n, bool)
    inb = (src_x >= 0) & (src_x < n)
    have[np.round(src_x[inb]).astype(int)] = True
    y_col = np.interp(np.arange(n), src_x, src_y)
    d = y_col - line_y_at(line, xs_roi)
    if mode == "cross":
        d = d - float(np.mean(d))          # G1 and G2 sit one sensor px apart
    return d, have


def run_mode(sub, xs, ys, row0, col0, nrow, ncol, mode, line, x_idx, y_sen,
             other, half_um, bin_um, taper, core_um, f_lo, f_hi, gap,
             bright_first):
    s = sub[row0:row0 + nrow, col0:col0 + ncol]
    xr = xs[col0:col0 + ncol]
    yr = ys[row0:row0 + nrow]
    delta, have = delta_for_mode(mode, xr, x_idx, y_sen, line, other)

    XX, YY = np.meshgrid(xr, yr)
    YY = YY - delta[None, :]
    keep = np.ones(ncol, bool) if gap == "interp" else have
    vals = s[:, keep].ravel().astype(float)
    r = L.sfr_from_sites2(vals, XX[:, keep].ravel(), YY[:, keep].ravel(), line,
                          bin_um, half_um, taper, core_um=core_um, deramp=True)
    fit = L.fit_fc(r["freq_cymm"], r["mtf"], f_lo, f_hi)
    rise = geom.rise_from_esf(r["centres_um"], r["esf"], far=0.6 * half_um)
    fit["rise_um"] = float(rise["rise_px"]) if rise else float("nan")
    fit["delta_rms_px"] = float(np.std(delta[keep]) / 2.0)
    fit["n_cols"] = int(keep.sum())
    fit["min_bin"] = int(np.min(r["count"]))
    fit["esf_contrast"] = float(r["contrast"])
    return fit, r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--which", default="G1")
    ap.add_argument("--row0", type=int, required=True)
    ap.add_argument("--col0", type=int, required=True)
    ap.add_argument("--nrow", type=int, default=120)
    ap.add_argument("--ncol", type=int, default=800)
    ap.add_argument("--half", type=float, default=96.0)
    ap.add_argument("--bin-um", type=float, default=0.64)
    ap.add_argument("--taper", type=float, default=0.10)
    ap.add_argument("--core-um", type=float, default=48.0)
    ap.add_argument("--f-lo", type=float, default=10.0)
    ap.add_argument("--f-hi", type=float, default=150.0)
    ap.add_argument("--gap", default="drop", choices=["drop", "interp"])
    ap.add_argument("--dark-first", action="store_true")
    ap.add_argument("--modes", nargs="+", default=list(MODES))
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    bright_first = not args.dark_first

    active = L.load_active(args.frame)
    sub, xs, ys = L.green_sites(active, args.which)
    oth, oxs, oys = L.green_sites(active, "G2" if args.which == "G1" else "G1")

    s = sub[args.row0:args.row0 + args.nrow, args.col0:args.col0 + args.ncol]
    xr = xs[args.col0:args.col0 + args.ncol]
    yr = ys[args.row0:args.row0 + args.nrow]
    line = sfr_run.line_from_crossings(s, xr, yr, bright_first, "horizontal")
    x_idx, y_sen, _hi, _lo = locus_sensor_y(s, yr, bright_first)

    so = oth[args.row0:args.row0 + args.nrow, args.col0:args.col0 + args.ncol]
    oyr = oys[args.row0:args.row0 + args.nrow]
    ox, oy, _h2, _l2 = locus_sensor_y(so, oyr, bright_first)

    print(f"{Path(args.frame).name}  plane {args.which}  ROI rows "
          f"{args.row0}..{args.row0 + args.nrow} cols "
          f"{args.col0}..{args.col0 + args.ncol}")
    print(f"  line angle {line['angle_deg']:+.4f} deg  straight-line residual "
          f"{line['resid_sd_px']:.3f} sensor px  contrast {line['contrast']:.0f} DN")
    print(f"  crossings: this plane {len(x_idx)}/{args.ncol}, "
          f"other plane {len(ox)}/{args.ncol}")
    print(f"  half {args.half} um  bin {args.bin_um} um  gaps: {args.gap}\n")

    hdr = (f"  {'mode':>6} {'ragged px':>9} {'ncol':>5} {'fc cy/mm':>9} "
           f"{'sigma um':>9} {'amp':>7} {'rms':>8} {'rise um':>8} {'bins':>5}")
    print(hdr)
    out = []
    for mode in args.modes:
        try:
            fit, _r = run_mode(sub, xs, ys, args.row0, args.col0, args.nrow,
                               args.ncol, mode, line, x_idx, y_sen, (ox, oy),
                               args.half, args.bin_um, args.taper,
                               args.core_um, args.f_lo, args.f_hi, args.gap,
                               bright_first)
        except L.EdgeFitError as e:
            print(f"  {mode:>6}  EdgeFitError: {e}")
            continue
        fit["mode"] = mode
        out.append(fit)
        pin = ""
        if fit["amp"] <= 0.5005:
            pin += " amp-pinned"
        if fit["fc_cymm"] >= 399.5:
            pin += " fc-pinned"
        print(f"  {mode:>6} {fit['delta_rms_px']:9.3f} {fit['n_cols']:5d} "
              f"{fit['fc_cymm']:9.2f} {fit['sigma_um']:9.3f} {fit['amp']:7.4f} "
              f"{fit['rms_resid']:8.5f} {fit['rise_um']:8.3f} "
              f"{fit['min_bin']:5d}{pin}")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(
            {"frame": args.frame, "which": args.which, "row0": args.row0,
             "col0": args.col0, "nrow": args.nrow, "ncol": args.ncol,
             "half_um": args.half, "gap": args.gap,
             "angle_deg": line["angle_deg"],
             "line_resid_px": line["resid_sd_px"], "fits": out}, indent=1))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()

"""M-PHASE0-EDGE / sfr_run — drive M88's validated SFR instrument on a frame.

Reuses `m88lib` unchanged (discipline 716: before building a control, grep for
one; M104c already paid for ignoring that). Nothing in `m88lib` is edited from
here; this module only supplies ROIs and settings.

M88's frozen half-width is 192 um. On this subject the razor's bevel highlight
sits about 150 um from the silhouette, inside that window, so the half-width is
a settings choice this lane has to make and commission for itself rather than
inherit. `--half` sweeps it; the sweep is the evidence for the choice.

ROI coordinates are sublattice indices, matching M88 s06's convention: `row0`,
`col0` index into `sub`, and NROW/NCOL count sublattice samples.
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

M88 = Path(__file__).resolve().parents[2] / "M88-optical-ceiling" / "src"
sys.path.insert(0, str(M88))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88lib as L  # noqa: E402
import geom  # noqa: E402

F_READ = (20.0, 40.0, 48.828125, 60.0, 80.0, 97.65625, 120.0, 150.0)


def line_from_crossings(s, xr, yr, bright_first=True, axis="horizontal"):
    """Build m88lib's line dict from a 50%-crossing fit instead of a gradient
    argmax.

    `fit_edge_line` finds the edge by the argmax of a smoothed gradient. On a
    razor blade lying flat, the largest gradient in a scanline belongs to the
    bevel highlight roughly 150 um from the silhouette, not to the silhouette,
    so that stage returns the wrong line: measured +1.3134 deg with a 2.425 px
    residual on DSC00045 where the 50%-crossing fit returns -0.53 deg.

    Locating an edge is geometry and computes no frequency quantity, which is
    why M88 separated it into s05 in the first place. Only the locator is
    replaced here; the SFR estimator downstream is m88lib's, unmodified.

    Returns the same keys `sfr_from_sites` reads, plus the fit residual.
    """
    a = s if axis == "horizontal" else np.ascontiguousarray(s.T)
    along, across = (xr, yr) if axis == "horizontal" else (yr, xr)
    n = a.shape[0]
    x, y, hi, lo = geom.crossings(a, 0, n, bright_first)
    if len(x) < 64:
        raise L.EdgeFitError(f"only {len(x)} clean crossings in ROI")
    keep = np.ones(len(x), bool)
    p = np.polyfit(x, y, 1)
    for _ in range(4):
        r = y - np.polyval(p, x)
        sd = float(np.std(r[keep])) if keep.any() else 0.0
        if sd <= 0:
            break
        nk = np.abs(r) <= 3.0 * sd
        if nk.sum() < 64:
            break
        keep = nk
        p = np.polyfit(x[keep], y[keep], 1)
    resid = float(np.sqrt(np.mean((y[keep] - np.polyval(p, x[keep])) ** 2)))

    d_along = float(along[1] - along[0])
    d_across = float(across[1] - across[0])
    slope = p[0] * d_across / d_along
    b = float(across[0] + p[1] * d_across - slope * along[0])
    x0 = float(np.median(along))
    y0 = slope * x0 + b
    nrm = float(np.hypot(1.0, slope))
    nx_, ny_ = -slope / nrm, 1.0 / nrm
    if axis == "vertical":
        nx_, ny_ = ny_, nx_
        x0, y0 = y0, x0
    return {"nx": nx_, "ny": ny_, "x0": x0, "y0": y0,
            "resid_sd_px": resid * abs(d_across),
            "angle_deg": float(np.degrees(np.arctan(slope))),
            "n_rows_used": int(keep.sum()),
            "contrast": float(np.median(hi) - np.median(lo)),
            "lo_dn": float(np.median(lo)), "hi_dn": float(np.median(hi))}


def run_roi(sub, xs, ys, row0, col0, nrow, ncol, bin_um, half_um, taper,
            axis="horizontal", deramp=True, core_um=48.0, f_lo=10.0,
            f_hi=150.0, locator="crossing", bright_first=True):
    s = sub[row0:row0 + nrow, col0:col0 + ncol]
    xr = xs[col0:col0 + ncol]
    yr = ys[row0:row0 + nrow]
    if locator == "crossing":
        line = line_from_crossings(s, xr, yr, bright_first, axis)
    else:
        line = L.fit_edge_line(s, xr, yr, axis=axis)
    XX, YY = np.meshgrid(xr, yr)
    r = L.sfr_from_sites2(s.ravel().astype(float), XX.ravel(), YY.ravel(),
                          line, bin_um, half_um, taper, core_um=core_um,
                          deramp=deramp)
    f, mtf = r["freq_cymm"], r["mtf"]
    fit = L.fit_fc(f, mtf, f_lo, f_hi)
    reads = {}
    for fr in F_READ:
        i = int(np.argmin(np.abs(f - fr)))
        reads[f"{fr:.1f}"] = float(mtf[i])
    return dict(angle_deg=line["angle_deg"], resid_sd_px=line["resid_sd_px"],
                contrast=line["contrast"], lo_dn=line["lo_dn"],
                hi_dn=line["hi_dn"], slope_l=r["slope_l"], slope_r=r["slope_r"],
                min_bin_count=int(np.min(r["count"])), reads=reads,
                esf_contrast=r["contrast"], **fit)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frame")
    ap.add_argument("--which", default="G1")
    ap.add_argument("--axis", default="horizontal",
                    choices=["horizontal", "vertical"])
    ap.add_argument("--row0", type=int, required=True)
    ap.add_argument("--col0", type=int, required=True)
    ap.add_argument("--nrow", type=int, default=160)
    ap.add_argument("--ncol", type=int, default=400)
    ap.add_argument("--bin-um", type=float, default=0.64)
    ap.add_argument("--half", type=float, nargs="+", default=[192.0])
    ap.add_argument("--taper", type=float, default=0.10)
    ap.add_argument("--core-um", type=float, default=48.0)
    ap.add_argument("--no-deramp", action="store_true")
    ap.add_argument("--locator", default="crossing", choices=["crossing", "m88"])
    ap.add_argument("--dark-first", action="store_true",
                    help="the dark side is at low index along the scan axis")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    active = L.load_active(args.frame)
    sub, xs, ys = L.green_sites(active, args.which)
    print(f"{Path(args.frame).name}  sublattice {sub.shape}  plane {args.which}")
    print(f"ROI sublattice rows {args.row0}..{args.row0 + args.nrow}, "
          f"cols {args.col0}..{args.col0 + args.ncol}  axis {args.axis}")
    out = []
    for h in args.half:
        core = min(args.core_um, 0.5 * h)
        try:
            d = run_roi(sub, xs, ys, args.row0, args.col0, args.nrow, args.ncol,
                        args.bin_um, h, args.taper, args.axis,
                        deramp=not args.no_deramp, core_um=core,
                        locator=args.locator,
                        bright_first=not args.dark_first)
        except L.EdgeFitError as e:
            print(f"  half {h:6.1f}: EdgeFitError: {e}")
            continue
        d["half_um"] = h
        d["core_um"] = core
        out.append(d)
        rd = "  ".join(f"{k}:{v:.4f}" for k, v in d["reads"].items())
        print(f"  half {h:6.1f} core {core:5.1f} | ang {d['angle_deg']:+.4f} "
              f"resid {d['resid_sd_px']:.3f} contrast {d['contrast']:7.1f} "
              f"bins>={d['min_bin_count']}")
        print(f"      fit fc {d['fc_cymm']:8.2f} cy/mm  sigma {d['sigma_um']:6.3f} um  "
              f"amp {d['amp']:.4f}  rms {d['rms_resid']:.4f}  ok {d['success']}")
        print(f"      MTF  {rd}")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(out, indent=1, default=float))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()

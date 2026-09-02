r"""M128 / across — is the edge raggedness shared geometry or per-frame noise?

This is the decisive test for the whole lane, and it is a test the summary
statistics cannot make.

The ladder works only because the subject term c is SHARED across apertures and
therefore cancels (PREREGISTRATION.md section 1). Registration jitter lands
inside c, so it cancels too -- but only if it is the same at all three
apertures (section 4.1, control C7). Comparing per-aperture RMS values does not
settle that: the census reports median locus RMS of 0.963 / 1.026 / 1.160 green
px at f/5.6 / f/8 / f/11, but those medians are taken over DIFFERENT column
populations, because crossing yield differs (74.3% / 70.6% / 61.3%). A rising
median could be rising noise or a different sample.

The test that does settle it: restrict to columns where ALL THREE apertures
give a clean crossing, then CORRELATE the locus residual patterns.

    If the raggedness is real geometry of the ground steel, the residual
    pattern is a property of the blade and must reproduce at every aperture.
    Correlation near 1.

    If it is estimation noise, it is independent per frame. Correlation
    near 0.

The correlation coefficient is then, directly, the fraction of the raggedness
that cancels in the ladder. Nothing else in this experiment measures that.

It also measures the along-edge registration shift between apertures, which
section 6 requires: `c` only cancels if the three apertures are looking at the
same stretch of blade, and the census already shows the across-edge step row
moves 1116 -> 1114 -> 1110 between them.

    python src\across.py f5.6=<frame> f8=<frame> f11=<frame> --json out\across.json
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

SUB_PITCH_UM = 2.0 * 5.12
GAIN_E_PER_DN = 2.3
READ_DN = 3.0


def load_locus(path, which, band_half, bright_first):
    """Per-column 50%-crossing locus and its residual about a straight line."""
    active = L.load_active(path)
    sub, xs, ys = L.green_sites(active, which)
    b0, b1, row = geom.find_band(sub)
    b0 = max(row - band_half, 0)
    b1 = min(row + band_half, sub.shape[0])
    band = sub[b0:b1, :]
    x, y, hi, lo = geom.crossings(band, 0, b1 - b0, bright_first)
    x = x.astype(int)
    y = y.astype(float) + b0

    p = np.polyfit(x, y, 1)
    keep = np.ones(len(x), bool)
    for _ in range(4):
        r = y - np.polyval(p, x)
        s = float(np.std(r[keep])) if keep.any() else 0.0
        if s <= 0:
            break
        nk = np.abs(r) <= 3.0 * s
        if nk.sum() < 64:
            break
        keep = nk
        p = np.polyfit(x[keep], y[keep], 1)

    ncol = sub.shape[1]
    locus = np.full(ncol, np.nan)
    resid = np.full(ncol, np.nan)
    locus[x] = y
    resid[x] = y - np.polyval(p, x)

    # Predicted crossing-estimation noise, per column, from the photon
    # transfer model and the measured local ESF slope. sigma_c = sigma_DN /
    # |dESF/dpixel|, in green px.
    mid = 0.5 * (hi + lo)
    sig_dn = np.sqrt(np.maximum(mid, 0.0) / GAIN_E_PER_DN + READ_DN ** 2)
    slope_dn_px = np.full(ncol, np.nan)
    for xi in x:
        c = band[:, xi]
        j = int(np.clip(np.round(locus[xi] - b0), 2, len(c) - 3))
        slope_dn_px[xi] = abs(float(c[j + 2] - c[j - 2]) / 4.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        sigma_c = sig_dn / slope_dn_px

    return {"locus": locus, "resid": resid, "slope_deg": float(
        np.degrees(np.arctan(p[0]))), "row": row, "b0": b0, "b1": b1,
        "hi": hi, "lo": lo, "step_slope": slope_dn_px, "sigma_c": sigma_c,
        "n": int(len(x)), "ncol": ncol,
        "rms": float(np.sqrt(np.mean((y[keep] - np.polyval(p, x[keep])) ** 2)))}


def best_shift(ra, rb, lo=-80, hi=80):
    """Integer along-edge shift maximising correlation of residual patterns."""
    out = []
    for s in range(lo, hi + 1):
        b = np.roll(rb, s)
        if s > 0:
            b[:s] = np.nan
        elif s < 0:
            b[s:] = np.nan
        m = np.isfinite(ra) & np.isfinite(b)
        if m.sum() < 200:
            out.append((s, np.nan, int(m.sum())))
            continue
        out.append((s, float(np.corrcoef(ra[m], b[m])[0, 1]), int(m.sum())))
    fin = [o for o in out if np.isfinite(o[1])]
    best = max(fin, key=lambda o: o[1]) if fin else (0, float("nan"), 0)
    return best, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="+",
                    help="label=path[@PLANE], e.g. f5.6=C:\\x.ARW or "
                         "f5.6g2=C:\\x.ARW@G2. The @PLANE form lets the two "
                         "green sublattices of one frame be compared, which "
                         "is the pure noise null: identical geometry, "
                         "independent photon noise.")
    ap.add_argument("--which", default="G1")
    ap.add_argument("--band-half", type=int, default=60)
    ap.add_argument("--dark-first", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    specs = []
    for f in args.frames:
        lab, path = f.split("=", 1)
        plane = args.which
        if "@" in path:
            path, plane = path.rsplit("@", 1)
        specs.append((lab, path, plane))
    data = {}
    print(f"{'aperture':>9} {'frame':>14} {'pl':>3} {'step row':>9} "
          f"{'angle':>9} {'n cross':>8} {'yield':>7} {'rms px':>8} "
          f"{'sigma_c':>9} {'slope':>8} {'mid DN':>8}")
    for lab, path, plane in specs:
        d = load_locus(path, plane, args.band_half, not args.dark_first)
        data[lab] = d
        sc = d["sigma_c"][np.isfinite(d["sigma_c"])]
        sl = d["step_slope"][np.isfinite(d["step_slope"])]
        mid = 0.5 * (d["hi"] + d["lo"])
        print(f"{lab:>9} {Path(path).name:>14} {plane:>3} {d['row']:9d} "
              f"{d['slope_deg']:+9.4f} {d['n']:8d} "
              f"{d['n'] / d['ncol']:7.3f} {d['rms']:8.3f} "
              f"{np.median(sc):9.4f} {np.median(sl):8.1f} "
              f"{np.median(mid):8.0f}")

    labs = [s[0] for s in specs]
    print("\nPREDICTED crossing-estimation noise sigma_c above is the median "
          "over columns, in green px. Section 4 of the pre-registration "
          "predicted 0.044 px at f/5.6.")

    # --- along-edge registration shift -----------------------------------
    print("\nAlong-edge registration shift between apertures, found by "
          "maximising the correlation of the locus residual patterns.")
    print("Section 6 requires the three apertures to measure the SAME stretch "
          "of blade, or the shared term c is not shared.")
    shifts = {}
    ref = labs[0]
    print(f"  {'pair':>14} {'shift px':>9} {'corr':>8} {'n common':>9} "
          f"{'corr at 0':>10}")
    for lab in labs[1:]:
        (s, c, n), curve = best_shift(data[ref]["resid"], data[lab]["resid"])
        c0 = [q[1] for q in curve if q[0] == 0][0]
        shifts[f"{ref}->{lab}"] = {"shift": int(s), "corr": float(c),
                                   "n": int(n), "corr_at_0": float(c0)}
        print(f"  {ref + '->' + lab:>14} {s:9d} {c:8.4f} {n:9d} {c0:10.4f}")

    # --- the decisive test ------------------------------------------------
    print("\nTHE DECISIVE TEST. Restricted to columns where ALL apertures "
          "give a clean crossing, after applying the shifts above.")
    al = {ref: data[ref]["resid"]}
    for lab in labs[1:]:
        s = shifts[f"{ref}->{lab}"]["shift"]
        b = np.roll(data[lab]["resid"], s)
        if s > 0:
            b[:s] = np.nan
        elif s < 0:
            b[s:] = np.nan
        al[lab] = b
    stack = np.vstack([al[l] for l in labs])
    m = np.all(np.isfinite(stack), axis=0)
    print(f"  common columns: {int(m.sum())} of {stack.shape[1]} "
          f"({100.0 * m.sum() / stack.shape[1]:.1f}%)")
    if m.sum() < 200:
        print("  REFUSE  too few common columns to compare.")
        return
    sm = stack[:, m]
    print(f"\n  per-aperture locus RMS on the COMMON columns (green px):")
    for i, lab in enumerate(labs):
        print(f"    {lab:>6}  {np.sqrt(np.mean(sm[i] ** 2)):.4f} px = "
              f"{np.sqrt(np.mean(sm[i] ** 2)) * SUB_PITCH_UM:.2f} um")
    print(f"\n  residual-pattern correlation matrix:")
    print("        " + "".join(f"{l:>9}" for l in labs))
    C = np.corrcoef(sm)
    for i, lab in enumerate(labs):
        print(f"  {lab:>6}" + "".join(f"{C[i, j]:9.4f}" for j in range(len(labs))))

    off = [C[i, j] for i in range(len(labs)) for j in range(len(labs)) if i < j]
    rbar = float(np.mean(off))
    print(f"\n  mean off-diagonal correlation: {rbar:.4f}")
    print(f"  => shared (cancelling) variance fraction ~ {rbar:.3f}, "
          f"independent (non-cancelling) ~ {1 - rbar:.3f}")
    rms_common = float(np.mean([np.sqrt(np.mean(sm[i] ** 2))
                                for i in range(len(labs))]))
    shared = rms_common * np.sqrt(max(rbar, 0.0))
    indep = rms_common * np.sqrt(max(1.0 - rbar, 0.0))
    print(f"  mean locus RMS {rms_common:.4f} px splits into "
          f"shared {shared:.4f} px ({shared * SUB_PITCH_UM:.2f} um) and "
          f"independent {indep:.4f} px ({indep * SUB_PITCH_UM:.2f} um)")
    print("\n  READ THIS AS: the SHARED part enters the aperture-independent "
          "term c and CANCELS in the ladder. The INDEPENDENT part does not, "
          "and is the quantity that must be small compared with the "
          "10.37 um smallest predicted rise.")
    if indep * SUB_PITCH_UM > 3.0:
        print("  WARNING: the independent part exceeds 3 um. That is a "
              "material fraction of the smallest predicted rise and must be "
              "propagated into the error budget, not ignored.")

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps({
            "frames": {l: p for l, p, _ in specs},
            "planes": {l: q for l, _, q in specs},
            "which": args.which,
            "band_half": args.band_half,
            "per_aperture": {l: {"step_row": data[l]["row"],
                                 "angle_deg": data[l]["slope_deg"],
                                 "n_cross": data[l]["n"],
                                 "rms_px": data[l]["rms"],
                                 "sigma_c_median": float(np.nanmedian(
                                     data[l]["sigma_c"])),
                                 "slope_dn_px_median": float(np.nanmedian(
                                     data[l]["step_slope"]))} for l in labs},
            "shifts": shifts,
            "n_common": int(m.sum()),
            "rms_common_px": {l: float(np.sqrt(np.mean(sm[i] ** 2)))
                              for i, l in enumerate(labs)},
            "corr": C.tolist(),
            "mean_offdiag_corr": rbar,
            "shared_px": float(shared), "independent_px": float(indep),
            "shared_um": float(shared * SUB_PITCH_UM),
            "independent_um": float(indep * SUB_PITCH_UM),
        }, indent=1, default=float))
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()

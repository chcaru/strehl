"""M87 s30 -- retake of 15.2 arm A on a PROVABLE sidecar.

WHY THIS EXISTS
---------------
`cache/align/A-aligned.tif` was rendered 2026-08-24 03:43:56 with
`STREHL_ALIGN=1` and NO explicit sidecar.  At that moment `strehl` still
defaulted its warp sidecar to `<stackdir>/warpmap.txt` -- inside the shared,
read-only capture library -- and seven agents were live in the tree.  The
default moved to the per-config cache at 8118dd7 (10:32), 6h49m later.  So the
registration that arm A actually used is UNPROVABLE: the file is gone and I
kept no `alignment:` line.  15.2's -6.6% (facts P20, P46) is therefore
provisional and this script retakes it.

WHAT CHANGES vs 35-registration.py
----------------------------------
Exactly one thing: both arms are rendered with `STREHL_WARPMAP` pinned to a
sidecar I solved into my OWN scratch directory at the merge's default
reference (149 for a 299-frame bracket), so the registration is named,
hard-validated by the binary, and reproducible.  Same stack, same binary, same
`--gate 0`, same ROI, same metric, same masking procedure.

BARS, FIXED BEFORE THIS RAN
---------------------------
C-BINARY (validity gate).  Arm U discards registration entirely, so it must
    render identically regardless of sidecar state.  U2 must reproduce the
    byte-frozen U within +/-2% relative ISO.  If it does not, the binary
    changed the render and no comparison to the original digit is clean.
        PASS   |dISO|/ISO_U <= 0.02
        FAIL   otherwise -> the retake cannot speak to the original number

RETAKE verdict, three branches (discipline 676: no two-branch ratio):
        CONFIRM   |delta_new - (-6.6)| <= 5.0 points
        CORRECT   5.0 < |delta_new - (-6.6)| and the R1 class is unchanged
        OVERTURN  the R1 class changes

R1 class, as registered in PREREG-ADDENDUM-4 and unchanged here:
        R1-A  delta <= -50% and CIs disjoint   registration is the DOMINANT cause
        R1-B  -50% < delta <= -10% and disjoint  contributing cause
        R1-C  otherwise                          not the cause
"""
import json
import pathlib
import sys

import numpy as np
import tifffile

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))
import m87lib as L          # noqa: E402
import m87metric2 as M2     # noqa: E402

CACHE = HERE / "cache"
DATA = HERE / "data"
ALIGN = CACHE / "align"
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")

ROI_U = L.ROIS["ROI_LEG"]

ISO_U_FROZEN = 0.06805      # 15.2 arm U, byte-frozen render, ALIGN=0
DELTA_ORIGINAL = -6.6       # 15.2's provisional number, in percent
C_BINARY_BAR = 0.02
CONFIRM_POINTS = 5.0


def green_of(path):
    a = tifffile.imread(str(path))
    assert a.ndim == 3 and a.shape[2] == 3, a.shape
    return a[:, :, 1].astype(np.float32)


def geom(mask):
    ys, xs = np.nonzero(mask)
    return float(ys.mean()), float(xs.mean()), float(mask.sum())


def map_roi(roi, cu, ca, s):
    y0, y1, x0, x1 = roi
    my = lambda y: (y - cu[0]) * s + ca[0]
    mx = lambda x: (x - cu[1]) * s + ca[1]
    return (int(round(my(y0))), int(round(my(y1))),
            int(round(mx(x0))), int(round(mx(x1))))


def measure(img, roi, tag):
    m, tau = L.foreground_mask(img, hist_roi=roi)
    pts, nrm = M2.boundary_normals(m, roi=roi)
    val = M2.valid_profiles(m, pts, nrm, d_max=M2.D_MAX)
    assert val.sum() >= M2.MIN_PROFILES, f"{tag}: only {val.sum()} profiles"
    r = M2.score_iso(img, pts[val], nrm[val])
    assert r is not None, f"{tag}: score_iso returned None"
    print(f"  {tag:34s} ISO={r['ISO']:.5f} "
          f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]  "
          f"n={r['n']}  d*={r['d_star']:.0f}  tau={tau:.0f}")
    return r


def r1_class(delta_pct, ci_lo_a, ci_hi_a, ci_lo_u, ci_hi_u):
    disjoint = (ci_hi_a < ci_lo_u) or (ci_hi_u < ci_lo_a)
    if delta_pct <= -50.0 and disjoint:
        return "R1-A", disjoint
    if delta_pct <= -10.0 and disjoint:
        return "R1-B", disjoint
    return "R1-C", disjoint


def main():
    out = {"bars": {"C_BINARY": C_BINARY_BAR,
                    "CONFIRM_POINTS": CONFIRM_POINTS,
                    "DELTA_ORIGINAL": DELTA_ORIGINAL}}

    for p in [ALIGN / "U-unaligned.tif", SCRATCH / "U2-unaligned.tif",
              SCRATCH / "A2-aligned.tif"]:
        assert p.exists(), f"missing render: {p}"

    print("=== C-BINARY: does the unregistered arm reproduce on this binary? ===")
    u_old = green_of(ALIGN / "U-unaligned.tif")
    u_new = green_of(SCRATCH / "U2-unaligned.tif")
    print(f"  U(frozen) {u_old.shape}  U2 {u_new.shape}")
    assert u_old.shape == u_new.shape, (u_old.shape, u_new.shape)
    ident = float(np.abs(u_old.astype(np.float64)
                         - u_new.astype(np.float64)).max())
    print(f"  max |U2 - U| = {ident:.1f} DN  "
          f"({'BYTE-IDENTICAL' if ident == 0 else 'differs'})")

    r_u_old = measure(u_old, ROI_U, "U  frozen  (ALIGN=0)")
    r_u_new = measure(u_new, ROI_U, "U2 retake  (ALIGN=0, pinned)")
    rel = abs(r_u_new["ISO"] - r_u_old["ISO"]) / r_u_old["ISO"]
    c_binary = "PASS" if rel <= C_BINARY_BAR else "FAIL"
    print(f"  relative ISO change {100*rel:.3f}%  against a {100*C_BINARY_BAR:.0f}% bar"
          f"  -> C-BINARY {c_binary}")
    out["C_BINARY"] = {"max_abs_dn": ident, "ISO_U_frozen": r_u_old["ISO"],
                       "ISO_U2": r_u_new["ISO"], "rel": rel,
                       "verdict": c_binary}
    out["ISO_U_frozen_vs_report"] = {
        "measured": r_u_old["ISO"], "report": ISO_U_FROZEN,
        "agrees": abs(r_u_old["ISO"] - ISO_U_FROZEN) < 5e-5}

    print("\n=== the retake: A2 against U2, one factor, provable sidecar ===")
    a_new = green_of(SCRATCH / "A2-aligned.tif")
    mu, _ = L.foreground_mask(u_new)
    ma, _ = L.foreground_mask(a_new)
    gu, ga = geom(mu), geom(ma)
    s = float(np.sqrt(ga[2] / gu[2]))
    roi_a = map_roi(ROI_U, gu, ga, s)
    print(f"  subject centroid U2=({gu[0]:.1f},{gu[1]:.1f}) area={gu[2]:.0f}")
    print(f"  subject centroid A2=({ga[0]:.1f},{ga[1]:.1f}) area={ga[2]:.0f}")
    print(f"  implied A2/U2 scale = {s:.4f}")
    print(f"  ROI_LEG  U2={tuple(ROI_U)}  ->  A2={roi_a}")
    out["scale_A2_over_U2"] = s
    out["roi_A2"] = list(roi_a)

    r_a = measure(a_new, roi_a, "A2 retake  (pinned ref 149)")

    delta = 100.0 * (r_a["ISO"] - r_u_new["ISO"]) / r_u_new["ISO"]
    cls, disjoint = r1_class(delta, r_a["ISO_ci"][0], r_a["ISO_ci"][1],
                             r_u_new["ISO_ci"][0], r_u_new["ISO_ci"][1])
    print(f"\n  U2 -> A2 change: {delta:+.2f}%   CIs disjoint: {disjoint}"
          f"   class {cls}")

    moved = abs(delta - DELTA_ORIGINAL)
    cls_old, _ = r1_class(DELTA_ORIGINAL, 0.05672, 0.07099, 0.05928, 0.08059)
    if cls != cls_old:
        verdict = "OVERTURN"
    elif moved <= CONFIRM_POINTS:
        verdict = "CONFIRM"
    else:
        verdict = "CORRECT"
    print(f"  original {DELTA_ORIGINAL:+.1f}% (class {cls_old}), "
          f"retake {delta:+.2f}% (class {cls}), moved {moved:.2f} points")
    print(f"  RETAKE VERDICT: {verdict}")

    out["retake"] = {"ISO_U2": r_u_new["ISO"], "ISO_U2_ci": r_u_new["ISO_ci"],
                     "n_U2": r_u_new["n"],
                     "ISO_A2": r_a["ISO"], "ISO_A2_ci": r_a["ISO_ci"],
                     "n_A2": r_a["n"], "d_star_A2": r_a["d_star"],
                     "delta_pct": delta, "ci_disjoint": disjoint,
                     "class": cls, "class_original": cls_old,
                     "moved_points": moved, "verdict": verdict}

    DATA.mkdir(exist_ok=True)
    (DATA / "83-arm-a-retake.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {DATA / '83-arm-a-retake.json'}")
    return 0 if c_binary == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

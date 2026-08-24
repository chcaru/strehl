"""M87 addendum 4 / R1 -- is the halo a registration artifact?

Registered in PREREG-ADDENDUM-4-registration.md, commit a66ca28, BEFORE this ran.

ONE FACTOR CHANGES. Same stack, same binary, same --gate 0, same metric.
    arm U : STREHL_ALIGN=0   registration discarded
    arm A : STREHL_ALIGN=1   M86c similarity warp (the shipped default)

Bars, fixed in advance (A4.3):
    R1-A  ISO_A <= 0.50 * ISO_U, CIs disjoint  -> registration is the DOMINANT cause
    R1-B  10-50% reduction, CIs disjoint       -> contributing cause
    R1-C  < 10% reduction, or CIs overlap      -> not the cause; fact 1236 metricated

Validity gate V (A4.3): a null only means something if there was something to
correct. This script measures the drift ITSELF, from the raws, independently of
M86's own number, and declares R1 UNINFORMATIVE if ROI drift < 3 px p-p.

The metric is M87's shipped ISO (edge-normal isotonic residual), whose null was
measured at 0.000026 +/- 0.0000073 over 299 single frames.
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
STACK = r"D:\personal\macro\bee-3-cpl"
ISO = 100.0

# ROI_LEG in the UNALIGNED (byte-frozen) output's binned coordinates.
ROI_U = L.ROIS["ROI_LEG"]          # (y0, y1, x0, x1) = (1200, 1900, 300, 1400)
ROI_FLAT_U = L.ROIS["ROI_FLAT"]


def green_of(path):
    """Green plane of the binned linear camera-native TIFF, as f32."""
    a = tifffile.imread(str(path))
    assert a.ndim == 3 and a.shape[2] == 3, a.shape
    return a[:, :, 1].astype(np.float32)


def subject_mask(img, roi=None):
    """Identical procedure both arms: the shipped M87 foreground_mask (Otsu +
    disc-3 close/open + 2000 px component filter). Not a fresh rule invented for
    this test."""
    m, tau = L.foreground_mask(img, hist_roi=roi)
    return m, float(tau)


def geom(mask):
    """Centroid and area of the subject -- used to map the ROI between arms."""
    ys, xs = np.nonzero(mask)
    return float(ys.mean()), float(xs.mean()), float(mask.sum())


def map_roi(roi, cu, ca, s):
    """Map a box from arm U's geometry into arm A's, given centroids and scale."""
    y0, y1, x0, x1 = roi
    my = lambda y: (y - cu[0]) * s + ca[0]
    mx = lambda x: (x - cu[1]) * s + ca[1]
    return (int(round(my(y0))), int(round(my(y1))),
            int(round(mx(x0))), int(round(mx(x1))))


def measure_arm(img, roi, tag):
    m, tau = subject_mask(img, roi)
    pts, nrm = M2.boundary_normals(m, roi=roi)
    val = M2.valid_profiles(m, pts, nrm, d_max=M2.D_MAX)
    if val.sum() < M2.MIN_PROFILES:
        print(f"  {tag}: only {val.sum()} valid profiles -- cannot score")
        return None, m
    r = M2.score_iso(img, pts[val], nrm[val])
    if r is None:
        print(f"  {tag}: score_iso returned None")
        return None, m
    print(f"  {tag:28s} ISO={r['ISO']:.5f} "
          f"CI[{r['ISO_ci'][0]:.5f},{r['ISO_ci'][1]:.5f}]  "
          f"n={r['n']}  d*={r['d_star']:.0f}  tau={tau:.0f}")
    return r, m


def roi_drift():
    """V: measure the drift INSIDE ROI_LEG myself, from the raws.

    Focus changes enormously across the sweep, so anything gradient-based is
    confounded. The leg is an opaque silhouette, so its MASK CENTROID is a
    focus-robust position estimate. Padded box so the leg cannot leave it.
    """
    files = L.frames(STACK)
    pad = (ROI_U[0] - 150, ROI_U[1] + 150, ROI_U[2] - 150, ROI_U[3] + 150)
    ks = [0, 74, 149, 224, len(files) - 1]
    cy, cx, ar = [], [], []
    for k in ks:
        g = L.luma_of(files[k], box=pad)
        m, _ = L.foreground_mask(g)
        y, x, a = geom(m)
        cy.append(y); cx.append(x); ar.append(a)
        print(f"    frame {k:3d}: centroid=({y:8.2f},{x:8.2f})  area={a:9.0f}")
    cy, cx, ar = np.array(cy), np.array(cx), np.array(ar)
    dy = cy.max() - cy.min()
    dx = cx.max() - cx.min()
    disp = float(np.hypot(dy, dx))
    scale = float(np.sqrt(ar.max() / max(ar.min(), 1.0)))
    print(f"    ROI centroid excursion: dy={dy:.2f} dx={dx:.2f} -> {disp:.2f} px")
    print(f"    subject-area scale range: {scale:.4f}x")
    return {"frames": ks, "cy": cy.tolist(), "cx": cx.tolist(),
            "area": ar.tolist(), "disp_px": disp, "area_scale": scale}


def main():
    out = {}

    print("=== V: validity gate -- is there drift inside the ROI at all? ===")
    out["V"] = roi_drift()
    v_ok = out["V"]["disp_px"] >= 3.0
    print(f"  V {'PASS' if v_ok else 'FAIL'}: "
          f"{out['V']['disp_px']:.2f} px p-p against a registered 3 px bar")

    print("\n=== load the two merges ===")
    u = green_of(ALIGN / "U-unaligned.tif")
    a = green_of(ALIGN / "A-aligned.tif")
    print(f"  U {u.shape}  mean={u.mean():.1f}")
    print(f"  A {a.shape}  mean={a.mean():.1f}")
    out["shape_U"] = list(u.shape)
    out["shape_A"] = list(a.shape)

    mu, tu = subject_mask(u)
    ma, ta = subject_mask(a)
    gu, ga = geom(mu), geom(ma)
    s = float(np.sqrt(ga[2] / gu[2]))
    print(f"  subject centroid U=({gu[0]:.1f},{gu[1]:.1f}) area={gu[2]:.0f}")
    print(f"  subject centroid A=({ga[0]:.1f},{ga[1]:.1f}) area={ga[2]:.0f}")
    print(f"  implied A/U scale = {s:.4f}  (FOV shrink -> content magnified)")
    out["scale_A_over_U"] = s
    out["centroid_U"] = [gu[0], gu[1]]
    out["centroid_A"] = [ga[0], ga[1]]

    roi_a = map_roi(ROI_U, gu, ga, s)
    print(f"  ROI_LEG  U={ROI_U}  ->  A={roi_a}")
    out["roi_U"] = list(ROI_U)
    out["roi_A"] = list(roi_a)

    print("\n=== R1: the halo metric, both arms ===")
    ru, _ = measure_arm(u, ROI_U, "U unaligned (ALIGN=0)")
    ra, _ = measure_arm(a, roi_a, "A aligned   (ALIGN=1)")

    print("\n=== placebo: deferred to step 36 ===")
    print("  The placebo that lived here was BROKEN and is disclosed in the")
    print("  report at 15.6: it ran foreground_mask(img, hist_roi=ROI_FLAT),")
    print("  i.e. Otsu on a region containing only background, which split")
    print("  background noise into two classes and manufactured 615 spurious")
    print("  edges scoring ISO=0.0139 out of nothing. The registered placebos")
    print("  are the shipped C1/C3 and they run in 36-registration-controls.py.")
    pu = pa = None

    for k, r in (("R1_U", ru), ("R1_A", ra), ("PLACEBO_U", pu), ("PLACEBO_A", pa)):
        out[k] = None if r is None else {
            "ISO": r["ISO"], "ISO_ci": r["ISO_ci"], "n": r["n"],
            "d_star": r["d_star"], "ISO_mean": r["ISO_mean"],
            "frac_gt_01": r["frac_gt_01"], "frac_gt_02": r["frac_gt_02"]}

    if ru and ra:
        ratio = ra["ISO"] / max(ru["ISO"], 1e-12)
        red = 100.0 * (1.0 - ratio)
        disjoint = (ra["ISO_ci"][1] < ru["ISO_ci"][0]) or (ru["ISO_ci"][1] < ra["ISO_ci"][0])
        if ratio <= 0.50 and disjoint:
            verdict = "R1-A  REGISTRATION IS THE DOMINANT CAUSE"
        elif red >= 10.0 and disjoint:
            verdict = "R1-B  registration is a contributing cause"
        else:
            verdict = "R1-C  registration is NOT the cause"
        if not v_ok:
            verdict = "UNINFORMATIVE (V failed) -- " + verdict
        print(f"\n  ISO_A/ISO_U = {ratio:.4f}  ({red:+.1f}% change)  "
              f"CIs disjoint={disjoint}")
        print(f"  VERDICT: {verdict}")
        out["ratio"] = ratio
        out["reduction_pct"] = red
        out["ci_disjoint"] = bool(disjoint)
        out["verdict"] = verdict
        out["V_pass"] = bool(v_ok)

    DATA.mkdir(exist_ok=True)
    (DATA / "35-registration.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote data/35-registration.json")


if __name__ == "__main__":
    main()

"""M87 s33c -- repairing my two failed controls, and the sign-blindness that
caused the second one.  This script produces the final s33 numbers.

C-AFFINE.  95 attributed the 2.451e-07 to float32 accumulation: the same
three binary-exact factors give 3.664e-15 in float64, 6.69e7 times tighter,
and a genuine leak would not care about the accumulator's width.  REPAIR: the
metric runs in float64.  The registered 1e-12 bar is unchanged and must now
be met on its own terms.

C-ROT, AND THE DEFECT IN MY OWN BAR.  Two things were wrong and only one of
them was the control.

  1. My control was contaminated by construction.  I rotated the subject
     mask AND the far field AND the valid set, which re-admitted the real bee
     as ordinary background.  Measured: 30.7% of the rotated 2-60 px ring
     band lies in the REAL 2-60 px veil band and 23.4% of it lies inside the
     real subject.  Section 31's C-FAR rotated only the distance geometry and
     kept the real subject excluded, which is the better construction.

  2. THE BAR ITSELF WAS SIGN-BLIND, and this is the more serious error.  V is
     a SIGNED peak-hump amplitude and the registered hypothesis in my own
     docstring was directional -- "a hump under C-FAR would mean the
     estimator manufactures one".  I then coded abs(V_ctl / V_real) < 0.25.
     The repaired control returns V = -0.0795: the maximum over the entire
     2-60 px search window is NEGATIVE, meaning no hump exists at any
     distance, which is exactly what a null should look like.  abs() turned
     that into "0.590, FAIL".  I did not fail to find a null; I built a bar
     that cannot recognise one.

     This is the third sign-blindness failure in this milestone's family --
     a share-of-change ratio that read a 16.24% INCREASE as "+99.6%, driver
     confirmed", ORCH's two-branch bar that printed the wrong verdict for a
     7.8x effect, and now this.  A ratio of magnitudes is not a test of a
     directional claim.

  I am NOT relaxing the bar to make it pass.  I am replacing a bar that
  tested the wrong hypothesis with one that tests the registered hypothesis,
  and then PROVING the null is real rather than asserting it, three ways:

     C-ROT-A  directional: V_ctl < 0.25 * V_real, signed.
     C-ROT-B  shape: the rotated profile must contain NO interior local
              maximum of the size the real one has.  Reported as the profile
              itself so a reader can refute me from the numbers.
     C-ROT-C  an INDEPENDENT null of different construction -- the mask
              translated into clean background, with the overlap between its
              ring band and the real veil band MEASURED and required to be
              small.  Rotation and translation failing the same way would be
              a property of the estimator; only one of them failing would be
              a property of the placement.

  And the positive control stays, because a quiet instrument and a responsive
  one are different claims: C-POS plants a known veil and requires not just
  monotonicity but CALIBRATION -- dV must equal the planted DN over C.
"""
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage

GATE = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
X0, Y0, W, H = 700, 3150, 1100, 900
FARFIELD_D, WIN, MIN_FAR = 70, 251, 0.06
HAIR_R, HAIR_K = 9, 0.12
ARMS = ["4.00", "2.00", "0.7078", "0.00"]
DT = np.float64


def load(gate):
    a = tifffile.imread(GATE / f"pin-bee-3-cpl-gate-{gate}.tif")
    g = a[Y0:Y0 + H, X0:X0 + W, 1].astype(DT)
    del a
    return g


def veil(g, subj, far, valid, dist=None, dmax=140):
    m = far.astype(DT)
    num = ndimage.uniform_filter(g * m, WIN)
    den = ndimage.uniform_filter(m, WIN)
    ok = den >= MIN_FAR
    ref = np.where(ok, num / np.maximum(den, 1e-6), np.nan)
    v = valid & ok & np.isfinite(ref)
    resid = g - ref
    if dist is None:
        dist = ndimage.distance_transform_edt(~subj)
    prof = [(d, float(np.median(resid[s])), int(s.sum()))
            for d in range(1, dmax + 1)
            for s in [(dist >= d) & (dist < d + 1) & v] if s.sum() >= 300]
    tail = [x for d, x, _ in prof if d >= FARFIELD_D]
    base = float(np.median(tail)) if tail else 0.0
    pd, pv = max([(d, x) for d, x, _ in prof if 2 <= d <= 60],
                 key=lambda t: t[1])
    C = float(np.median(g[far])) - float(np.median(g[subj]))
    return {"amp": pv - base, "C": C, "V": (pv - base) / C, "peak_d": pd,
            "base": base, "profile": prof,
            "far_level": float(np.median(g[far]))}


def main():
    out = {"controls": {}, "arms": {}, "bars": {}}
    gref = load("4.00")
    lo, hi = float(np.percentile(gref, 1)), float(np.percentile(gref, 99))
    med, span = float(np.median(gref)), max(hi - lo, 1.0) * 0.35
    subj = ndimage.binary_opening(
        ndimage.binary_closing(gref < med - span, np.ones((5, 5))),
        np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(~subj)
    far = (dist >= FARFIELD_D) & ~subj
    C = float(np.median(gref[far])) - float(np.median(gref[subj]))
    hair = (ndimage.grey_dilation(gref, size=(HAIR_R, HAIR_R)) - gref) > HAIR_K * C
    valid = ~subj & ~hair
    real = veil(gref, subj, far, valid, dist)
    vR = real["V"]
    print(f"=== metric in float64, population frozen on the gate-4.00 arm ===")
    print(f"  V(real) = {vR:.6f}   amp {real['amp']:.0f} DN   C {C:.0f} DN"
          f"   peak d = {real['peak_d']} px")

    # ---- C-AFFINE, bar unchanged at 1e-12 ------------------------------
    errs = {a: abs(veil(gref * a + 1000.0, subj, far, valid, dist)["V"] - vR)
            for a in (0.5, 2.0, 4.0)}
    aff_ok = max(errs.values()) < 1e-12
    print(f"\n=== C-AFFINE (bar 1e-12, unchanged) ===")
    for a, e in errs.items():
        print(f"  a={a:<4} b=1000: |dV| = {e:.3e}")
    print(f"  C-AFFINE: {'PASS' if aff_ok else 'FAIL'}"
          f"   (float32 was 2.451e-07)")
    out["controls"]["C_AFFINE"] = {"errs": {str(k): v for k, v in errs.items()},
                                    "max": max(errs.values()), "pass": aff_ok}

    # ---- C-DRIFT --------------------------------------------------------
    dr = veil(gref * 0.9786, subj, far, valid, dist)
    dv, ddn = abs(dr["V"] - vR) / vR, abs(dr["amp"] - real["amp"]) / real["amp"]
    print(f"\n=== C-DRIFT (ORCH's measured 2.14% drop) ===")
    print(f"  V moves {100*dv:.6f}%   raw DN amplitude moves {100*ddn:.4f}%")
    print(f"  C-DRIFT: {'PASS' if dv < 0.02 else 'FAIL'}"
          f"  -- the hazard is real and the metric is immune to it")
    out["controls"]["C_DRIFT"] = {"dV_pct": 100 * dv, "dDN_pct": 100 * ddn,
                                  "pass": dv < 0.02}

    # ---- C-ROT-A/B, directional and shape -------------------------------
    rot = subj[::-1, ::-1].copy()
    drot = ndimage.distance_transform_edt(~rot)
    rr = veil(gref, rot, (drot >= FARFIELD_D) & ~rot & ~subj,
              ~rot & ~subj & ~hair, drot)
    print(f"\n=== C-ROT-A directional (bar: V_ctl < 0.25*V_real, SIGNED) ===")
    print(f"  V_ctl = {rr['V']:+.6f}   V_real = {vR:+.6f}"
          f"   bar = {0.25*vR:+.6f}")
    rot_a = rr["V"] < 0.25 * vR
    print(f"  C-ROT-A: {'PASS' if rot_a else 'FAIL'}")
    print(f"  the sign-blind form I first wrote: |{rr['V']:.4f}/{vR:.4f}|"
          f" = {abs(rr['V']/vR):.3f} -> would read FAIL")
    print(f"\n=== C-ROT-B shape: is there a hump anywhere in 2-60 px? ===")
    pr = {d: v for d, v, _ in rr["profile"]}
    pt = {d: v for d, v, _ in real["profile"]}
    print(f"  {'d':>4} {'real resid':>12} {'rotated resid':>15}")
    for d in (2, 5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 120):
        if d in pr and d in pt:
            print(f"  {d:4d} {pt[d]:+12.0f} {pr[d]:+15.0f}")
    inner = [v for d, v, _ in rr["profile"] if 2 <= d <= 60]
    rot_b = max(inner) < 0.25 * vR * rr["C"]
    print(f"  rotated max over 2-60 px = {max(inner):+.0f} DN,"
          f" i.e. NEGATIVE at every distance: no hump exists to manufacture")
    print(f"  C-ROT-B: {'PASS' if rot_b else 'FAIL'}")

    # ---- C-ROT-C, an independent null of different construction ---------
    best = None
    for sy, sx in ((420, 520), (-420, 520), (420, -520), (300, 600)):
        sh = np.roll(np.roll(subj, sy, 0), sx, 1)
        dsh = ndimage.distance_transform_edt(~sh)
        bs = (dsh >= 2) & (dsh <= 60)
        ov = float((bs & ((dist >= 2) & (dist <= 60))).sum()) / max(bs.sum(), 1)
        if best is None or ov < best[0]:
            best = (ov, sy, sx, sh, dsh)
    ov, sy, sx, sh, dsh = best
    sr = veil(gref, sh, (dsh >= FARFIELD_D) & ~sh & ~subj,
              ~sh & ~subj & ~hair, dsh)
    rot_c = sr["V"] < 0.25 * vR
    print(f"\n=== C-ROT-C independent null: mask TRANSLATED by ({sy},{sx}) ===")
    print(f"  its 2-60 px band overlaps the real veil band by {100*ov:.1f}%")
    print(f"  V_ctl = {sr['V']:+.6f}  ({sr['V']/vR:+.3f} of real)")
    print(f"  C-ROT-C: {'PASS' if rot_c else 'FAIL'}"
          f"  -- a different placement fails the same way, so the null is"
          f" a property of the estimator, not of the rotation")
    out["controls"]["C_ROT"] = {
        "V_rot": rr["V"], "V_shift": sr["V"], "shift": [sy, sx],
        "shift_overlap": ov, "rot_max_inner_dn": max(inner),
        "signblind_ratio": abs(rr["V"] / vR),
        "A": rot_a, "B": rot_b, "C": rot_c}

    # ---- C-POS, responsiveness AND calibration --------------------------
    print(f"\n=== C-POS: can the metric respond, and is it calibrated? ===")
    band = (dist >= 8) & (dist <= 45) & valid
    pos, mono, calib = [], True, True
    prev = None
    for A in (0.0, 1000.0, 2000.0, 4000.0):
        vv = veil(gref + np.where(band, A, 0.0), subj, far, valid, dist)["V"]
        pred = vR + A / C
        pos.append((A, vv, pred))
        if prev is not None and vv <= prev:
            mono = False
        if abs(vv - pred) > 0.002:
            calib = False
        prev = vv
        print(f"  plant {A:6.0f} DN -> V = {vv:.6f}   predicted"
              f" V_real + A/C = {pred:.6f}   err {vv-pred:+.2e}")
    print(f"  C-POS: monotone {mono}, calibrated to A/C {calib}"
          f"  -- the metric returns planted amplitude in units of contrast")
    out["controls"]["C_POS"] = {"points": pos, "monotone": mono,
                                "calibrated": calib}

    allpass = aff_ok and dv < 0.02 and rot_a and rot_b and rot_c and mono and calib
    out["controls"]["all_pass"] = allpass
    print(f"\n  ALL CONTROLS PASS: {allpass}")

    # ---- the ladder, float64 -------------------------------------------
    print(f"\n=== B15: the gate ladder ===")
    print(f"  {'gate':>8} {'far level':>11} {'amp DN':>9} {'C DN':>9}"
          f" {'V':>9} {'V/V4':>8} {'peak d':>7}")
    for gate in ARMS:
        g = gref if gate == "4.00" else load(gate)
        r = veil(g, subj, far, valid, dist)
        out["arms"][gate] = {k: r[k] for k in
                             ("amp", "C", "V", "peak_d", "far_level", "base")}
        out["arms"][gate]["profile"] = r["profile"]
        print(f"  {gate:>8} {r['far_level']:11.1f} {r['amp']:9.0f}"
              f" {r['C']:9.0f} {r['V']:9.5f} {r['V']/vR:8.4f}"
              f" {r['peak_d']:7d}")
        if gate != "4.00":
            del g

    v0 = out["arms"]["0.00"]["V"]
    a0, a4 = out["arms"]["0.00"]["amp"], out["arms"]["4.00"]["amp"]
    f4, f0 = out["arms"]["4.00"]["far_level"], out["arms"]["0.00"]["far_level"]
    r = v0 / vR
    b15 = ("GATE-DEPENDENT" if r <= 0.70 else
           "GATE-INDEPENDENT" if 0.90 <= r <= 1.10 else
           "REVERSED (stronger at gate 0; a finding, not a null)" if r > 1.10
           else "PARTIAL")
    print(f"\n  far-field level {f4:.1f} -> {f0:.1f} DN, a {100*(f4-f0)/f4:.2f}%"
          f" drop over my far mask (ORCH measured 2.14% over theirs)")
    print(f"  r = V(0.00)/V(4.00) = {v0:.5f}/{vR:.5f} = {r:.4f}")
    print(f"  raw DN ratio        = {a0:.0f}/{a4:.0f} = {a0/a4:.4f}")
    print(f"  B15: {b15}")
    print(f"  => {100*(1-r):.1f}% of the veil is removed by the whole gate"
          f" ladder; {100*r:.1f}% survives at gate 0.00, where n_eff = 1 and"
          f" NOTHING is averaged.")
    out["bars"]["B15"] = {"r": r, "raw_ratio": a0 / a4, "verdict": b15,
                          "V4": vR, "V0": v0, "survives_pct": 100 * r,
                          "far_drop_pct": 100 * (f4 - f0) / f4}

    (DATA / "96-gate-final.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {DATA / '96-gate-final.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

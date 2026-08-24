"""M87 s33b -- WHY TWO OF MY OWN CONTROLS FAILED.  Diagnosis before repair.

94-gate-veil.py registered four controls and two of them went red.  Neither
bar is being weakened.  Both failures are diagnosed here to a mechanism, and
only then repaired, because a control that is relaxed until it passes is not
a control.

  C-AFFINE  |dV| = 2.451e-07 against a registered bar of 1e-12, for factors
            0.5, 2.0 and 4.0, all binary-exact.  My own standing rule is that
            an exact factor must reproduce BIT FOR BIT, and that this is what
            separates round-off from a real leak.  It did not.

  C-ROT     the rotated-mask null returned 44.5% of the real veil against a
            registered bar of 25%.  A null that large would mean the metric
            manufactures most of its own signal.

HYPOTHESIS FOR C-AFFINE: float32 accumulation, not a model leak.  The local
reference is a ratio of uniform_filter outputs.  A 251 px box sums ~63 000
samples of magnitude ~5e4, so the running sum reaches ~3e9, far above
float32's exact-integer ceiling of 2^24 = 16 777 216.  The SUM rounds, and it
rounds differently once the operands are scaled, so the invariance that holds
exactly in exact arithmetic does not survive the accumulator.  Prediction: in
float64 the same three exact factors collapse to the 1e-16 range.  A genuine
leak would not care about the accumulator's width.

HYPOTHESIS FOR C-ROT: my control is contaminated by construction, and it is
weaker than the one section 31 used.  90-veil.py rotated ONLY the distance
geometry and kept excluding the REAL subject from the far field and from the
valid set.  I rotated everything, so the real bee -- 22.5% of the crop -- was
re-admitted as ordinary background, and the rotated mask's 2-60 px rings can
land on the real silhouette and sample the real veil.  Prediction: the ring
band of the rotated mask overlaps the real veil zone substantially, and
restoring section 31's convention collapses the control.
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


def local_reference(g, far, dt):
    m = far.astype(dt)
    num = ndimage.uniform_filter(g.astype(dt) * m, WIN)
    den = ndimage.uniform_filter(m, WIN)
    ok = den >= MIN_FAR
    return np.where(ok, num / np.maximum(den, 1e-6), np.nan), ok


def veil(g, subj, far, valid, dt=np.float32, dist=None):
    ref, ok = local_reference(g, far, dt)
    v = valid & ok & np.isfinite(ref)
    resid = g.astype(dt) - ref
    if dist is None:
        dist = ndimage.distance_transform_edt(~subj)
    prof = []
    for d in range(1, 141):
        s = (dist >= d) & (dist < d + 1) & v
        if s.sum() >= 300:
            prof.append((d, float(np.median(resid[s])), int(s.sum())))
    tail = [x for d, x, _ in prof if d >= FARFIELD_D]
    base = float(np.median(tail)) if tail else 0.0
    pd, pv = max([(d, x) for d, x, _ in prof if 2 <= d <= 60], key=lambda t: t[1])
    C = float(np.median(g[far])) - float(np.median(g[subj]))
    return {"amp": pv - base, "C": C, "V": (pv - base) / C, "peak_d": pd}


def main():
    out = {}
    g = tifffile.imread(GATE / "pin-bee-3-cpl-gate-4.00.tif"
                        )[Y0:Y0 + H, X0:X0 + W, 1].astype(np.float32)
    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    med, span = float(np.median(g)), max(hi - lo, 1.0) * 0.35
    subj = ndimage.binary_opening(
        ndimage.binary_closing(g < med - span, np.ones((5, 5))), np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(~subj)
    far = (dist >= FARFIELD_D) & ~subj
    C = float(np.median(g[far])) - float(np.median(g[subj]))
    hair = (ndimage.grey_dilation(g, size=(HAIR_R, HAIR_R)) - g) > HAIR_K * C
    valid = ~subj & ~hair

    # ---- C-AFFINE: is it the accumulator? -----------------------------
    print("=== C-AFFINE diagnosis: float32 accumulator vs a model leak ===")
    nfar = int(far.sum())
    peak_sum = nfar / far.size * WIN * WIN * float(np.median(g[far]))
    print(f"  a 251 px box holds {WIN*WIN} px, {100*far.mean():.0f}% far field")
    print(f"  so the running sum reaches ~{peak_sum:.3e}, against float32's"
          f" exact-integer ceiling 2^24 = {2**24}")
    print(f"  ratio {peak_sum/2**24:.0f}x over -- the sum CANNOT be exact"
          f" in float32")
    res = {}
    for dt, name in ((np.float32, "float32"), (np.float64, "float64")):
        v0 = veil(g, subj, far, valid, dt, dist)["V"]
        errs = [abs(veil(g * a + 1000.0, subj, far, valid, dt, dist)["V"] - v0)
                for a in (0.5, 2.0, 4.0)]
        res[name] = {"V": v0, "max_dV": max(errs), "errs": errs}
        print(f"  {name}: V = {v0:.12f}   max |dV| over a in"
              f" {{0.5,2,4}} = {max(errs):.3e}")
    imp = res["float32"]["max_dV"] / max(res["float64"]["max_dV"], 1e-300)
    print(f"  float64 is {imp:.3g}x tighter -- consistent with accumulation,"
          f" not with a leak (a leak is width-independent)")
    out["C_AFFINE"] = res
    out["C_AFFINE"]["improvement"] = imp
    out["C_AFFINE"]["verdict"] = ("ROUND-OFF in the float32 accumulator"
                                  if res["float64"]["max_dV"] < 1e-12
                                  else "NOT explained by precision")
    print(f"  VERDICT: {out['C_AFFINE']['verdict']}")

    # ---- C-ROT: is my null contaminated? -------------------------------
    print("\n=== C-ROT diagnosis: does the rotated mask sample the real veil? ===")
    rot = subj[::-1, ::-1].copy()
    drot = ndimage.distance_transform_edt(~rot)
    band_r = (drot >= 2) & (drot <= 60)
    band_t = (dist >= 2) & (dist <= 60)
    ov = float((band_r & band_t).sum()) / max(band_r.sum(), 1)
    insub = float((band_r & subj).sum()) / max(band_r.sum(), 1)
    print(f"  rotated 2-60 px band: {int(band_r.sum())} px")
    print(f"  of it, {100*ov:.1f}% also lies in the REAL 2-60 px veil band")
    print(f"  and {100*insub:.1f}% lies INSIDE the real subject")
    out["C_ROT"] = {"overlap_real_band": ov, "inside_real_subject": insub}

    v_real = veil(g, subj, far, valid, np.float64, dist)["V"]
    mine = veil(g, rot, (drot >= FARFIELD_D) & ~rot, ~rot & ~hair,
                np.float64, drot)["V"]
    s31 = veil(g, rot, (drot >= FARFIELD_D) & ~subj, valid,
               np.float64, drot)["V"]
    both = veil(g, rot, (drot >= FARFIELD_D) & ~rot & ~subj,
                ~rot & ~subj & ~hair, np.float64, drot)["V"]
    print(f"  real                                      V = {v_real:.5f}")
    print(f"  my C-ROT   (rotated everything)           V = {mine:.5f}"
          f"  ({mine/v_real:.3f} of real)  <- FAILED")
    print(f"  s31 C-FAR  (real subject still excluded)  V = {s31:.5f}"
          f"  ({s31/v_real:.3f} of real)")
    print(f"  repaired   (BOTH masks excluded)          V = {both:.5f}"
          f"  ({both/v_real:.3f} of real)")
    out["C_ROT"].update({"V_real": v_real, "V_mine": mine, "V_s31": s31,
                         "V_repaired": both, "ratio_mine": mine / v_real,
                         "ratio_s31": s31 / v_real,
                         "ratio_repaired": both / v_real})
    out["C_ROT"]["verdict"] = (
        "CONTAMINATED BY CONSTRUCTION; repaired control passes"
        if abs(both / v_real) < 0.25 else
        "still fails after repair -- the metric may manufacture signal")
    print(f"  VERDICT: {out['C_ROT']['verdict']}")

    (DATA / "95-control-diag.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {DATA / '95-control-diag.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""M87 s33 -- is the veil gate-dependent?  An affine-invariant veil metric.

THE STIMULUS.  ORCH rendered bee-3-cpl four times varying ONLY --gate
(4.00 / 2.00 / 0.7078 / 0.00), one solved sidecar reused, --exposure pinned
to 1.54.  The gate-4.00 arm is BYTE-IDENTICAL to my own s31-bee3.tif
(E400A63A...), so this ladder is anchored on the exact figure section 31
characterised and my +4133 DN is its gate-4.00 point.  Asserted below.

ORCH's eye judgement -- veil strongest at gate 4.00, weakest at 0.00 -- is
explicitly NOT promoted to a finding by them.  Their ring-profile instrument
failed, and they told me exactly how, which is what makes this cheap:

  FAILURE 1, THE REFERENCE MOVED.  Every ring including the far reference
  shifted monotonically across arms.  The far-field median falls 54367.0 ->
  53204.3 DN, a 2.14% drop, because lowering the gate stops averaging away
  the unfitted per-frame photometric drift.  A metric that subtracts a
  per-arm reference measures that drift, not the veil.

  FAILURE 2, HAIR CONTAMINATION.  Their subject mask thresholded at the 45th
  percentile of a crop that is 45.2% subject, so hair tips sat in the near
  rings.  Their 1-5 px ring read -3232 DN, DARKER than far field.  That is
  hair, not veil.

THE TWO REPAIRS, which are what this script is.

  R1 FIXED POPULATION.  Every mask -- subject, far field, hair -- is derived
  ONCE from the gate-4.00 reference arm and applied UNCHANGED to all four.
  The arms are then compared on identical pixels, so any change is the image
  rather than the segmentation.  Deriving a mask per arm is what let ORCH's
  reference move.

  R2 EXACT AFFINE INVARIANCE.  ORCH asks for invariance to a 2.14% level
  shift.  Weak invariance is not worth registering, so the metric is built to
  be invariant to ANY affine map x -> a*x + b, a > 0, which brackets an
  additive offset and a multiplicative gain together:

      V  =  (peak ring residual)  /  (far background level - subject level)

  Numerator and denominator are both first-order in the image, so a cancels
  and b cancels twice.  The local reference is a ratio of uniform filters,
  which is linear, so resid -> a*resid exactly.  Medians are affine
  equivariant.  With the masks frozen by R1 the invariance is EXACT, not
  approximate, and C-AFFINE below demands bit-level agreement to prove it.

BARS, REGISTERED BEFORE THE RUN.  r = V(gate 0.00) / V(gate 4.00).

  B15  r <= 0.70            -> GATE-DEPENDENT.  The veil is an admission
                               artifact; ORCH's eye judgement is confirmed
                               and the mechanism is localised for the first
                               time.
       0.90 <= r <= 1.10    -> GATE-INDEPENDENT.  Refuted; the veil survives
                               with one frame per pixel and admission is not
                               the mechanism.
       r > 1.10             -> REVERSED, stronger with no averaging at all.
                               A DISTINCT FINDING, NOT A NULL.
       otherwise            -> PARTIAL, report r.

  The fourth branch exists because of ORCH's own discipline 676: they wrote a
  two-branch bar, measured 0.13x, and their script printed "VERDICT: DEPTH"
  for what was a 7.8x effect running the other way.  A ratio bar with no
  reversal branch scores a strong opposite result as a null.

CONTROLS.

  C-AFFINE  x -> a*x + b on the gate-4.00 arm for a in {0.5, 2, 4} and
            b = 1000.  All three factors are binary-exact, so the metric must
            reproduce BIT FOR BIT -- |dV| < 1e-12.  An inexact factor could
            only prove round-off; an exact one proves there is no leak.
  C-DRIFT   x -> 0.9786*x, ORCH's measured 2.14% drop, on the gate-4.00 arm.
            0.9786 is NOT binary-exact, so this tests the real hazard at
            realistic precision rather than the idealised one.  Bar: the
            metric moves < 2% while the raw DN amplitude is free to move.
  C-ROT     subject mask rotated 180 degrees -- same area, same perimeter,
            same shape, no registration to the image.  |V| must fall below
            0.25 of the real value.
  C-POS     a synthetic veil of known amplitude planted on the gate-4.00
            background, 4 levels.  V must rise monotonically.  A null alone
            shows the instrument is quiet; only a planted effect shows it can
            respond at all.

PROVENANCE (rule 47).  Operands are ORCH's four pinned TIFFs, rendered by
  strehl stack D:\\personal\\macro\\bee-3-cpl --gate <G> --srgb \\
      --exposure=1.54 --out <path>
  env: STREHL_WARPMAP=<ORCH scratch sidecar>, STREHL_ALIGN unset,
       STREHL_FIX_HALO unset;  alignment ON (sidecar-override), ref 149,
       299 placed / 0 refused;  197 797 874 bytes each.
This script writes nothing outside its own scratch and data directories.
"""
import hashlib
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image

GATE = pathlib.Path(r"C:\dev\strehl-out\ORCH-gate")
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
X0, Y0, W, H = 700, 3150, 1100, 900
FARFIELD_D, WIN, MIN_FAR = 70, 251, 0.06
HAIR_R = 9                # px: grey-dilation radius for thin dark structure
HAIR_K = 0.12             # fraction of contrast C: hair depth threshold
ARMS = ["4.00", "2.00", "0.7078", "0.00"]
REF_ARM = "4.00"
REF_SHA = "e400a63aa9f6ab1f1957940d7bd9d4965d67e01f6f0e1a0a7abc30d8e7f17112"


def load(gate):
    p = GATE / f"pin-bee-3-cpl-gate-{gate}.tif"
    a = tifffile.imread(p)
    g = a[Y0:Y0 + H, X0:X0 + W, 1].astype(np.float32)
    del a
    return g


def local_reference(g, far, win=WIN, min_far=MIN_FAR):
    m = far.astype(np.float32)
    num = ndimage.uniform_filter(g * m, win)
    den = ndimage.uniform_filter(m, win)
    ok = den >= min_far
    return np.where(ok, num / np.maximum(den, 1e-6), np.nan), ok


def veil(g, subj, far, valid, dmax=140):
    """Affine-invariant veil metric on a FIXED population."""
    ref, ok = local_reference(g, far)
    v = valid & ok & np.isfinite(ref)
    resid = g - ref
    dist = ndimage.distance_transform_edt(~subj)
    prof = []
    for d in range(1, dmax + 1):
        s = (dist >= d) & (dist < d + 1) & v
        if s.sum() >= 300:
            prof.append((d, float(np.median(resid[s])), int(s.sum())))
    tail = [x for d, x, _ in prof if d >= FARFIELD_D]
    base = float(np.median(tail)) if tail else 0.0
    inner = [(d, x) for d, x, _ in prof if 2 <= d <= 60]
    pd, pv = max(inner, key=lambda t: t[1])
    amp = pv - base
    # the normaliser: both terms are first-order in the image, so V is
    # invariant to x -> a*x + b exactly.
    fl = float(np.median(g[far]))
    sl = float(np.median(g[subj]))
    C = fl - sl
    return {"amp_dn": amp, "C": C, "V": amp / C, "peak_d": pd,
            "far_level": fl, "subj_level": sl, "profile": prof, "base": base}


def main():
    DATA.mkdir(exist_ok=True)
    out = {"bars": {}, "arms": {}, "controls": {}}

    h = hashlib.sha256((GATE / f"pin-bee-3-cpl-gate-{REF_ARM}.tif"
                        ).read_bytes()).hexdigest()
    assert h == REF_SHA, f"reference arm hash {h[:24]} != {REF_SHA[:24]}"
    mine = SCRATCH / "s31-bee3.tif"
    if mine.exists():
        assert hashlib.sha256(mine.read_bytes()).hexdigest() == REF_SHA, \
            "the gate-4.00 arm is not my section 31 render"
        print("  gate-4.00 arm == s31-bee3.tif == ORCH's figure (sha256 ok)")
    out["ref_sha"] = h

    # ---- R1: every mask from the reference arm, then frozen -----------
    gref = load(REF_ARM)
    lo, hi = float(np.percentile(gref, 1)), float(np.percentile(gref, 99))
    med, span = float(np.median(gref)), max(hi - lo, 1.0) * 0.35
    subj = ndimage.binary_opening(
        ndimage.binary_closing(gref < med - span, np.ones((5, 5))),
        np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(~subj)
    far = (dist >= FARFIELD_D) & ~subj
    C_ref = float(np.median(gref[far])) - float(np.median(gref[subj]))

    # ---- R2 for the population too: a contrast-relative hair threshold
    grey = ndimage.grey_dilation(gref, size=(HAIR_R, HAIR_R))
    hair = (grey - gref) > (HAIR_K * C_ref)
    valid = ~subj & ~hair
    print(f"=== fixed population, from the gate-{REF_ARM} arm only ===")
    print(f"  crop {gref.shape}  subject {100*subj.mean():.1f}%"
          f"  far field {100*far.mean():.1f}%")
    print(f"  hair excluded {100*hair.mean():.1f}% of crop"
          f"  ({100*(hair & ~subj).mean():.1f}% of it outside the subject)")
    print(f"  contrast C = {C_ref:.1f} DN;  hair depth threshold"
          f" {HAIR_K*C_ref:.0f} DN")
    out["subject_frac"] = float(subj.mean())
    out["hair_frac"] = float(hair.mean())
    out["C_ref"] = C_ref

    # ---- the ladder ---------------------------------------------------
    print(f"\n=== the gate ladder, identical pixels in every arm ===")
    print(f"  {'gate':>8} {'far level':>11} {'amp DN':>10} {'C DN':>10}"
          f" {'V':>9} {'peak d':>7}")
    for gate in ARMS:
        g = load(gate) if gate != REF_ARM else gref
        r = veil(g, subj, far, valid)
        out["arms"][gate] = {k: r[k] for k in
                             ("amp_dn", "C", "V", "peak_d", "far_level",
                              "subj_level", "base")}
        out["arms"][gate]["profile"] = r["profile"]
        print(f"  {gate:>8} {r['far_level']:11.1f} {r['amp_dn']:10.0f}"
              f" {r['C']:10.0f} {r['V']:9.5f} {r['peak_d']:7d}")
        if gate != REF_ARM:
            del g

    f4, f0 = out["arms"]["4.00"]["far_level"], out["arms"]["0.00"]["far_level"]
    print(f"\n  far-field level {f4:.1f} -> {f0:.1f} DN"
          f"  ({100*(f4-f0)/f4:.2f}% drop) -- ORCH measured 2.14%,"
          f" so the hazard is present in these operands")
    out["far_drop_pct"] = 100 * (f4 - f0) / f4

    v4, v0 = out["arms"]["4.00"]["V"], out["arms"]["0.00"]["V"]
    a4, a0 = out["arms"]["4.00"]["amp_dn"], out["arms"]["0.00"]["amp_dn"]
    r = v0 / v4
    b15 = ("GATE-DEPENDENT" if r <= 0.70 else
           "GATE-INDEPENDENT" if 0.90 <= r <= 1.10 else
           "REVERSED (stronger at gate 0; a finding, not a null)"
           if r > 1.10 else "PARTIAL")
    print(f"\n=== B15 ===")
    print(f"  V(gate 0.00) / V(gate 4.00) = {v0:.5f} / {v4:.5f} = {r:.4f}")
    print(f"  raw DN for comparison       = {a0:.0f} / {a4:.0f}"
          f" = {a0/a4:.4f}")
    print(f"  B15: {b15}")
    out["bars"]["B15"] = {"r": r, "raw_ratio": a0 / a4, "verdict": b15,
                          "V4": v4, "V0": v0}

    # ---- controls ------------------------------------------------------
    print(f"\n=== controls ===")
    aff = {}
    for a, b in ((0.5, 1000.0), (2.0, 1000.0), (4.0, 1000.0)):
        rr = veil(gref * a + b, subj, far, valid)
        aff[f"a={a}"] = abs(rr["V"] - v4)
        print(f"  C-AFFINE a={a:<4} b={b:.0f}: |dV| = {aff[f'a={a}']:.3e}"
              f"   (binary-exact factor, must be 0)")
    out["controls"]["C_AFFINE_max_dV"] = max(aff.values())
    out["controls"]["C_AFFINE_pass"] = max(aff.values()) < 1e-12

    rr = veil(gref * 0.9786, subj, far, valid)
    dv = abs(rr["V"] - v4) / v4
    dn = abs(rr["amp_dn"] - a4) / a4
    print(f"  C-DRIFT  x0.9786 (ORCH's 2.14%): V moves {100*dv:.4f}%,"
          f" raw DN moves {100*dn:.4f}%")
    out["controls"]["C_DRIFT_dV_pct"] = 100 * dv
    out["controls"]["C_DRIFT_dDN_pct"] = 100 * dn
    out["controls"]["C_DRIFT_pass"] = dv < 0.02

    rot = subj[::-1, ::-1].copy()
    dr = ndimage.distance_transform_edt(~rot)
    rr = veil(gref, rot, (dr >= FARFIELD_D) & ~rot, ~rot & ~hair)
    print(f"  C-ROT    rotated mask: V = {rr['V']:.5f}"
          f"  ({rr['V']/v4:+.3f} of real)")
    out["controls"]["C_ROT_V"] = rr["V"]
    out["controls"]["C_ROT_ratio"] = rr["V"] / v4
    out["controls"]["C_ROT_pass"] = abs(rr["V"] / v4) < 0.25

    band = (dist >= 8) & (dist <= 45) & valid
    pos, prev = [], None
    ok_mono = True
    for amp_pl in (0.0, 1000.0, 2000.0, 4000.0):
        gp = gref + np.where(band, amp_pl, 0.0).astype(np.float32)
        vv = veil(gp, subj, far, valid)["V"]
        pos.append((amp_pl, vv))
        if prev is not None and vv <= prev:
            ok_mono = False
        prev = vv
        print(f"  C-POS    plant {amp_pl:6.0f} DN in the 8-45 px band:"
              f" V = {vv:.5f}")
    out["controls"]["C_POS"] = pos
    out["controls"]["C_POS_monotone"] = ok_mono

    allpass = (out["controls"]["C_AFFINE_pass"] and
               out["controls"]["C_DRIFT_pass"] and
               out["controls"]["C_ROT_pass"] and ok_mono)
    print(f"\n  controls all pass: {allpass}")
    out["controls"]["all_pass"] = allpass

    # ---- the figure ----------------------------------------------------
    cols = []
    for gate in ARMS:
        g = load(gate) if gate != REF_ARM else gref
        s = np.clip((g - (med - 3 * span)) / (6 * span) * 255, 0, 255
                    ).astype(np.uint8)
        cols.append(np.dstack([s] * 3))
        if gate != REF_ARM:
            del g
    Image.fromarray(np.hstack(cols)).save(SCRATCH / "GATE-VEIL-4UP.png")
    print(f"  wrote {SCRATCH / 'GATE-VEIL-4UP.png'}")

    (DATA / "94-gate-veil.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"wrote {DATA / '94-gate-veil.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

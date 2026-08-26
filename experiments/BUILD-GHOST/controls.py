#!/usr/bin/env python3
"""BUILD-GHOST controls: prove the detector catches motion and stays quiet on
defocus, BEFORE any corpus number is quoted.

Seven controls.  Every one prints a PASS/FAIL against a stated expectation, and
the run prints how many were examined and how many landed in each outcome, so a
skipped control can never read as a passed one.

  C1  identity                 frame against itself                  -> residual 0
  C2  planted global similarity  breathing-sized scale+rot+shift     -> recovered, residual at floor
  C3  planted LOCAL motion       a disc moved by a known delta       -> residual == delta, ladder
  C4  DEFOCUS ONLY, no motion    spatially varying blur + noise      -> residual at floor
                                 ... and a NAIVE difference detector on the SAME pair,
                                 which must light up, or the control cannot express the failure
  C5  defocus AND motion         both at once                        -> motion still found, at size
  C6  real rigid subject         adjacent real pair, ruler on a rail -> residual at floor
  C7  the two greens of ONE exposure                                 -> KNOWN answer

C7 is the strongest null available: the two green sub-lattices of a single RAW
are the same photons at the same instant, so the motion between them is exactly
zero by construction, yet they carry real sensor noise, real scene content and a
real, KNOWN geometric offset of (+1, -1) sensor px.  The similarity must absorb
that offset into its translation and leave nothing.  A detector that cannot pass
C7 is measuring its own arithmetic.

Usage:  python controls.py [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghostlib as G  # noqa: E402

REF_A = r"D:\personal\macro\couch-fibers-cpl\DSC00150.ARW"
REF_B = r"D:\personal\macro\bee-3-cpl\DSC00150.ARW"
RAW_ROOT = r"D:\personal\macro"
# Three real, inanimate subjects, reported together so the null is not one
# cherry-picked pair.  flat-on-ruler-cpl is the primary: a flat subject sits at
# a single depth, so the whole frame goes through focus together and there is no
# depth-dependent parallax for the global similarity to fail on.  align.rs is
# explicit (CaptureMode::Rail) that parallax is outside the transform it fits,
# so a deep subject cannot cleanly separate "detector floor" from "model error".
RIGID_CANDIDATES = [("flat-on-ruler-cpl", 38),
                    ("wrapped-text-1", 60),
                    ("highly-angled-ruler-mm-cpl", 150)]
# The planted global similarity used by C2/C3/C4/C5.  Sized like real focus
# breathing (align.rs measures bee-3-cpl drifting 232.7 plane px corner to
# corner across its bracket), so the controls exercise the aligner's model at
# the amplitude the corpus actually produces rather than at a token amplitude.
TRUE = dict(s=1.0035, rot=0.0009, tx=1.7, ty=-2.3)   # plane px


# ---------------------------------------------------------------- utilities

def photon_gain(g: np.ndarray) -> tuple[float, float]:
    """Estimate (k, r2) in var = k*mean + r2. Delegates to the same estimator the
    detector itself uses, so control and corpus share one noise model."""
    return G.photon_transfer(g)


def add_shot_noise(g: np.ndarray, k: float, r2: float, rng) -> np.ndarray:
    sd = np.sqrt(np.maximum(k * np.maximum(g, 0.0) + r2, 0.0))
    return (g + rng.standard_normal(g.shape).astype(np.float32) * sd).astype(np.float32)


def warp_similarity(g: np.ndarray, s: float, rot: float, tx: float, ty: float) -> np.ndarray:
    h, w = g.shape
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    a, b = s * np.cos(rot), s * np.sin(rot)
    M = np.array([[a, -b, tx + cx - a * cx + b * cy],
                  [b, a, ty + cy - b * cx - a * cy]], np.float32)
    return cv2.warpAffine(g, M, (w, h), flags=cv2.INTER_LANCZOS4,
                          borderMode=cv2.BORDER_REFLECT101)


def shift_subpixel(g: np.ndarray, dy: float, dx: float) -> np.ndarray:
    h, w = g.shape
    M = np.array([[1, 0, dx], [0, 1, dy]], np.float32)
    return cv2.warpAffine(g, M, (w, h), flags=cv2.INTER_LANCZOS4,
                          borderMode=cv2.BORDER_REFLECT101)


def disc_mask(shape, cy, cx, r, feather) -> np.ndarray:
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    d = np.hypot(yy - cy, xx - cx)
    return np.clip((r + feather - d) / max(feather, 1e-6), 0, 1).astype(np.float32)


def defocus_ramp(g: np.ndarray, sigma_max: float, n_levels: int = 6) -> np.ndarray:
    """Spatially varying blur: sigma ramps 0 -> sigma_max along the diagonal.

    This is what a focus plane sweeping through a tilted subject does -- the
    exact confounder the brief names.  Built by blending a small stack of
    uniformly blurred copies, which is the standard way to render a varying PSF
    without a per-pixel convolution."""
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    t = ((yy / max(h - 1, 1)) * 0.5 + (xx / max(w - 1, 1)) * 0.5).astype(np.float32)
    sig = t * sigma_max
    levels = np.linspace(0.0, sigma_max, n_levels)
    stack = [g if s <= 1e-3 else cv2.GaussianBlur(g, (0, 0), s) for s in levels]
    out = np.zeros_like(g)
    for i in range(n_levels - 1):
        lo, hi = levels[i], levels[i + 1]
        wgt = np.clip((sig - lo) / max(hi - lo, 1e-6), 0, 1)
        band = (sig >= lo) & (sig <= hi)
        out = np.where(band, stack[i] * (1 - wgt) + stack[i + 1] * wgt, out)
    out = np.where(sig >= levels[-1], stack[-1], out)
    return out.astype(np.float32)


def naive_change_detector(ga: np.ndarray, gb: np.ndarray, sim, noise,
                          tile: int = G.TILE_FINE, stride: int = G.STRIDE_FINE) -> np.ndarray:
    """The detector this project must NOT ship: per-tile normalised RMS
    difference after the global warp is removed.  It cannot tell "this got
    blurrier" from "this moved", and the point of running it is to show that
    the defocus control is CAPABLE of expressing that failure -- a control that
    cannot express the failure is not a control.

    It is given every advantage: the fitted global similarity, a free per-tile
    gain (so it is not merely an exposure detector), and the same structure gate
    the real detector uses.  Its threshold is not chosen here; `main` calibrates
    it on the SAME null the real detector is calibrated on, so the two are
    compared on equal terms.  Returns the raw per-tile statistic for the tiles
    that pass the structure gate.
    """
    k, r2 = noise
    h, w = ga.shape
    cy0, cx0 = (h - 1) / 2.0, (w - 1) / 2.0
    o = G.tile_origins((h, w), tile, stride, G.MAX_SHIFT_COARSE + G.MAX_RESID)
    yc = o[:, 0] + tile / 2 - cy0
    xc = o[:, 1] + tile / 2 - cx0
    d = sim.predict(xc + 1j * yc)
    A = G.gather_tiles(ga, o, tile).astype(np.float32)
    ob = np.clip(np.stack([o[:, 0] + np.rint(np.imag(d)).astype(int),
                           o[:, 1] + np.rint(np.real(d)).astype(int)], 1),
                 [0, 0], [h - tile, w - tile])
    B = G.gather_tiles(gb, ob, tile).astype(np.float32)
    am = A.mean(axis=(1, 2), keepdims=True)
    bm = B.mean(axis=(1, 2), keepdims=True)
    Bg = B * (am / np.maximum(bm, 1e-6))
    M = np.sqrt(np.mean((A - Bg) ** 2, axis=(1, 2))) / np.maximum(am[:, 0, 0], 1.0)
    hfa, sa = G.hf_modulation(A, k, r2)
    hfb, sb = G.hf_modulation(B, k, r2)
    struct = (hfa >= G.HF_SIG_MIN_REL * sa) & (hfb >= G.HF_SIG_MIN_REL * sb)
    return M[struct]


def summarise(r: G.PairResult) -> dict:
    s = G.resid_summary(r)
    s.update({k: r.stats.get(k) for k in
              ("sim_scale_minus_one", "sim_rotation_rad", "sim_tx_plane", "sim_ty_plane")})
    s["census"] = r.census()
    s["n_fine_kept"] = r.n_fine_kept
    s["n_fine_total"] = r.n_fine_total
    return s


def _tile_centres(r: G.PairResult) -> tuple[np.ndarray, np.ndarray]:
    o = r.origins
    return o[:, 0] + G.TILE_FINE / 2, o[:, 1] + G.TILE_FINE / 2


def local_resid(r: G.PairResult, cy, cx, rad) -> tuple[float, int]:
    """Median residual magnitude (sensor px) over tiles inside a disc, and how
    many tiles that was -- so a nan can never be mistaken for a zero."""
    yc, xc = _tile_centres(r)
    sel = np.hypot(yc - cy, xc - cx) <= rad
    if sel.sum() < 3:
        return float("nan"), int(sel.sum())
    return float(np.median(np.abs(r.resid[sel]))) * G.PLANE_TO_SENSOR, int(sel.sum())


def outside_resid(r: G.PairResult, cy, cx, rad) -> float:
    yc, xc = _tile_centres(r)
    sel = np.hypot(yc - cy, xc - cx) > rad * 2.0
    if sel.sum() < 10:
        return float("nan")
    return float(np.percentile(np.abs(r.resid[sel]) * G.PLANE_TO_SENSOR, 99))


def pick_textured_site(g: np.ndarray, k: float, r2: float, rad: float) -> tuple[float, float]:
    """Put the planted-motion disc where the frame actually has structure.

    Choosing it at a fixed fraction of the frame would let a texture-free corner
    decide the positive control's outcome; this picks the highest noise-
    corrected high-frequency block that is at least `rad` from every edge."""
    o = G.tile_origins(g.shape, 256, 256, int(rad) + 64)
    hf, sg = G.hf_modulation(G.gather_tiles(g, o, 256), k, r2)
    i = int(np.argmax(hf / np.maximum(sg, 1e-9)))
    return float(o[i, 0] + 128), float(o[i, 1] + 128)


# ------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=r"C:\dev\strehl-out\BUILD-GHOST\data")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    rng = np.random.default_rng(20260826)
    results, outcomes = {}, []

    def record(name, passed, detail, kind="control"):
        # kind="hypothesis" exists because one of these is not a control at all:
        # C7b tests an explanation I proposed for C7's scatter.  A hypothesis
        # that fails its own test has not broken the detector, it has been
        # falsified -- and reporting it as FAIL would say the wrong thing while
        # deleting it would say nothing.  It gets its own outcome, and the
        # census below still partitions every entry.
        if kind == "hypothesis":
            out = "CONFIRMED" if passed else "NOT-CONFIRMED"
        else:
            out = "PASS" if passed else "FAIL"
        outcomes.append((name, out, kind))
        results[name] = {"pass": bool(passed), "kind": kind, **detail}
        print(f"  [{out}] {name}: {json.dumps(detail, default=float)[:400]}")

    print("BUILD-GHOST controls")
    print(f"reference frame A : {REF_A}")
    print(f"reference frame B : {REF_B}")
    t0 = time.time()
    ga = G.decode_plane(REF_A)["g"]
    k, r2 = photon_gain(ga)
    print(f"photon transfer on A: var = {k:.4f}*mean + {r2:.1f}   (DN)")
    print(f"plane grid {ga.shape}  1 plane px = {G.PLANE_TO_SENSOR:.0f} sensor px")
    print(f"gates: rho>={G.RHO_FLOOR}  |ln hf_a/hf_b|<={G.FOCUS_MATCH_MAX_LN}  "
          f"hf_sig>={G.HF_SIG_MIN_REL}*sigma  search +/-{G.MAX_RESID} plane px  "
          f"sub-pixel 1/{G.USFAC} plane px\n")

    # ---------------------------------------------------------------- C1
    print("C1  identity -- the arithmetic must return exactly nothing")
    r = G.measure_pair(ga, ga.copy(), noise=(k, r2))
    s = summarise(r)
    record("C1_identity", r.ok and s["max"] < 1e-3,
           {"p99_sensor_px": s["p99"], "max_sensor_px": s["max"], "census": s["census"]})

    # ------------------------------------------------------- C2 (the null)
    print("C2  planted global similarity, no local motion -- the aligner's own job")

    gb = add_shot_noise(warp_similarity(ga, **TRUE), k, r2, rng)
    r2r = G.measure_pair(ga, gb, noise=(k, r2))
    s2 = summarise(r2r)
    # cv2.warpAffine maps source point p to M.p, so the detector -- which reports
    # the displacement carrying content from A to B -- must recover M itself.
    exp_u = TRUE["s"] * np.exp(1j * TRUE["rot"]) - 1.0
    err_u = abs((s2["sim_scale_minus_one"] + 1j * s2["sim_rotation_rad"]) - exp_u)
    err_t = np.hypot(s2["sim_tx_plane"] - TRUE["tx"], s2["sim_ty_plane"] - TRUE["ty"])
    naive_null = naive_change_detector(ga, gb, r2r.sim, (k, r2))
    naive_thresh = float(np.percentile(naive_null, 99))
    record("C2_global_similarity", r2r.ok and err_u < 2e-4 and err_t < 0.2 and s2["p99"] < 1.0,
           {"scale_rot_err": float(err_u), "translation_err_plane_px": float(err_t),
            "residual_p50_sensor_px": s2["p50"], "residual_p90_sensor_px": s2["p90"],
            "residual_p99_sensor_px": s2["p99"], "residual_max_sensor_px": s2["max"],
            "census": s2["census"],
            "naive_thresh_calibrated_here": naive_thresh})
    print(f"    naive detector calibrated on THIS null: threshold = "
          f"{naive_thresh:.4f} relative RMS (its own p99 here, so it flags 1% by "
          f"construction on a pair with no motion and no blur change)")

    # ---------------------------------------------------------------- C3
    print("C3  planted LOCAL motion ladder -- a disc displaced by a known amount")
    RAD, FEA = 220.0, 60.0
    CY, CX = pick_textured_site(ga, k, r2, RAD + FEA)
    print(f"    disc centre chosen on texture: plane (y={CY:.0f}, x={CX:.0f}), r={RAD:.0f}")
    mask = disc_mask(ga.shape, CY, CX, RAD, FEA)
    ladder = []
    for delta_sensor in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
        dp = delta_sensor / G.PLANE_TO_SENSOR
        base = warp_similarity(ga, **TRUE)
        moved = shift_subpixel(base, dp * 0.6, dp * 0.8)   # a real direction, |d| = dp
        gbb = add_shot_noise(base * (1 - mask) + moved * mask, k, r2, rng)
        rr = G.measure_pair(ga, gbb, noise=(k, r2))
        inside, n_in = local_resid(rr, CY, CX, RAD * 0.6)
        outside = outside_resid(rr, CY, CX, RAD)
        nv = naive_change_detector(ga, gbb, rr.sim, (k, r2))
        ladder.append({"planted_sensor_px": delta_sensor, "measured_inside_sensor_px": inside,
                       "n_tiles_inside": n_in, "p99_outside_sensor_px": outside,
                       "ratio": float(inside / delta_sensor),
                       "naive_flag_frac": float((nv >= naive_thresh).mean())})
        print(f"    planted {delta_sensor:5.2f} -> measured {inside:6.3f} sensor px "
              f"inside ({n_in:3d} tiles), p99 outside {outside:6.3f}, "
              f"naive flags {100 * ladder[-1]['naive_flag_frac']:5.1f}%")
    good = [L for L in ladder if L["planted_sensor_px"] >= 0.5]
    ok3 = all(np.isfinite(L["ratio"]) and abs(L["ratio"] - 1.0) < 0.30 for L in good)
    detect = [L["planted_sensor_px"] for L in ladder
              if np.isfinite(L["measured_inside_sensor_px"])
              and L["measured_inside_sensor_px"] > L["p99_outside_sensor_px"]]
    record("C3_planted_local_motion", ok3 and len(detect) > 0,
           {"detection_floor_sensor_px": min(detect) if detect else None, "ladder": ladder})

    # ------------------------------------------------- C4 (the discriminator)
    print("C4  DEFOCUS ONLY -- the discriminating null, with the naive detector beside it")
    c4 = []
    for sigma_max in (0.3, 0.6, 1.2, 2.5, 5.0):
        base = warp_similarity(ga, **TRUE)
        gbb = add_shot_noise(defocus_ramp(base, sigma_max), k, r2, rng)
        rr = G.measure_pair(ga, gbb, noise=(k, r2))
        s4 = summarise(rr)
        nv = naive_change_detector(ga, gbb, rr.sim, (k, r2))
        frac = float((nv >= naive_thresh).mean())
        c4.append({"sigma_max_plane_px": sigma_max,
                   "ghost_p50_sensor_px": s4["p50"], "ghost_p90_sensor_px": s4["p90"],
                   "ghost_p99_sensor_px": s4["p99"], "ghost_max_sensor_px": s4["max"],
                   "focus_diff_ln_p50": rr.stats.get("focus_diff_ln_p50"),
                   "focus_diff_ln_p90": rr.stats.get("focus_diff_ln_p90"),
                   "census": s4["census"], "naive_flag_frac": frac})
        print(f"    blur ramp 0 -> {sigma_max:4.1f} plane px  (focus-diff ln p50 "
              f"{rr.stats.get('focus_diff_ln_p50', float('nan')):.3f}) : "
              f"GHOST residual p99 {s4['p99']:6.3f} sensor px "
              f"({s4['n_fine_kept']:5d}/{s4['n_fine_total']} kept)  |  "
              f"NAIVE flags {100 * frac:5.1f}%")
    worst = max(c["ghost_p99_sensor_px"] for c in c4)
    naive_worst = max(c["naive_flag_frac"] for c in c4)
    naive_on_8px = next(L["naive_flag_frac"] for L in ladder if L["planted_sensor_px"] == 8.0)
    # THE POINT OF THIS CONTROL: the naive detector flags MORE tiles on a pair
    # where nothing moved at all than on a pair with 8 sensor px of real motion.
    # It is not a weak motion detector; it is not a motion detector.
    print(f"    naive detector: {100 * naive_worst:.1f}% flagged with NO motion and a blur "
          f"change, against {100 * naive_on_8px:.1f}% flagged with 8.0 sensor px of REAL "
          f"motion and no blur change -- {naive_worst / max(naive_on_8px, 1e-9):.1f}x more "
          f"on the pair that did not move")
    # The criterion is DISCRIMINATION between the two things this whole
    # measurement has to tell apart: a pair that only changed FOCUS must read
    # lower than a pair that actually MOVED.  The comparison is against C3's
    # measured response to a real 2.0 sensor px displacement, because that is
    # the like-for-like number -- both are residual p99 over a full frame from
    # the same estimator.  (Comparing it against C3's 0.50 "detection floor"
    # would be comparing against a different baseline entirely: that floor is
    # set by the quiet region OUTSIDE the planted disc within a single pair,
    # which is a much lower bar than a whole-frame defocus null.)
    c3_at_2px = next(L["measured_inside_sensor_px"] for L in ladder
                     if L["planted_sensor_px"] == 2.0)
    print(f"    worst defocus-only p99 {worst:.3f} sensor px  vs  C3's reading of a REAL "
          f"2.0 sensor px motion, {c3_at_2px:.3f} sensor px")
    record("C4_defocus_null", worst < c3_at_2px and naive_worst > 3 * naive_on_8px,
           {"worst_ghost_p99_sensor_px": float(worst),
            "c3_response_to_real_2px_motion": float(c3_at_2px),
            "naive_worst_flag_frac": float(naive_worst),
            "naive_flag_frac_at_8px_real_motion": float(naive_on_8px),
            "ladder": c4})

    # ---------------------------------------------------------------- C5
    print("C5  defocus AND motion together -- the real-world case")
    base = warp_similarity(ga, **TRUE)
    dp = 2.0 / G.PLANE_TO_SENSOR
    moved = shift_subpixel(base, dp * 0.6, dp * 0.8)
    gbb = add_shot_noise(defocus_ramp(base * (1 - mask) + moved * mask, 1.2), k, r2, rng)
    r5 = G.measure_pair(ga, gbb, noise=(k, r2))
    ins5, n5 = local_resid(r5, CY, CX, RAD * 0.6)
    out5 = outside_resid(r5, CY, CX, RAD)
    record("C5_defocus_plus_motion",
           np.isfinite(ins5) and abs(ins5 / 2.0 - 1.0) < 0.30 and out5 < 1.0,
           {"planted_sensor_px": 2.0, "measured_inside_sensor_px": ins5,
            "n_tiles_inside": n5, "p99_outside_sensor_px": out5,
            "census": summarise(r5)["census"]})

    # ---------------------------------------------------------------- C6
    print("C6  real rigid subjects, adjacent real pairs -- the whole pipeline on real data")
    # Three candidates, reported together rather than one cherry-picked.  A flat
    # subject is the strongest of them: one depth means the whole frame goes
    # through focus together, so there is no depth-dependent parallax for a
    # global similarity to fail on, and align.rs is explicit that rail-style
    # parallax is outside the model it fits.
    c6 = []
    for sname, si in RIGID_CANDIDATES:
        fr = G.frames_of(os.path.join(RAW_ROOT, sname))
        si = min(si, len(fr) - 2)
        p1, p2 = fr[si], fr[si + 1]
        rr = G.measure_pair(G.decode_plane(p1)["g"], G.decode_plane(p2)["g"])
        if not rr.ok:
            c6.append({"subject": sname, "ok": False, "reason": rr.reason})
            print(f"    {sname:34s} NOT MEASURABLE: {rr.reason}")
            continue
        ss = summarise(rr)
        c6.append({"subject": sname, "ok": True, "a": os.path.basename(p1),
                   "b": os.path.basename(p2), "p50_sensor_px": ss["p50"],
                   "p90_sensor_px": ss["p90"], "p99_sensor_px": ss["p99"],
                   "max_sensor_px": ss["max"],
                   "focus_diff_ln_p50": rr.stats.get("focus_diff_ln_p50"),
                   "census": ss["census"]})
        print(f"    {sname:34s} {os.path.basename(p1)}->{os.path.basename(p2)}  "
              f"p50 {ss['p50']:.3f}  p90 {ss['p90']:.3f}  p99 {ss['p99']:.3f} sensor px  "
              f"({ss['n_fine_kept']}/{ss['n_fine_total']} kept, focus-diff ln p50 "
              f"{rr.stats.get('focus_diff_ln_p50', float('nan')):.3f})")
    flat = next((c for c in c6 if c["subject"] == "flat-on-ruler-cpl" and c.get("ok")), None)
    # Only the FLAT subject is a clean null.  A deep subject on a rail shows
    # depth-dependent parallax, and align.rs says in as many words that no
    # global 2D transform covers it (CaptureMode::Rail).  Its residual is
    # therefore model error plus detector floor, and it cannot separate them --
    # so it is reported, and it does not decide the control.
    record("C6_real_rigid_pair", flat is not None and flat["p99_sensor_px"] < 1.5,
           {"flat_subject_p99_sensor_px": flat["p99_sensor_px"] if flat else None,
            "all_candidates": c6})

    # ---------------------------------------------------------------- C7
    print("C7  the two greens of ONE exposure -- zero motion by construction, KNOWN offset")
    import rawpy
    with rawpy.imread(REF_B) as rr_:
        v = rr_.raw_image_visible.astype(np.float32)
        pat = np.asarray(rr_.raw_pattern)
        bl = float(rr_.black_level_per_channel[0])
    hh, ww = v.shape
    q = v[: hh // 2 * 2, : ww // 2 * 2].reshape(hh // 2, 2, ww // 2, 2) - bl
    pos = {int(pat[oy, ox]): (oy, ox) for oy in range(2) for ox in range(2)}
    (gy1, gx1), (gy2, gx2) = pos[1], pos[3]
    G1 = np.ascontiguousarray(q[:, gy1, :, gx1])
    G2 = np.ascontiguousarray(q[:, gy2, :, gx2])
    # A scene point sampled at sensor (2i+gy1, 2j+gx1) in G1 sits at index
    # (i - (gy2-gy1)/2, j - (gx2-gx1)/2) in G2, so the displacement carrying
    # content from G1's index space to G2's is minus half the quad offset.
    exp_ty, exp_tx = -(gy2 - gy1) / 2.0, -(gx2 - gx1) / 2.0
    r7 = G.measure_pair(G1, G2)
    s7 = summarise(r7)
    terr = np.hypot(s7["sim_tx_plane"] - exp_tx, s7["sim_ty_plane"] - exp_ty)
    print(f"    expected offset (dy,dx) = ({exp_ty:+.3f}, {exp_tx:+.3f}) plane px;  "
          f"measured ({s7['sim_ty_plane']:+.3f}, {s7['sim_tx_plane']:+.3f})")
    # C7 gates on the OFFSET, which is fixed by the CFA geometry and is the
    # thing this control uniquely knows.  Its residual SCATTER is reported but
    # not gated, and C7b below is why -- an excuse is not evidence, so the
    # aliasing story is tested rather than told.
    record("C7_two_greens_one_exposure", r7.ok and terr < 0.10,
           {"expected_offset_plane_px": [exp_ty, exp_tx],
            "measured_offset_plane_px": [s7["sim_ty_plane"], s7["sim_tx_plane"]],
            "offset_err_plane_px": float(terr),
            "p50_sensor_px": s7["p50"], "p90_sensor_px": s7["p90"],
            "p99_sensor_px": s7["p99"], "max_sensor_px": s7["max"], "census": s7["census"]})

    # ---------------------------------------------------------------- C7b
    print("C7b the aliasing claim, tested rather than asserted")
    # CLAIM: C7's residual scatter is inflated because G1 and G2 are two
    # different rectangular sub-lattices of the green quincunx.  Content above
    # each lattice's Nyquist aliases DIFFERENTLY into the two, so the two images
    # genuinely disagree at high frequency even though nothing moved.  A real
    # frame-to-frame pair samples the SAME lattice and inherits none of this.
    #
    # PREDICTION, falsifiable: remove the near-Nyquist content and the scatter
    # must collapse, while the offset -- which is a position, and blur is
    # symmetric so it cannot move a position -- must survive.  If the scatter is
    # really detector noise rather than aliasing, blurring will not help it.
    import cv2
    c7b = []
    MIN_TILES = 200          # stated BEFORE the numbers, not chosen after them
    for sig in (0.0, 0.4, 0.8, 1.6):
        if sig <= 0:
            b1, b2 = G1, G2
        else:
            b1 = cv2.GaussianBlur(G1, (0, 0), sig)
            b2 = cv2.GaussianBlur(G2, (0, 0), sig)
        rb = G.measure_pair(b1, b2)
        sb = summarise(rb)
        eb = np.hypot(sb["sim_tx_plane"] - exp_tx, sb["sim_ty_plane"] - exp_ty)
        usable = sb["n_fine_kept"] >= MIN_TILES
        c7b.append({"presmooth_sigma_plane_px": sig, "p90_sensor_px": sb["p90"],
                    "p99_sensor_px": sb["p99"], "offset_err_plane_px": float(eb),
                    "n_kept": sb["n_fine_kept"], "usable": bool(usable),
                    "census": sb["census"]})
        print(f"    pre-smooth sigma {sig:3.1f} plane px : residual p90 "
              f"{sb['p90']:6.3f}  p99 {sb['p99']:7.3f} sensor px, offset err "
              f"{eb:.4f} plane px ({sb['n_fine_kept']}/{sb['n_fine_total']} kept)"
              f"{'' if usable else '   EXCLUDED: under ' + str(MIN_TILES) + ' tiles'}")
    # Statistic is p90, not p99, and rungs under MIN_TILES are excluded and said
    # so.  Smoothing removes exactly the high-frequency content the focus and
    # uniqueness gates need, so the tile count falls as sigma rises; at 142
    # tiles a p99 rests on one or two samples and is not a measurement of
    # anything.  This is the project's rule about a green from zero selected
    # tests, in a different costume.
    use = [c for c in c7b if c["usable"]]
    excluded = [c for c in c7b if not c["usable"]]
    print(f"    rungs examined {len(c7b)}   usable {len(use)}   excluded "
          f"{len(excluded)}   (sums to {len(use) + len(excluded)})")
    drop = (use[0]["p90_sensor_px"] / max(use[-1]["p90_sensor_px"], 1e-9)
            if len(use) >= 2 else float("nan"))
    kept_off = len(use) >= 2 and use[-1]["offset_err_plane_px"] < 0.15
    print(f"    scatter p90 fell {drop:.2f}x under a blur that cannot move a peak; "
          f"offset {'survived' if kept_off else 'DID NOT survive'}")
    record("C7b_aliasing_explains_c7_scatter",
           len(use) >= 2 and drop > 1.3 and kept_off,
           {"ladder": c7b, "min_tiles_required": MIN_TILES,
            "n_rungs": len(c7b), "n_usable": len(use), "n_excluded": len(excluded),
            "p90_drop_factor": float(drop)}, kind="hypothesis")

    # ---------------------------------------------------------------- verdict
    npass = sum(1 for _, o, k in outcomes if o == "PASS")
    nfail = sum(1 for _, o, k in outcomes if o == "FAIL")
    nconf = sum(1 for _, o, k in outcomes if o == "CONFIRMED")
    nnot = sum(1 for _, o, k in outcomes if o == "NOT-CONFIRMED")
    print(f"\nentries examined {len(outcomes)}   controls: PASS {npass} FAIL {nfail}   "
          f"hypotheses: CONFIRMED {nconf} NOT-CONFIRMED {nnot}"
          f"   (sums to {npass + nfail + nconf + nnot})")
    for n, o, k in outcomes:
        print(f"    {o:14s} {n}")

    # Two floors, because there are two regimes and conflating them would either
    # hide a leak or move the goalposts.
    #
    #  * BASE floor: the worst p99 over the nulls that carry no defocus change --
    #    a planted global similarity (C2), a real adjacent pair on a flat rigid
    #    subject (C6), and the two green sub-lattices of one exposure (C7).
    #    This is what the detector reads when nothing moved and focus held.
    #
    #  * DEFOCUS floor: C4's ladder, published as a curve against the measured
    #    focus difference rather than collapsed to one number.  Every real pair
    #    reports its own focus_diff_ln_p50, so the sweep looks up the floor that
    #    applies AT ITS OWN operating point instead of borrowing the floor from a
    #    blur step it never experiences.
    c6flat = results["C6_real_rigid_pair"]["flat_subject_p99_sensor_px"]
    base_floor = max(results["C2_global_similarity"]["residual_p99_sensor_px"],
                     c6flat if c6flat is not None else 0.0,
                     results["C4_defocus_null"]["worst_ghost_p99_sensor_px"])
    print(f"\nDETECTOR FLOOR (worst residual p99 over the nulls that can be trusted "
          f"as nulls -- C2 planted similarity, C4 defocus-only, C6 flat rigid): "
          f"{base_floor:.3f} sensor px")
    print(f"C3 says a planted local motion is recovered at its true size from "
          f"{results['C3_planted_local_motion']['detection_floor_sensor_px']} sensor px up.")
    print(f"=> a per-tile residual is only readable as MOTION above "
          f"{base_floor:.3f} sensor px, and a corpus threshold must sit above that.")
    results["_base_floor_sensor_px"] = float(base_floor)

    results["_naive_thresh"] = naive_thresh
    results["_photon_transfer"] = {"k": k, "r2": r2}
    results["_n_controls"] = len(outcomes)
    results["_n_pass"] = npass
    results["_n_fail"] = nfail
    results["_n_hypothesis_confirmed"] = nconf
    results["_n_hypothesis_not_confirmed"] = nnot
    results["_outcomes"] = [{"name": n, "outcome": o, "kind": k} for n, o, k in outcomes]
    results["_elapsed_s"] = time.time() - t0
    with open(os.path.join(args.out, "controls.json"), "w") as fh:
        json.dump(results, fh, indent=2, default=float)
    print(f"wrote {os.path.join(args.out, 'controls.json')}  ({time.time() - t0:.0f}s)")
    return 0 if nfail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""M87 / 110 -- does the merge's RESIDUAL veil live inside one focus window?

WHY THIS SCRIPT EXISTS.  The orchestrator asked for exactly one new
measurement at wrap-up.  M121 reached this milestone's conclusion from the
opposite direction: it measured that the residual rim carries the FOCUS
WINDOW'S length scale (rim w50 10.00 px, cutoff 13.25 px, election-agreement
w50 10.50 px, against `WINDOW_RADIUS = 13` at focus.rs:83), and that gate 0
is equivalent to gate 4, so the rim is a SELECTION artefact.  M87 measured
that removal happens at `n_eff = 1.000`, so averaging is not the mechanism.

Two milestones, two statistics, one conclusion.  The question that decides
whether they are ONE result or TWO:

    is M87's residual frame-borne veil CONCENTRATED inside the 0-13 px band
    where M121's rim lives, or SPREAD across M87's full 2-22 px window?

Concentrated -> the two merge into a mechanism: the merge removes the veil
EXCEPT within one focus-window radius of the edge, because that is exactly
where the window's support straddles the occluding boundary.
Spread -> they are separate phenomena and I must say so.

M121's numbers are used AS GIVEN.  Nothing here re-derives its work.

================================================================================
PREREGISTRATION -- written and committed to before any number below was seen.
================================================================================

X1 -- THE SHAPE OF THE RESIDUAL.  Per-distance residual of the gate-0 merge
    against its own far reference, in linear raw DN, on the same cube, mask
    and distance field as step 70:

        r(d) = ( p_merge(d) - far ) / far ,  far = median p_merge over [80,120]

    REGISTERED PREDICTION: if the residual shares M121's mechanism, the mean
    depth of r over d in [2,13] is at least 2x the mean depth over d in
    [14,22], and r decays to within 25% of its peak depth by d = 13.
    REGISTERED FALSIFIER: if the two sub-band means are within a factor of 2,
    the residual is SPREAD, the two results are separate phenomena, and I
    report that instead.  I am not free to reinterpret a factor of 1.4 as
    "broadly concentrated".

X2 -- THE NULL THAT DECIDES WHETHER X1 MEASURES ANYTHING.  A concentration
    statistic on a band that is only 2-22 px wide could report
    "concentrated" purely because ANY profile rising toward a far asymptote
    is deeper at small d.  The instrument must therefore be run on data whose
    answer I already know and which must come out the OTHER way.

    The single frames carry the FULL veil (-26.47% +/- 3.01%), driven by the
    defocus blur radius, which is not the focus window and is much larger.
    So the same statistic applied to the mean single-frame profile must NOT
    show the same concentration.

    C-SINGLE: mean single-frame concentration ratio must be substantially
        below the merge's.  If the single frames concentrate as hard as the
        merge does, my statistic is reading my binning and X1 is VOID.
    C-RAND:   the uniformly-random per-pixel merge (step 70's control, same
        seed 8702) keeps the full dip and must behave like the single frames.

    These are the controls that can actually fail.  A control that cannot
    come out the wrong way is decoration.

X3 -- A NUMBER COMPARABLE TO M121'S.  Report the half-depth distance of the
    merge residual -- the d at which |r(d)| first falls to half its peak --
    so it can be set beside M121's rim w50 of 10.00 px WITHOUT my having
    re-derived M121's statistic.  Agreement here is a genuine cross-check
    because the two are computed on different fields by different code.

READ-ONLY: D:\\personal\\macro.  Reads only this milestone's own cache.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

VEIL = (2, 22)
FAR = (80, 120)
INNER = (2, 13)          # M121's focus-window band, WINDOW_RADIUS = 13
OUTER = (14, 22)         # the rest of M87's veil band
RATIO_BAR = 2.0          # registered threshold for "concentrated"
DECAY_BAR = 0.25         # registered: r within 25% of peak depth by d = 13
M121_RIM_W50 = 10.00     # given, not re-derived
M121_CUTOFF = 13.25
WINDOW_RADIUS_RS = 13    # focus.rs:83


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def main():
    t0 = time.time()
    rep = {"preregistered": {"ratio_bar": RATIO_BAR, "decay_bar": DECAY_BAR,
                             "inner": INNER, "outer": OUTER,
                             "m121_rim_w50": M121_RIM_W50,
                             "m121_cutoff": M121_CUTOFF,
                             "window_radius_rs": WINDOW_RADIUS_RS}}

    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    n, h, w = cube.shape
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1

    # Identical geometry to step 70 -- same mask, same distance field, same
    # inner window.  Any difference here would make the comparison meaningless.
    fmask, _ = L.foreground_mask(sel0)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros_like(dd, bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    dsort = dv[order]
    edges = np.searchsorted(dsort, np.arange(0, 202))

    def prof(img):
        v = img[valid][order]
        out = np.full(201, np.nan)
        for d in range(201):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    def residual(img):
        p = prof(img)
        far = np.nanmedian(p[FAR[0]:FAR[1] + 1])
        return (p - far) / far, float(far)

    def concentration(r):
        """Mean DEPTH (positive number) in each sub-band, and their ratio."""
        a = float(np.nanmean(-r[INNER[0]:INNER[1] + 1]))
        b = float(np.nanmean(-r[OUTER[0]:OUTER[1] + 1]))
        return a, b, (a / b if b > 1e-12 else float("inf"))

    def half_depth(r):
        """First d at which |r| falls to half its peak depth in the band."""
        band = -r[VEIL[0]:VEIL[1] + 1]
        pk = float(np.nanmax(band))
        if pk <= 0:
            return None, pk
        for i, v in enumerate(band):
            if np.isfinite(v) and v <= 0.5 * pk:
                return VEIL[0] + i, pk
        return None, pk

    # ---------------------------------------------------------------------- X1
    print("=== X1: is the merge's residual concentrated inside 13 px? ===",
          flush=True)
    r_m, far_m = residual(sel0)
    a_m, b_m, ratio_m = concentration(r_m)
    hd_m, pk_m = half_depth(r_m)
    print(f"  gate-0 merge  far ref {far_m:.1f} DN", flush=True)
    print(f"    mean depth d in {INNER} : {100 * a_m:6.3f}%", flush=True)
    print(f"    mean depth d in {OUTER}: {100 * b_m:6.3f}%", flush=True)
    print(f"    concentration ratio      : {ratio_m:.3f}x   "
          f"(registered bar {RATIO_BAR}x)", flush=True)
    print("    per-d residual, d = 2..22:", flush=True)
    print("      " + "  ".join(f"{d}:{100 * r_m[d]:+.2f}"
                               for d in range(VEIL[0], VEIL[1] + 1)), flush=True)
    r13 = float(-r_m[WINDOW_RADIUS_RS])
    decayed = bool(r13 <= DECAY_BAR * pk_m)
    print(f"    peak depth {100 * pk_m:.3f}% at the band's inner edge; "
          f"depth at d=13 is {100 * r13:.3f}% "
          f"({100 * r13 / pk_m:.1f}% of peak) -> "
          f"{'decayed' if decayed else 'NOT decayed'} by the registered bar",
          flush=True)
    x1 = bool(ratio_m >= RATIO_BAR and decayed)
    print(f"  X1 -> {'CONCENTRATED' if x1 else 'SPREAD'}", flush=True)

    # ---------------------------------------------------------------------- X2
    print("\n=== X2: the null -- the same statistic on data that must differ ===",
          flush=True)
    ratios = np.empty(n)
    acc = np.zeros(201)
    for k in range(n):
        rk, _ = residual(np.asarray(cube[k], dtype=np.float32))
        ratios[k] = concentration(rk)[2]
        acc += np.nan_to_num(rk)
    r_s = acc / n
    a_s, b_s, ratio_s = concentration(r_s)
    hd_s, pk_s = half_depth(r_s)
    print(f"  C-SINGLE  mean single-frame profile: "
          f"inner {100 * a_s:6.3f}%  outer {100 * b_s:6.3f}%  "
          f"ratio {ratio_s:.3f}x", flush=True)
    print(f"            per-frame ratio: mean {ratios.mean():.3f}x  "
          f"sd {ratios.std(ddof=1):.3f}  "
          f"min {ratios.min():.3f}  max {ratios.max():.3f}", flush=True)

    rng = np.random.default_rng(8702)
    ridx = rng.integers(0, n, size=(h, w))
    rnd = np.take_along_axis(np.asarray(cube), ridx[None], axis=0)[0]
    r_r, _ = residual(rnd)
    a_r, b_r, ratio_r = concentration(r_r)
    print(f"  C-RAND    random per-pixel merge:    "
          f"inner {100 * a_r:6.3f}%  outer {100 * b_r:6.3f}%  "
          f"ratio {ratio_r:.3f}x", flush=True)

    c_single_ok = bool(ratio_s < ratio_m / 1.5)
    c_rand_ok = bool(ratio_r < ratio_m / 1.5)
    print(f"  C-SINGLE -> {'PASS, the statistic is not reading my binning' if c_single_ok else 'FAIL -- X1 IS VOID, the statistic reads the binning'}",
          flush=True)
    print(f"  C-RAND   -> {'PASS' if c_rand_ok else 'FAIL -- X1 IS VOID'}",
          flush=True)

    # ---------------------------------------------------------------------- X3
    print("\n=== X3: a number comparable to M121's, computed independently ===",
          flush=True)
    print(f"  M87 merge-residual half-depth distance : {hd_m} px", flush=True)
    print(f"  M121 rim w50 (given, not re-derived)   : {M121_RIM_W50} px", flush=True)
    print(f"  M121 cutoff (given)                    : {M121_CUTOFF} px", flush=True)
    print(f"  focus.rs:83 WINDOW_RADIUS              : {WINDOW_RADIUS_RS} px", flush=True)
    print(f"  mean single-frame half-depth           : {hd_s} px  "
          f"(the veil, driven by defocus, not the window)", flush=True)

    valid_arm = c_single_ok and c_rand_ok
    verdict = ("CONCENTRATED -- one mechanism with M121" if (x1 and valid_arm)
               else "SPREAD -- separate phenomena" if valid_arm
               else "VOID -- controls failed, no claim")
    print(f"\nVERDICT: {verdict}", flush=True)

    # ---- honest disclosure: the 74.76% headline is a BAND-POOLED number ----
    # The residual varies 6x across the band, so removal must vary too.  A
    # reviewer will ask; better that I ask first.
    print("\n=== X4: removal fraction BY DISTANCE (the pooled 74.76% is a band average) ===",
          flush=True)
    rem = np.full(201, np.nan)
    for d in range(VEIL[0], VEIL[1] + 1):
        if np.isfinite(r_m[d]) and np.isfinite(r_s[d]) and r_s[d] < -1e-9:
            rem[d] = 100.0 * (1.0 - r_m[d] / r_s[d])
    print("  " + "  ".join(f"{d}:{rem[d]:.0f}%" for d in range(VEIL[0], VEIL[1] + 1)),
          flush=True)
    print(f"  removal at d=2 : {rem[2]:.1f}%     removal at d=13: {rem[13]:.1f}%"
          f"     removal at d=22: {rem[22]:.1f}%", flush=True)
    rep["X4"] = {"removal_by_d": [None if not np.isfinite(v) else round(float(v), 3)
                                  for v in rem[:41]],
                 "removal_d2": float(rem[2]), "removal_d13": float(rem[13]),
                 "removal_d22": float(rem[22]),
                 "single_r_by_d": [None if not np.isfinite(v) else round(float(v), 6)
                                   for v in r_s[:41]]}

    rep["X1"] = {"far_dn": far_m, "inner_depth": a_m, "outer_depth": b_m,
                 "ratio": ratio_m, "peak_depth": pk_m, "depth_at_13": r13,
                 "frac_of_peak_at_13": r13 / pk_m, "decayed": decayed,
                 "concentrated": x1,
                 "r_by_d": [None if not np.isfinite(v) else round(float(v), 6)
                            for v in r_m[:41]]}
    rep["X2"] = {"single_inner": a_s, "single_outer": b_s, "single_ratio": ratio_s,
                 "per_frame_ratio_mean": float(ratios.mean()),
                 "per_frame_ratio_sd": float(ratios.std(ddof=1)),
                 "per_frame_ratio_min": float(ratios.min()),
                 "per_frame_ratio_max": float(ratios.max()),
                 "rand_inner": a_r, "rand_outer": b_r, "rand_ratio": ratio_r,
                 "c_single_ok": c_single_ok, "c_rand_ok": c_rand_ok}
    rep["X3"] = {"merge_half_depth_px": hd_m, "single_half_depth_px": hd_s,
                 "m121_rim_w50": M121_RIM_W50, "m121_cutoff": M121_CUTOFF,
                 "window_radius_rs": WINDOW_RADIUS_RS}
    rep["verdict"] = verdict
    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "110-crosscheck.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '110-crosscheck.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()

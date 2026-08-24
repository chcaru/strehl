"""M87 / 63 -- the halo on the image the owner actually judged (`bee3-full.tif`),
and whether a bee leg is the same problem as a flower bud.

WHY THIS EXISTS.  Every halo measurement in this milestone so far has been on
synthetic two-layer scenes, on M13's occluding-edge cells, or on
`flower-bud-alone-cpl` -- a BULKY subject against a blank white card.  The
orchestrator has now established (fact 1344, correcting fact 1341) that the
image the owner delivered his "do not look too good" verdict against was
`C:\\dev\\strehl-out\\bee3-full.png`, written 2026-08-23 23:37, and that the
halo is conspicuous in it at 8.24 MP without pixel-peeping.  I have confirmed
the geometry independently: `bee3-full.tif` is (2344, 3516, 3) uint16, exactly
half of 7032x4688 in each direction.

`bee-3-cpl`'s legs are a DIFFERENT SUBJECT CLASS from the bud: thin dark limbs
against a bright field, rather than a bulky dark body against a bright field.
The orchestrator's ask is whether a correction that improves one improves the
other.  This script answers that from geometry and from mechanism.

================================================================================
PREREGISTRATION -- written and committed to before any number below was seen.
================================================================================

The instrument is section 2's frozen band profile: P(d) = median of a value over
BACKGROUND pixels at rounded euclidean distance d from the subject mask, inside
a registered ROI.  ROI_LEG = (1200, 1900, 300, 1400) is the exact region of
`crop-leg-halo.png`, the crop the owner was shown.

Three statistics, all from P(d):
    peak       = max  P(d) over d in [1, D_PEAK],           D_PEAK = 30
    local_base = med  P(d) over d in (D_PEAK, D_FAR_LO)
    far        = med  P(d) over d in [D_FAR_LO, D_FAR_HI]
    lift_local = 100 * (peak - local_base) / local_base
    overshoot  = 100 * (peak - far) / far

N1 -- THE CONVEX BOUND, and the headline.
    A two-layer composite I = a*F + (1-a)*B with a in [0,1] is a CONVEX blend and
    cannot exceed both layers.  The bee's background is bright and its legs are
    dark, so if the bright leg rim is a veil, its peak MUST NOT exceed the far
    background.  On `flower-bud-alone-cpl` (section 24.4) the rim peaked 10.2%
    BELOW far background, z = -62.8, verdict O1: bound holds.
    REGISTERED: I predict O1 again here -- overshoot <= the C-BROKEN bias floor.
    If instead overshoot exceeds the bias floor, the bound is BREACHED, the bee
    rim is NOT a two-layer veil, and a veil correction will not remove it.
    Either outcome is reportable; the second is the more interesting.

N2 -- IS THE RIM REAL AT ALL.  lift_local must exceed the C-BROKEN bias floor by
    a wide margin.  On the bud this was +18.97% against +0.42%, i.e. 45.6x.
    REGISTERED: I predict lift_local / broken_lift_local > 10.

N3 -- THE ANNULUS COLLISION, and the reason the two subject classes may differ.
    Section 24 measured the correctable band on the bud at ~20 binned px wide,
    peaking 7 px OUTSIDE the silhouette.  A correction with that reach, applied
    from both sides of a limb, overlaps the limb's own core whenever the limb's
    half-width is below the reach.  Statistic: A_r = fraction of SUBJECT-mask
    pixels inside the ROI whose inner distance d_in <= r.  A_20 = 1.0 means the
    entire subject lies within a 20 px annulus of its own boundary, i.e. a 20 px
    correction rewrites all of it.
    REGISTERED: I predict A_20(bee legs) > 0.80 and A_20(flower bud) < 0.30,
    i.e. the geometry differs by design and the bud-tuned reach cannot be
    transferred to a leg unaltered.

N4 -- ACHROMATIC OR CHROMATIC.  Commit `bdfd12c` (facts 1377-1378) names
    Malvar-He-Cutler demosaic fringing at high-contrast diagonal edges as M107's
    candidate (c) for bright bee-edge artifacts, and says it "describes a bee
    hair".  That is a COMPETING hypothesis for the thing I am measuring and it
    belongs to another milestone.  A two-layer veil is a blend of two real
    colours and is achromatic in the sense that all three channels lift in the
    same direction by a similar relative amount; demosaic fringing is chromatic
    by construction and drives channels apart.
    REGISTERED: I predict the three per-channel lift_local values agree in sign
    and lie within a factor 1.5 of one another.  If any channel lifts while
    another falls, the rim is at least partly a demosaic artifact and I hand
    that share to M107 rather than claiming it.

CONTROLS -- all three registered, all three run whatever the outcome.

C-BROKEN (deliberately broken arm, per bar X4's lesson).  The identical pipeline
    driven by `L.shifted_mask`, the registered C1 control: the true subject mask
    translated by (512, 512) so that it becomes an INVENTED boundary lying in
    open background.  Every spatial statistic of the mask is preserved and the
    physical boundary is destroyed.  Whatever this arm reports is the
    instrument's own bias floor and no claim below may be smaller than it.

C-PARAM (varies MY parameter, not the data).  Section 24.3's lesson, fact P64:
    two pre-registered lengthscale "confirmations" in a row turned out to be my
    own instrument constants read back to me, and registration did not catch
    either -- only re-running with my parameter changed did.  So N1's verdict is
    recomputed over the grid
        D_FAR in {(48,96), (100,150), (150,200)}   x   tau in {otsu, .9, 1.1}
    and the verdict must be INVARIANT across all nine cells.  If the sign of the
    overshoot flips anywhere in that grid, I report NO VERDICT for N1.
    This matters specifically because on the bud I measured a broad ~150 px
    depression around the subject: a far window at 48-96 px may sit INSIDE it,
    which would bias `far` downward and manufacture an overshoot.

C-FRAME (the decisive one; transfers this milestone's foundational claim).  The
    same rim statistic computed on each of the 299 SINGLE INPUT FRAMES, from the
    cached through-focus cube, using the same mask and the same ROI.  A single
    frame is one exposure of a real scene and cannot contain a selection
    artifact.
    REGISTERED: I predict the merge's lift_local exceeds the MAXIMUM over all
    299 single frames.  Reported against the max, never the mean -- fact 1298
    was folded against the mean wearing the language of the maximum and had to
    be corrected in place; I will not repeat that.

WHAT WOULD FALSIFY THE WHOLE PICTURE.  If C-FRAME shows single frames carrying a
rim as large as the merge's, the halo is in the capture, not in the merge, and
this milestone's foundational claim is wrong on this stack.

READ-ONLY: D:\\personal\\macro.  Writes only to experiments/M87-occlusion/data
and C:\\dev\\strehl-out\\M87-bee.
"""
import json
import os
import pathlib
import sys
import time

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
DATA.mkdir(parents=True, exist_ok=True)
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

MERGE = r"C:\dev\strehl-out\bee3-full.tif"
ROI_LEG = L.ROIS["ROI_LEG"]
MARGIN = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1  # 22
BOX = (ROI_LEG[0] - MARGIN, ROI_LEG[1] + MARGIN, ROI_LEG[2] - MARGIN, ROI_LEG[3] + MARGIN)
CUBE_ROI = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)

D_PEAK = 30
D_MAX = 200
MIN_BIN = 200
FAR_GRID = [(48, 96), (100, 150), (150, 200)]
TAU_GRID = [1.0, 0.9, 1.1]


# ------------------------------------------------------------------ profiler
def make_profiler(mask, roi, d_max=D_MAX, min_bin=MIN_BIN):
    """Closure form of L.band_profile: the EDT and the binning are done once.

    Returns prof_of(value) -> P(d).  Verified below to reproduce
    L.band_profile exactly on a real frame.
    """
    dist = distance_transform_edt(~mask)
    y0, y1, x0, x1 = roi
    d = dist[y0:y1, x0:x1]
    bg = ~mask[y0:y1, x0:x1]
    dr = np.rint(d).astype(np.int32)
    sel = bg & (dr >= 1) & (dr <= d_max)
    ds = dr[sel]
    order = np.argsort(ds, kind="stable")
    flat = np.flatnonzero(sel.ravel())[order]
    edges = np.searchsorted(ds[order], np.arange(1, d_max + 2))
    counts = np.diff(edges)

    def prof_of(value):
        v = np.ascontiguousarray(value[y0:y1, x0:x1]).ravel()[flat]
        prof = np.full(d_max + 1, np.nan)
        for i in range(d_max):
            a, b = edges[i], edges[i + 1]
            if b - a >= min_bin:
                prof[i + 1] = np.median(v[a:b])
        return prof

    return prof_of, counts


def stats(prof, far_lo, far_hi):
    d = np.arange(len(prof))
    near = (d >= 1) & (d <= D_PEAK) & np.isfinite(prof)
    mid = (d > D_PEAK) & (d < far_lo) & np.isfinite(prof)
    far = (d >= far_lo) & (d <= far_hi) & np.isfinite(prof)
    if near.sum() < 5 or mid.sum() < 5 or far.sum() < 5:
        return None
    peak = float(np.nanmax(prof[near]))
    dstar = int(d[near][int(np.nanargmax(prof[near]))])
    local = float(np.median(prof[mid]))
    fr = float(np.median(prof[far]))
    return {
        "peak": peak,
        "d_star": dstar,
        "local_base": local,
        "far": fr,
        "lift_local_pct": 100.0 * (peak - local) / max(local, 1e-9),
        "overshoot_pct": 100.0 * (peak - fr) / max(fr, 1e-9),
        "n_near": int(near.sum()),
        "n_far": int(far.sum()),
    }


def fmt(s):
    if s is None:
        return "  (insufficient bins)"
    return (f"  peak={s['peak']:.1f} at d={s['d_star']}  local={s['local_base']:.1f}  "
            f"far={s['far']:.1f}  lift_local={s['lift_local_pct']:+.3f}%  "
            f"overshoot={s['overshoot_pct']:+.3f}%")


def main():
    print(__doc__.split("=" * 80)[1][:60], "...\n", flush=True)
    rep = {"preregistration": "see module docstring", "inputs": {}}
    t0 = time.time()

    # ---------------------------------------------------------------- arm A
    print("=== ARM A: the judged merge, bee3-full.tif, ROI_LEG ===", flush=True)
    img = tifffile.imread(MERGE)
    assert img.ndim == 3 and img.shape[2] == 3, img.shape
    rep["inputs"]["merge"] = {"path": MERGE, "shape": list(img.shape), "dtype": str(img.dtype)}
    print(f"  {MERGE}  {img.shape} {img.dtype}", flush=True)
    rgb = img.astype(np.float32)
    g = rgb[..., 1]

    mask, tau = L.foreground_mask(g)
    rep["mask"] = {"tau": float(tau), "fg_frac_full": float(mask.mean()),
                   "fg_frac_roi": float(mask[ROI_LEG[0]:ROI_LEG[1],
                                             ROI_LEG[2]:ROI_LEG[3]].mean())}
    print(f"  otsu tau={tau:.1f}  subject fraction full={mask.mean():.4f}  "
          f"ROI_LEG={rep['mask']['fg_frac_roi']:.4f}", flush=True)

    prof_of, counts = make_profiler(mask, ROI_LEG)

    # instrument self-check: must reproduce the frozen library routine exactly
    ref, _ = L.band_profile(g, mask, ROI_LEG, d_max=96, min_bin=MIN_BIN)
    mine = prof_of(g)[:97]
    both = np.isfinite(ref) & np.isfinite(mine)
    dev = float(np.max(np.abs(ref[both] - mine[both]))) if both.any() else float("nan")
    same_nan = bool((np.isfinite(ref) == np.isfinite(mine)).all())
    print(f"  SELF-CHECK vs L.band_profile: max|dev|={dev:.6g} over {int(both.sum())} bins, "
          f"nan-pattern identical={same_nan}", flush=True)
    assert same_nan and dev == 0.0, "fast profiler does not reproduce the frozen routine"
    rep["self_check"] = {"max_abs_dev": dev, "bins": int(both.sum()), "nan_identical": same_nan}

    # N1/N2 at the registered default
    s_def = stats(prof_of(g), *FAR_GRID[0])
    print("  MERGE  G:", flush=True)
    print(fmt(s_def), flush=True)

    # C-BROKEN
    bmask = L.shifted_mask(mask)
    bprof_of, bcounts = make_profiler(bmask, ROI_LEG)
    s_brk = stats(bprof_of(g), *FAR_GRID[0])
    print("  C-BROKEN (mask translated by (512,512) into open background):", flush=True)
    print(fmt(s_brk), flush=True)
    rep["N1_N2_default"] = {"merge": s_def, "broken": s_brk, "far_window": list(FAR_GRID[0])}

    if s_def and s_brk:
        r_lift = s_def["lift_local_pct"] / max(abs(s_brk["lift_local_pct"]), 1e-9)
        print(f"\n  N2  lift ratio merge/broken = {r_lift:.1f}x   "
              f"(registered bar: > 10)  -> {'PASS' if r_lift > 10 else 'FAIL'}", flush=True)
        rep["N2"] = {"ratio": r_lift, "bar": 10.0, "verdict": "PASS" if r_lift > 10 else "FAIL"}

    # ---------------------------------------------------------------- N4
    print("\n=== N4: achromatic or chromatic (M107's demosaic hypothesis) ===", flush=True)
    chan = {}
    for ci, cn in enumerate("RGB"):
        s = stats(prof_of(rgb[..., ci]), *FAR_GRID[0])
        chan[cn] = s
        print(f"  {cn}:", fmt(s)[2:], flush=True)
    lifts = {k: v["lift_local_pct"] for k, v in chan.items() if v}
    over = {k: v["overshoot_pct"] for k, v in chan.items() if v}
    if len(lifts) == 3:
        sgn = len(set(np.sign(list(lifts.values())))) == 1
        rng = max(lifts.values()) / max(min(lifts.values()), 1e-9)
        ok = bool(sgn and 1 / 1.5 <= rng <= 1.5)
        print(f"  signs agree={sgn}  max/min lift ratio={rng:.3f}  "
              f"(registered: same sign and within 1.5x) -> "
              f"{'ACHROMATIC (veil)' if ok else 'CHROMATIC (hand share to M107)'}", flush=True)
        rep["N4"] = {"lift_pct": lifts, "overshoot_pct": over, "signs_agree": sgn,
                     "max_over_min": rng, "verdict": "ACHROMATIC" if ok else "CHROMATIC"}

    # ---------------------------------------------------------------- C-PARAM
    print("\n=== C-PARAM: does N1's verdict survive changing MY parameters? ===", flush=True)
    grid = []
    for tmul in TAU_GRID:
        m2, _ = L.foreground_mask(g, tau=tau * tmul)
        p2, _ = make_profiler(m2, ROI_LEG)
        pr2 = p2(g)
        for far in FAR_GRID:
            s = stats(pr2, *far)
            if s is None:
                grid.append({"tau_mul": tmul, "far": list(far), "overshoot_pct": None})
                print(f"  tau x{tmul:.1f}  far={far}  (insufficient bins)", flush=True)
                continue
            grid.append({"tau_mul": tmul, "far": list(far),
                         "fg_frac": float(m2.mean()),
                         "overshoot_pct": s["overshoot_pct"],
                         "lift_local_pct": s["lift_local_pct"], "d_star": s["d_star"]})
            print(f"  tau x{tmul:.1f} (fg {m2.mean():.3f})  far={str(far):10s} "
                  f"overshoot={s['overshoot_pct']:+8.3f}%  lift={s['lift_local_pct']:+8.3f}%  "
                  f"d*={s['d_star']}", flush=True)
    vals = [c["overshoot_pct"] for c in grid if c["overshoot_pct"] is not None]
    signs = set(np.sign(np.round(vals, 6)))
    invariant = len(signs) == 1
    print(f"\n  overshoot sign over the 3x3 grid: {sorted(signs)}  -> "
          f"{'INVARIANT' if invariant else 'FLIPS -- N1 gets NO VERDICT'}", flush=True)
    rep["C_PARAM"] = {"grid": grid, "signs": sorted(float(s) for s in signs),
                      "invariant": bool(invariant),
                      "range_pct": [float(min(vals)), float(max(vals))] if vals else None}

    # ---------------------------------------------------------------- N1 verdict
    if s_def and s_brk:
        excess = s_def["overshoot_pct"] - s_brk["overshoot_pct"]
        if not invariant:
            verdict = "NO VERDICT (C-PARAM sign flip)"
        elif s_def["overshoot_pct"] <= max(s_brk["overshoot_pct"], 0.0):
            verdict = "O1 -- convex bound HOLDS (two-layer veil survives)"
        else:
            verdict = "O2 -- convex bound BREACHED (not a two-layer veil)"
        print(f"\n  N1  merge overshoot {s_def['overshoot_pct']:+.3f}%  vs  "
              f"broken bias floor {s_brk['overshoot_pct']:+.3f}%  "
              f"excess {excess:+.3f}%\n  N1 VERDICT: {verdict}", flush=True)
        rep["N1"] = {"overshoot_pct": s_def["overshoot_pct"],
                     "broken_overshoot_pct": s_brk["overshoot_pct"],
                     "excess_pct": excess, "verdict": verdict}

    # ---------------------------------------------------------------- N3
    print("\n=== N3: annulus collision -- how much subject is within reach r? ===", flush=True)
    n3 = {}
    din = distance_transform_edt(mask)
    sub = din[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3]]
    sub = sub[sub > 0]
    n3["bee_leg"] = {str(r): float((sub <= r).mean()) for r in (5, 10, 15, 20, 30, 40)}
    n3["bee_leg"]["median_d_in"] = float(np.median(sub))
    n3["bee_leg"]["p95_d_in"] = float(np.percentile(sub, 95))
    n3["bee_leg"]["n_px"] = int(sub.size)
    print(f"  bee legs (ROI_LEG, {sub.size} subject px): "
          f"median d_in={np.median(sub):.2f}  p95={np.percentile(sub, 95):.2f}", flush=True)
    for r in (5, 10, 15, 20, 30, 40):
        print(f"    A_{r:<3d} = {(sub <= r).mean() * 100:6.2f}%", flush=True)

    fm_p = CACHE / "18-alone-mask.npy"
    if fm_p.exists():
        fmask = np.load(fm_p)
        fd = distance_transform_edt(fmask)
        fs = fd[fd > 0]
        n3["flower_bud"] = {str(r): float((fs <= r).mean()) for r in (5, 10, 15, 20, 30, 40)}
        n3["flower_bud"]["median_d_in"] = float(np.median(fs))
        n3["flower_bud"]["p95_d_in"] = float(np.percentile(fs, 95))
        n3["flower_bud"]["n_px"] = int(fs.size)
        print(f"  flower bud ({fs.size} subject px): median d_in={np.median(fs):.2f}  "
              f"p95={np.percentile(fs, 95):.2f}", flush=True)
        for r in (5, 10, 15, 20, 30, 40):
            print(f"    A_{r:<3d} = {(fs <= r).mean() * 100:6.2f}%", flush=True)
        a20b = n3["bee_leg"]["20"]
        a20f = n3["flower_bud"]["20"]
        ok = a20b > 0.80 and a20f < 0.30
        print(f"\n  N3  A_20 bee={a20b * 100:.2f}%  bud={a20f * 100:.2f}%  "
              f"(registered: bee>80%, bud<30%) -> {'PASS' if ok else 'FAIL'}", flush=True)
        n3["verdict"] = "PASS" if ok else "FAIL"
        n3["ratio_A20"] = a20b / max(a20f, 1e-9)
    rep["N3"] = n3

    # ---------------------------------------------------------------- C-FRAME
    print("\n=== C-FRAME: does any of the 299 single frames carry this rim? ===", flush=True)
    cube_p = CACHE / "bee3-leg-luma.npy"
    cmask_p = CACHE / "bee3-leg-mask.npy"
    if cube_p.exists() and cmask_p.exists():
        cube = np.load(cube_p, mmap_mode="r")
        cmask = np.load(cmask_p)
        csel = np.load(CACHE / "bee3-leg-sel.npy")
        cg2 = np.load(CACHE / "bee3-leg-g2.npy")
        print(f"  cube {cube.shape}  mask {cmask.shape}  ROI {CUBE_ROI}", flush=True)
        cp, _ = make_profiler(cmask, CUBE_ROI, d_max=96)
        cb, _ = make_profiler(L.shifted_mask(cmask, (256, 256)), CUBE_ROI, d_max=96)
        s_sel = stats(cp(csel), 48, 96)
        s_g2 = stats(cp(cg2), 48, 96)
        s_cbk = stats(cb(csel), 48, 96)
        print(f"  merge gate0 :{fmt(s_sel)[1:]}", flush=True)
        print(f"  merge gate2 :{fmt(s_g2)[1:]}", flush=True)
        print(f"  C-BROKEN    :{fmt(s_cbk)[1:]}", flush=True)
        lifts_k = []
        for k in range(cube.shape[0]):
            s = stats(cp(np.asarray(cube[k])), 48, 96)
            lifts_k.append(np.nan if s is None else s["lift_local_pct"])
            if k % 60 == 0:
                print(f"    frame {k:3d}/{cube.shape[0]}  lift={lifts_k[-1]:+.3f}%  "
                      f"[{time.time() - t0:.0f}s]", flush=True)
        lk = np.array(lifts_k, float)
        fin = np.isfinite(lk)
        mx = float(np.nanmax(lk))
        kmx = int(np.nanargmax(lk))
        print(f"\n  single frames: n={int(fin.sum())}  "
              f"max lift={mx:+.4f}% (frame {kmx})  "
              f"mean={np.nanmean(lk):+.4f}%  sd={np.nanstd(lk):.4f}%", flush=True)
        if s_sel:
            ratio_max = s_sel["lift_local_pct"] / max(abs(mx), 1e-9)
            ratio_mean = s_sel["lift_local_pct"] / max(abs(np.nanmean(lk)), 1e-9)
            sd = float(np.nanstd(lk))
            se_units = (s_sel["lift_local_pct"] - np.nanmean(lk)) / max(sd, 1e-9)
            print(f"  merge gate0 lift {s_sel['lift_local_pct']:+.4f}%\n"
                  f"    vs WORST single frame : {ratio_max:.2f}x   <-- the conservative statement\n"
                  f"    vs MEAN single frame  : {ratio_mean:.2f}x\n"
                  f"    in sd units           : {se_units:.1f}", flush=True)
            rep["C_FRAME"] = {
                "n_frames": int(fin.sum()), "max_lift_pct": mx, "argmax_frame": kmx,
                "mean_lift_pct": float(np.nanmean(lk)), "sd_lift_pct": sd,
                "merge_gate0_lift_pct": s_sel["lift_local_pct"],
                "merge_gate2_lift_pct": s_g2["lift_local_pct"] if s_g2 else None,
                "broken_lift_pct": s_cbk["lift_local_pct"] if s_cbk else None,
                "ratio_vs_max": ratio_max, "ratio_vs_mean": ratio_mean, "sd_units": se_units,
                "verdict": "PASS -- merge exceeds every single frame"
                           if s_sel["lift_local_pct"] > mx else
                           "FAIL -- a single frame matches the merge",
                "per_frame_lift_pct": [None if not np.isfinite(x) else round(float(x), 5)
                                       for x in lk],
            }
            print(f"  C-FRAME VERDICT: {rep['C_FRAME']['verdict']}", flush=True)
    else:
        print("  cube absent -- C-FRAME skipped", flush=True)
        rep["C_FRAME"] = {"skipped": True}

    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "63-bee-judged.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\nwrote {DATA / '63-bee-judged.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()

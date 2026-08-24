"""M87 / 65 -- separating what the bee rim is made of: occlusion, photometry, drift.

Step 64 replaced the frozen band-profile with the ELECTION BRIGHTNESS RANK,

    R(p) = mid-rank percentile of the ELECTED sample within pixel p's own
           through-focus samples,   null = 0.5 exactly,

and it read the artifact the eye sees: rendered, high-R pixels trace every leg,
hair and claw of `bee-3-cpl` with the same lobed boundary as the visible veil
(`64-rank-map.png` against `crop-leg-halo.png`).  R rises from 0.5134 at d = 1
to 0.8758 at d = 5, holds ~0.87 through d = 12, and falls back through 0.55 at
d = 27.  The uniform-random-index broken arm sat at 0.5 within 0.0176.

But step 64 also returned TWO results I did not register and must explain rather
than bury:

  (i) R at far background is 0.1745, not 0.5.  Selection out there prefers DARK
      frames, strongly.  Registered bar R1 FAILED on that clause.
  (ii) The C-SHUF broken arm -- the elected-index FIELD rolled by (317,511),
      which preserves the marginal distribution of elected depths and destroys
      only their registration with the boundary -- did NOT return 0.5.  It ran
      0.59 to 0.67, rising with d.

Both have the same candidate cause, and it is not mine: `bee-3-cpl` carries a
per-frame photometric drift (M96/M99; ORCH measured a 5.31% early-frame
brightness bias).  If the frames that are sharp on the background plane are
systematically dimmer, then any pixel whose election lands there ranks low, with
no occlusion involved at all.  C-SHUF is exactly that effect isolated, because
it keeps the depth distribution and throws away the geometry.

That makes C-SHUF far more useful than the broken arm I meant it to be:

    dR(d) = R_true(d) - R_shuf(d)

is the OCCLUSION-SPECIFIC excess, with the photometric share already removed by
construction.  The orchestrator asked for exactly this decomposition and warned
me not to attribute the whole halo to occlusion before making it.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

P1 -- THE PHOTOMETRIC / OPTICAL SPLIT.  Recompute R on frames normalised by a
    per-frame gain g_k, estimated as the median over pixels that are background
    AND at least 40 px from the subject in the merge.  This is a crude version
    of what M99's `photometric.rs` does properly; it does not need to be theirs.
    REGISTERED: after normalisation the FAR field returns toward the null,
    |R_far - 0.5| < 0.10 (from 0.1745, i.e. 0.325 away), WHILE the near peak
    survives above 0.75 (from 0.876).  That would show the far-field tilt is
    photometric and the near band is not.
    If instead the near peak also collapses, the rim is substantially a
    photometric artifact, M99 owns a share of it, and I say so.

P2 -- THE OCCLUSION-SPECIFIC REACH.  dR(d) = R_true - R_shuf.
    REGISTERED: dR is positive over a contiguous band, peaks at d between 3 and
    12, and returns to zero by d = 40.  The peak location is the design
    constraint for the annulus fix and section 24.4 measured the equivalent on
    `flower-bud-alone-cpl` at 7 px outside the silhouette, so I predict a peak
    in the same neighbourhood on a completely different subject class.

P3 -- THE INTERNAL PLACEBO, and the point of the whole exercise.  Not every
    boundary in ROI_LEG is an occluding one.  For each background pixel take
    k_fg = elected index of its NEAREST subject pixel and k_bg = a locally
    smoothed elected index over far background, and call |k_fg - k_bg| the
    boundary's DEPTH STEP.  Where the step is ~0 the two sides are at the same
    depth: a reflectance or in-plane edge, no occlusion possible.
    REGISTERED: R in the band d in [3,16] increases monotonically across depth-
    step terciles, and the BOTTOM tercile is within 0.05 of R_shuf -- i.e. the
    band is absent where there is no depth step.
    This is the control that separates "occlusion" from "any edge at all".  If
    the bottom tercile shows the same band as the top, my mechanism is wrong and
    the rim is an edge artifact of some other kind.

C-DRIFT -- IS ANY OF THIS JUST MISREGISTRATION?  The cube is built from
    UNALIGNED frames and this stack carries 232.7 px of uncorrected inter-frame
    drift at full resolution.  ORCH has measured that the rendered halo is
    unchanged by alignment, but that is a statement about the render, not about
    my statistic.  So: estimate each frame's integer translation by FFT phase
    correlation against frame 0, roll BOTH the luma and the focus-field cubes,
    recompute best/argbest/sel/mask from the rolled fields, and recompute R.
    Both arms are scored on the SAME shrunken ROI, inset by the largest shift,
    so no wrap-around enters either.
    REGISTERED: the dR peak amplitude changes by less than 25% and its location
    by less than 50%.  If instead the band collapses when drift is removed, it
    is a registration artifact, it is not mine, and I hand it to M103.

READ-ONLY: D:\\personal\\macro.  Writes only to experiments/M87-occlusion/data
and C:\\dev\\strehl-out\\M87-bee.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt, uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

MARGIN = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1
D_MAX = 96
MIN_BIN = 200
ROLL = (317, 511)
SEED = 8702
BAND = (3, 16)


def rank_of(cube, idx, rows=48):
    n, h, w = cube.shape
    out = np.empty((h, w), np.float32)
    for r0 in range(0, h, rows):
        r1 = min(r0 + rows, h)
        blk = np.asarray(cube[:, r0:r1, :], dtype=np.float32)
        sel = np.take_along_axis(blk, idx[None, r0:r1, :].astype(np.intp), axis=0)[0]
        out[r0:r1] = ((blk < sel[None]).sum(0) + 0.5 * ((blk == sel[None]).sum(0) - 1)) / (n - 1)
    return out


def profile_of(field, mask, roi, d_max=D_MAX, min_bin=MIN_BIN, weight=None):
    dist = distance_transform_edt(~mask)
    y0, y1, x0, x1 = roi
    dr = np.rint(dist[y0:y1, x0:x1]).astype(np.int32)
    bg = ~mask[y0:y1, x0:x1]
    if weight is not None:
        bg = bg & weight[y0:y1, x0:x1]
    v = field[y0:y1, x0:x1]
    prof = np.full(d_max + 1, np.nan)
    cnt = np.zeros(d_max + 1, np.int64)
    for d in range(1, d_max + 1):
        s = bg & (dr == d)
        cnt[d] = int(s.sum())
        if cnt[d] >= min_bin:
            prof[d] = float(np.median(v[s]))
    return prof, cnt


def band_stat(prof, lo=BAND[0], hi=BAND[1]):
    seg = prof[lo:hi + 1]
    return float(np.nanmedian(seg))


def zero_cross(dr_prof):
    for d in range(1, len(dr_prof)):
        if np.isfinite(dr_prof[d]) and dr_prof[d] <= 0:
            rest = dr_prof[d:][np.isfinite(dr_prof[d:])]
            if rest.size and float(np.nanmax(rest)) <= 0.02:
                return d
    return None


def estimate_shifts(cube, ref=0):
    """Integer per-frame translation by FFT phase correlation on frame gradients."""
    n, h, w = cube.shape
    a0 = np.asarray(cube[ref], dtype=np.float32)
    a0 = a0 - uniform_filter(a0, 31)
    F0 = np.fft.rfft2(a0)
    dy = np.zeros(n, int)
    dx = np.zeros(n, int)
    for k in range(n):
        a = np.asarray(cube[k], dtype=np.float32)
        a = a - uniform_filter(a, 31)
        F = np.fft.rfft2(a)
        cps = F0 * np.conj(F)
        cps /= np.maximum(np.abs(cps), 1e-9)
        c = np.fft.irfft2(cps, s=(h, w))
        p = np.unravel_index(int(np.argmax(c)), c.shape)
        dy[k] = p[0] if p[0] <= h // 2 else p[0] - h
        dx[k] = p[1] if p[1] <= w // 2 else p[1] - w
    return dy, dx


def main():
    t0 = time.time()
    rep = {}
    rng = np.random.default_rng(SEED)

    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(CACHE / "bee3-leg-field.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    arg0 = np.load(CACHE / "bee3-leg-argbest.npy").astype(np.int32)
    n, h, w = cube.shape
    print(f"cube {cube.shape}", flush=True)

    # ------------------------------------------------------------- C-DRIFT
    print("\n=== C-DRIFT: estimating per-frame translation ===", flush=True)
    dy, dx = estimate_shifts(cube)
    span = (int(dy.max() - dy.min()), int(dx.max() - dx.min()))
    m = int(max(np.abs(dy).max(), np.abs(dx).max())) + 2
    print(f"  dy {dy.min()}..{dy.max()}  dx {dx.min()}..{dx.max()}  "
          f"span {span} binned px  ({2 * span[0]}, {2 * span[1]} at full res)  "
          f"inset={m}  [{time.time() - t0:.0f}s]", flush=True)
    rep["drift"] = {"dy_span": span[0], "dx_span": span[1], "inset": m,
                    "dy": dy.tolist(), "dx": dx.tolist()}

    ROI = (MARGIN + m, MARGIN + 700 - m, MARGIN + m, MARGIN + 1100 - m)
    print(f"  paired ROI (both arms) = {ROI}", flush=True)

    # ------------------------------------------------------------- baseline R
    print("\n=== arms on the UNALIGNED cube ===", flush=True)
    R = rank_of(cube, arg0)
    R_shuf = rank_of(cube, np.roll(arg0, ROLL, axis=(0, 1)))
    p_t, cnt = profile_of(R, mask, ROI)
    p_s, _ = profile_of(R_shuf, mask, ROI)
    dR = p_t - p_s
    print(f"  R done [{time.time() - t0:.0f}s]", flush=True)

    # ------------------------------------------------------------- P1
    print("\n=== P1: photometric / optical split ===", flush=True)
    dist = distance_transform_edt(~mask)
    farbg = (~mask) & (dist >= 40)
    print(f"  gain region: {farbg.sum()} px ({100 * farbg.mean():.2f}% of crop)", flush=True)
    g = np.empty(n)
    for k in range(n):
        g[k] = float(np.median(np.asarray(cube[k])[farbg]))
    g /= g.mean()
    print(f"  per-frame gain: min={g.min():.5f} max={g.max():.5f} "
          f"span={100 * (g.max() - g.min()):.3f}%  first10={g[:10].mean():.5f} "
          f"last10={g[-10:].mean():.5f}", flush=True)
    rep["gain"] = {"g": [round(float(x), 6) for x in g],
                   "span_pct": float(100 * (g.max() - g.min())),
                   "first10": float(g[:10].mean()), "last10": float(g[-10:].mean())}

    norm = np.lib.format.open_memmap(OUT / "65-norm.npy", mode="w+",
                                     dtype=np.float32, shape=(n, h, w))
    for k in range(n):
        norm[k] = np.asarray(cube[k], dtype=np.float32) / g[k]
    norm.flush()
    Rn = rank_of(norm, arg0)
    Rn_shuf = rank_of(norm, np.roll(arg0, ROLL, axis=(0, 1)))
    p_tn, _ = profile_of(Rn, mask, ROI)
    p_sn, _ = profile_of(Rn_shuf, mask, ROI)
    dRn = p_tn - p_sn

    def summ(tag, pt, ps, dd):
        near = float(np.nanmax(pt[1:21]))
        dstar = int(np.nanargmax(np.where(np.isfinite(pt[:21]), pt[:21], -9)))
        far = float(np.nanmedian(pt[80:97]))
        dpk = float(np.nanmax(dd[1:41]))
        dpk_d = int(np.nanargmax(np.where(np.isfinite(dd[:41]), dd[:41], -9)))
        print(f"  {tag:14s} peak R={near:.4f} at d={dstar:3d}   far R={far:.4f}   "
              f"shuf(band)={band_stat(ps):.4f}   dR peak={dpk:+.4f} at d={dpk_d}",
              flush=True)
        return {"peak_R": near, "d_peak": dstar, "far_R": far,
                "shuf_band": band_stat(ps), "dR_peak": dpk, "dR_d_peak": dpk_d,
                "dR_zero": zero_cross(dd)}

    s_raw = summ("raw", p_t, p_s, dR)
    s_nrm = summ("gain-normed", p_tn, p_sn, dRn)
    p1 = bool(abs(s_nrm["far_R"] - 0.5) < 0.10 and s_nrm["peak_R"] > 0.75)
    print(f"  P1 (registered: |far-0.5|<0.10 AND peak>0.75) -> "
          f"{'PASS' if p1 else 'FAIL'}", flush=True)
    print(f"     far moved {s_raw['far_R']:.4f} -> {s_nrm['far_R']:.4f}  "
          f"(toward null by {abs(s_raw['far_R'] - 0.5) - abs(s_nrm['far_R'] - 0.5):+.4f})",
          flush=True)
    print(f"     photometric share of the FAR tilt = "
          f"{100 * (abs(s_raw['far_R'] - 0.5) - abs(s_nrm['far_R'] - 0.5)) / max(abs(s_raw['far_R'] - 0.5), 1e-9):.1f}%",
          flush=True)
    print(f"     dR band peak {s_raw['dR_peak']:+.4f} -> {s_nrm['dR_peak']:+.4f}  "
          f"({100 * (s_nrm['dR_peak'] - s_raw['dR_peak']) / max(s_raw['dR_peak'], 1e-9):+.1f}%)",
          flush=True)
    rep["P1"] = {"raw": s_raw, "normed": s_nrm, "verdict": "PASS" if p1 else "FAIL"}

    # ------------------------------------------------------------- P2
    print("\n=== P2: occlusion-specific reach dR(d) = R_true - R_shuf ===", flush=True)
    print("    d      n     R_true   R_shuf      dR", flush=True)
    for d in [1, 2, 3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 24, 28, 32, 40, 50, 64, 80, 96]:
        if np.isfinite(p_t[d]):
            print(f"  {d:3d} {cnt[d]:7d}   {p_t[d]:7.4f}  {p_s[d]:7.4f}  {dR[d]:+7.4f}",
                  flush=True)
    p2 = bool(3 <= s_raw["dR_d_peak"] <= 12 and s_raw["dR_zero"] is not None
              and s_raw["dR_zero"] <= 40)
    print(f"\n  P2  dR peaks {s_raw['dR_peak']:+.4f} at d={s_raw['dR_d_peak']}, "
          f"returns to 0 at d={s_raw['dR_zero']}  "
          f"(registered: peak in 3..12, zero by 40) -> {'PASS' if p2 else 'FAIL'}", flush=True)
    rep["P2"] = {"d": list(range(D_MAX + 1)),
                 "R_true": [None if not np.isfinite(x) else round(float(x), 5) for x in p_t],
                 "R_shuf": [None if not np.isfinite(x) else round(float(x), 5) for x in p_s],
                 "dR": [None if not np.isfinite(x) else round(float(x), 5) for x in dR],
                 "counts": [int(c) for c in cnt], "verdict": "PASS" if p2 else "FAIL"}

    # ------------------------------------------------------------- P3
    print("\n=== P3: internal placebo -- does the band need a depth step? ===", flush=True)
    _, inds = distance_transform_edt(~mask, return_indices=True)
    k_fg = arg0[inds[0], inds[1]].astype(np.float32)
    bgfar = ((~mask) & (dist >= 40)).astype(np.float32)
    num = uniform_filter(arg0.astype(np.float32) * bgfar, 129)
    den = uniform_filter(bgfar, 129)
    k_bg = num / np.maximum(den, 1e-6)
    step = np.abs(k_fg - k_bg)
    y0, y1, x0, x1 = ROI
    dr = np.rint(dist[y0:y1, x0:x1]).astype(np.int32)
    inband = (~mask[y0:y1, x0:x1]) & (dr >= BAND[0]) & (dr <= BAND[1]) & (den[y0:y1, x0:x1] > 1e-3)
    sv = step[y0:y1, x0:x1][inband]
    rv = R[y0:y1, x0:x1][inband]
    shv = R_shuf[y0:y1, x0:x1][inband]
    q1, q2 = np.percentile(sv, [33.333, 66.667])
    terc = [(sv <= q1), (sv > q1) & (sv <= q2), (sv > q2)]
    names = ["low step", "mid step", "high step"]
    rows = []
    print(f"  band d in [{BAND[0]},{BAND[1]}]: {inband.sum()} px   "
          f"depth-step terciles at |dk| = {q1:.1f}, {q2:.1f} frames", flush=True)
    for nm, t in zip(names, terc):
        row = {"name": nm, "n": int(t.sum()), "median_step": float(np.median(sv[t])),
               "R": float(np.median(rv[t])), "R_shuf": float(np.median(shv[t]))}
        row["dR"] = row["R"] - row["R_shuf"]
        rows.append(row)
        print(f"    {nm:10s} n={row['n']:7d}  median|dk|={row['median_step']:6.1f}  "
              f"R={row['R']:.4f}  R_shuf={row['R_shuf']:.4f}  dR={row['dR']:+.4f}", flush=True)
    mono = rows[0]["dR"] < rows[1]["dR"] < rows[2]["dR"]
    flat = abs(rows[0]["dR"]) < 0.05
    print(f"  monotone in depth step: {mono}   low tercile within 0.05 of shuffle: "
          f"{flat}  -> {'PASS' if (mono and flat) else 'FAIL'}", flush=True)
    rep["P3"] = {"terciles": rows, "monotone": bool(mono), "low_flat": bool(flat),
                 "verdict": "PASS" if (mono and flat) else "FAIL"}

    # ------------------------------------------------------------- C-DRIFT arm
    print("\n=== C-DRIFT: recompute everything on drift-corrected frames ===", flush=True)
    best = np.full((h, w), -np.inf, np.float32)
    argA = np.zeros((h, w), np.int32)
    for k in range(n):
        f = np.roll(np.asarray(field[k], dtype=np.float32), (-dy[k], -dx[k]), axis=(0, 1))
        upd = f > best
        best[upd] = f[upd]
        argA[upd] = k
    alr = np.lib.format.open_memmap(OUT / "65-aligned.npy", mode="w+",
                                    dtype=np.float32, shape=(n, h, w))
    for k in range(n):
        alr[k] = np.roll(np.asarray(cube[k], dtype=np.float32), (-dy[k], -dx[k]), axis=(0, 1))
    alr.flush()
    selA = np.take_along_axis(alr, argA[None], axis=0)[0]
    maskA, tauA = L.foreground_mask(selA)
    print(f"  aligned merge: mask fg={maskA.mean():.4f} (unaligned {mask.mean():.4f})",
          flush=True)
    RA = rank_of(alr, argA)
    RA_shuf = rank_of(alr, np.roll(argA, ROLL, axis=(0, 1)))
    p_ta, _ = profile_of(RA, maskA, ROI)
    p_sa, _ = profile_of(RA_shuf, maskA, ROI)
    dRA = p_ta - p_sa
    s_ali = summ("drift-corrected", p_ta, p_sa, dRA)
    da = 100 * (s_ali["dR_peak"] - s_raw["dR_peak"]) / max(s_raw["dR_peak"], 1e-9)
    dl = 100 * abs(s_ali["dR_d_peak"] - s_raw["dR_d_peak"]) / max(s_raw["dR_d_peak"], 1)
    cd = bool(abs(da) < 25 and dl < 50)
    print(f"  dR peak {s_raw['dR_peak']:+.4f} -> {s_ali['dR_peak']:+.4f} ({da:+.1f}%),  "
          f"d* {s_raw['dR_d_peak']} -> {s_ali['dR_d_peak']} ({dl:.1f}%)", flush=True)
    print(f"  C-DRIFT (registered: |amp|<25%, |loc|<50%) -> {'PASS' if cd else 'FAIL'}",
          flush=True)
    rep["C_DRIFT"] = {"aligned": s_ali, "amp_change_pct": da, "loc_change_pct": dl,
                      "mask_fg_aligned": float(maskA.mean()), "tau": float(tauA),
                      "dR": [None if not np.isfinite(x) else round(float(x), 5) for x in dRA],
                      "verdict": "PASS" if cd else "FAIL"}

    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "65-decompose.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)
    print(f"\nwrote {DATA / '65-decompose.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()

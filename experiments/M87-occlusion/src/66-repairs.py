"""M87 / 66 -- repairing three defects in step 65, and one result it hid.

Step 65 registered four bars.  P2 passed and is the design constraint I wanted.
The other three are compromised, by my own instruments, and this step fixes each
rather than reporting them as they stand.

DEFECT 1 -- C-DRIFT DID NOT RUN.  My FFT phase-correlation estimator returned
    dy = dx = 0 for ALL 299 frames.  That cannot be right: step 35's independent
    mask-centroid instrument measures 63.04 px peak-to-peak of drift at ROI_LEG
    in the binned plane, and step 39 confirmed it against the aligner's own
    sidecar.  So C-DRIFT's "PASS" was the unaligned arm compared with itself and
    it is VACUOUS.  Repaired two ways here: a PLANTED POSITIVE CONTROL that
    tells me whether the estimator or the data is at fault, and authoritative
    per-frame shifts read from the aligner's warpmap sidecar.

DEFECT 2 -- P3's TERCILES NEVER CONTAINED A PLACEBO.  I split band pixels into
    depth-step terciles and required the bottom one to look like the shuffle.
    But the bottom tercile's median step is 7.3 frames -- a real depth step, not
    zero -- so the population the control needed did not exist in the split.
    Same failure class as step 58's discs planted where no subject ring existed
    and step 63's C-BROKEN translated onto the bee.  Three times now I have
    built a control whose required geometry was absent from where I put it, so
    this step uses ABSOLUTE |dk| bins with a decidability gate on each.

DEFECT 3 -- P1's CONCLUSION WAS INCOMPLETE.  Per-frame gain normalisation moved
    the far-field rank by 0.0101 out of 0.3255, i.e. it removed 3.1% of the
    far-field tilt, and the bar FAILED.  I registered that bar expecting the
    tilt to be photometric.  It is not.  But "not photometric" is not the same
    as "instrument defect", and there is a specific alternative that the
    two-layer model itself predicts, tested below as F1.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

D1 -- IS MY DRIFT ESTIMATOR OR THE DATA AT FAULT?  Take frame 0, roll it by a
    known (dy, dx) = (+13, -21), and hand the pair to the same estimator.
    REGISTERED: a working estimator recovers (+13, -21) exactly.  If it does,
    the estimator is sound and the cube really has no integer translation; if it
    does not, the estimator is broken and step 65's C-DRIFT is void.
    Either way I report which, because a green control that was never capable of
    going red is worth nothing.

D2 -- C-DRIFT ON AUTHORITATIVE SHIFTS.  Per-frame displacement at the ROI_LEG
    centre from the aligner's warpmap (`a*z + b`, centred convention, derived
    in step 39 and re-derived here rather than assumed).  Roll the luma and the
    focus-field cubes by the rounded displacement, recompute best / argbest /
    sel / mask from the rolled fields, recompute R and dR, and score both arms
    on the same ROI inset by the largest shift.
    REGISTERED: dR peak amplitude changes by less than 25% and its location by
    less than 50%.  If the band collapses, it is registration, not occlusion,
    and it belongs to M103.

D3 -- THE PLACEBO, WITH BINS THAT CAN CONTAIN ONE.  Absolute bins on the
    boundary depth step |dk| = |k_fg - k_bg|: [0,3), [3,10), [10,30), [30,60),
    [60,inf).  Each bin is reported with its pixel count and is DECIDABLE only
    if it holds at least 2000 band pixels.
    REGISTERED: R rises monotonically across decidable bins, and the [0,3) bin
    -- two sides at the same depth, so no occlusion is geometrically possible --
    shows dR <= 0.05.  That bin is the placebo.  If it shows the same band as
    [60,inf), the mechanism is not occlusion and my account is wrong.

F1 -- THE SIGN-FLIPPED PREDICTION, and the reason P1's failure may be a result.
    The two-layer account says election at a background pixel picks the frame
    that maximises the focus response there.  Close to a limb the response is
    dominated by the LIMB's edge, so the limb-sharp frame wins -- and that is
    the frame in which the limb's blur disc has shrunk OFF the pixel, so the
    pixel is bright.  Far from every limb the response is dominated by the
    CARD's own texture, so the card-sharp frame wins -- and that is the frame in
    which every surrounding limb is maximally defocused, so their dark discs are
    spread at their widest and veil the pixel most.  The same mechanism
    therefore predicts R > 0.5 near a limb and R < 0.5 far from limbs, with the
    far-field deficit DEEPENING as more defocused subject surrounds the pixel.
    Statistic: at background pixels with d >= 40, bin by local subject COVERAGE
    = fraction of subject within a 96 px radius, and measure R per bin.
    REGISTERED: R decreases monotonically with coverage, and the shuffled-index
    arm shows a change less than a third as large across the same bins.
    If R is flat in coverage, the far-field tilt is unexplained and I say so
    rather than attributing it.

C-LINEAR-2 -- step 64 regressed `bee3-g0.tif`'s green channel on the cache's
    linear raw green DN and got R^2 = 0.9698, and I caveated the chromaticity
    arm as "not linear".  That inference was too quick: the TIFF's green channel
    is DEMOSAICED and the cache's is BINNED RAW, so they differ by resampling as
    well as by any tone curve, and resampling scatter depresses R^2 without
    implying curvature.  Repaired by binning pixels on raw DN and regressing the
    per-bin MEDIANS, where resampling scatter averages out and only curvature
    survives.
    REGISTERED: if the binned relation is straight to R^2 > 0.999 and the
    quadratic term contributes less than 1% of the fitted range, the transform
    is linear and step 64's chromaticity result stands uncaveated.

READ-ONLY: D:\\personal\\macro.  Writes only to experiments/M87-occlusion/data
and C:\\dev\\strehl-out\\M87-bee.
"""
import json
import pathlib
import struct
import sys
import time

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)
WM = CACHE / "align" / "bee3-warpmap.txt"

ROI_LEG = L.ROIS["ROI_LEG"]
MARGIN = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1
D_MAX = 96
MIN_BIN = 200
ROLL = (317, 511)
BAND = (3, 16)
PLANT = (13, -21)
COV_R = 96
STEP_BINS = [(0, 3), (3, 10), (10, 30), (30, 60), (60, 10**9)]
DECIDABLE = 2000


def f64(hx):
    return struct.unpack(">d", bytes.fromhex(hx))[0]


def parse_wm(path):
    a, b, meta = [], [], {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        t = line.split()
        if t[0] in ("plane", "reference", "frames"):
            meta[t[0]] = t[1]
        if len(t) >= 6 and t[1] == "placed":
            a.append(complex(f64(t[2]), f64(t[3])))
            b.append(complex(f64(t[4]), f64(t[5])))
    return np.array(a), np.array(b), meta


def rank_of(cube, idx, rows=48):
    n, h, w = cube.shape
    out = np.empty((h, w), np.float32)
    for r0 in range(0, h, rows):
        r1 = min(r0 + rows, h)
        blk = np.asarray(cube[:, r0:r1, :], dtype=np.float32)
        sel = np.take_along_axis(blk, idx[None, r0:r1, :].astype(np.intp), axis=0)[0]
        out[r0:r1] = ((blk < sel[None]).sum(0) + 0.5 * ((blk == sel[None]).sum(0) - 1)) / (n - 1)
    return out


def profile_of(fieldv, mask, roi, d_max=D_MAX, min_bin=MIN_BIN):
    dist = distance_transform_edt(~mask)
    y0, y1, x0, x1 = roi
    dr = np.rint(dist[y0:y1, x0:x1]).astype(np.int32)
    bg = ~mask[y0:y1, x0:x1]
    v = fieldv[y0:y1, x0:x1]
    prof = np.full(d_max + 1, np.nan)
    for d in range(1, d_max + 1):
        s = bg & (dr == d)
        if int(s.sum()) >= min_bin:
            prof[d] = float(np.median(v[s]))
    return prof


def peak_of(dd, hi=41):
    seg = np.where(np.isfinite(dd[:hi]), dd[:hi], -9)
    i = int(np.argmax(seg))
    return float(dd[i]), i


def est_shift(a0hp, b_img):
    h, w = a0hp.shape
    bb = b_img - uniform_filter(b_img, 31)
    cps = np.fft.rfft2(a0hp) * np.conj(np.fft.rfft2(bb))
    cps /= np.maximum(np.abs(cps), 1e-9)
    c = np.fft.irfft2(cps, s=(h, w))
    p = np.unravel_index(int(np.argmax(c)), c.shape)
    return (p[0] if p[0] <= h // 2 else p[0] - h,
            p[1] if p[1] <= w // 2 else p[1] - w)


def main():
    t0 = time.time()
    rep = {}
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(CACHE / "bee3-leg-field.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    arg0 = np.load(CACHE / "bee3-leg-argbest.npy").astype(np.int32)
    n, h, w = cube.shape

    # ------------------------------------------------------------------ D1
    print("=== D1: planted positive control for my drift estimator ===", flush=True)
    f0 = np.asarray(cube[0], dtype=np.float32)
    f0hp = f0 - uniform_filter(f0, 31)
    got_self = est_shift(f0hp, f0.copy())
    planted = np.roll(f0, PLANT, axis=(0, 1))
    got = est_shift(f0hp, planted)
    exp = (-PLANT[0], -PLANT[1])
    ok = tuple(got) == exp
    print(f"  frame0 vs itself        -> {got_self}  (expect (0, 0))", flush=True)
    print(f"  frame0 vs frame0 rolled by {PLANT} -> {got}  (expect {exp})", flush=True)
    print(f"  D1 -> {'ESTIMATOR SOUND' if ok else 'ESTIMATOR BROKEN'}", flush=True)
    got_last = est_shift(f0hp, np.asarray(cube[n - 1], dtype=np.float32))
    print(f"  frame0 vs frame{n - 1} (real data) -> {got_last}", flush=True)
    rep["D1"] = {"self": [int(v) for v in got_self], "planted": [int(v) for v in got],
                 "expected": [int(v) for v in exp], "sound": bool(ok),
                 "first_vs_last": [int(v) for v in got_last]}

    # ------------------------------------------------------------------ D2
    print("\n=== D2: authoritative shifts from the aligner's warpmap ===", flush=True)
    A, B, meta = parse_wm(WM)
    W, H = (int(v) for v in meta["plane"].split("x"))
    best = None
    for name, off in (("raw", 0 + 0j), ("centred", complex(W / 2.0, H / 2.0))):
        cs = [complex(x, y) - off for x in (0.0, W) for y in (0.0, H)]
        worst = max(abs(A[-1] * z + B[-1] - z) for z in cs)
        print(f"  convention {name:8s}: worst-corner drift {worst:8.3f} px "
              f"vs the tool's 186.702", flush=True)
        e = abs(worst - 186.702)
        if best is None or e < best[2]:
            best = (name, off, e)
    print(f"  -> adopting {best[0]} (step 39 derived the same)", flush=True)
    assert best[2] < 5.0, "neither convention reproduces the tool's own number"
    off = best[1]
    cy = (ROI_LEG[0] + ROI_LEG[1]) / 2.0
    cx = (ROI_LEG[2] + ROI_LEG[3]) / 2.0
    z = complex(cx, cy) - off
    disp = A * z + B - z
    dy = np.rint(disp.imag).astype(int)
    dx = np.rint(disp.real).astype(int)
    pp = float(np.hypot(disp.real.max() - disp.real.min(),
                        disp.imag.max() - disp.imag.min()))
    print(f"  frames in sidecar={len(A)}  cube frames={n}", flush=True)
    if len(A) != n:
        print(f"  !! length mismatch -- truncating to {min(len(A), n)}", flush=True)
    nn = min(len(A), n)
    dy, dx = dy[:nn], dx[:nn]
    m = int(max(np.abs(dy).max(), np.abs(dx).max())) + 2
    print(f"  in-ROI drift {pp:.2f} px p-p (step 35 mask-centroid: 63.04) "
          f"ratio {pp / 63.04:.3f}", flush=True)
    print(f"  dy {dy.min()}..{dy.max()}  dx {dx.min()}..{dx.max()}  inset={m}", flush=True)
    rep["D2_shifts"] = {"pp_px": pp, "dy_span": int(dy.max() - dy.min()),
                        "dx_span": int(dx.max() - dx.min()), "inset": m,
                        "convention": best[0], "n_frames": int(nn)}

    ROI = (MARGIN + m, MARGIN + 700 - m, MARGIN + m, MARGIN + 1100 - m)
    print(f"  paired ROI (both arms) = {ROI}", flush=True)

    R = rank_of(cube, arg0)
    Rs = rank_of(cube, np.roll(arg0, ROLL, axis=(0, 1)))
    dR_u = profile_of(R, mask, ROI) - profile_of(Rs, mask, ROI)
    a_u, d_u = peak_of(dR_u)
    print(f"  UNALIGNED   dR peak {a_u:+.4f} at d={d_u}", flush=True)

    bestf = np.full((h, w), -np.inf, np.float32)
    argA = np.zeros((h, w), np.int32)
    for k in range(nn):
        f = np.roll(np.asarray(field[k], dtype=np.float32), (-dy[k], -dx[k]), axis=(0, 1))
        u = f > bestf
        bestf[u] = f[u]
        argA[u] = k
    al = np.lib.format.open_memmap(OUT / "66-aligned.npy", mode="w+",
                                   dtype=np.float32, shape=(nn, h, w))
    for k in range(nn):
        al[k] = np.roll(np.asarray(cube[k], dtype=np.float32), (-dy[k], -dx[k]), axis=(0, 1))
    al.flush()
    selA = np.take_along_axis(al, argA[None], axis=0)[0]
    maskA, _ = L.foreground_mask(selA)
    RA = rank_of(al, argA)
    RAs = rank_of(al, np.roll(argA, ROLL, axis=(0, 1)))
    dR_a = profile_of(RA, maskA, ROI) - profile_of(RAs, maskA, ROI)
    a_a, d_a = peak_of(dR_a)
    da = 100 * (a_a - a_u) / max(a_u, 1e-9)
    dl = 100 * abs(d_a - d_u) / max(d_u, 1)
    cd = bool(abs(da) < 25 and dl < 50)
    print(f"  DRIFT-CORR  dR peak {a_a:+.4f} at d={d_a}   mask fg "
          f"{maskA.mean():.4f} vs {mask.mean():.4f}", flush=True)
    print(f"  change: amplitude {da:+.1f}%, location {dl:.1f}%  "
          f"-> D2 {'PASS' if cd else 'FAIL'}  [{time.time() - t0:.0f}s]", flush=True)
    rep["D2"] = {"unaligned_peak": a_u, "unaligned_d": d_u, "aligned_peak": a_a,
                 "aligned_d": d_a, "amp_pct": da, "loc_pct": dl,
                 "mask_fg_aligned": float(maskA.mean()),
                 "dR_aligned": [None if not np.isfinite(x) else round(float(x), 5)
                                for x in dR_a],
                 "verdict": "PASS" if cd else "FAIL"}

    # ------------------------------------------------------------------ D3
    print("\n=== D3: the placebo, in absolute depth-step bins ===", flush=True)
    dist = distance_transform_edt(~mask)
    _, inds = distance_transform_edt(~mask, return_indices=True)
    k_fg = arg0[inds[0], inds[1]].astype(np.float32)
    bgfar = ((~mask) & (dist >= 40)).astype(np.float32)
    den = uniform_filter(bgfar, 129)
    k_bg = uniform_filter(arg0.astype(np.float32) * bgfar, 129) / np.maximum(den, 1e-6)
    step = np.abs(k_fg - k_bg)
    y0, y1, x0, x1 = ROI
    dr = np.rint(dist[y0:y1, x0:x1]).astype(np.int32)
    inb = ((~mask[y0:y1, x0:x1]) & (dr >= BAND[0]) & (dr <= BAND[1])
           & (den[y0:y1, x0:x1] > 1e-3))
    sv = step[y0:y1, x0:x1][inb]
    rv = R[y0:y1, x0:x1][inb]
    hv = Rs[y0:y1, x0:x1][inb]
    print(f"  band d in [{BAND[0]},{BAND[1]}]: {int(inb.sum())} px", flush=True)
    rows = []
    for lo, hi in STEP_BINS:
        s = (sv >= lo) & (sv < hi)
        nb = int(s.sum())
        dec = nb >= DECIDABLE
        row = {"lo": lo, "hi": None if hi > 10**8 else hi, "n": nb, "decidable": dec}
        if dec:
            row.update({"median_step": float(np.median(sv[s])),
                        "R": float(np.median(rv[s])),
                        "R_shuf": float(np.median(hv[s]))})
            row["dR"] = row["R"] - row["R_shuf"]
            print(f"    |dk| in [{lo:3d},{'inf' if hi > 10**8 else hi:>4}) "
                  f"n={nb:7d}  median={row['median_step']:6.1f}  R={row['R']:.4f}  "
                  f"shuf={row['R_shuf']:.4f}  dR={row['dR']:+.4f}", flush=True)
        else:
            print(f"    |dk| in [{lo:3d},{'inf' if hi > 10**8 else hi:>4}) "
                  f"n={nb:7d}  NOT DECIDABLE (< {DECIDABLE})", flush=True)
        rows.append(row)
    dec = [r for r in rows if r["decidable"]]
    mono = all(dec[i]["R"] < dec[i + 1]["R"] for i in range(len(dec) - 1))
    plc = dec[0] if dec and dec[0]["lo"] == 0 else None
    flat = bool(plc is not None and plc["dR"] <= 0.05)
    print(f"  R monotone across decidable bins: {mono}", flush=True)
    if plc is None:
        print("  PLACEBO BIN [0,3) NOT DECIDABLE -- D3 returns NO VERDICT", flush=True)
        v3 = "NO VERDICT"
    else:
        v3 = "PASS" if (mono and flat) else "FAIL"
        print(f"  placebo bin [0,3): dR={plc['dR']:+.4f} (registered <= 0.05) "
              f"-> D3 {v3}", flush=True)
    rep["D3"] = {"bins": rows, "monotone_R": bool(mono), "verdict": v3}

    # ------------------------------------------------------------------ F1
    print("\n=== F1: does the far-field deficit deepen with subject coverage? ===",
          flush=True)
    cov = uniform_filter(mask.astype(np.float32), 2 * COV_R + 1)
    far = (~mask[y0:y1, x0:x1]) & (dr >= 40)
    cvv = cov[y0:y1, x0:x1][far]
    rvv = R[y0:y1, x0:x1][far]
    hvv = Rs[y0:y1, x0:x1][far]
    qs = np.percentile(cvv, [0, 20, 40, 60, 80, 100])
    frows = []
    print(f"  far pixels (d >= 40): {int(far.sum())}", flush=True)
    for i in range(5):
        s = (cvv >= qs[i]) & (cvv <= qs[i + 1] if i == 4 else cvv < qs[i + 1])
        if int(s.sum()) < DECIDABLE:
            continue
        fr = {"quintile": i + 1, "n": int(s.sum()),
              "coverage": float(np.median(cvv[s])), "R": float(np.median(rvv[s])),
              "R_shuf": float(np.median(hvv[s]))}
        frows.append(fr)
        print(f"    Q{i + 1} n={fr['n']:7d}  coverage={fr['coverage']:.4f}  "
              f"R={fr['R']:.4f}  shuf={fr['R_shuf']:.4f}", flush=True)
    if len(frows) >= 3:
        mono_f = all(frows[i]["R"] > frows[i + 1]["R"] for i in range(len(frows) - 1))
        rng_t = abs(frows[0]["R"] - frows[-1]["R"])
        rng_s = abs(frows[0]["R_shuf"] - frows[-1]["R_shuf"])
        okf = bool(mono_f and rng_s < rng_t / 3.0)
        print(f"  R monotone decreasing in coverage: {mono_f}   "
              f"range true={rng_t:.4f} shuf={rng_s:.4f}  -> F1 "
              f"{'PASS' if okf else 'FAIL'}", flush=True)
        rep["F1"] = {"quintiles": frows, "monotone": bool(mono_f), "range_true": rng_t,
                     "range_shuf": rng_s, "verdict": "PASS" if okf else "FAIL"}

    # ------------------------------------------------------- C-LINEAR-2
    print("\n=== C-LINEAR-2: curvature, with resampling scatter binned away ===",
          flush=True)
    g0 = tifffile.imread(r"C:\dev\strehl-out\bee3-g0.tif")[..., 1].astype(np.float64)
    sel0 = np.load(CACHE / "bee3-leg-sel.npy").astype(np.float64)
    a = g0[ROI_LEG[0]:ROI_LEG[1], ROI_LEG[2]:ROI_LEG[3]].ravel()
    b = sel0[MARGIN:MARGIN + 700, MARGIN:MARGIN + 1100].ravel()
    lo, hi = np.percentile(b, [0.5, 99.5])
    edges = np.linspace(lo, hi, 65)
    ib = np.digitize(b, edges) - 1
    xs, ys = [], []
    for i in range(64):
        s = ib == i
        if s.sum() >= 500:
            xs.append(float(np.median(b[s])))
            ys.append(float(np.median(a[s])))
    xs, ys = np.array(xs), np.array(ys)
    sl, ic = np.polyfit(xs, ys, 1)
    r2 = 1 - float(((ys - (sl * xs + ic)) ** 2).sum() / ((ys - ys.mean()) ** 2).sum())
    q = np.polyfit(xs, ys, 2)
    curv = abs(q[0]) * (xs.max() - xs.min()) ** 2 / max(ys.max() - ys.min(), 1e-9)
    linear = bool(r2 > 0.999 and curv < 0.01)
    print(f"  {len(xs)} DN bins   linear fit R^2={r2:.6f}   slope={sl:.4f}", flush=True)
    print(f"  quadratic term as fraction of fitted range = {curv:.5f}", flush=True)
    print(f"  -> {'LINEAR: step 64 chromaticity stands UNCAVEATED' if linear else 'CURVED: chromaticity arm stays caveated'}",
          flush=True)
    rep["C_LINEAR2"] = {"n_bins": len(xs), "r2": r2, "slope": float(sl),
                        "curv_frac": float(curv), "linear": linear}

    rep["elapsed_s"] = round(time.time() - t0, 1)
    def _np(o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return float(o)
        raise TypeError(repr(o))

    with open(DATA / "66-repairs.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '66-repairs.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()

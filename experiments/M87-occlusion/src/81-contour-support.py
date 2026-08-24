"""M87 step 81 -- is the two-layer unmix's shortfall a SUPPORT problem?

The orchestrator's proposal (facts 1360-1362): on flowers-cpl the boundary-
elected pixels render as thin curved ribbons tracing petal edges, not as a
region. If the true occlusion population is CONTOURS, then "a fit whose support
assumes a broad region will be starved of pixels on most of the population, and
the shortfall would be a support problem, not a model problem". Requested test:
re-score the unmix restricted to contour pixels and see whether -28.2% moves.

WHAT I FOUND AT SOURCE BEFORE REGISTERING ANYTHING, because it reshapes the
question rather than answering it:

  * `13-unmix.py:fit()` and `17-perpixel-depth.py` regress I~_k on alpha_k
    ACROSS THE FRAME AXIS, at each pixel INDEPENDENTLY. There is no spatial
    neighbourhood, no patch, no window. The support of the estimator at a pixel
    is n frames, and n frames is what a one-pixel-wide contour has too. So
    contour geometry cannot starve this fit BY PIXEL COUNT. T2 measures that
    rather than asserting it.

  * Geometry does enter, but somewhere else: alpha_k = blur_{sigma_k}(matte).
    A thin structure blurred by a large sigma loses amplitude far faster than a
    broad one, so on a contour alpha never rises much above 0 -- and the
    admission gate `amax >= A_MIN & (amax - amin) >= A_RANGE` then rejects the
    pixel. That is the orchestrator's hypothesis in its CORRECT form: not
    starved of pixels, gated out for insufficient alpha excursion. T3.

  * The recorded numbers already push back on the starvation framing. The
    global-k_F arm treated 12.5% of the band; the per-pixel arm treated 19.8%
    and did BETTER. More coverage, better result -- the opposite of starvation.

BARS ARE THREE-BRANCH THROUGHOUT, per the orchestrator's discipline 676: a
ratio that can run either way needs a meaning for "below 1", or a strong
inverted effect gets scored as a null.

SIGN CONVENTION, stated once: dISO = 100 * (ISO_arm / ISO_F0 - 1). NEGATIVE is
an improvement (less halo). The shipped per-pixel arm is -28.16%.
"""

import json
import pathlib
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87metric2 as M2  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT, DATA, CACHE = ROOT / "out", ROOT / "data", ROOT / "cache"
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
FLOWERS_IDX = pathlib.Path(r"C:\dev\strehl-out\ORCH-flowers\argmax-index.tif")

MARGIN = 22
INNER = (MARGIN, MARGIN + 700, MARGIN, MARGIN + 1100)
A_MIN, A_RANGE = 0.05, 0.05
C_SHIPPED = 0.8
MARCH_MAX = 40          # inward march cap when measuring local half-width
N_SIGMA = 48            # sigma grid for the alpha-excursion reconstruction
SIGMA_LOCAL = 40.0      # "local" sigma cap: blur still carries geometry here
N_NULL = 20             # shuffles for the T4 null distribution
SEED = 8781

# ---- registered bars -------------------------------------------------------
T1_THIN, T1_BROAD = 1.5, 4.0        # median half-width, px
T2_REFUTE, T2_CONFIRM = 0.05, 0.25  # relative difference in observation count
T3_REJECT, T3_REFUTE = 0.33, 0.67   # pass_thin / pass_broad
T4_POINTS = 10.0                    # dISO_thin - dISO_broad, percentage points
T4_REPRO = 0.5                      # C-T4-ALL must reproduce -28.16 within this
SPECKLE_MAX = 50                    # component size below which a blob is speckle

verdicts = {}


def branch(name, value, lo, hi, low_label, mid_label, high_label):
    """Three-branch verdict. Every bar in this file has a meaning below 1."""
    v = low_label if value < lo else (high_label if value > hi else mid_label)
    verdicts[name] = {"value": float(value), "lo": lo, "hi": hi, "verdict": v}
    print(f"  [{name}] {value:+.4f}  ->  {v}", flush=True)
    return v


def halfwidth_map(mask):
    """Local half-width of the foreground: EDT measured INSIDE the mask."""
    return ndi.distance_transform_edt(mask).astype(np.float32)


def march_width(hw, pts, nrm, steps=MARCH_MAX):
    """Local half-width of the structure each boundary point sits on.

    March inward along -normal and take the running max of the interior EDT.
    On a thin limb the march exits the other side and the max is the limb's
    half-width; on a bulky body the max is censored at `steps`.
    """
    h, w = hw.shape
    best = np.zeros(len(pts), np.float32)
    for t in range(steps + 1):
        y = np.clip(pts[:, 0] - t * nrm[:, 0], 0, h - 1)
        x = np.clip(pts[:, 1] - t * nrm[:, 1], 0, w - 1)
        best = np.maximum(best, M2._bilinear(hw, y, x).astype(np.float32))
    return best


def t1_flowers(res):
    print("\n--- T1 morphology of the boundary population (flowers-cpl) ---",
          flush=True)
    import tifffile
    idx = tifffile.imread(str(FLOWERS_IDX))
    hi = int(idx.max())
    m0, mhi = (idx == 0), (idx == hi)
    bnd = m0 | mhi
    print(f"  index map {idx.shape} {idx.dtype}  frames 0..{hi}", flush=True)
    print(f"  elect frame 0 {100 * m0.mean():.4f}%   frame {hi} "
          f"{100 * mhi.mean():.4f}%   boundary {100 * bnd.mean():.4f}%",
          flush=True)

    hw = halfwidth_map(bnd)
    wid = hw[bnd]
    q = np.percentile(wid, [10, 25, 50, 75, 90])
    print(f"  half-width px: p10 {q[0]:.2f}  p25 {q[1]:.2f}  median {q[2]:.2f} "
          f"  p75 {q[3]:.2f}  p90 {q[4]:.2f}", flush=True)
    fr = {f"le{t}": float((wid <= t).mean()) for t in (1, 2, 4, 8, 16)}
    print("  fraction of the population at half-width <= "
          + "  ".join(f"{t}px {100 * fr[f'le{t}']:.1f}%" for t in (1, 2, 4, 8, 16)),
          flush=True)

    lab, nlab = ndi.label(bnd)
    sizes = np.bincount(lab.ravel())[1:]
    big = sizes.max()
    speckle = float(sizes[sizes < SPECKLE_MAX].sum() / sizes.sum())
    print(f"  {nlab} components; largest holds "
          f"{100 * big / sizes.sum():.2f}% of the population; "
          f"{100 * speckle:.2f}% lies in components < {SPECKLE_MAX}px",
          flush=True)

    res["T1"] = {"frame0": float(m0.mean()), "framehi": float(mhi.mean()),
                 "boundary": float(bnd.mean()), "p10": float(q[0]),
                 "p25": float(q[1]), "median": float(q[2]), "p75": float(q[3]),
                 "p90": float(q[4]), "frac": fr, "n_components": int(nlab),
                 "largest_share": float(big / sizes.sum()), "speckle": speckle}
    branch("T1 median half-width", q[2], T1_THIN, T1_BROAD,
           "THIN CONTOURS (ORCH's reading)", "MIXED",
           "BROAD -- ORCH's contour reading is not what the operand says")

    # discipline 677: render the map, do not report only scalars.
    try:
        from PIL import Image
        s = 4
        sub = bnd[::s, ::s]
        subw = hw[::s, ::s]
        rgb = np.zeros(sub.shape + (3,), np.uint8)
        rgb[..., 0] = np.where(sub, 255, 30)
        thin = sub & (subw <= 2)
        rgb[thin] = (255, 255, 0)
        broad = sub & (subw >= 8)
        rgb[broad] = (0, 128, 255)
        SCRATCH.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb).save(SCRATCH / "81-flowers-width.png")
        print(f"  wrote {SCRATCH / '81-flowers-width.png'} "
              f"(yellow <=2px, blue >=8px, red mid)", flush=True)
    except Exception as e:  # pragma: no cover
        print(f"  map render skipped: {e}", flush=True)


def main():
    res = {}
    t1_flowers(res)

    print("\n--- loading the bee cube ---", flush=True)
    lumas = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    mask = np.load(CACHE / "bee3-leg-mask.npy")
    sel = np.load(CACHE / "bee3-leg-sel.npy")
    fixed = np.load(CACHE / f"17-fixed-c{C_SHIPPED}.npy")
    n, h, w = lumas.shape
    matte = mask.astype(np.float32)

    pts, nrm = M2.boundary_normals(mask, roi=INNER)
    val = M2.valid_profiles(mask, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    print(f"  {len(p)} valid boundary points", flush=True)

    # normals must point OUTWARD for the inward march to be inward.
    inside = M2._bilinear(matte, p[:, 0] - 3 * nv[:, 0], p[:, 1] - 3 * nv[:, 1])
    outside = M2._bilinear(matte, p[:, 0] + 3 * nv[:, 0], p[:, 1] + 3 * nv[:, 1])
    print(f"  C-NORMAL: matte 3px inward {inside.mean():.3f}, "
          f"3px outward {outside.mean():.3f}", flush=True)
    assert inside.mean() > outside.mean(), "normals are not outward-pointing"

    hw_in = halfwidth_map(mask)
    wid = march_width(hw_in, p, nv)
    qs = np.percentile(wid, [25, 75])
    thin_p, broad_p = wid <= qs[0], wid >= qs[1]
    print(f"  boundary-point half-width: p25 {qs[0]:.2f}px  p75 {qs[1]:.2f}px "
          f" -> {thin_p.sum()} thin / {broad_p.sum()} broad points", flush=True)

    dist = ndi.distance_transform_edt(~mask).astype(np.float32)
    inner = np.zeros(mask.shape, bool)
    inner[INNER[0]:INNER[1], INNER[2]:INNER[3]] = True
    band = inner & (~mask) & (dist >= 2) & (dist <= 40)

    # ---- T2 pixel-count support -------------------------------------------
    print("\n--- T2 can contour geometry starve this fit by pixel count? ---",
          flush=True)
    # Propagate the BOUNDARY-POINT widths outward, so T2/T3 partition the band
    # by the same quantity T4 partitions the boundary by.
    #
    # The obvious shortcut -- nearest foreground pixel via
    # distance_transform_edt(~mask, return_indices=True), then read hw_in there
    # -- is WRONG and silently degenerate: the nearest foreground pixel to a
    # background pixel always lies ON the boundary, where the interior EDT is
    # ~1. It returned p25 = p75 = 1.0, i.e. no partition at all.
    bpt = np.zeros(mask.shape, bool)
    yi = np.clip(np.round(p[:, 0]).astype(int), 0, h - 1)
    xi = np.clip(np.round(p[:, 1]).astype(int), 0, w - 1)
    bpt[yi, xi] = True
    wimg = np.zeros(mask.shape, np.float32)
    wimg[yi, xi] = wid
    _, (jy, jx) = ndi.distance_transform_edt(~bpt, return_indices=True)
    band_w = wimg[jy, jx][band]
    tw, bw = np.percentile(band_w, [25, 75])
    print(f"  band pixels inherit the nearest boundary point's half-width: "
          f"p25 {tw:.2f}px  p75 {bw:.2f}px", flush=True)
    assert bw - tw > 1.0, "the band partition is degenerate"
    obs = np.zeros(band.sum(), np.float64)
    for k in range(0, n, 8):                # every 8th frame: count is per-pixel
        obs += np.isfinite(np.asarray(lumas[k], np.float32)[band])
    n_thin = float(obs[band_w <= tw].mean())
    n_broad = float(obs[band_w >= bw].mean())
    rel = abs(n_thin - n_broad) / max(n_broad, 1e-9)
    print(f"  finite observations per pixel: thin {n_thin:.3f}  "
          f"broad {n_broad:.3f}", flush=True)
    res["T2"] = {"n_thin": n_thin, "n_broad": n_broad, "rel": rel,
                 "thin_w": float(tw), "broad_w": float(bw)}
    branch("T2 observation-count gap", rel, T2_REFUTE, T2_CONFIRM,
           "pixel-count starvation REFUTED", "PARTIAL",
           "pixel-count starvation CONFIRMED")

    # ---- T3 alpha excursion and the admission gate -------------------------
    print("\n--- T3 does the alpha gate reject thin structures? ---", flush=True)
    smax = C_SHIPPED * (n - 1)
    print(f"  shipped c={C_SHIPPED} implies sigma up to {smax:.0f}px on a "
          f"{h}x{w} ROI", flush=True)
    res["T3"] = {}
    for tag, cap in (("full", smax), ("local", SIGMA_LOCAL)):
        grid = np.concatenate([[0.0], np.geomspace(0.3, cap, N_SIGMA - 1)])
        amax = np.zeros((h, w), np.float32)
        amin = np.ones((h, w), np.float32)
        for s in grid:
            a = ndi.gaussian_filter(matte, s) if s > 0.3 else matte
            np.maximum(amax, a, out=amax)
            np.minimum(amin, a, out=amin)
        gate = (~mask) & (amax >= A_MIN) & ((amax - amin) >= A_RANGE)
        cover = float(gate[band].mean())
        at, ab = amax[band][band_w <= tw], amax[band][band_w >= bw]
        allb = amax[band]
        iqr = float(np.percentile(allb, 75) - np.percentile(allb, 25))
        # diagnose the PARTITION, not only the statistic: two subsets returning
        # the same median is uninformative if the partition itself is degenerate.
        sep = float(np.median(ab) - np.median(at))
        pt, pb = float(gate[band][band_w <= tw].mean()), \
            float(gate[band][band_w >= bw].mean())
        ratio = pt / max(pb, 1e-9)
        print(f"\n  sigma <= {cap:.0f}px: alpha-gate coverage of the band "
              f"{100 * cover:.2f}%  (recorded gate, with R^2: 19.8%)", flush=True)
        print(f"    gate pass: thin {100 * pt:.2f}%  broad {100 * pb:.2f}%   "
              f"median amax: thin {np.median(at):.4f}  broad {np.median(ab):.4f}",
              flush=True)
        print(f"    amax over the band: IQR {iqr:.6f}; broad minus thin median "
              f"{sep:+.6f}", flush=True)
        res["T3"][tag] = {"cap": float(cap), "coverage": cover, "pass_thin": pt,
                          "pass_broad": pb, "ratio": ratio,
                          "amax_iqr": iqr, "amax_sep": sep,
                          "amax_thin": float(np.median(at)),
                          "amax_broad": float(np.median(ab))}
        # three-branch, per discipline 676: "far too high" must have a meaning.
        cv = branch(f"C-T3-COVER {tag}", cover, 0.198, 0.60,
                    "BROKEN: the reconstruction is not a superset of the "
                    "recorded gate", "plausible",
                    "DEGENERATE: the alpha gate is non-binding, so it cannot "
                    "be what rejects anything")
        if cv == "plausible":
            branch(f"T3 gate pass ratio thin/broad ({tag})", ratio,
                   T3_REJECT, T3_REFUTE,
                   "the gate REJECTS the thin population (ORCH's mechanism)",
                   "PARTIAL",
                   "the gate does NOT reject thin structures -- REFUTED")
        else:
            verdicts[f"T3 gate pass ratio thin/broad ({tag})"] = {
                "verdict": f"VOID -- coverage control says {cv}"}
            print(f"    T3/{tag} VOID: {cv}", flush=True)

    # ---- T4 the re-score the orchestrator asked for -------------------------
    print("\n--- T4 does -28.16% move when restricted to thin structures? ---",
          flush=True)

    def d_iso(sub, tag, boot=500, quiet=False):
        b = M2.score_iso(sel, p[sub], nv[sub], boot=boot)
        f = M2.score_iso(fixed, p[sub], nv[sub], boot=boot)
        d = 100.0 * (f["ISO"] / b["ISO"] - 1.0)
        if not quiet:
            print(f"  {tag:<28} n={int(sub.sum()):>5}  F0 {b['ISO']:.5f}  "
                  f"fixed {f['ISO']:.5f}  dISO {d:+.2f}%  "
                  f"absolute {f['ISO'] - b['ISO']:+.5f}", flush=True)
        return {"n": int(sub.sum()), "F0": b["ISO"], "fixed": f["ISO"],
                "dISO": d, "abs": f["ISO"] - b["ISO"]}

    allp = np.ones(len(p), bool)
    r_all = d_iso(allp, "ALL points (C-T4-ALL)")
    repro = abs(r_all["dISO"] - (-28.16))
    a_ok = repro <= T4_REPRO
    print(f"  C-T4-ALL: reproduces the shipped -28.16% to {repro:.2f} points "
          f"-> {'PASS' if a_ok else 'FAIL -- T4 IS VOID'}", flush=True)

    r_thin = d_iso(thin_p, "THIN quartile (limbs)")
    r_broad = d_iso(broad_p, "BROAD quartile (bulk)")
    gap = r_thin["dISO"] - r_broad["dISO"]

    # A single shuffle is one draw, not a null. Take a distribution.
    rng = np.random.default_rng(SEED)
    ngaps = []
    for _ in range(N_NULL):
        perm = rng.permutation(len(p))
        a = d_iso(thin_p[perm], "", boot=0, quiet=True)["dISO"]
        b = d_iso(broad_p[perm], "", boot=0, quiet=True)["dISO"]
        ngaps.append(a - b)
    ngaps = np.array(ngaps)
    n95 = float(np.percentile(np.abs(ngaps), 95))
    n_ok = n95 <= T4_POINTS
    print(f"  C-T4-NULL: {N_NULL} shuffles, gap mean {ngaps.mean():+.2f}  "
          f"sd {ngaps.std():.2f}  p95|gap| {n95:.2f} points -> "
          f"{'PASS' if n_ok else 'FAIL'}", flush=True)
    print(f"  observed gap is {abs(gap) / max(ngaps.std(), 1e-9):.1f} null "
          f"standard deviations", flush=True)

    res["T4"] = {"all": r_all, "thin": r_thin, "broad": r_broad, "gap": gap,
                 "null_mean": float(ngaps.mean()), "null_sd": float(ngaps.std()),
                 "null_p95": n95, "n_null": N_NULL,
                 "z": float(abs(gap) / max(ngaps.std(), 1e-9)),
                 "all_ok": bool(a_ok), "null_ok": bool(n_ok), "repro": repro,
                 "thin_w_max": float(qs[0]), "broad_w_min": float(qs[1])}
    if a_ok and n_ok:
        branch("T4 thin minus broad (points)", gap, -T4_POINTS, T4_POINTS,
               "the unmix does BETTER on thin contours", "NO STRUCTURE DEPENDENCE",
               "the unmix does WORSE on thin contours (ORCH's prediction)")
    else:
        verdicts["T4 thin minus broad (points)"] = {"verdict": "VOID"}
        print("  T4 VOID: a registered control failed", flush=True)

    res["verdicts"] = verdicts
    print("\n" + "=" * 74 + "\n=== VERDICT ===", flush=True)
    for k, v in verdicts.items():
        print(f"  {k}: {v['verdict']}", flush=True)
    DATA.mkdir(exist_ok=True)
    json.dump(res, open(DATA / "81-contour-support.json", "w"), indent=1,
              default=float)
    print(f"\nwrote {DATA / '81-contour-support.json'}", flush=True)


if __name__ == "__main__":
    main()

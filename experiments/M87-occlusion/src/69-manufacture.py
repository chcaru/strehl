"""M87 / 69 -- no motion, a repaired third instrument, and the overshoot the
merge manufactures.

WHAT STEP 68 ESTABLISHED, AND THE THREE THINGS IT LEFT OPEN.

(a) H1's registered falsifier fired: all 24 tiles of ROI_LEG return EXACTLY
    (0,0) between frame 0 and frame 298, while the same instrument recovers a
    planted 1.010 scale as 0.00901 (R^2 = 0.9904) and step 67's G1 recovered a
    planted (13,-21) translation exactly.  The cube is unaligned raw -- 04
    builds it with `L.read_planes(p, BOX)` at a FIXED box, no warp -- so zero is
    a measurement of the raw frames.  OPEN: 24 tiles of one frame pair, with
    correlation peaks of only 0.05-0.11, is thin evidence for a claim this
    consequential.  Harden it or withdraw it.

(b) H2 explained G2's dead control: 32.83% of the analysis window's BORDER is
    dark class, so the windowed centroid is pinned by the window.  The repair
    works -- a border-free component of 8009 px moved 38.02 px for a planted 40.
    OPEN: run the repaired instrument over all 299 frames and get the number.
    This matters because step 35's 63.04 px used the pinned version.

(c) H3's registered prediction FAILED, in the informative direction.  The linear
    radial profile is NOT monotone: it rises 10280 (d=1) -> 13720 (d=20), DIPS
    to 13564 (d=25), and only then resumes to 16659 at d=200.  There is an
    interior local maximum at d = 17, and its location coincides with the d~21
    reach of the dR band measured in step 65.  But the bump is worth only ~1.2%
    over the local floor while the ramp from d=1 to d=120 is ~47%, which is why
    a difference-from-baseline metric reads +0.280% here.
    OPEN, AND THIS IS THE ONE THAT MATTERS: is that bump in the DATA, or does
    the merge make it?  A veil is present in every frame, so a monotone rise is
    expected from physics alone; a local maximum with a dip beyond it is not.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

J1 -- HARDENING THE NO-MOTION CLAIM.  Tile-estimate five frame pairs spanning
    the sweep (0-75, 0-150, 0-224, 0-298, 140-160), and for each pair run a
    PAIRED positive control that plants (+5, -7) on the second frame.
    REGISTERED: the claim "no image motion in ROI_LEG" is established only if,
    for every pair, >= 80% of tiles return (0,0) as-is AND >= 80% recover the
    plant exactly.  If the planted arm does not recover, the instrument is weak
    on this content and the zero means nothing -- I withdraw the claim.

J2 -- THE REPAIRED CENTROID, ALL 299 FRAMES.  Track the border-free dark
    component identified in step 68 across the sweep by overlap.
    REGISTERED: I predict its peak-to-peak excursion is < 10 px, i.e. it
    CONFIRMS the tile estimator rather than step 35's 63.04 px.  If instead it
    reproduces ~63 px, the tile estimator is somehow blind on real content
    despite two passing plants, and I have a genuine three-way conflict to
    report unresolved.

J3 -- DOES THE MERGE MANUFACTURE THE OVERSHOOT?  Everything in linear raw DN
    from one cube, one mask, one distance field, so nothing is cross-scale.
    Define, per image, the overshoot statistic
        O = ( median profile over d in [12,22] - median profile over d in [30,45] )
            / median profile over d in [80,120]
    O > 0 means the profile has a local bump inside 22 px that decays beyond it.
    Compute O for the gate-0 selection merge and for each of the 299 single
    frames.
    REGISTERED PREDICTION: O(merge) > 0, and O(merge) exceeds O of EVERY single
    frame.  That is the same form as step 63's C-FRAME and it is falsifiable in
    one number.
    REGISTERED FALSIFIER: if any single frame matches or exceeds the merge, the
    bump is in the data and the merge only selects it, and my "the merge
    manufactures the halo" claim does not extend to the linear profile.
    C-SHUFO: recompute O for a merge built by electing a UNIFORMLY RANDOM frame
    per pixel.  A random merge must land inside the single-frame range; if the
    random merge also beats every single frame, O is measuring "any per-pixel
    mixture" rather than "this election", and the arm is void.

READ-ONLY: D:\\personal\\macro.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt, label, uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

GRID = (4, 6)
PAIRS = [(0, 75), (0, 150), (0, 224), (0, 298), (140, 160)]
PLANT = (5, -7)
BAND_IN = (12, 22)
BAND_OUT = (30, 45)
FAR = (80, 120)


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def est(a, b):
    h, w = a.shape
    aa = a - uniform_filter(a, 31)
    bb = b - uniform_filter(b, 31)
    cps = np.fft.rfft2(aa) * np.conj(np.fft.rfft2(bb))
    cps /= np.maximum(np.abs(cps), 1e-9)
    c = np.fft.irfft2(cps, s=(h, w))
    p = np.unravel_index(int(np.argmax(c)), c.shape)
    return (int(p[0] if p[0] <= h // 2 else p[0] - h),
            int(p[1] if p[1] <= w // 2 else p[1] - w))


def tiles(a, b):
    h, w = a.shape
    th, tw = h // GRID[0], w // GRID[1]
    out = []
    for i in range(GRID[0]):
        for j in range(GRID[1]):
            ys, xs = i * th, j * tw
            out.append(est(a[ys:ys + th, xs:xs + tw].astype(np.float32),
                           b[ys:ys + th, xs:xs + tw].astype(np.float32)))
    return out


def main():
    t0 = time.time()
    rep = {}
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    n, h, w = cube.shape

    # ---------------------------------------------------------------------- J1
    print("=== J1: five frame pairs, each with a paired plant ===", flush=True)
    j1 = {}
    allok = True
    for a, b in PAIRS:
        fa = np.asarray(cube[a], dtype=np.float32)
        fb = np.asarray(cube[b], dtype=np.float32)
        asis = tiles(fa, fb)
        pl = tiles(fa, np.roll(fb, PLANT, axis=(0, 1)))
        exp = (-PLANT[0], -PLANT[1])
        z = sum(1 for s in asis if s == (0, 0))
        r = sum(1 for s in pl if s == exp)
        ok = z >= 0.8 * len(asis) and r >= 0.8 * len(pl)
        allok &= ok
        print(f"  frames {a:3d} vs {b:3d}:  as-is zero in {z:2d}/{len(asis)} tiles; "
              f"plant {PLANT} recovered in {r:2d}/{len(pl)}  -> {'OK' if ok else 'WEAK'}",
              flush=True)
        if z < len(asis):
            nzs = [s for s in asis if s != (0, 0)]
            print(f"      non-zero tiles: {nzs}", flush=True)
        j1[f"{a}-{b}"] = {"zero": z, "recovered": r, "n": len(asis), "ok": bool(ok),
                          "nonzero": [list(s) for s in asis if s != (0, 0)]}
    print(f"  J1 -> {'no image motion in ROI_LEG, established on 5 pairs with paired plants' if allok else 'NOT established; claim withdrawn'}",
          flush=True)
    rep["J1"] = {"pairs": j1, "established": bool(allok), "plant": list(PLANT)}

    # ---------------------------------------------------------------------- J2
    print("\n=== J2: repaired border-free centroid, all 299 frames ===", flush=True)
    _, tau = L.foreground_mask(sel0)
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1
    y0, y1, x0, x1 = M, M + 700, M, M + 1100
    ref = np.asarray(cube[0], dtype=np.float32)[y0:y1, x0:x1] < tau
    lab0, n0 = label(ref)
    sz = np.bincount(lab0.ravel())
    sz[0] = 0
    touch = set(np.unique(np.concatenate([lab0[0], lab0[-1], lab0[:, 0], lab0[:, -1]])))
    free = [i for i in range(1, n0 + 1) if i not in touch and sz[i] > 2000]
    comp = lab0 == max(free, key=lambda i: sz[i])
    cy, cx, ok_f = [], [], 0
    for k in range(n):
        m = np.asarray(cube[k], dtype=np.float32)[y0:y1, x0:x1] < tau
        lk, nk = label(m)
        ov = np.bincount(lk[comp], minlength=nk + 1)
        ov[0] = 0
        if ov.max() < 500:
            cy.append(np.nan)
            cx.append(np.nan)
            continue
        yy, xx = np.nonzero(lk == int(np.argmax(ov)))
        if yy.min() == 0 or xx.min() == 0 or yy.max() == 699 or xx.max() == 1099:
            cy.append(np.nan)
            cx.append(np.nan)
            continue
        cy.append(yy.mean())
        cx.append(xx.mean())
        ok_f += 1
    cy, cx = np.array(cy), np.array(cx)
    pp = float(np.hypot(np.nanmax(cy) - np.nanmin(cy), np.nanmax(cx) - np.nanmin(cx)))
    print(f"  tracked in {ok_f}/{n} frames (border-free and >=500 px overlap)", flush=True)
    print(f"  excursion = {pp:.2f} px p-p   (step 35 pinned version: 63.04, "
          f"warpmap: 70.97, tiles: 0.00)", flush=True)
    print(f"  J2 -> {'CONFIRMS the tile estimator' if pp < 10 else 'does NOT confirm; three-way conflict stands'}",
          flush=True)
    rep["J2"] = {"tracked": ok_f, "n": n, "pp_px": pp, "confirms_tiles": bool(pp < 10),
                 "cy": [None if not np.isfinite(v) else round(float(v), 2) for v in cy],
                 "cx": [None if not np.isfinite(v) else round(float(v), 2) for v in cx]}

    # ---------------------------------------------------------------------- J3
    print("\n=== J3: does the merge manufacture the interior overshoot? ===", flush=True)
    fmask, _ = L.foreground_mask(sel0)
    do = distance_transform_edt(~fmask)
    dd = np.rint(do).astype(np.int32)
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

    def O(img):
        p = prof(img)
        i = np.nanmedian(p[BAND_IN[0]:BAND_IN[1] + 1])
        o = np.nanmedian(p[BAND_OUT[0]:BAND_OUT[1] + 1])
        f = np.nanmedian(p[FAR[0]:FAR[1] + 1])
        return float((i - o) / f), i, o, f

    Om, i_, o_, f_ = O(sel0)
    print(f"  merge (gate 0): in[{BAND_IN}]={i_:.1f}  out[{BAND_OUT}]={o_:.1f}  "
          f"far[{FAR}]={f_:.1f}   O = {Om:+.6f}", flush=True)
    Os = np.empty(n)
    for k in range(n):
        Os[k], *_ = O(np.asarray(cube[k], dtype=np.float32))
        if k % 60 == 0:
            print(f"    frame {k}: O = {Os[k]:+.6f}", flush=True)
    kmax = int(np.argmax(Os))
    print(f"  single frames: mean {Os.mean():+.6f}  sd {Os.std(ddof=1):.6f}  "
          f"max {Os[kmax]:+.6f} (frame {kmax})  min {Os.min():+.6f}", flush=True)
    print(f"  frames with O > 0: {int((Os > 0).sum())}/{n}", flush=True)
    beats = bool(Om > 0 and Om > Os.max())
    marg = (Om - Os.max()) / max(Os.std(ddof=1), 1e-12)
    print(f"  merge exceeds the best single frame by {Om - Os.max():+.6f} "
          f"= {marg:.2f} single-frame sd", flush=True)
    print(f"  J3 -> {'PASS: the merge manufactures the overshoot' if beats else 'FALSIFIED: the bump is in the data'}",
          flush=True)

    rng = np.random.default_rng(8701)
    ridx = rng.integers(0, n, size=(h, w))
    rnd = np.take_along_axis(np.asarray(cube), ridx[None], axis=0)[0]
    Or, *_ = O(rnd)
    void = bool(Or > Os.max())
    print(f"  C-SHUFO: uniformly random per-pixel merge -> O = {Or:+.6f}  "
          f"({'INSIDE' if not void else 'OUTSIDE'} the single-frame range)", flush=True)
    print(f"  C-SHUFO -> {'arm VOID: O responds to any mixture' if void else 'arm stands: O responds to THIS election'}",
          flush=True)
    rep["J3"] = {"O_merge": Om, "in": i_, "out": o_, "far": f_,
                 "O_frames_mean": float(Os.mean()), "O_frames_sd": float(Os.std(ddof=1)),
                 "O_frames_max": float(Os.max()), "O_frames_argmax": kmax,
                 "O_frames_min": float(Os.min()), "n_pos": int((Os > 0).sum()),
                 "beats_all": beats, "margin_sd": float(marg), "O_random": Or,
                 "control_void": void,
                 "O_frames": [round(float(v), 6) for v in Os]}

    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "69-manufacture.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '69-manufacture.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()

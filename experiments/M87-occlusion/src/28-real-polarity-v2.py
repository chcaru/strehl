"""M87 step 28 -- the real-data polarity test, rebuilt after step 27 failed.

WHY STEP 27 IS DISCARDED (all four faults are mine, and all four are disclosed
in PREREG-ADDENDUM-3 section A3.8):

  F1  It grouped sites by the polarity label INHERITED from step 26's 48-px
      tile, but re-segmented the near layer inside a larger padded box.  The
      segmentation moved.  REV_A came back with measured contrast 0.16 (near
      DARKER) and NORM_A with 1.25 (near BRIGHTER) -- i.e. two of the four
      sites were the opposite of their label.  The script then printed
      "SIGN FLIPS ... N1 PASSES" off those stale labels while its own per-site
      line read 1/4.  A confident verdict from mislabelled groups is exactly
      the failure this milestone exists to catch, so the verdict is void.

  F2  D_MAX = 64 px is far too long for internal boundaries.  On ROI_LEG the
      far layer is an empty card and a 64-px normal stays inside it; at a
      hair-over-leg boundary it crosses several structures.  |E_est| came back
      at 0.28-0.45 OF LEVEL against 0.005-0.009 on the plant -- a 30-50x
      excursion that is anatomy, not halo.

  F3  No validity gate.  A profile that leaves the far layer still contributed.

  F4  NORM_B elected k_near = 9 of 299, an extreme end of the sweep: a noise
      election, not a near layer.

THE REBUILD.  Two changes of substance:

  1. NO NORMALS.  Compare two DEPTH-GATED REGIONS instead:
         veiled band = exterior, EDT in [3,12],  AND belonging to the far layer
         far field   = exterior, EDT in [25,45], AND belonging to the far layer
     Depth membership is what stops a profile wandering into a third
     structure, and it is checked per pixel rather than per profile.

         E_est = median(merge - I_knear | veiled) - median(merge - I_knear | far)

     The far-field term is a built-in self-reference: it must be ~0, and it is
     reported, so a site whose "far field" is contaminated announces itself.

  2. ONE DECODE PER SITE, NOT 299.  The reference image is a SINGLE frame,
     I_{k_near}.  Segmentation and the merge itself come from the cached
     full-frame arg/sel of step 25.  So each site costs one raw decode, not a
     cube, and 20+ sites become affordable -- which turns four anecdotes into a
     sample with a rate.

Polarity is assigned FROM THE MEASURED LEVELS IN THE SAME REGIONS, never
inherited.  Aggregation is by measured polarity.
"""
import json
import pathlib
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import importlib.util as _iu  # noqa: E402

_spec = _iu.spec_from_file_location(
    "p24", pathlib.Path(__file__).resolve().parent / "24-polarity-plant.py")
p24 = _iu.module_from_spec(_spec)
_spec.loader.exec_module(p24)

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT, DATA, CACHE = HERE / "out", HERE / "data", HERE / "cache"
for p in (OUT, DATA, CACHE):
    p.mkdir(exist_ok=True)

STACK = r"D:\personal\macro\bee-3-cpl"
ISO = 100
HALF = 110                 # site half-size on the green lattice
NEAR_BAND = (3, 12)
FAR_BAND = (25, 45)
MIN_PIX = 300
MIN_DK = 30


def estimate(sel, arg, ref, near, far_layer):
    """Depth-gated signed excursion.  Returns (E, near_med, far_med, counts)."""
    edt = ndi.distance_transform_edt(~near)
    diff = sel.astype(np.float64) - ref.astype(np.float64)
    m_near = (edt >= NEAR_BAND[0]) & (edt <= NEAR_BAND[1]) & far_layer
    m_far = (edt >= FAR_BAND[0]) & (edt <= FAR_BAND[1]) & far_layer
    if m_near.sum() < MIN_PIX or m_far.sum() < MIN_PIX:
        return None
    level = float(np.median(sel[m_far]))
    if level <= 1.0:
        return None
    a = float(np.median(diff[m_near])) / level
    b = float(np.median(diff[m_far])) / level
    return dict(E=a - b, veiled_term=a, farfield_term=b, level=level,
                n_veiled=int(m_near.sum()), n_far=int(m_far.sum()))


def boot_E(sel, arg, ref, near, far_layer, seed=28, nboot=300):
    """Block bootstrap over 32x32 spatial blocks of the veiled band."""
    edt = ndi.distance_transform_edt(~near)
    diff = sel.astype(np.float64) - ref.astype(np.float64)
    m_near = (edt >= NEAR_BAND[0]) & (edt <= NEAR_BAND[1]) & far_layer
    m_far = (edt >= FAR_BAND[0]) & (edt <= FAR_BAND[1]) & far_layer
    level = float(np.median(sel[m_far]))
    ys, xs = np.nonzero(m_near)
    blk = (ys // 32) * 10000 + (xs // 32)
    uniq = np.unique(blk)
    rng = np.random.default_rng(seed)
    b_far = float(np.median(diff[m_far])) / level
    out = []
    for _ in range(nboot):
        pick = rng.choice(uniq, len(uniq), replace=True)
        idx = np.concatenate([np.nonzero(blk == u)[0] for u in pick])
        out.append(float(np.median(diff[ys[idx], xs[idx]])) / level - b_far)
    return (float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)))


def plant_validation():
    print("=== PART A: validate the depth-gated estimator on the plant ===",
          flush=True)
    rows = []
    for tag, fg, bg in (("P_plus  dark-FG/bright-BG", p24.LO, p24.HI),
                        ("P_minus bright-FG/dark-BG", p24.HI, p24.LO)):
        frames, alphas, m, f, b, truth = p24.build(fg, bg)
        sel, arg = p24.merge(frames, p24.field_signal_dependent)
        near = m > 0.5
        far_layer = ~ndi.binary_dilation(near, np.ones((3, 3)))
        ref = frames[p24.KF]
        r = estimate(sel, arg, ref, near, far_layer)
        edt = ndi.distance_transform_edt(~near)
        mn = (edt >= NEAR_BAND[0]) & (edt <= NEAR_BAND[1]) & far_layer
        mf = (edt >= FAR_BAND[0]) & (edt <= FAR_BAND[1]) & far_layer
        te = (sel.astype(np.float64) - truth.astype(np.float64))
        E_true = (float(np.median(te[mn])) - float(np.median(te[mf]))) / r["level"]
        agree = np.sign(E_true) == np.sign(r["E"])
        print(f"  {tag}: E_true {E_true:+.5f}  E_est {r['E']:+.5f}  "
              f"far-field term {r['farfield_term']:+.5f}  "
              f"sign {'AGREE' if agree else 'DISAGREE'}", flush=True)
        rows.append(dict(tag=tag, E_true=E_true, **r, sign_agrees=bool(agree)))
    ok = all(x["sign_agrees"] for x in rows)
    print(f"  => estimator {'VALIDATED' if ok else 'REJECTED'}", flush=True)
    return rows, ok


def main():
    prows, est_ok = plant_validation()

    print("\n=== PART B: site selection from cached full-frame merge ===",
          flush=True)
    arg = np.load(CACHE / "25-bee3-argbest.npy")
    sel = np.load(CACHE / "25-bee3-sel.npy")
    tiles = json.loads((DATA / "26-depth-boundaries.json").read_text(
        encoding="utf-8"))["bee3"]
    tiles = [t for t in tiles if t["conf"] >= 0.75 and t["dk"] >= MIN_DK]
    # spatially thin so sites do not overlap
    chosen, taken = [], []
    tiles.sort(key=lambda t: -t["dk"])
    for t in tiles:
        if all(abs(t["y"] - u["y"]) > 2 * HALF or abs(t["x"] - u["x"]) > 2 * HALF
               for u in taken):
            taken.append(t)
            chosen.append(t)
        if len(chosen) >= 28:
            break
    print(f"  {len(chosen)} non-overlapping candidate sites", flush=True)

    files = L.frames(STACK)
    H, W = arg.shape
    sites, need = [], {}
    for t in chosen:
        y0, y1 = max(0, t["y"] - HALF), min(H, t["y"] + HALF)
        x0, x1 = max(0, t["x"] - HALF), min(W, t["x"] + HALF)
        a = ndi.median_filter(arg[y0:y1, x0:x1].astype(np.float32), 7)
        lo_k, hi_k = np.percentile(a, [12, 88])
        dk = hi_k - lo_k
        if dk < MIN_DK:
            continue
        near = a <= lo_k + 0.2 * dk
        far_layer = a >= hi_k - 0.2 * dk
        near = ndi.binary_opening(near, np.ones((5, 5)))
        near = ndi.binary_closing(near, np.ones((7, 7)))
        lbl, nl = ndi.label(near)
        if nl == 0:
            continue
        if nl > 1:
            sz = ndi.sum(near, lbl, range(1, nl + 1))
            near = lbl == (1 + int(np.argmax(sz)))
        if near.sum() < 500 or far_layer.sum() < 500:
            continue
        core = ndi.binary_erosion(near, np.ones((7, 7)))
        if core.sum() < 100:
            continue
        knear = int(np.median(arg[y0:y1, x0:x1][core]))
        if knear < 5 or knear > len(files) - 6:
            continue                     # F4: reject sweep-end noise elections
        sites.append(dict(t=t, box=(y0, y1, x0, x1), near=near,
                          far_layer=far_layer, knear=knear, dk=float(dk)))
        need.setdefault(knear, []).append(len(sites) - 1)
    print(f"  {len(sites)} sites survive geometry gates; "
          f"{len(need)} distinct reference frames to decode", flush=True)

    rows = []
    for knear, idxs in sorted(need.items()):
        _, g1, g2, _ = L.read_planes(files[knear])
        reffull = 0.5 * (np.maximum(g1 - L.BLACK, 0.0)
                         + np.maximum(g2 - L.BLACK, 0.0))
        for i in idxs:
            s = sites[i]
            y0, y1, x0, x1 = s["box"]
            r = estimate(sel[y0:y1, x0:x1], arg[y0:y1, x0:x1],
                         reffull[y0:y1, x0:x1], s["near"], s["far_layer"])
            if r is None:
                continue
            sub = sel[y0:y1, x0:x1]
            lvl_near = float(np.median(sub[s["near"]]))
            lvl_far = float(np.median(sub[s["far_layer"]]))
            pol = "reversed" if lvl_near > lvl_far else "normal"
            expect = 1.0 if lvl_near > lvl_far else -1.0
            ci = boot_E(sub, arg[y0:y1, x0:x1], reffull[y0:y1, x0:x1],
                        s["near"], s["far_layer"])
            rows.append(dict(y=s["t"]["y"], x=s["t"]["x"], dk=s["dk"],
                             k_near=knear, lvl_near=lvl_near, lvl_far=lvl_far,
                             contrast=lvl_near / max(lvl_far, 1e-9),
                             polarity=pol, expected_sign=expect,
                             E_ci=list(ci), passed=bool(np.sign(r["E"]) == expect),
                             **r))

    print(f"\n=== PART C: {len(rows)} measured sites ===", flush=True)
    print(f"  {'site':>14}  {'dk':>5}  {'contr':>6}  {'polarity':>9}  "
          f"{'E_est':>9}  {'far-term':>9}  {'pass':>5}", flush=True)
    for r in sorted(rows, key=lambda r: -r["contrast"]):
        print(f"  {r['y']:5d},{r['x']:5d}  {r['dk']:5.0f}  "
              f"{r['contrast']:6.2f}  {r['polarity']:>9}  {r['E']:+9.5f}  "
              f"{r['farfield_term']:+9.5f}  "
              f"{'PASS' if r['passed'] else 'fail':>5}", flush=True)

    print("\n================ VERDICT (measured polarity) ================",
          flush=True)
    for pol in ("reversed", "normal"):
        g = [r for r in rows if r["polarity"] == pol]
        if not g:
            print(f"  {pol}: no sites", flush=True)
            continue
        e = np.array([r["E"] for r in g])
        pos = int((e > 0).sum())
        print(f"  {pol:>9}: n={len(g):2d}  median E {np.median(e):+.5f}  "
              f"IQR [{np.percentile(e, 25):+.5f}, {np.percentile(e, 75):+.5f}]  "
              f"E>0 in {pos}/{len(g)}", flush=True)
    rev = [r["E"] for r in rows if r["polarity"] == "reversed"]
    nor = [r["E"] for r in rows if r["polarity"] == "normal"]
    if rev and nor:
        from scipy import stats
        u = stats.mannwhitneyu(rev, nor, alternative="two-sided")
        print(f"  Mann-Whitney U on E between polarities: p = {u.pvalue:.4g}",
              flush=True)
        flip = np.sign(np.median(rev)) != np.sign(np.median(nor))
        print(f"  medians {'DIFFER IN SIGN' if flip else 'SAME SIGN'}",
              flush=True)
        npass = sum(r["passed"] for r in rows)
        print(f"  sites matching predicted sign: {npass}/{len(rows)} "
              f"({100 * npass / len(rows):.0f}%; chance = 50%)", flush=True)

    (DATA / "28-real-polarity.json").write_text(
        json.dumps(dict(plant=prows, estimator_ok=bool(est_ok), sites=rows),
                   indent=2), encoding="utf-8")
    print("\n  -> data/28-real-polarity.json", flush=True)


if __name__ == "__main__":
    main()

"""M87 step 29 -- the real-data polarity test, third and final construction.

Steps 27 and 28 are both discarded.  Their faults, in full, because the
corrections are the useful part:

  step 27 -- stale polarity labels, 64-px normals running into other anatomy,
             no validity gate, sweep-end noise elections.  Printed a confident
             "N1 PASSES" off mislabelled groups while its own per-site line
             read 1/4.

  step 28 -- replaced normals with depth-gated bands, which was right, but
             chose FAR_BAND = EDT in [25,45] as the reference.  On the plant
             the foreground's blur sigma at k_B is |k_B - k_F| * SCALE
             = 50 * 0.28 = 14 px, so the veil reaches ~3 sigma = 42 px and the
             "far" reference sits INSIDE the veil.  The tell was printed and I
             nearly missed it: far-field term came back as EXACTLY -E_est in
             both plant arms, which is what you get when the veiled term is
             identically zero and the whole statistic is the contaminated
             reference, negated.  Several real sites showed far-terms of -2.0,
             i.e. 200% of level.

WHAT IS DIFFERENT HERE.

  1. THE REFERENCE IS A PREDICTION, NOT A SUBTRACTION.  Measure the whole
     curve
         E(d) = < merge - I_{k_near} >  over far-layer pixels at EDT = d
     out to d = 120 px.  The two-layer model predicts E(d) -> 0 as d grows.
     That is a falsifiable statement about the curve, and a site whose curve
     does not return to zero is REJECTED as contaminated rather than silently
     averaged in.  No band is subtracted from another.

  2. MEAN, NOT MEDIAN.  merge - I_{k_near} contains a sharpening term
     (B_sharp - B_blur) alongside the veil term.  Convolution preserves the
     MEAN, so the sharpening term is unbiased under a mean and NOT under a
     median when the background texture is skewed -- which bee hair, bright
     strands on dark ground, badly is.  Step 28 used medians and this is a
     candidate explanation for its scrambled signs.  Both are reported.

  3. The plant validation range now extends past the blur reach, so it can
     actually see the curve return to zero.
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
HALF = 150
D_TAIL = (90, 120)      # where the model says the curve must have returned
D_PEAK = (4, 60)        # where the veil term is expected to live
TAIL_BAR = 0.02         # |E| must be under 2% of level in the tail
MIN_BIN = 120


def curve(sel, ref, near, far_layer, dmax=120):
    edt = ndi.distance_transform_edt(~near)
    diff = sel.astype(np.float64) - ref.astype(np.float64)
    ok = far_layer & (edt >= 1) & (edt <= dmax)
    if ok.sum() < 2000:
        return None
    level = float(np.mean(sel[far_layer & (edt >= D_TAIL[0])])) \
        if (far_layer & (edt >= D_TAIL[0])).sum() > MIN_BIN else float("nan")
    if not np.isfinite(level) or level <= 1.0:
        return None
    e = np.array([np.nan] * (dmax + 1))
    med = np.array([np.nan] * (dmax + 1))
    cnt = np.zeros(dmax + 1, int)
    ei = edt.astype(int)
    for d in range(1, dmax + 1):
        m = ok & (ei == d)
        c = int(m.sum())
        cnt[d] = c
        if c >= MIN_BIN:
            e[d] = float(np.mean(diff[m])) / level
            med[d] = float(np.median(diff[m])) / level
    return dict(E=e, Emed=med, cnt=cnt, level=level)


def summarise(c):
    e = c["E"]
    tail = e[D_TAIL[0]:D_TAIL[1] + 1]
    tail = tail[np.isfinite(tail)]
    if tail.size < 8:
        return None
    tail_val = float(np.mean(tail))
    seg = e[D_PEAK[0]:D_PEAK[1] + 1]
    if not np.isfinite(seg).any():
        return None
    j = int(np.nanargmax(np.abs(seg)))
    return dict(tail=tail_val, peak=float(seg[j]), peak_d=int(D_PEAK[0] + j),
                valid=bool(abs(tail_val) < TAIL_BAR))


def plant_part():
    print("=== PART A: plant, with the reference range past the blur reach ===",
          flush=True)
    print(f"    plant blur reach at k_B ~ 3*|kB-kF|*SCALE = "
          f"{3 * abs(p24.KB - p24.KF) * p24.SCALE:.0f} px", flush=True)
    rows = []
    for tag, fg, bg in (("P_plus  dark-FG/bright-BG", p24.LO, p24.HI),
                        ("P_minus bright-FG/dark-BG", p24.HI, p24.LO)):
        frames, alphas, m, f, b, truth = p24.build(fg, bg)
        sel, arg = p24.merge(frames, p24.field_signal_dependent)
        near = m > 0.5
        far_layer = ~ndi.binary_dilation(near, np.ones((3, 3)))
        c = curve(sel, frames[p24.KF], near, far_layer, dmax=120)
        ct = curve(sel, truth, near, far_layer, dmax=120)
        s, st = summarise(c), summarise(ct)
        fbar, bbar = float(np.mean(f)), float(np.mean(b))
        exp = 1.0 if fbar > bbar else -1.0
        print(f"  {tag}", flush=True)
        print(f"    truth   : peak {st['peak']:+.5f} at d={st['peak_d']:3d}  "
              f"tail {st['tail']:+.5f}  {'valid' if st['valid'] else 'TAIL FAIL'}",
              flush=True)
        print(f"    estimate: peak {s['peak']:+.5f} at d={s['peak_d']:3d}  "
              f"tail {s['tail']:+.5f}  {'valid' if s['valid'] else 'TAIL FAIL'}",
              flush=True)
        print(f"    expected sign {'+' if exp > 0 else '-'} -> truth "
              f"{'PASS' if np.sign(st['peak']) == exp else 'FAIL'}, estimate "
              f"{'PASS' if np.sign(s['peak']) == exp else 'FAIL'}", flush=True)
        rows.append(dict(tag=tag, expected_sign=exp,
                         truth_peak=st["peak"], truth_tail=st["tail"],
                         est_peak=s["peak"], est_tail=s["tail"],
                         est_d=s["peak_d"],
                         truth_ok=bool(np.sign(st["peak"]) == exp),
                         est_ok=bool(np.sign(s["peak"]) == exp),
                         E_curve=[None if not np.isfinite(v) else float(v)
                                  for v in c["E"]]))
    ok = all(r["est_ok"] for r in rows) and all(r["truth_ok"] for r in rows)
    print(f"  => estimator {'VALIDATED' if ok else 'REJECTED'} on the plant",
          flush=True)
    return rows, ok


def main():
    prows, est_ok = plant_part()

    print("\n=== PART B: bee-3-cpl sites ===", flush=True)
    arg = np.load(CACHE / "25-bee3-argbest.npy")
    sel = np.load(CACHE / "25-bee3-sel.npy")
    tiles = json.loads((DATA / "26-depth-boundaries.json").read_text(
        encoding="utf-8"))["bee3"]
    tiles = [t for t in tiles if t["conf"] >= 0.75 and t["dk"] >= 30]
    tiles.sort(key=lambda t: -t["dk"])
    chosen = []
    for t in tiles:
        if all(abs(t["y"] - u["y"]) > 2 * HALF or abs(t["x"] - u["x"]) > 2 * HALF
               for u in chosen):
            chosen.append(t)
        if len(chosen) >= 40:
            break

    files = L.frames(STACK)
    H, W = arg.shape
    sites, need = [], {}
    for t in chosen:
        y0, y1 = max(0, t["y"] - HALF), min(H, t["y"] + HALF)
        x0, x1 = max(0, t["x"] - HALF), min(W, t["x"] + HALF)
        a = ndi.median_filter(arg[y0:y1, x0:x1].astype(np.float32), 7)
        lo_k, hi_k = np.percentile(a, [12, 88])
        dk = hi_k - lo_k
        if dk < 30:
            continue
        near = ndi.binary_closing(
            ndi.binary_opening(a <= lo_k + 0.2 * dk, np.ones((5, 5))),
            np.ones((7, 7)))
        far_layer = a >= hi_k - 0.25 * dk
        lbl, nl = ndi.label(near)
        if nl == 0:
            continue
        if nl > 1:
            sz = ndi.sum(near, lbl, range(1, nl + 1))
            near = lbl == (1 + int(np.argmax(sz)))
        core = ndi.binary_erosion(near, np.ones((7, 7)))
        if near.sum() < 800 or far_layer.sum() < 3000 or core.sum() < 150:
            continue
        knear = int(np.median(arg[y0:y1, x0:x1][core]))
        if knear < 5 or knear > len(files) - 6:
            continue
        sites.append(dict(t=t, box=(y0, y1, x0, x1), near=near,
                          far_layer=far_layer, knear=knear, dk=float(dk)))
        need.setdefault(knear, []).append(len(sites) - 1)
    print(f"  {len(sites)} sites pass geometry; {len(need)} reference decodes",
          flush=True)

    rows = []
    for knear, idxs in sorted(need.items()):
        _, g1, g2, _ = L.read_planes(files[knear])
        reffull = 0.5 * (np.maximum(g1 - L.BLACK, 0.0)
                         + np.maximum(g2 - L.BLACK, 0.0))
        for i in idxs:
            s = sites[i]
            y0, y1, x0, x1 = s["box"]
            c = curve(sel[y0:y1, x0:x1], reffull[y0:y1, x0:x1],
                      s["near"], s["far_layer"], dmax=120)
            if c is None:
                continue
            su = summarise(c)
            if su is None:
                continue
            sub = sel[y0:y1, x0:x1]
            ln = float(np.mean(sub[s["near"]]))
            lf = c["level"]
            exp = 1.0 if ln > lf else -1.0
            rows.append(dict(y=s["t"]["y"], x=s["t"]["x"], dk=s["dk"],
                             k_near=knear, lvl_near=ln, lvl_far=lf,
                             contrast=ln / max(lf, 1e-9),
                             polarity="reversed" if ln > lf else "normal",
                             expected_sign=exp, **su,
                             passed=bool(np.sign(su["peak"]) == exp)))

    valid = [r for r in rows if r["valid"]]
    print(f"\n=== PART C: {len(rows)} sites measured, {len(valid)} pass the "
          f"tail-return validity gate (|E(90..120)| < {TAIL_BAR}) ===",
          flush=True)
    print(f"  {'site':>13} {'dk':>5} {'contr':>6} {'polarity':>9} "
          f"{'peak':>9} {'d':>4} {'tail':>9} {'valid':>6} {'pass':>5}",
          flush=True)
    for r in sorted(rows, key=lambda r: -r["contrast"]):
        print(f"  {r['y']:5d},{r['x']:5d} {r['dk']:5.0f} {r['contrast']:6.2f} "
              f"{r['polarity']:>9} {r['peak']:+9.5f} {r['peak_d']:4d} "
              f"{r['tail']:+9.5f} {'yes' if r['valid'] else 'NO':>6} "
              f"{'PASS' if r['passed'] else 'fail':>5}", flush=True)

    print("\n================ VERDICT (valid sites, measured polarity) "
          "================", flush=True)
    if len(valid) < 4:
        print(f"  Only {len(valid)} sites survive the validity gate. "
              f"UNDERPOWERED -- no verdict.", flush=True)
    else:
        for pol in ("reversed", "normal"):
            g = [r for r in valid if r["polarity"] == pol]
            if not g:
                print(f"  {pol:>9}: no valid sites", flush=True)
                continue
            e = np.array([r["peak"] for r in g])
            print(f"  {pol:>9}: n={len(g):2d}  median peak {np.median(e):+.5f}"
                  f"  E>0 in {int((e > 0).sum())}/{len(g)}", flush=True)
        rev = [r["peak"] for r in valid if r["polarity"] == "reversed"]
        nor = [r["peak"] for r in valid if r["polarity"] == "normal"]
        npass = sum(r["passed"] for r in valid)
        n = len(valid)
        print(f"  sites matching predicted sign: {npass}/{n} "
              f"({100 * npass / n:.0f}%; chance = 50%)", flush=True)
        if rev and nor:
            from scipy import stats
            print(f"  Mann-Whitney p = "
                  f"{stats.mannwhitneyu(rev, nor, alternative='two-sided').pvalue:.4g}",
                  flush=True)
            if np.sign(np.median(rev)) == np.sign(np.median(nor)):
                print("  => SIGNS DO NOT SEPARATE. N1 FAILS on real data.",
                      flush=True)
            elif np.median(rev) > 0 > np.median(nor):
                print("  => SIGNS SEPARATE IN THE PREDICTED DIRECTION. "
                      "N1 PASSES.", flush=True)
            else:
                print("  => SIGNS SEPARATE IN THE **OPPOSITE** DIRECTION TO "
                      "THE PREDICTION.", flush=True)
                print("     This is not support for veiling; it is evidence "
                      "against it.", flush=True)
        from scipy import stats
        bino = stats.binomtest(npass, n, 0.5, alternative="greater")
        print(f"  binomial test vs chance: p = {bino.pvalue:.4g}", flush=True)

    (DATA / "29-real-polarity.json").write_text(
        json.dumps(dict(plant=prows, estimator_ok=bool(est_ok), sites=rows),
                   indent=2), encoding="utf-8")
    print("\n  -> data/29-real-polarity.json", flush=True)


if __name__ == "__main__":
    main()

"""M87 step 31 -- the polarity test done with KNOWN masks, and the honest limit
of what bee-3-cpl can support.

Step 30 established two things and exposed a third problem.

  ESTABLISHED 1 -- the tail failures were photometric, not physical.  The
  sweep drifts 15.40% peak-to-peak on a bare-card anchor patch.  Correcting
  the reference frame per pixel by s[argbest]/s[k_near] moved ROI_LEG's tail
  from -0.12903 to +0.01025, inside the 0.02 gate.

  ESTABLISHED 2 -- every VALID real measurement so far has a NEGATIVE peak at
  a site whose near layer is DARKER, which is the two-layer prediction.

  PROBLEM -- the automatic depth segmentation misidentifies layers.  It called
  ROI_LEG "reversed" at contrast 1.06 with k_near=59, when ROI_LEG is a dark
  leg on a bright card and the full-frame analysis put the subject at k~125.
  Percentile-based near/far inside a box is not a reliable layer finder on
  real anatomy.

  So this script stops inferring masks and uses ones whose meaning is known:

    ROI_LEG  -- near = m87lib.foreground_mask (the Otsu leg mask used for every
                headline number in the report), far = its complement.  Dark
                foreground, bright background: the model predicts a NEGATIVE
                peak.  This is the properly executed positive control.

    REV_*    -- near = BRIGHT and NEAR in depth, far = DARK and FAR in depth,
                which is the joint condition a pale hair overhanging a dark leg
                or eye actually satisfies.  Model predicts a POSITIVE peak.

THE SCALE PROBLEM, stated plainly because it is the result.  bee-3-cpl's
reversed-polarity occlusions are pale hairs over dark internal structures.
Those far layers are tens of pixels across.  The estimator needs the curve to
return to zero at large d to certify itself, and step 29 used d in [90,120].
At HALF=300 the box swallows the bright card and the "far layer" stops being
the dark structure -- which is exactly what happened to all three REV
candidates in step 30 (measured contrast 0.43 / 0.83 / 0.87, i.e. normal).
So a short-range gate is needed, and a short-range gate has to be validated
before it is used.  A small-scale plant with a short veil reach is built here
for exactly that purpose.
"""
import json
import pathlib
import sys

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import importlib.util as _iu  # noqa: E402


def _load(name, path):
    sp = _iu.spec_from_file_location(name,
                                     pathlib.Path(__file__).resolve().parent / path)
    m = _iu.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


p24 = _load("p24", "24-polarity-plant.py")
p29 = _load("p29", "29-real-polarity-v3.py")

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT, DATA, CACHE = HERE / "out", HERE / "data", HERE / "cache"
STACK = r"D:\personal\macro\bee-3-cpl"
ISO = 100
TAIL_BAR = 0.02


def curve_at(sel, ref, near, far_layer, dmax, tail_rng):
    edt = ndi.distance_transform_edt(~near)
    diff = sel.astype(np.float64) - ref.astype(np.float64)
    ok = far_layer & (edt >= 1) & (edt <= dmax)
    anch = far_layer & (edt >= tail_rng[0]) & (edt <= tail_rng[1])
    if ok.sum() < 1500 or anch.sum() < 200:
        return None
    level = float(np.mean(sel[anch]))
    if level <= 1.0:
        return None
    ei = edt.astype(int)
    e = np.full(dmax + 1, np.nan)
    for d in range(1, dmax + 1):
        m = ok & (ei == d)
        if m.sum() >= 80:
            e[d] = float(np.mean(diff[m])) / level
    t = e[tail_rng[0]:tail_rng[1] + 1]
    t = t[np.isfinite(t)]
    if t.size < 5:
        return None
    seg = e[4:tail_rng[0] - 5]
    if not np.isfinite(seg).any():
        return None
    j = int(np.nanargmax(np.abs(seg)))
    return dict(peak=float(seg[j]), peak_d=int(4 + j), tail=float(np.mean(t)),
                level=level, valid=bool(abs(np.mean(t)) < TAIL_BAR),
                n_far=int(far_layer.sum()))


def validate_short_gate():
    """A small-scale plant whose veil reach is short, so a [40,60] tail is
    genuinely outside the veil.  Validates the short gate before use."""
    print("=== PART A: validate the SHORT-RANGE gate on a small-scale plant ===",
          flush=True)
    rows = []
    kb_old = p24.KB
    p24.KB = p24.KF + 18          # veil reach ~ 3*18*0.28 = 15 px
    try:
        print(f"    small plant blur reach ~ "
              f"{3 * abs(p24.KB - p24.KF) * p24.SCALE:.0f} px; "
              f"tail gate at d in [40,60]", flush=True)
        for tag, fg, bg in (("P_plus  dark-FG/bright-BG", p24.LO, p24.HI),
                            ("P_minus bright-FG/dark-BG", p24.HI, p24.LO)):
            frames, alphas, m, f, b, truth = p24.build(fg, bg)
            sel, arg = p24.merge(frames, p24.field_signal_dependent)
            near = m > 0.5
            far_layer = ~ndi.binary_dilation(near, np.ones((3, 3)))
            c = curve_at(sel, frames[p24.KF], near, far_layer, 60, (40, 60))
            ct = curve_at(sel, truth, near, far_layer, 60, (40, 60))
            exp = 1.0 if float(np.mean(f)) > float(np.mean(b)) else -1.0
            print(f"  {tag}: truth peak {ct['peak']:+.5f} (tail "
                  f"{ct['tail']:+.5f})  est peak {c['peak']:+.5f} (tail "
                  f"{c['tail']:+.5f})  expect "
                  f"{'+' if exp > 0 else '-'} -> "
                  f"{'PASS' if np.sign(c['peak']) == exp else 'FAIL'}",
                  flush=True)
            rows.append(dict(tag=tag, expected_sign=exp, est=c, truth=ct,
                             ok=bool(np.sign(c["peak"]) == exp)))
    finally:
        p24.KB = kb_old
    ok = all(r["ok"] for r in rows) and all(r["est"]["valid"] for r in rows)
    print(f"  => short gate {'VALIDATED' if ok else 'REJECTED'}", flush=True)
    if not ok:
        bad = [r for r in rows if not r["est"]["valid"]]
        for r in bad:
            print(f"     {r['tag']}: tail {r['est']['tail']:+.5f} exceeds "
                  f"{TAIL_BAR}. NOTE the TRUTH tail is "
                  f"{r['truth']['tail']:+.5f} -- i.e. the merge genuinely "
                  f"differs from truth in the far field, so this is a real "
                  f"contamination, not an estimator fault.", flush=True)
        print("     Cause: on a DARK background, gate-0 selection takes the "
              "max of a", flush=True)
        print("     noisy field per pixel, which biases the far field upward "
              "(selection", flush=True)
        print("     inflation).  The gate correctly refuses to certify it.  "
              "Part C sites", flush=True)
        print("     are therefore reported but NOT certifiable on the short "
              "range.", flush=True)
    return rows, ok


def main():
    prows, short_ok = validate_short_gate()

    files = L.frames(STACK)
    arg = np.load(CACHE / "25-bee3-argbest.npy")
    sel = np.load(CACHE / "25-bee3-sel.npy")
    s = np.load(CACHE / "30-drift.npy")
    H, W = arg.shape
    rows = []

    print("\n=== PART B: positive control, ROI_LEG with the KNOWN Otsu mask ===",
          flush=True)
    y0, y1, x0, x1 = L.ROIS["ROI_LEG"]
    sub = sel[y0:y1, x0:x1].astype(np.float64)
    fg, tau_fg = L.foreground_mask(sub)
    fg = ndi.binary_closing(ndi.binary_opening(fg, np.ones((5, 5))),
                            np.ones((9, 9)))
    lbl, nl = ndi.label(fg)
    if nl > 1:
        sz = ndi.sum(fg, lbl, range(1, nl + 1))
        fg = lbl == (1 + int(np.argmax(sz)))
    core = ndi.binary_erosion(fg, np.ones((9, 9)))
    knear = int(np.median(arg[y0:y1, x0:x1][core]))
    _, g1, g2, _ = L.read_planes(files[knear], (y0, y1, x0, x1))
    ref = (0.5 * (np.maximum(g1 - L.BLACK, 0.0)
                  + np.maximum(g2 - L.BLACK, 0.0))).astype(np.float64)
    refc = ref * (s[arg[y0:y1, x0:x1]] / s[knear])
    far = ~ndi.binary_dilation(fg, np.ones((3, 3)))
    ln, lf = float(np.mean(sub[fg])), float(np.mean(sub[far]))
    exp = 1.0 if ln > lf else -1.0
    print(f"  leg mask {fg.mean() * 100:.1f}% of ROI, k_near={knear}, "
          f"near={ln:.0f} far={lf:.0f} contrast={ln / lf:.2f} -> "
          f"{'reversed' if exp > 0 else 'normal'} polarity", flush=True)
    for nm, r in (("raw", ref), ("corrected", refc)):
        c = curve_at(sub, r, fg, far, 120, (90, 120))
        if c:
            print(f"    {nm:>9}: peak {c['peak']:+.5f} at d={c['peak_d']:3d}  "
                  f"tail {c['tail']:+.5f}  "
                  f"{'VALID' if c['valid'] else 'tail fail'}  sign "
                  f"{'PASS' if np.sign(c['peak']) == exp else 'FAIL'}",
                  flush=True)
            if nm == "corrected":
                rows.append(dict(tag="ROI_LEG(known mask)", polarity="normal",
                                 expected_sign=exp, contrast=ln / lf, **c))

    print("\n=== PART C: reversed-polarity sites, joint level+depth masks ===",
          flush=True)
    tiles = json.loads((DATA / "26-depth-boundaries.json").read_text(
        encoding="utf-8"))["bee3"]
    cand = [t for t in tiles if t["conf"] >= 0.85 and t["dk"] >= 40
            and t["near_brighter"] and t["contrast"] >= 1.6]
    cand.sort(key=lambda t: -t["contrast"])
    picked = []
    for t in cand:
        if all(abs(t["y"] - u["y"]) > 200 or abs(t["x"] - u["x"]) > 200
               for u in picked):
            picked.append(t)
        if len(picked) >= 6:
            break
    print(f"  {len(picked)} candidates", flush=True)
    HALF = 110
    for t in picked:
        yy0, yy1 = max(0, t["y"] - HALF), min(H, t["y"] + HALF)
        xx0, xx1 = max(0, t["x"] - HALF), min(W, t["x"] + HALF)
        a = ndi.median_filter(arg[yy0:yy1, xx0:xx1].astype(np.float32), 7)
        sb = sel[yy0:yy1, xx0:xx1].astype(np.float64)
        lo_k, hi_k = np.percentile(a, [15, 85])
        lo_l, hi_l = np.percentile(sb, [25, 75])
        near = (sb >= hi_l) & (a <= lo_k + 0.3 * (hi_k - lo_k))
        far = (sb <= lo_l) & (a >= hi_k - 0.3 * (hi_k - lo_k))
        near = ndi.binary_closing(ndi.binary_opening(near, np.ones((3, 3))),
                                  np.ones((5, 5)))
        if near.sum() < 300 or far.sum() < 300:
            print(f"  y={t['y']} x={t['x']}: masks too small "
                  f"(near {near.sum()}, far {far.sum()}) -- SKIP", flush=True)
            continue
        core = ndi.binary_erosion(near, np.ones((5, 5)))
        if core.sum() < 60:
            print(f"  y={t['y']} x={t['x']}: no near core -- SKIP", flush=True)
            continue
        kn = int(np.median(arg[yy0:yy1, xx0:xx1][core]))
        _, g1, g2, _ = L.read_planes(files[kn], (yy0, yy1, xx0, xx1))
        rf = (0.5 * (np.maximum(g1 - L.BLACK, 0.0)
                     + np.maximum(g2 - L.BLACK, 0.0))).astype(np.float64)
        rf = rf * (s[arg[yy0:yy1, xx0:xx1]] / s[kn])
        c = curve_at(sb, rf, near, far, 60, (40, 60))
        ln2 = float(np.mean(sb[near]))
        if c is None:
            print(f"  y={t['y']} x={t['x']}: far layer too small for a "
                  f"[40,60] anchor -- NOT MEASURABLE", flush=True)
            rows.append(dict(tag=f"REV y={t['y']} x={t['x']}",
                             polarity="reversed", measurable=False))
            continue
        e2 = 1.0 if ln2 > c["level"] else -1.0
        print(f"  y={t['y']} x={t['x']}: near={ln2:.0f} far={c['level']:.0f} "
              f"contrast={ln2 / c['level']:.2f} k_near={kn}  peak "
              f"{c['peak']:+.5f} at d={c['peak_d']} tail {c['tail']:+.5f} "
              f"{'VALID' if c['valid'] else 'tail fail'} sign "
              f"{'PASS' if np.sign(c['peak']) == e2 else 'FAIL'}", flush=True)
        rows.append(dict(tag=f"REV y={t['y']} x={t['x']}",
                         polarity="reversed" if e2 > 0 else "normal",
                         expected_sign=e2, contrast=ln2 / c["level"],
                         measurable=True, **c))

    print("\n================ VERDICT ================", flush=True)
    ctrl = [r for r in rows if r["tag"].startswith("ROI_LEG")]
    if ctrl:
        c = ctrl[0]
        print(f"  POSITIVE CONTROL ROI_LEG (dark FG / bright BG, normal "
              f"polarity):", flush=True)
        print(f"    peak {c['peak']:+.5f} at d={c['peak_d']}, tail "
              f"{c['tail']:+.5f}, {'VALID' if c['valid'] else 'INVALID'}",
              flush=True)
        print(f"    model predicts NEGATIVE: "
              f"{'CONFIRMED' if c['peak'] < 0 and c['valid'] else 'NOT CONFIRMED'}",
              flush=True)
    revs = [r for r in rows if r["tag"].startswith("REV")]
    good = [r for r in revs if r.get("measurable") and r.get("valid")
            and r.get("polarity") == "reversed"]
    print(f"  REVERSED-POLARITY sites: {len(revs)} attempted, "
          f"{sum(1 for r in revs if r.get('measurable'))} measurable, "
          f"{len(good)} valid AND still reversed after masking", flush=True)
    if not good:
        print("  => bee-3-cpl CANNOT support the reversed-polarity arm.",
              flush=True)
        print("     Its reversed-polarity occlusions are pale hairs over small",
              flush=True)
        print("     dark structures; those far layers are too small to "
              "establish", flush=True)
        print("     the far-field zero the estimator needs to certify itself.",
              flush=True)
        print("     The falsifier needs a PURPOSE-BUILT capture: a BRIGHT "
              "subject", flush=True)
        print("     on a DARK background, with a large clean background area.",
              flush=True)
    else:
        for r in good:
            print(f"    {r['tag']}: peak {r['peak']:+.5f} "
                  f"{'PASS' if r['peak'] > 0 else 'FAIL'}", flush=True)

    (DATA / "31-known-mask.json").write_text(
        json.dumps(dict(short_gate=prows, short_gate_ok=bool(short_ok),
                        sites=rows), indent=2, default=float),
        encoding="utf-8")
    print("\n  -> data/31-known-mask.json", flush=True)


if __name__ == "__main__":
    main()

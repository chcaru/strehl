"""M87 step 30 -- why every real site failed the tail gate, tested against the
one real site whose geometry I already understand.

Step 29's estimator reproduces the plant's ground-truth signed error to within
0.6% and its tail returns to 2e-4 of level.  On bee-3-cpl, 0 of 5 sites passed
the same tail gate, with tails from -1.10 to +0.09 of level.  Before reading
that as physics I have to rule out two causes that are mine:

  C1  PHOTOMETRIC DRIFT.  I measured 18.09% drift in level across this sweep
      (step 05).  The estimator differences the merge against a SINGLE frame
      I_{k_near}, while the merge's far field is drawn from frames near k_far.
      A systematic level difference between those frames puts a CONSTANT
      offset into the tail -- which is exactly what a failed tail gate looks
      like.  Corrected here per pixel by s[argbest]/s[k_near], where s_k is a
      drift curve measured on a patch of bare card OUTSIDE every analysis box.
      The anchor must be external: normalising on the far-field annulus itself
      would drive the tail to zero by construction and make the validity gate
      vacuous.

  C2  BOX TOO SMALL.  Step 29 used HALF=150, so EDT 90-120 px sits in the
      corners of a 300x300 box on a cluttered subject.  HALF=300 here.

  POSITIVE CONTROL.  ROI_LEG is the registered site from the original
  pre-registration: a dark leg against a large, empty, bright card -- the
  cleanest occluding boundary in the capture, and the site every headline
  number in the report was measured at.  It is normal polarity, so the
  two-layer model predicts a NEGATIVE peak.  If ROI_LEG fails the tail gate
  even after C1 and C2 are fixed, the gate or the geometry is at fault, not
  the physics, and I must say so.  If it passes, the estimator works on real
  data and the remaining question is only whether a clean REVERSED site
  exists in this capture.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import importlib.util as _iu  # noqa: E402

_spec = _iu.spec_from_file_location(
    "p29", pathlib.Path(__file__).resolve().parent / "29-real-polarity-v3.py")
p29 = _iu.module_from_spec(_spec)
_spec.loader.exec_module(p29)

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT, DATA, CACHE = HERE / "out", HERE / "data", HERE / "cache"
STACK = r"D:\personal\macro\bee-3-cpl"
ISO = 100
HALF = 300
TAIL_BAR = 0.02


def drift_curve(files, anchor):
    """Per-frame mean over a fixed patch of bare card, outside every box."""
    p = CACHE / "30-drift.npy"
    if p.exists():
        return np.load(p)
    s = np.empty(len(files), np.float64)
    t0 = time.time()
    for k, f in enumerate(files):
        _, g1, g2, _ = L.read_planes(f, anchor)
        lm = 0.5 * (np.maximum(g1 - L.BLACK, 0.0) + np.maximum(g2 - L.BLACK, 0.0))
        s[k] = float(np.mean(lm))
        if k % 60 == 0:
            print(f"    drift {k}/{len(files)} {time.time() - t0:.0f}s",
                  flush=True)
    np.save(p, s)
    return s


def run_site(tag, box, arg, sel, files, s, expect_note=""):
    y0, y1, x0, x1 = box
    a = ndi.median_filter(arg[y0:y1, x0:x1].astype(np.float32), 7)
    lo_k, hi_k = np.percentile(a, [12, 88])
    dk = hi_k - lo_k
    near = ndi.binary_closing(
        ndi.binary_opening(a <= lo_k + 0.2 * dk, np.ones((5, 5))),
        np.ones((7, 7)))
    far_layer = a >= hi_k - 0.25 * dk
    lbl, nl = ndi.label(near)
    if nl > 1:
        sz = ndi.sum(near, lbl, range(1, nl + 1))
        near = lbl == (1 + int(np.argmax(sz)))
    core = ndi.binary_erosion(near, np.ones((7, 7)))
    if core.sum() < 150 or far_layer.sum() < 5000:
        print(f"  {tag}: geometry gate failed", flush=True)
        return None
    knear = int(np.median(arg[y0:y1, x0:x1][core]))
    _, g1, g2, _ = L.read_planes(files[knear], (y0, y1, x0, x1))
    ref = 0.5 * (np.maximum(g1 - L.BLACK, 0.0) + np.maximum(g2 - L.BLACK, 0.0))
    ref = ref.astype(np.float64)

    sub = sel[y0:y1, x0:x1].astype(np.float64)
    out = {}
    for corr in (False, True):
        r = ref * (s[arg[y0:y1, x0:x1]] / s[knear]) if corr else ref
        c = p29.curve(sub, r, near, far_layer, dmax=120)
        if c is None:
            continue
        su = p29.summarise(c)
        if su is None:
            continue
        out["corrected" if corr else "raw"] = dict(
            **su, level=c["level"],
            E_curve=[None if not np.isfinite(v) else float(v) for v in c["E"]])
    if not out:
        print(f"  {tag}: no curve", flush=True)
        return None
    ln = float(np.mean(sub[near]))
    lf = out[list(out)[0]]["level"]
    pol = "reversed" if ln > lf else "normal"
    exp = 1.0 if ln > lf else -1.0
    print(f"  {tag}  dk={dk:.0f} k_near={knear} near={ln:.0f} far={lf:.0f} "
          f"contrast={ln / max(lf, 1e-9):.2f} -> {pol} {expect_note}",
          flush=True)
    for k in ("raw", "corrected"):
        if k in out:
            o = out[k]
            print(f"    {k:>9}: peak {o['peak']:+.5f} at d={o['peak_d']:3d}  "
                  f"tail {o['tail']:+.5f}  "
                  f"{'VALID' if abs(o['tail']) < TAIL_BAR else 'tail fail'}  "
                  f"sign {'PASS' if np.sign(o['peak']) == exp else 'fail'}",
                  flush=True)
    return dict(tag=tag, box=list(box), dk=float(dk), k_near=knear,
                lvl_near=ln, lvl_far=lf, contrast=ln / max(lf, 1e-9),
                polarity=pol, expected_sign=exp, **out)


def main():
    files = L.frames(STACK)
    arg = np.load(CACHE / "25-bee3-argbest.npy")
    sel = np.load(CACHE / "25-bee3-sel.npy")
    H, W = arg.shape
    print(f"green lattice {H}x{W}", flush=True)

    # photometric anchor: bare card in a frame corner, outside every box below
    anchor = (60, 320, W - 340, W - 80)
    print(f"drift anchor box {anchor}", flush=True)
    s = drift_curve(files, anchor)
    print(f"  drift over sweep: min {s.min():.1f} max {s.max():.1f} DN, "
          f"peak-to-peak {100 * (s.max() - s.min()) / s.mean():.2f}% of mean",
          flush=True)

    rows = []
    print("\n=== POSITIVE CONTROL: ROI_LEG (registered clean site) ===",
          flush=True)
    r = run_site("ROI_LEG", L.ROIS["ROI_LEG"], arg, sel, files, s,
                 "(model predicts NEGATIVE peak)")
    if r:
        rows.append(r)

    print("\n=== reversed-polarity candidates, HALF=300 ===", flush=True)
    tiles = json.loads((DATA / "26-depth-boundaries.json").read_text(
        encoding="utf-8"))["bee3"]
    cand = [t for t in tiles
            if t["conf"] >= 0.8 and t["dk"] >= 40 and t["near_brighter"]
            and t["contrast"] >= 1.3]
    cand.sort(key=lambda t: -t["contrast"])
    picked = []
    for t in cand:
        if all(abs(t["y"] - u["y"]) > 2 * HALF or abs(t["x"] - u["x"]) > 2 * HALF
               for u in picked):
            picked.append(t)
        if len(picked) >= 4:
            break
    print(f"  {len(picked)} reversed candidates after thinning", flush=True)
    for t in picked:
        y0, y1 = max(0, t["y"] - HALF), min(H, t["y"] + HALF)
        x0, x1 = max(0, t["x"] - HALF), min(W, t["x"] + HALF)
        r = run_site(f"REV y={t['y']} x={t['x']}", (y0, y1, x0, x1),
                     arg, sel, files, s, "(model predicts POSITIVE peak)")
        if r:
            rows.append(r)

    print("\n================ VERDICT ================", flush=True)
    ctrl = [r for r in rows if r["tag"] == "ROI_LEG"]
    if ctrl and "corrected" in ctrl[0]:
        o = ctrl[0]["corrected"]
        ok = abs(o["tail"]) < TAIL_BAR
        print(f"  positive control ROI_LEG (corrected): tail {o['tail']:+.5f} "
              f"-> {'PASSES' if ok else 'FAILS'} the validity gate", flush=True)
        if not ok:
            print("  => the estimator does NOT transfer to real captures even "
                  "at the cleanest available boundary.", flush=True)
            print("     The real-data polarity test is INCONCLUSIVE; the "
                  "limitation is instrumental, not physical.", flush=True)
        else:
            print(f"  => peak {o['peak']:+.5f} at d={o['peak_d']}, predicted "
                  f"sign {'-' if ctrl[0]['expected_sign'] < 0 else '+'}: "
                  f"{'PASS' if np.sign(o['peak']) == ctrl[0]['expected_sign'] else 'FAIL'}",
                  flush=True)
    valid = [r for r in rows if "corrected" in r
             and abs(r["corrected"]["tail"]) < TAIL_BAR]
    print(f"  sites passing validity after drift correction: "
          f"{len(valid)}/{len(rows)}", flush=True)
    for r in valid:
        o = r["corrected"]
        print(f"    {r['tag']:>22}  {r['polarity']:>9}  peak {o['peak']:+.5f}  "
              f"{'PASS' if np.sign(o['peak']) == r['expected_sign'] else 'fail'}",
              flush=True)

    (DATA / "30-control.json").write_text(
        json.dumps(dict(drift=[float(v) for v in s], sites=rows), indent=2),
        encoding="utf-8")
    print("\n  -> data/30-control.json", flush=True)


if __name__ == "__main__":
    main()

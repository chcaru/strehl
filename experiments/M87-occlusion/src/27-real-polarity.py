"""M87 step 27 -- THE POLARITY FALSIFIER ON REAL DATA.

Registered in PREREG-ADDENDUM-3-polarity.md (commit 4e04877).

The plant (step 24) passed N1/N2/N3 in all four arms, but the plant is BUILT
FROM the two-layer equation, so its sign flip is close to tautological: a scene
generated as alpha*F + (1-alpha)*B cannot refute the claim that its residual
carries sign(F-B).  What the plant genuinely establishes is the non-obvious
half -- that SELECTION lands in the veiled band with the alpha the forward
model assumes, rather than escaping to k_F where the error would be ~0.  The
falsification has to happen on a real capture, and this is it.

Step 26 found, in bee-3-cpl, genuine depth discontinuities of BOTH polarities:

  reversed (near layer BRIGHTER)  y=1248 x=960   dk=128  contrast 2.38 conf 0.90
  normal   (near layer DARKER)    y=1344 x=3216  dk=134  contrast 0.10 conf 1.00

TRUTH-FREE SIGNED ESTIMATOR.  Real captures have no ground truth, so E cannot
be computed directly.  The two-layer model supplies its own reference: at
k = k_near the foreground is SHARP, so alpha ~ 0 just outside the silhouette
and the background pixel there is UNVEILED.  Therefore

    E_est(d) = merge(d) - I_{k_near}(d)  ~=  alpha_{k_hat}(d) * (Fbar - B_blur)

carries the same sign as E.  I_{k_near} carries B blurred rather than sharp,
but blurring preserves local means, so the MEDIAN over profiles is unbiased for
the level.  Part A validates this estimator against the plant's KNOWN E before
it is trusted on the bee -- a metric must be validated on a case where the
answer is known.
"""
import json
import pathlib
import sys
import time

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402
import importlib.util as _iu  # noqa: E402

_spec = _iu.spec_from_file_location(
    "p24", pathlib.Path(__file__).resolve().parent / "24-polarity-plant.py")
p24 = _iu.module_from_spec(_spec)
_spec.loader.exec_module(p24)

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
CACHE = HERE / "cache"
for p in (OUT, DATA, CACHE):
    p.mkdir(exist_ok=True)

STACK = r"D:\personal\macro\bee-3-cpl"
ISO = 100
D_MAX = 64
BAND = (3, 40)

SITES = {
    "REV_A hair-over-leg":   dict(box=(1150, 1430, 860, 1240), polarity="rev"),
    "REV_B hair-over-dark":  dict(box=(1900, 2180, 1700, 2010), polarity="rev"),
    "NORM_A leg-on-card":    dict(box=(1250, 1530, 3060, 3400), polarity="norm"),
    "NORM_B leg-on-card":    dict(box=(1600, 1880, 2600, 2910), polarity="norm"),
}


def profiles_from_mask(imgs, near, pad=40, step=2):
    solid = near
    edt = ndi.distance_transform_edt(~solid)
    s = ndi.gaussian_filter(edt.astype(np.float64), 4.0)
    gy, gx = np.gradient(s)
    nn = np.hypot(gy, gx)
    ny, nx = gy / np.maximum(nn, 1e-9), gx / np.maximum(nn, 1e-9)
    h, w = near.shape
    band = (edt > 0.5) & (edt < 1.5)
    ys, xs = np.nonzero(band)
    keep = ((ys > pad) & (ys < h - pad) & (xs > pad) & (xs < w - pad))
    ys, xs = ys[keep][::step], xs[keep][::step]
    ds = np.arange(D_MAX + 1, dtype=np.float64)
    out = []
    for img in imgs:
        pr = np.empty((len(ys), D_MAX + 1), np.float64)
        for j, (y, x) in enumerate(zip(ys, xs)):
            pr[j] = ndi.map_coordinates(
                img, [y + ny[y, x] * ds, x + nx[y, x] * ds],
                order=1, mode="nearest")
        out.append(pr)
    return out, ds, len(ys)


def band_stat(err, level, seed=27):
    lo, hi = BAND
    b = slice(lo, hi + 1)
    E = np.median(err, axis=0) / level
    val = float(np.median(E[b]))
    rng = np.random.default_rng(seed)
    n = err.shape[0]
    nb = max(1, n // 32)
    boot = []
    for _ in range(400):
        idx = np.concatenate([np.arange(i * 32, min((i + 1) * 32, n))
                              for i in rng.integers(0, nb, nb)])
        boot.append(np.median(np.median(err[idx], axis=0)[b]) / level)
    return val, (float(np.percentile(boot, 2.5)),
                 float(np.percentile(boot, 97.5))), E


def part_a():
    print("=== PART A: validate the truth-free estimator on the plant ===",
          flush=True)
    rows = []
    for tag, fg, bg in (("P_plus  dark-FG/bright-BG", p24.LO, p24.HI),
                        ("P_minus bright-FG/dark-BG", p24.HI, p24.LO)):
        frames, alphas, m, f, b, truth = p24.build(fg, bg)
        sel, arg = p24.merge(frames, p24.field_signal_dependent)
        near = m > 0.5
        knear = p24.KF                      # known exactly on the plant
        ref = frames[knear].astype(np.float64)
        (ps, pt, pr), ds, n = profiles_from_mask(
            [sel.astype(np.float64), truth.astype(np.float64), ref], near)
        e_true, ci_t, Et = band_stat(ps - pt, p24.LEVEL)
        e_est, ci_e, Ee = band_stat(ps - pr, p24.LEVEL)
        r = float(np.corrcoef(Et, Ee)[0, 1])
        agree = np.sign(e_true) == np.sign(e_est)
        print(f"  {tag}: E_true {e_true:+.5f}  E_est {e_est:+.5f}  "
              f"ratio {e_est / e_true if e_true else float('nan'):+.3f}  "
              f"r {r:+.3f}  sign {'AGREE' if agree else 'DISAGREE'}",
              flush=True)
        rows.append(dict(tag=tag, E_true=e_true, E_true_ci=list(ci_t),
                         E_est=e_est, E_est_ci=list(ci_e),
                         ratio=float(e_est / e_true) if e_true else None,
                         pearson_r=r, sign_agrees=bool(agree),
                         n_profiles=int(n)))
    ok = all(r["sign_agrees"] for r in rows)
    print(f"  => estimator {'VALIDATED' if ok else 'REJECTED'} "
          f"(sign agrees in {sum(r['sign_agrees'] for r in rows)}/2 arms)",
          flush=True)
    return rows, ok


def load_cube(box, tag):
    cp = CACHE / f"27-{tag}.npz"
    if cp.exists():
        z = np.load(cp)
        return z["lum"], z["arg"], z["sel"]
    files = L.frames(STACK)
    n = len(files)
    h, w = box[1] - box[0], box[3] - box[2]
    lum = np.empty((n, h, w), np.float32)
    best = np.full((h, w), -np.inf, np.float32)
    arg = np.zeros((h, w), np.int16)
    t0 = time.time()
    for k, p in enumerate(files):
        _, g1, g2, _ = L.read_planes(p, box)
        lm = 0.5 * (np.maximum(g1 - L.BLACK, 0.0) + np.maximum(g2 - L.BLACK, 0.0))
        lum[k] = lm
        fl = L.regularised_field(lm.astype(np.float64), ISO)
        better = fl > best
        best[better] = fl[better]
        arg[better] = k
        if k % 80 == 0:
            print(f"    {tag} {k}/{n} {time.time() - t0:.0f}s", flush=True)
    sel = np.take_along_axis(lum, arg[None].astype(np.intp), 0)[0]
    np.savez_compressed(cp, lum=lum, arg=arg, sel=sel)
    return lum, arg, sel


def part_b(est_ok):
    print("\n=== PART B: the falsifier on bee-3-cpl ===", flush=True)
    rows = []
    for tag, cfg in SITES.items():
        box = cfg["box"]
        short = tag.split()[0]
        lum, arg, sel = load_cube(box, short)
        d = ndi.median_filter(arg.astype(np.float32), 7)
        lo_k, hi_k = np.percentile(d, [15, 85])
        dk = hi_k - lo_k
        near = d <= lo_k + 0.15 * dk               # LOWER k = NEARER (step 25)
        near = ndi.binary_opening(near, np.ones((5, 5)))
        near = ndi.binary_closing(near, np.ones((7, 7)))
        lbl, nl = ndi.label(near)
        if nl > 1:
            sizes = ndi.sum(near, lbl, range(1, nl + 1))
            near = lbl == (1 + int(np.argmax(sizes)))
        if near.sum() < 400:
            print(f"  {tag}: near layer too small ({near.sum()} px) -- SKIP",
                  flush=True)
            continue
        knear = int(np.median(arg[ndi.binary_erosion(near, np.ones((7, 7)))]))
        far = d >= hi_k - 0.15 * dk
        lvl_near = float(np.median(sel[near]))
        lvl_far = float(np.median(sel[far])) if far.sum() else float("nan")
        ref = lum[knear].astype(np.float64)
        (ps, pr), ds, n = profiles_from_mask(
            [sel.astype(np.float64), ref], near)
        if n < 64:
            print(f"  {tag}: only {n} profiles -- SKIP", flush=True)
            continue
        level = float(np.median(ps[:, 48:]))
        e_est, ci, E = band_stat(ps - pr, level)
        expect = +1.0 if lvl_near > lvl_far else -1.0
        ok = np.sign(e_est) == expect
        print(f"  {tag}", flush=True)
        print(f"    dk {dk:6.1f} frames | near {lvl_near:7.1f} / far "
              f"{lvl_far:7.1f} | contrast {lvl_near / max(lvl_far, 1e-9):5.2f} "
              f"| k_near {knear} | {n} profiles", flush=True)
        print(f"    E_est {e_est:+.5f} of level  95% CI "
              f"[{ci[0]:+.5f}, {ci[1]:+.5f}]", flush=True)
        print(f"    predicted sign {'+' if expect > 0 else '-'} -> "
              f"{'PASS' if ok else 'FAIL'}", flush=True)
        rows.append(dict(tag=tag, polarity=cfg["polarity"], dk=float(dk),
                         lvl_near=lvl_near, lvl_far=lvl_far,
                         contrast=lvl_near / max(lvl_far, 1e-9),
                         k_near=knear, n_profiles=int(n), level=level,
                         E_est=e_est, E_ci=list(ci),
                         expected_sign=float(expect), passed=bool(ok),
                         E_profile=[float(v) for v in E]))
    return rows


def main():
    a, est_ok = part_a()
    b = part_b(est_ok)

    print("\n================ REGISTERED VERDICT (real data) ================",
          flush=True)
    rev = [r for r in b if r["polarity"] == "rev"]
    nor = [r for r in b if r["polarity"] == "norm"]
    if rev and nor:
        mr = float(np.median([r["E_est"] for r in rev]))
        mn = float(np.median([r["E_est"] for r in nor]))
        print(f"  reversed polarity (near BRIGHTER): E_est median {mr:+.5f}",
              flush=True)
        print(f"  normal   polarity (near DARKER  ): E_est median {mn:+.5f}",
              flush=True)
        if np.sign(mr) != np.sign(mn):
            print("  => SIGN FLIPS ON REAL DATA. N1 PASSES. The artifact "
                  "carries sign(F-B).", flush=True)
            print("     Veiling SURVIVES a test it could have failed.",
                  flush=True)
        else:
            print("  => SIGN DOES NOT FLIP. N1 FAILS.", flush=True)
            print("     VEILING REFUTED as the dominant cause; the artifact "
                  "is polarity-independent.", flush=True)
    npass = sum(r["passed"] for r in b)
    print(f"  per-site: {npass}/{len(b)} sites match their predicted sign",
          flush=True)

    (DATA / "27-real-polarity.json").write_text(
        json.dumps(dict(plant_validation=a, estimator_ok=bool(est_ok),
                        sites=b), indent=2), encoding="utf-8")
    print("\n  -> data/27-real-polarity.json", flush=True)


if __name__ == "__main__":
    main()

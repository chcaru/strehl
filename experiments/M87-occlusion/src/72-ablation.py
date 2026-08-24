"""M87 / 72 -- is the -28.2% a refutation of the two-layer MODEL, or of one
IMPLEMENTATION of it?  An oracle ablation ladder on ground truth.

THE QUESTION, AS THE ORCHESTRATOR PUT IT.  My header rules out three
explanations for the halo and leaves no surviving mechanism.  An external
reviewer named two-layer bimodal unmixing as the headline unbuilt idea in this
project, and my step 13 reached only **-28.2%** against a -50% bar.  If that
shortfall is the two-component FIT, the model is dead and the reviewer's
proposal with it.  If it is the winner field or the `k_F` propagation FEEDING
the fit, the model is untested and still live.

WHAT I FOUND BEFORE BUILDING ANYTHING, AT SOURCE.  `13-unmix.py:98` reads

    kF = int(np.bincount(argbest[mask]).argmax())

-- a SINGLE GLOBAL SCALAR, the modal elected index over the whole foreground
mask.  The alpha model is `sigma_k = c * |k - k_F|`, so if the foreground
actually spans a range of depths, alpha_k is wrong for most pixels and the
regression's design matrix is wrong.  The intercept it solves for is then biased
no matter how good the two-component model is.  My own P34 already measured the
consequence from the other side: a global `k_F` removes 1.2% of the flower's
halo against 84.6% for a per-pixel map.

THE TRAP I NEARLY WALKED INTO, AND IT WOULD HAVE BEEN THE FIFTH THIS MILESTONE.
`16-plant.py` builds its foreground as a bar at ONE depth, `KF = 40`, blurred by
`sigma_F(k) = |k - KF| * SCALE`.  On that plant a global scalar `k_F` is
**correct by construction**, so the degradation I am hypothesising cannot occur
there and an ablation would return "no effect" for the wrong reason.  The plant
has to be extended before it can answer the question.  So this script builds a
DEPTH-SPREAD foreground -- horizontal stripes, each at its own sharp frame,
blurred separately at its own sigma and summed, which is exact because the
stripes are disjoint -- and keeps the original flat plant as the placebo where
the ablation MUST show nothing.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

Primary metric is FIDELITY AGAINST TRUTH, never suppression.  Bar X4 measured
that three of four deliberately broken unmixings improved the halo metric by
77-85%, so no suppression number may certify anything here.  Score is band RMSE
against `unveiled_b`, the known unveiled background, over the fixed band
d in [2, 22] outside the true matte, as a percentage of scene level, reported as
the change relative to the uncorrected merge.  The treated set is IDENTICAL
across arms by construction, so the ladder isolates the alpha VALUES and not the
treated population.

THE LADDER, on each plant:
    A  shipped        estimated matte, GLOBAL SCALAR k_F, fitted c
    B  oracle k_F     estimated matte, TRUE per-pixel k_F map, fitted c
    C  oracle c       estimated matte, global scalar k_F, TRUE c
    D  oracle matte   TRUE matte, TRUE per-pixel k_F, TRUE c
    E  oracle alpha   the TRUE alpha_k cube handed straight to the fit
    X  BROKEN         alpha -> 1 - alpha, registered in the set, not after it

N1 -- PLACEBO, flat plant.  The foreground is at one depth, so an oracle k_F
    carries no information a scalar lacks.  REGISTERED: on the flat plant, arms
    A and E must agree within 20% relative on band RMSE improvement.  If they do
    not, the ladder is measuring something other than k_F propagation and every
    number below is void.

N2 -- THE VERDICT, depth-spread plant.  REGISTERED: if arm E improves band RMSE
    at least 2x more than arm A, the fit is not the limiter, the -28.2% is a
    refutation of the PROPAGATION and not of the model, and the reviewer's
    proposal is still live.  If E and A agree within that factor, the
    two-component fit itself is the ceiling and step 13 stands as a refutation
    of the model.

    AMENDED, after the flat plant's capability line and before ANY arm number
    was produced.  I wrote the paragraph above believing the -28.2% was the
    global-scalar arm, because `13-unmix.py:98` is a global scalar.  I then read
    section 5.2 of my own report at source: the global scalar produced **+3.7%**
    and the **-28.2% is ALREADY the per-pixel k_F arm** (median band R^2 0.200,
    coverage 19.8%).  My premise was wrong.  The shipped state of the art is
    therefore arm B, not arm A, and N2 is judged **E vs B**; judging E vs A
    would let the already-banked +3.7% -> -28.2% gain masquerade as new
    headroom.  E/A is still reported because it is what I registered.

N3 -- THE BROKEN ARM.  REGISTERED: arm X must be WORSE than the uncorrected
    merge on band RMSE.  If a deliberately broken unmixing improves fidelity
    against truth, the fidelity instrument is void exactly as the suppression
    instrument was, and I report that instead of a verdict.

C-CAP -- capability, per SYNTHESIS 567/568/603.  Each plant must express the
    artifact: merge ISO >= 0.02 and ground-truth ISO <= 0.005.  A plant that
    cannot show a halo cannot show one being removed.

READ-ONLY: D:\\personal\\macro.  Writes only under experiments/M87-occlusion.
"""
import importlib.util
import json
import pathlib
import sys

import numpy as np
from scipy import ndimage as ndi
from scipy.ndimage import distance_transform_edt

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import m87lib as L  # noqa: E402
import m87metric2 as M2  # noqa: E402

spec = importlib.util.spec_from_file_location("plant", HERE / "16-plant.py")
P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(P)

DATA = HERE.parents[0] / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
OUT.mkdir(parents=True, exist_ok=True)

BAND = (2, 22)
BAND2 = (2, 40)       # section 4.2's band, carried so the two are comparable
N_STRIPES = 6
SPREAD = 60           # k_F ranges KF +/- SPREAD/2 across the depth-spread plant
# section 5.2 swept c in {0.1, 0.2, 0.4, 0.8} and measured the ISO flat from 0.4
# to 0.8, so a fine grid buys nothing and costs an hour: sigma reaches |k-kF|*c
# = 120*0.6 = 72 px, whose 4-sigma scipy kernel is wider than the 384x512 plant.
C_GRID = (0.10, 0.20, 0.28, 0.40, 0.60)
SIG_CAP = 40.0        # beyond this the matte is flat to well under the noise
_BLUR: dict = {}


def blur(m, sigma, tag):
    """gaussian_filter memoised on (matte identity, quantised sigma).  Each arm
    rebuilds the same alpha cube for the c-sweep and then again to run, so
    without this every blur is computed at least twice."""
    if sigma <= 0.3:
        return m
    s = min(float(sigma), SIG_CAP)
    key = (tag, round(s, 2))
    v = _BLUR.get(key)
    if v is None:
        v = ndi.gaussian_filter(m, s, truncate=3.0)
        _BLUR[key] = v
    return v


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def build(spread):
    """P.build() with the foreground split into stripes at different depths.
    spread = 0 reproduces the original flat plant exactly in structure."""
    rng = np.random.default_rng(87)
    yy, xx = np.mgrid[0:P.H, 0:P.W]
    b = 0.75 + 0.035 * np.sin(xx / 1.6) * np.cos(yy / 1.9)
    b += 0.012 * ndi.gaussian_filter(rng.standard_normal((P.H, P.W)), 0.8)
    b = np.clip(b, 0.2, 1.0)

    m = ((xx > 150) & (xx < 260)).astype(np.float32)
    m *= (yy > 20) & (yy < P.H - 20)
    m = ndi.gaussian_filter(m, 0.6)
    m = np.clip(m, 0, 1)
    f = 0.08 + 0.03 * np.sin(yy / 7.0)

    band_id = np.clip((yy * N_STRIPES) // P.H, 0, N_STRIPES - 1)
    if spread == 0:
        kf_of = np.full(N_STRIPES, float(P.KF))
    else:
        kf_of = P.KF + np.linspace(-spread / 2.0, spread / 2.0, N_STRIPES)
    kf_map = kf_of[band_id].astype(np.float32)

    frames = np.empty((P.N, P.H, P.W), np.float32)
    alphas = np.empty((P.N, P.H, P.W), np.float32)
    for k in range(P.N):
        a = np.zeros((P.H, P.W), np.float32)
        fb = np.zeros((P.H, P.W), np.float32)
        for s in range(N_STRIPES):
            ms = np.where(band_id == s, m, 0.0).astype(np.float32)
            sf = abs(k - kf_of[s]) * P.SCALE
            a += ndi.gaussian_filter(ms, sf) if sf > 0.3 else ms
            fbs = (ms * f).astype(np.float32)
            fb += ndi.gaussian_filter(fbs, sf) if sf > 0.3 else fbs
        a = np.clip(a, 0.0, 1.0)
        sb = abs(k - P.KB) * P.SCALE
        bb = ndi.gaussian_filter(b, sb) if sb > 0.3 else b.copy()
        img = fb + bb * (1.0 - a)
        alphas[k] = a
        v = img * P.LEVEL
        frames[k] = v + rng.normal(0, np.sqrt(np.maximum(v, 1.0)) + P.READ_SD,
                                   (P.H, P.W))
    truth = (m * f + b * (1.0 - m)) * P.LEVEL
    unveiled = b * P.LEVEL
    return frames, alphas, m, kf_map, truth, unveiled


def alpha_from(matte, kf, scale, n, tag):
    """Per-pixel kf if kf is an array, scalar otherwise.  Stripe-exact for the
    array case: group pixels by rounded kf and blur each group at its sigma.
    Exact because gaussian_filter is linear and the groups partition the matte."""
    out = np.empty((n,) + matte.shape, np.float32)
    if np.isscalar(kf) or np.ndim(kf) == 0:
        for k in range(n):
            out[k] = blur(matte, abs(k - float(kf)) * scale, tag)
        return out
    lev = np.unique(np.rint(kf))
    parts = [(v, np.where(np.rint(kf) == v, matte, 0.0).astype(np.float32))
             for v in lev]
    for k in range(n):
        acc = np.zeros_like(matte, np.float32)
        for v, ms in parts:
            acc += blur(ms, abs(k - float(v)) * scale, (tag, float(v)))
        out[k] = np.clip(acc, 0.0, 1.0)
    return out


def run_plant(tag_, spread, rep):
    print(f"\n{'=' * 74}\n=== {tag_} (spread {spread}) ===", flush=True)
    _BLUR.clear()   # tags are reused between plants but the mattes are not
    frames, alphas, m, kf_map, truth, unveiled = build(spread)
    mask_true = m > 0.5
    sel, argbest = P.merge(frames)

    pts, nrm = M2.boundary_normals(mask_true, roi=P.ROI)
    val = M2.valid_profiles(mask_true, pts, nrm, d_max=M2.D_MAX)
    p, nv = pts[val], nrm[val]
    iso_merge = M2.score_iso(sel, p, nv, boot=0)["ISO"]
    iso_truth = M2.score_iso(truth, p, nv, boot=0)["ISO"]
    cap = bool(iso_merge >= 0.02 and iso_truth <= 0.005)
    print(f"  C-CAP: merge ISO={iso_merge:.5f} (>=0.02), truth ISO={iso_truth:.5f} "
          f"(<=0.005) -> {'PASS' if cap else 'FAIL, plant cannot answer'}", flush=True)

    d_out = distance_transform_edt(~mask_true)
    roi = np.zeros_like(mask_true)
    roi[P.ROI[0]:P.ROI[1], P.ROI[2]:P.ROI[3]] = True
    bg = (~mask_true) & roi
    band = bg & (d_out >= BAND[0]) & (d_out <= BAND[1])
    band2 = bg & (d_out >= BAND2[0]) & (d_out <= BAND2[1])
    print(f"  band d in {BAND}: {int(band.sum())} px; section 4.2 band d in "
          f"{BAND2}: {int(band2.sum())} px; identical across all arms", flush=True)

    def rmse(img, sel_band):
        return float(np.sqrt(np.mean((img[sel_band] - unveiled[sel_band]) ** 2))
                     / P.LEVEL * 100)

    base = rmse(sel, band)
    base2 = rmse(sel, band2)
    floor = rmse(truth, band)
    print(f"  uncorrected merge band RMSE = {base:.4f}% (d{BAND})  "
          f"{base2:.4f}% (d{BAND2});  ground-truth floor = {floor:.4f}%", flush=True)

    sel_mask, _ = L.foreground_mask(sel)
    kf_scalar = int(np.bincount(argbest[sel_mask]).argmax())
    m_est = ndi.gaussian_filter(sel_mask.astype(np.float32), 0.6)
    kf_true_est = np.rint(ndi.median_filter(argbest.astype(np.float32), 15))
    print(f"  estimated global k_F = {kf_scalar}   true k_F map spans "
          f"{kf_map.min():.0f} to {kf_map.max():.0f}", flush=True)

    def best_c(matte, kf, tag):
        bc, br = None, -np.inf
        for c in C_GRID:
            a = alpha_from(matte, kf, float(c), P.N, tag)
            _, r2 = P.unmix(frames, a)
            v = float(np.nanmedian(r2[band]))
            if v > br:
                br, bc = v, float(c)
        return bc, br

    arms = {}

    def arm(name, matte, kf, c, tag=None, alpha=None, note=""):
        if alpha == "oracle":
            a = alphas
        elif alpha == "broken":
            a = (1.0 - alphas).astype(np.float32)
        else:
            a = alpha_from(matte, kf, c, P.N, tag)
        a0, _ = P.unmix(frames, a)
        good = np.isfinite(a0)
        img = sel.copy()
        img[band2 & good] = a0[band2 & good]
        r, r2b = rmse(img, band), rmse(img, band2)
        imp = 100.0 * (1.0 - r / base)
        iso = M2.score_iso(img, p, nv, boot=0)["ISO"]
        sup = 100.0 * (1.0 - iso / iso_merge)
        print(f"  {name:<26} RMSE {r:8.4f}% ({imp:+7.2f}%)  d2-40 {r2b:7.4f}% "
              f"({100.0 * (1.0 - r2b / base2):+7.2f}%)  [supp {sup:+6.1f}%]  {note}",
              flush=True)
        arms[name] = {"rmse_pct": r, "improve_pct": imp, "rmse2_pct": r2b,
                      "improve2_pct": 100.0 * (1.0 - r2b / base2),
                      "iso": float(iso), "suppress_pct": sup}
        return imp

    cA, _ = best_c(m_est, kf_scalar, "est")
    cB, _ = best_c(m_est, kf_true_est, "estmap")
    print(f"  fitted c: scalar-kF arm {cA:.2f}, map-kF arm {cB:.2f}, "
          f"true c = {P.SCALE:.2f}", flush=True)

    iA = arm("A shipped scalar k_F", m_est, kf_scalar, cA, "est",
             note="the +3.7% arm of section 5.1")
    iB = arm("B oracle k_F map", m_est, kf_true_est, cB, "estmap",
             note="the -28.2% arm of section 5.2")
    arm("C oracle c", m_est, kf_scalar, P.SCALE, "est", note="true blur constant")
    iD = arm("D oracle matte+kF+c", m, kf_map, P.SCALE, "true",
             note="every input true, alpha still MODELLED")
    iE = arm("E oracle alpha", None, None, None, alpha="oracle",
             note="true alpha_k cube: the FIT's own ceiling")
    iX = arm("X BROKEN 1-alpha", None, None, None, alpha="broken",
             note="registered broken arm")

    n3 = iX < 0
    gapDE = abs(iE - iD) / max(abs(iE), 1e-9)
    print(f"  N3 broken arm worse than the merge: {n3} "
          f"({'OK' if n3 else 'FIDELITY INSTRUMENT VOID'})", flush=True)
    print(f"  C-DE machinery check: D {iD:+.2f}% vs E {iE:+.2f}%, relative gap "
          f"{100 * gapDE:.1f}% ({'OK' if gapDE <= 0.20 else 'alpha_from DIVERGES from the plant'})",
          flush=True)
    rep[tag_] = {"spread": spread, "iso_merge": float(iso_merge),
                 "iso_truth": float(iso_truth), "capability": cap,
                 "band_px": int(band.sum()), "base_rmse_pct": base,
                 "base_rmse2_pct": base2, "truth_floor_pct": floor,
                 "kf_scalar": kf_scalar, "kf_map_min": float(kf_map.min()),
                 "kf_map_max": float(kf_map.max()), "c_A": cA, "c_B": cB,
                 "arms": arms, "N3_broken_worse": bool(n3),
                 "C_DE_gap": gapDE, "A_improve": iA, "B_improve": iB,
                 "E_improve": iE}
    return iA, iB, iE


def main():
    rep = {}
    aF, bF, eF = run_plant("FLAT placebo", 0, rep)
    aS, bS, eS = run_plant("DEPTH-SPREAD", SPREAD, rep)

    print(f"\n{'=' * 74}\n=== VERDICT ===", flush=True)
    print("  AMENDMENT, recorded before any arm number was read.  The"
          " preregistration compared E against A, on my belief that the -28.2%"
          " was the global-scalar k_F arm.  I then read section 5.2 at source:"
          " the -28.2% is ALREADY the per-pixel k_F arm and the global scalar"
          " produced +3.7%.  So the shipped state of the art is arm B, and N2 is"
          " judged E vs B.  E vs A is retained below because it is what I"
          " registered.", flush=True)
    rel = abs(eF - aF) / max(abs(aF), 1e-9)
    n1 = rel <= 0.20
    print(f"  N1 placebo (flat): A {aF:+.2f}%  B {bF:+.2f}%  E {eF:+.2f}%  "
          f"A-E relative gap {100 * rel:.1f}%  -> "
          f"{'PASS' if n1 else 'FAIL, ladder is void'}", flush=True)
    rA = eS / aS if abs(aS) > 1e-9 else float("inf")
    rB = eS / bS if abs(bS) > 1e-9 else float("inf")
    n2 = rB >= 2.0
    print(f"  N2 (depth-spread): A {aS:+.2f}%  B {bS:+.2f}%  E {eS:+.2f}%   "
          f"E/B = {rB:.2f}x   (as registered, E/A = {rA:.2f}x)", flush=True)
    print("  N2 -> " + ("THE PROPAGATION IS THE LIMITER: the two-layer model is"
                        " NOT refuted and the reviewer's proposal is still live"
                        if n2 else
                        "THE FIT IS THE CEILING: step 13 refutes the MODEL"),
          flush=True)
    rep["verdict"] = {"N1_rel_gap": rel, "N1_pass": bool(n1),
                      "N2_ratio_EB": float(rB), "N2_ratio_EA": float(rA),
                      "N2_pass": bool(n2), "flat_A": aF, "flat_B": bF,
                      "flat_E": eF, "spread_A": aS, "spread_B": bS,
                      "spread_E": eS,
                      "amendment": "N2 judged E vs B, not E vs A: section 5.2 "
                                   "shows the -28.2% is the per-pixel k_F arm"}
    with open(DATA / "72-ablation.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '72-ablation.json'}", flush=True)


if __name__ == "__main__":
    main()

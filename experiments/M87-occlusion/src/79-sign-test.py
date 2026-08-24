"""M87 / 79 -- the orchestrator's two remaining tests, and an audit of my own
plants against M99's corrected fact 23.

Item 3 (photometric normalisation) is withdrawn: M99 owns it and has measured
it.  What is left is the orchestrator's restated hypothesis, which does NOT run
through the election:

    at a silhouette the winner field jumps between two frame indices far apart
    on the focus axis; if those frames differ photometrically the rendered
    output carries a SIGNED STEP there, independent of veiling and independent
    of the election being correct.

M99 fact 22 makes this the right framing.  A gain that propagates into the noise
model is election-neutral by construction (contrast/sigma; a gain scales both),
measured at 0.001% against a 0.43-0.74% null.  So the mechanism cannot be tested
by moving the election -- it must be tested on what is composited.

WHAT I AM CHECKING FIRST, BECAUSE IT IS A CHALLENGE TO MY OWN CONTROLS.  The
orchestrator relayed fact 23 as "any plant must be MONOTONE in frame index or it
understates the effect by ~11x".  M99's own section 12.3 has already corrected
that wording at source: the natural gain that enriched 20.64x/8.32x is NOT
monotone, it is a single smooth hump rising to a maximum at frame 103-120 and
falling, max/min 1.1818, endpoint ratio only 1.0380.  The operative property is
that the gain is SMOOTHLY ORDERED (low-frequency) in frame index, not that it is
monotone; the pseudo-random plant under-performed because it was UNORDERED.  So
the test my plants must pass is smooth ordering, and S0 measures it.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

S0 -- PLANT VALIDITY AND DRIFT SHAPE.  Measure this cube's per-frame level
    ordering (Spearman rho against frame index), the location of its maximum,
    max/min and endpoint ratios.  Compare against M99 section 12.3.
    REGISTERED: my plants are valid iff they are smoothly ordered.  A linspace
    ramp has |rho| = 1 by construction, so the question is whether the REAL
    drift is ordered too -- if it is not, a ramp plant is the wrong shape and I
    must say so.  I additionally build a hump plant matching M99's measured
    shape and run every arm on both.

S1 -- INDEX GAP, ON M96'S POPULATION (the orchestrator's test 1).  Reuse M96's
    disconnected-competitive-set definition verbatim from `52-photometric-share`
    -- admit(k) = best - field_k <= t*sqrt(2)*FOCUS_NOISE_SD,
    gap = (hi - lo + 1) - n, DISCONNECTED if > 0 -- and regress the rendered
    excess on the gap, on the disconnected population and on its complement.
    REGISTERED: a photometric-step mechanism predicts a MONOTONE POSITIVE
    relationship.  Report Spearman rho within distance bins (distance must be
    partialled out; section 27.7 showed the un-partialled version reads +0.0660
    on a rolled null) with a rolled-gap null, and report the ladder.

S2 -- THE SIGN TEST (the orchestrator's test 2, and the cleanest discriminator).
    For 4-adjacent background pixel pairs (p,q) in the veil band that elected
    different frames, the two-layer/veiling account and the photometric-step
    account make different predictions:

        photometric step:  M(p) - M(q)  ~=  S * (g_kp - g_kq)
        veiling:           sign is fixed by which side occludes, and carries no
                           relation to g at all

    So regress the observed step on the predicted photometric step.  Under a
    pure photometric-step mechanism the SLOPE IS 1 BY CONSTRUCTION and sign
    agreement is high.
    REGISTERED:
      CONFIRMED if slope is in [0.5, 1.5] and sign agreement > 60%.
      REFUTED  if |slope| < 0.25 and sign agreement < 55%, AND both positive
               controls pass.
      Anything else is partial and reported as such.
    Also report AMPLITUDE -- median |predicted| over median |observed| -- because
    a real but tiny effect is a different finding from no effect, and a
    correlation alone cannot tell them apart.

C-POS-RAMP -- plant a monotone +/-10% ramp, freeze the election bit-for-bit
    (which is what M99 fact 22 says a correct correction does), recompose, and
    run S2 with the known g.  MUST return slope ~1.
C-POS-HUMP -- the same with M99's measured hump shape (max/min 1.18, peak at
    frame 110).  MUST also return slope ~1.  If the ramp passes and the hump
    fails, my instrument is keyed to the plant's shape and S2 is void.
C-NULL -- shuffle the frame->level map.  Slope MUST collapse toward 0.  This is
    the arm that says the regression is not fitting scene structure.

READ-ONLY: D:\\personal\\macro.
"""
import importlib.util
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt
from scipy.stats import spearmanr

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")

_s = importlib.util.spec_from_file_location(
    "m52", pathlib.Path(__file__).resolve().parent / "52-photometric-share.py")
m52 = importlib.util.module_from_spec(_s)
_s.loader.exec_module(m52)

ISO = 100.0
REF_D = 140
BAND = (2, 40)
DMAX = 200
ROLL = (317, 511)
SEED = 8779
PLANT = 0.10
HUMP_PEAK = 110
HUMP_RATIO = 1.18


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def ols(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    xc = x - x.mean()
    yc = y - y.mean()
    den = float((xc * xc).sum())
    if den <= 0:
        return float("nan"), float("nan")
    b = float((xc * yc).sum() / den)
    r2 = b * b * den / float((yc * yc).sum()) if float((yc * yc).sum()) > 0 else np.nan
    return b, r2


def main():
    t0 = time.time()
    luma = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    field = np.load(CACHE / "bee3-leg-field.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    argbest = np.load(CACHE / "bee3-leg-argbest.npy")
    best = np.load(CACHE / "bee3-leg-best.npy")
    n, h, w = luma.shape
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1

    fmask, _ = L.foreground_mask(sel0)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros((h, w), bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    band = valid & (dd >= BAND[0]) & (dd <= BAND[1])
    ref_px = valid & (dd >= REF_D)

    # ---------------- S0
    print("--- S0 drift shape, and whether my plants are the right shape ---",
          flush=True)
    lvl = np.empty(n)
    for k in range(n):
        lvl[k] = float(np.asarray(luma[k], np.float32)[ref_px].mean())
    Lref = float(lvl.mean())
    g_real = lvl / Lref
    rho_k = float(spearmanr(lvl, np.arange(n)).statistic)
    print(f"  argmax frame {int(lvl.argmax())}   max/min {lvl.max() / lvl.min():.4f}"
          f"   endpoint {lvl[0] / lvl[-1]:.4f}   Spearman rho vs k {rho_k:+.4f}",
          flush=True)
    print(f"  M99 section 12.3 on its decks: peak at frame 103-120, max/min "
          f"1.1818, endpoint 1.0380", flush=True)
    ordered = abs(rho_k) > 0.5
    print(f"  -> the real drift is {'SMOOTHLY ORDERED' if ordered else 'UNORDERED'}"
          f", so a smoothly-ordered plant is "
          f"{'the right shape' if ordered else 'the WRONG shape'}", flush=True)

    ramp = np.linspace(1 - PLANT, 1 + PLANT, n)
    kk = np.arange(n)
    hump = 1.0 + (HUMP_RATIO - 1.0) * np.exp(-0.5 * ((kk - HUMP_PEAK) / (n / 4.0)) ** 2)
    hump = hump / hump.mean()
    rng = np.random.default_rng(SEED)
    shuf = rng.permutation(n)
    for tag, gp in (("ramp", ramp), ("hump", hump)):
        print(f"  plant {tag:<5}: rho vs k {spearmanr(gp, kk).statistic:+.4f}   "
              f"max/min {gp.max() / gp.min():.4f}", flush=True)

    # ---------------- S1
    print("\n--- S1 index gap on M96's disconnected competitive set ---",
          flush=True)
    disc, gap96, cnt = m52.m96_stats(field, best)
    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    edges = np.searchsorted(dv[order], np.arange(0, DMAX + 2))

    def prof(img):
        v = img[valid][order]
        out = np.full(DMAX + 1, np.nan)
        for d in range(DMAX + 1):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    P = np.empty((n, DMAX + 1))
    for k in range(n):
        P[k] = prof(np.asarray(luma[k], np.float32))
    with np.errstate(invalid="ignore"):
        ens = np.nanmean(P, axis=0)
    far = float(np.nanmedian(ens[80:121]))
    ensmap = np.interp(dd, np.arange(DMAX + 1), np.nan_to_num(ens, nan=far))
    exc = (sel0 - ensmap) / far
    print(f"  disconnected on this ROI: {100 * float(disc[band].mean()):.3f}% of "
          f"band pixels (section 21.2 measured 27.083% ROI-wide)", flush=True)

    gap_roll = np.roll(gap96, ROLL, axis=(0, 1))

    def pooled(gmap, sub):
        num = wsum = 0.0
        for d in range(BAND[0], BAND[1] + 1):
            s = sub & (dd == d)
            if int(s.sum()) < 500 or float(gmap[s].std()) < 1e-6:
                continue
            r = spearmanr(gmap[s], exc[s]).statistic
            if np.isfinite(r):
                num += r * int(s.sum())
                wsum += int(s.sum())
        return num / wsum if wsum else float("nan")

    s1 = {}
    for tag, sub in (("disconnected", band & disc), ("connected", band & ~disc)):
        r = pooled(gap96, sub)
        r0 = pooled(gap_roll, sub)
        s1[tag] = {"rho": r, "rho_null": r0, "px": int(sub.sum())}
        print(f"  {tag:<13} n={int(sub.sum()):>7}   pooled rho(excess, M96 gap) "
              f"{r:+.4f}   rolled null {r0:+.4f}", flush=True)
    print("  ladder on the disconnected population:", flush=True)
    gb, eb = gap96[band & disc], exc[band & disc]
    for lo, hi in ((1, 5), (5, 20), (20, 60), (60, 150), (150, 400)):
        s = (gb >= lo) & (gb < hi)
        if s.sum() > 300:
            print(f"    gap [{lo:>3},{hi:>3}): {int(s.sum()):>7} px   median "
                  f"excess {np.median(eb[s]):+.5f}", flush=True)

    # ---------------- S2
    print("\n--- S2 the sign test ---", flush=True)
    ay, ax = np.where(band[:-1, :] & band[1:, :])
    by, bx = np.where(band[:, :-1] & band[:, 1:])
    pi = np.concatenate([np.ravel_multi_index((ay, ax), (h, w)),
                         np.ravel_multi_index((by, bx), (h, w))])
    qi = np.concatenate([np.ravel_multi_index((ay + 1, ax), (h, w)),
                         np.ravel_multi_index((by, bx + 1), (h, w))])
    kp = argbest.ravel()[pi]
    kq = argbest.ravel()[qi]
    diff = kp != kq
    pi, qi, kp, kq = pi[diff], qi[diff], kp[diff], kq[diff]
    print(f"  {len(pi)} adjacent background pairs in d{BAND} elected different "
          f"frames ({100 * len(pi) / max(int(diff.size), 1):.2f}% of adjacencies)",
          flush=True)

    def run(merged, g, tag):
        mp = merged.ravel()[pi]
        mq = merged.ravel()[qi]
        obs = mp - mq
        pred = 0.5 * (mp + mq) * (g[kp] - g[kq])
        keep = np.abs(pred) > 1e-9
        b, r2 = ols(pred[keep], obs[keep])
        thr = np.quantile(np.abs(pred[keep]), 0.5)
        big = keep & (np.abs(pred) >= thr)
        agree = float((np.sign(obs[big]) == np.sign(pred[big])).mean())
        amp = float(np.median(np.abs(pred[keep])) / np.median(np.abs(obs[keep])))
        print(f"  {tag:<26} slope {b:+8.4f}   R2 {r2:7.4f}   sign agreement "
              f"{100 * agree:5.2f}%   amplitude {100 * amp:6.2f}%", flush=True)
        return {"slope": b, "r2": float(r2), "sign_agreement": agree,
                "amplitude": amp, "n": int(keep.sum())}

    def compose(g):
        out = np.empty((h, w), np.float32)
        for k in range(n):
            s = argbest == k
            if s.any():
                out[s] = (np.asarray(luma[k], np.float32) * np.float32(g[k]))[s]
        return out

    s2 = {}
    s2["real"] = run(sel0, g_real, "REAL DATA")
    s2["null_shuffled"] = run(sel0, g_real[shuf], "C-NULL shuffled g")
    s2["pos_ramp"] = run(compose(ramp), g_real * ramp, "C-POS-RAMP planted +/-10%")
    s2["pos_hump"] = run(compose(hump), g_real * hump, "C-POS-HUMP M99 shape")

    r = s2["real"]
    pos_ok = (0.5 <= s2["pos_ramp"]["slope"] <= 1.5 and
              0.5 <= s2["pos_hump"]["slope"] <= 1.5)
    null_ok = abs(s2["null_shuffled"]["slope"]) < 0.25
    if 0.5 <= r["slope"] <= 1.5 and r["sign_agreement"] > 0.60:
        verdict = "CONFIRMED"
    elif abs(r["slope"]) < 0.25 and r["sign_agreement"] < 0.55 and pos_ok:
        verdict = "REFUTED"
    else:
        verdict = "PARTIAL"

    print("\n" + "=" * 74 + "\n=== VERDICT ===", flush=True)
    print(f"  controls: positive arms {'PASS' if pos_ok else 'FAIL'}  "
          f"(ramp {s2['pos_ramp']['slope']:+.4f}, hump "
          f"{s2['pos_hump']['slope']:+.4f});  null "
          f"{'PASS' if null_ok else 'FAIL'} ({s2['null_shuffled']['slope']:+.4f})",
          flush=True)
    print(f"  S2 photometric-step mechanism at the silhouette: {verdict}   "
          f"(slope {r['slope']:+.4f}, sign agreement "
          f"{100 * r['sign_agreement']:.2f}%, amplitude {100 * r['amplitude']:.2f}% "
          f"of the observed step)", flush=True)
    print(f"  S1 index-gap: disconnected rho {s1['disconnected']['rho']:+.4f} "
          f"against a {s1['disconnected']['rho_null']:+.4f} null -- a "
          f"photometric step predicts monotone POSITIVE", flush=True)

    rep = {"level": lvl.tolist(), "rho_level_vs_k": rho_k,
           "argmax": int(lvl.argmax()), "maxmin": float(lvl.max() / lvl.min()),
           "endpoint": float(lvl[0] / lvl[-1]), "ordered": bool(ordered),
           "plant_ramp_rho": float(spearmanr(ramp, kk).statistic),
           "plant_hump_rho": float(spearmanr(hump, kk).statistic),
           "hump_maxmin": float(hump.max() / hump.min()),
           "disc_pct_band": 100 * float(disc[band].mean()),
           "S1": s1, "S2": s2, "verdict": verdict,
           "pos_ok": bool(pos_ok), "null_ok": bool(null_ok),
           "n_pairs": int(len(pi))}
    with open(DATA / "79-sign-test.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '79-sign-test.json'}   {time.time() - t0:.0f}s",
          flush=True)


if __name__ == "__main__":
    main()

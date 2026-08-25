"""O3 -- commission the instrument on ground truth I built, before touching the capture.

Discipline 594: a null is a claim about the world only if the instrument could
have said otherwise, and you must SHOW the instrument saying otherwise. Nothing
here looks at the election. Everything here asks whether the two rules can find
a peak whose location I chose myself.

Controls run, all pre-registered in docs/research/M95-election-quality.md §6:

  K0  Sobel noise kernel: Monte Carlo vs the closed form 0.375*v
  K1  identity blur is EXACTLY identity (no resampling anywhere in the plant)
  K2  the blur plant recovers its own sigma
  P3  G1 and G2 are independent samples
  N0  noiseless ramp: elector and oracle agree >= 99 %   (magnitude-vs-energy confound)
  B2  noisy ramp: cross-fitted oracle within +/-1 frame of truth on >= 90 %
  N2  noiseless ramp: deficit reads ~0 for both rules
  P1s deficit is monotone in a forced offset, on synthetic
  P2  a frame with planted blur is not elected

The plant is a frequency-domain Gaussian: exactly known, exactly invertible in
the sense that it multiplies a spectrum by a closed form, and it RESAMPLES
NOTHING. That last point is the standing warning -- any plant that resamples has
already changed the quantity a sharpness metric measures.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import o2lib as O  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

CUBE = r"C:\dev\strehl-out\M95-oracle"
OUTD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

K = 41
KSTAR = 20
SIG0 = 0.15
PAD = 48


def fft_blur(img: np.ndarray, sigma: float) -> np.ndarray:
    """Exact Gaussian blur by spectrum multiplication. No resampling, no interpolation."""
    if sigma <= 0.0:
        return img.astype(np.float64).copy()
    a = np.pad(img.astype(np.float64), PAD, mode="reflect")
    h, w = a.shape
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    H = np.exp(-2.0 * (np.pi ** 2) * (sigma ** 2) * (fy * fy + fx * fx))
    out = np.real(np.fft.ifft2(np.fft.fft2(a) * H))
    return out[PAD:PAD + img.shape[0], PAD:PAD + img.shape[1]]


def trim(a: np.ndarray, m: int) -> np.ndarray:
    return a[m:-m, m:-m] if m else a


def argmax_stack(scores: np.ndarray) -> np.ndarray:
    return np.argmax(scores, axis=0).astype(np.int32)


def build(clean, noise, rng, noisy: bool):
    """Return (sel, ev) score stacks. sel selects, ev evaluates -- independent noise."""
    e_sel, o_sel, o_ev = [], [], []
    for k in range(K):
        s = fft_blur(clean, SIG0 * abs(k - KSTAR))
        if noisy:
            v = noise.var(s)
            a = s + rng.normal(0.0, np.sqrt(v))
            b = s + rng.normal(0.0, np.sqrt(v))
        else:
            a = b = s
        e_sel.append(O.elector_score(a, noise).astype(np.float32))
        o_sel.append(O.oracle_score(a, noise).astype(np.float32))
        o_ev.append(O.oracle_score(b, noise).astype(np.float32))
    return np.stack(e_sel), np.stack(o_sel), np.stack(o_ev)


def deficit(o_ev, choice_a, choice_b):
    """D = 1 - mean O_ev[choice_a] / mean O_ev[choice_b]."""
    ii, jj = np.indices(choice_a.shape)
    va = o_ev[choice_a, ii, jj]
    vb = o_ev[choice_b, ii, jj]
    return 1.0 - float(va.mean()) / float(vb.mean())


def main() -> int:
    os.makedirs(OUTD, exist_ok=True)
    meta = json.load(open(os.path.join(CUBE, "cube_meta.json"), encoding="utf-8"))
    black = meta["black"]
    res = {}

    print("=" * 74)
    print("K0  Sobel noise kernel: Monte Carlo vs closed form")
    k0 = O.test_sobel_noise_kernel()
    print(f"    measured {k0['measured']:.6f}  closed form {k0['closed_form']:.6f}  "
          f"ratio {k0['ratio']:.5f}")
    k0ok = abs(k0["ratio"] - 1.0) < 0.01
    print(f"    K0 {'PASS' if k0ok else 'FAIL'} (bar: ratio within 1 %)")
    res["K0"] = dict(**k0, passed=bool(k0ok))

    g1 = np.load(os.path.join(CUBE, "ROI-LOWDRIFT.g1.npy"), mmap_mode="r")
    g2 = np.load(os.path.join(CUBE, "ROI-LOWDRIFT.g2.npy"), mmap_mode="r")

    print("\nP3  G1/G2 independence")
    a183 = np.asarray(g1[183], dtype=np.float64)
    b183 = np.asarray(g2[183], dtype=np.float64)
    eq = float(np.mean(a183 == b183)) * 100.0
    r = float(np.corrcoef((a183 - a183.mean()).ravel(), (b183 - b183.mean()).ravel())[0, 1])
    print(f"    identical pixels {eq:.4f} %   scene correlation r={r:.4f}")
    p3ok = eq < 50.0
    print(f"    P3 {'PASS' if p3ok else 'FAIL'} (bar: < 50 % identical)")
    res["P3"] = dict(pct_identical=eq, r=r, passed=bool(p3ok))

    print("\n--  noise model, fitted from G1-G2 on the FLAT roi of this capture")
    f1 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g1.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    f2 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g2.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    noise, fit = O.fit_noise(f1.reshape(-1, f1.shape[-1]), f2.reshape(-1, f2.shape[-1]), black)
    print(f"    {noise}   R^2={fit['r2']:.5f} over {len(fit['x'])} level bins")
    res["noise"] = dict(gain=noise.gain, floor=noise.floor, black=black, r2=fit["r2"],
                        nbins=len(fit["x"]))

    print("\nK1  identity blur must be EXACTLY identity")
    src = np.asarray(g1[183], dtype=np.float64)
    d0 = float(np.abs(fft_blur(src, 0.0) - src).max())
    print(f"    max abs diff at sigma=0: {d0:.10g}")
    k1ok = d0 == 0.0
    print(f"    K1 {'PASS' if k1ok else 'FAIL'} (bar: exactly 0)")
    res["K1"] = dict(max_abs_diff=d0, passed=bool(k1ok))

    print("\nK2  the plant recovers its own sigma (windowed frequency-domain fit)")
    k2 = []
    base = trim(src, 96)
    for s in (0.25, 0.50, 1.00, 1.50):
        b = trim(fft_blur(src, s), 96)
        est = O.recover_sigma(base, b)
        k2.append(dict(planted=s, recovered=est, err_pct=100.0 * (est - s) / s))
        print(f"    sigma {s:.2f} -> recovered {est:.4f}  ({100.0*(est-s)/s:+.2f} %)")
    k2ok = all(abs(r["err_pct"]) < 5.0 for r in k2)
    print(f"    K2 {'PASS' if k2ok else 'FAIL'} (bar: within 5 %)")
    res["K2"] = dict(rows=k2, passed=bool(k2ok))

    clean = src
    m = PAD + O.BOX_R + 1

    print("\nN0  noiseless ramp: does magnitude-vs-energy change the answer?")
    e_s, o_s, o_e = build(clean, noise, np.random.default_rng(1), noisy=False)
    ea, oa = argmax_stack(e_s), argmax_stack(o_s)
    eam, oam = trim(ea, O.BOX_R + 1), trim(oa, O.BOX_R + 1)
    agree = float(np.mean(eam == oam)) * 100.0
    e_true = float(np.mean(eam == KSTAR)) * 100.0
    o_true = float(np.mean(oam == KSTAR)) * 100.0
    print(f"    elector==oracle {agree:.4f} %   elector==truth {e_true:.4f} %   "
          f"oracle==truth {o_true:.4f} %")
    n0ok = agree >= 99.0
    print(f"    N0 {'PASS' if n0ok else 'FAIL'} (bar: >= 99 % agreement)")
    res["N0"] = dict(agree_pct=agree, elector_true_pct=e_true, oracle_true_pct=o_true,
                     passed=bool(n0ok))

    print("\nN2  noiseless ramp: the deficit must have a zero")
    d_noiseless = deficit(o_e, eam, oam) * 100.0
    print(f"    D(elector vs oracle), noiseless = {d_noiseless:+.4f} %")
    n2ok = abs(d_noiseless) < 1.0
    print(f"    N2 {'PASS' if n2ok else 'FAIL'} (bar: |D| < 1 %)")
    res["N2"] = dict(D_pct=d_noiseless, passed=bool(n2ok))

    print("\nB2  noisy ramp: cross-fitted oracle vs truth")
    e_s, o_s, o_e = build(clean, noise, np.random.default_rng(2), noisy=True)
    ea, oa = argmax_stack(e_s), argmax_stack(o_s)
    eam, oam = trim(ea, O.BOX_R + 1), trim(oa, O.BOX_R + 1)
    o_w1 = float(np.mean(np.abs(oam - KSTAR) <= 1)) * 100.0
    e_w1 = float(np.mean(np.abs(eam - KSTAR) <= 1)) * 100.0
    print(f"    oracle within +/-1 of truth : {o_w1:.4f} %")
    print(f"    elector within +/-1 of truth: {e_w1:.4f} %")
    print(f"    median |offset|  oracle {np.median(np.abs(oam-KSTAR)):.2f}  "
          f"elector {np.median(np.abs(eam-KSTAR)):.2f}")
    b2ok = o_w1 >= 90.0
    print(f"    B2 {'PASS' if b2ok else 'FAIL'} (bar: >= 90 %)")
    res["B2"] = dict(oracle_within1_pct=o_w1, elector_within1_pct=e_w1,
                     oracle_med_off=float(np.median(np.abs(oam - KSTAR))),
                     elector_med_off=float(np.median(np.abs(eam - KSTAR))),
                     passed=bool(b2ok))

    print("\nP1s  deficit must be monotone in a FORCED offset (synthetic)")
    rows = []
    for off in (0, 1, 2, 5, 10, 25):
        forced = np.clip(oam + off, 0, K - 1)
        d = deficit(o_e, forced, oam) * 100.0
        rows.append(dict(offset=off, D_pct=d))
        print(f"    forced +{off:2d} frames -> D = {d:+8.4f} %")
    seq = [r["D_pct"] for r in rows]
    p1ok = all(seq[i] < seq[i + 1] for i in range(len(seq) - 1))
    print(f"    P1s {'PASS' if p1ok else 'FAIL'} (bar: strictly increasing)")
    print(f"    sign convention read off this control: a WORSE choice gives a "
          f"{'POSITIVE' if seq[-1] > 0 else 'NEGATIVE'} D")
    res["P1s"] = dict(rows=rows, passed=bool(p1ok), positive_is_worse=bool(seq[-1] > 0))

    print("\nP2  a frame with planted blur must not be elected")
    e_s2 = e_s.copy()
    o_s2 = o_s.copy()
    kk = KSTAR
    bad = fft_blur(clean, 1.0)
    v = noise.var(bad)
    rng = np.random.default_rng(3)
    a = bad + rng.normal(0.0, np.sqrt(v))
    e_s2[kk] = O.elector_score(a, noise).astype(np.float32)
    o_s2[kk] = O.oracle_score(a, noise).astype(np.float32)
    e_pick = float(np.mean(trim(argmax_stack(e_s2), O.BOX_R + 1) == kk)) * 100.0
    o_pick = float(np.mean(trim(argmax_stack(o_s2), O.BOX_R + 1) == kk)) * 100.0
    before = float(np.mean(eam == kk)) * 100.0
    print(f"    frame {kk} elected before plant: {before:.4f} %")
    print(f"    after sigma=1.0 plant -- elector {e_pick:.4f} %   oracle {o_pick:.4f} %")
    p2ok = e_pick < before and o_pick < before
    print(f"    P2 {'PASS' if p2ok else 'FAIL'} (bar: both demote it)")
    res["P2"] = dict(before_pct=before, elector_pct=e_pick, oracle_pct=o_pick,
                     passed=bool(p2ok))

    names = ["K0", "K1", "K2", "P3", "N0", "N2", "B2", "P1s", "P2"]
    npass = sum(1 for n in names if res[n]["passed"])
    print("\n" + "=" * 74)
    print(f"COMMISSIONING: {npass}/{len(names)} controls passed")
    for n in names:
        print(f"   {n:4s} {'PASS' if res[n]['passed'] else 'FAIL'}")
    with open(os.path.join(OUTD, "o3_commission.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(f"wrote {os.path.join(OUTD, 'o3_commission.json')}")
    return 0 if npass == len(names) else 1


if __name__ == "__main__":
    raise SystemExit(main())

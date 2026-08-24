"""M70 s09 - the decomposition that decides core versus plugin.

The charter's decisive words are that off-peak frames must carry mid-band
signal that is "substantial, *distinct*". Substantial is settled: s08 measured
rel_amp_1 = 0.879-0.970 and n_eff(+-5) = 3.4-6.8 on all twelve stacks.
Distinctness is a separate question and it is the one that decides the
architecture, because a matched filter over frames whose transfer functions
differ only by a SCALE degenerates exactly into a weighted average - and a
weighted average of admitted frames is what the shipped gated mean already is.

Two measurements.

  1. THE GAIN DECOMPOSITION. The matched filter's total SNR gain over averaging
     the best m frames factors exactly into

        total(m) = weight_gain(m) x reach_gain(m)

        weight_gain(m) = sqrt(m . sum_{top m}|H|^2) / sum_{top m}|H|
        reach_gain(m)  = sqrt(sum_all |H|^2 / sum_{top m}|H|^2)

     weight_gain is 1 exactly when the admitted frames have equal |H|: it is
     the gain from optimal WEIGHTING of frames the merge already uses.
     reach_gain is the gain from frames the merge does not use at all. The
     architectural consequence differs completely: a large weight_gain argues
     for a matched filter in the merge, a large reach_gain argues only for
     widening the gate.

  2. SHAPE COLLINEARITY. Whether off-peak frames carry DIFFERENT frequencies,
     not just less of the same ones. For frames within +-W of peak, build the
     band-amplitude matrix, normalise each frame's row to unit length so only
     spectral SHAPE survives, and take the SVD. The first singular value's
     share of the energy is 1 exactly when every frame is a scaled copy of
     every other - the case in which deconvolution along the focus axis can
     recover nothing that a weighted average cannot.

     Controls: the s03 plant, where the OTF shape variation is known and swept
     over 16x in step density, and a synthetic rank-1 case that must return
     exactly 1.000.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
import s03_plant as P3  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402

OUT = A5.OUT
STACKS = S7.STACKS
APERTURE = S7.APERTURE
SHAPE_BANDS = ("b2", "b3_mid", "b4_mid", "b5_mid", "b6_above_f11_cut")


def decompose(s: np.ndarray, m: int, W: int | None = None):
    """s: (K,) noise-subtracted band power. Returns weight/reach/total gain."""
    ssm = M.smooth3(s)
    i = int(np.argmax(ssm))
    sel = s if W is None else s[max(0, i - W): min(s.size, i + W + 1)]
    order = np.sort(sel)[::-1]
    top = order[:m]
    tot_top = float(np.clip(top, 0.0, None).sum())
    tot_all = float(sel.sum())
    amp = float(np.sqrt(np.clip(top, 0.0, None)).sum())
    if amp <= 0 or tot_top <= 0:
        return np.nan, np.nan, np.nan
    weight = float(np.sqrt(m * tot_top) / amp)
    reach = float(np.sqrt(max(tot_all, 0.0) / tot_top))
    return weight, reach, weight * reach


def shape_collinearity(sm: np.ndarray, W: int) -> float:
    """sm: (K, B) band power. Row-normalise the amplitude within +-W of the
    peak of the band-summed response, then report s1^2 / sum s^2."""
    tot = sm.sum(axis=1)
    i = int(np.argmax(M.smooth3(tot)))
    lo, hi = max(0, i - W), min(sm.shape[0], i + W + 1)
    A = np.sqrt(np.clip(sm[lo:hi], 0.0, None))
    n = np.linalg.norm(A, axis=1, keepdims=True)
    keep = (n[:, 0] > 0)
    if keep.sum() < 2:
        return np.nan
    A = A[keep] / n[keep]
    sv = np.linalg.svd(A, compute_uv=False)
    return float(sv[0] ** 2 / (sv ** 2).sum())


def controls():
    print("=" * 100)
    print("0. CONTROLS FOR THE SHAPE STATISTIC")
    print("=" * 100)
    rng = np.random.default_rng(909)
    # rank-1: every frame a scaled copy. Must return exactly 1.000.
    base = np.array([9.0, 4.0, 2.0, 1.0, 0.4])
    scales = np.linspace(1.0, 0.05, 41)[:, None] ** 2
    print(f"  synthetic rank-1 (scaled copies)      s1^2 share = "
          f"{shape_collinearity(base[None, :] * scales, 5):.4f}   (must be 1.0000)")
    # pure noise rows: must be far below 1
    noise = np.abs(rng.normal(size=(41, 5)))
    print(f"  synthetic rank-full (iid noise rows)  s1^2 share = "
          f"{shape_collinearity(noise, 5):.4f}")

    latent, _ = P3.load_latent()
    K = 41
    print()
    print(f"  {'plant case':>14s} {'s1^2 share':>11s} {'weight(3)':>10s} {'reach(3)':>9s} "
          f"{'total(3)':>9s}")
    out = []
    for tag, radii in [("static", [0.0] * K)] + [
        (f"delta {dd}", [abs(k - K // 2) * dd for k in range(K)])
        for dd in (0.125, 0.25, 0.5, 1.0, 2.0)
    ]:
        noisy = P3.make_frames(latent, radii, P3.LATENT_ISO, rng, noise=True)
        mn = P3.measure_frames(noisy, P3.LATENT_ISO, subtract_noise=True)
        sm = np.array([[r[b] for b in SHAPE_BANDS] for r in mn])
        sc = shape_collinearity(sm, 5)
        j = SHAPE_BANDS.index("b4_mid")
        w, rch, t = decompose(sm[:, j], 3, 5)
        print(f"  {tag:>14s} {sc:11.4f} {w:10.4f} {rch:9.4f} {t:9.4f}")
        out.append({"case": tag, "shape": sc, "weight3": w, "reach3": rch})
    return out


def main() -> None:
    ctl = controls()

    rows = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d)
        tex, _ = A5.classify(d, s, nvar)
        idx = [p for p in range(s.shape[1]) if tex[p]]
        jb = [d["bands"].index(b) for b in SHAPE_BANDS]
        r = {"stack": st, "K": int(s.shape[0]), "F": APERTURE[st], "n_tex": len(idx)}
        for W in (3, 5, 10):
            r[f"shape_w{W}"] = A5.med([shape_collinearity(s[:, p, :][:, jb], W)
                                       for p in idx])
        for m in (2, 3, 5):
            for W in (3, 5, None):
                key = "inf" if W is None else str(W)
                ws, rs, ts = [], [], []
                for b in M.MID_BANDS:
                    j = d["bands"].index(b)
                    v = [decompose(s[:, p, j], m, W) for p in idx]
                    ws.append(A5.med([x[0] for x in v]))
                    rs.append(A5.med([x[1] for x in v]))
                    ts.append(A5.med([x[2] for x in v]))
                r[f"w{key}_m{m}_weight"] = float(np.mean(ws))
                r[f"w{key}_m{m}_reach"] = float(np.mean(rs))
                r[f"w{key}_m{m}_total"] = float(np.mean(ts))
        rows.append(r)

    print()
    print("=" * 118)
    print("1. THE GAIN DECOMPOSITION, mid band, median over textured patches")
    print("   weight = matched filter vs EQUAL average of the SAME best-3 frames")
    print("   reach  = including frames beyond the best 3")
    print("=" * 118)
    print(f"{'stack':16s} {'K':>4s} {'F':>5s} | {'weight3':>8s} {'reach3':>7s} {'tot3':>6s}"
          f" (+-3) | {'weight3':>8s} {'reach3':>7s} {'tot3':>6s} (+-5) | "
          f"{'weight3':>8s} {'reach3':>7s} {'tot3':>6s} (all)")
    for r in rows:
        print(f"{r['stack']:16s} {r['K']:4d} {r['F']:5.1f} | "
              f"{r['w3_m3_weight']:8.4f} {r['w3_m3_reach']:7.4f} {r['w3_m3_total']:6.3f}       | "
              f"{r['w5_m3_weight']:8.4f} {r['w5_m3_reach']:7.4f} {r['w5_m3_total']:6.3f}       | "
              f"{r['winf_m3_weight']:8.4f} {r['winf_m3_reach']:7.4f} {r['winf_m3_total']:6.3f}")
    wq = [r["w5_m3_weight"] for r in rows]
    rq = [r["w5_m3_reach"] for r in rows]
    print(f"\n  weight_gain(3) over the corpus: min {min(wq):.4f}  median "
          f"{np.median(wq):.4f}  max {max(wq):.4f}")
    print(f"  reach_gain(3, +-5)            : min {min(rq):.4f}  median "
          f"{np.median(rq):.4f}  max {max(rq):.4f}")

    print()
    print("=" * 118)
    print("2. SHAPE COLLINEARITY - is the off-peak signal DIFFERENT, or just smaller?")
    print("   s1^2 share = 1.0000 means every frame's spectrum is a scaled copy of")
    print("   every other, in which case a matched filter IS a weighted average.")
    print("=" * 118)
    print(f"{'stack':16s} {'K':>4s} {'F':>5s} {'+-3':>9s} {'+-5':>9s} {'+-10':>9s}")
    for r in rows:
        print(f"{r['stack']:16s} {r['K']:4d} {r['F']:5.1f} {r['shape_w3']:9.4f} "
              f"{r['shape_w5']:9.4f} {r['shape_w10']:9.4f}")
    s5 = [r["shape_w5"] for r in rows]
    print(f"\n  s1^2 share at +-5 over the corpus: min {min(s5):.4f}  median "
          f"{np.median(s5):.4f}  max {max(s5):.4f}")

    print()
    print("=" * 118)
    print("3. CRITERION D on the window-bounded statistic (the one that survives "
          "the sigma sensitivity)")
    print("=" * 118)
    import s08_decisive  # noqa: F401  (only for the file's presence)
    with open(os.path.join(OUT, "s08_decisive.json"), encoding="utf-8") as fh:
        s08 = json.load(fh)
    k = np.array([r["K"] for r in s08["rows"]], dtype=float)
    for key, lab in (("w1_n_eff", "n_eff(+-1)"), ("w3_n_eff", "n_eff(+-3)"),
                     ("w5_n_eff", "n_eff(+-5)"), ("winf_n_eff", "n_eff(all)")):
        v = np.array([r[key] for r in s08["rows"]], dtype=float)
        sl = np.polyfit(np.log(k), np.log(np.clip(v, 1e-6, None)), 1)[0]
        r2 = np.corrcoef(np.log(k), np.log(np.clip(v, 1e-6, None)))[0, 1] ** 2
        sp = v.max() / v.min()
        verdict = "HABIT" if 0.7 <= sl <= 1.3 else ("PHYSICS" if sp < 3.0 else "INDET")
        print(f"  {lab:12s} slope {sl:+.3f} (R2 {r2:.2f})  spread {sp:5.2f}x over a "
              f"{k.max() / k.min():.1f}x range in K  ->  {verdict}")

    with open(os.path.join(OUT, "s09_decomposition.json"), "w", encoding="utf-8") as fh:
        json.dump({"controls": ctl, "rows": rows}, fh, indent=1)
    print("\nwrote out/s09_decomposition.json")


if __name__ == "__main__":
    main()

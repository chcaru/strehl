"""M70 s25 - does M69's refutation of the noise floor's FORM reach my domain?

M69 refuted the FORM of `FOCUS_NOISE_SD`: the same operator's response noise
spans 4.06x on a plant and p05-p95 = 2.0x within a real stack, driven by
gradient-DIRECTION coherence across a 27x27 window rather than by SNR.

Read at source, M69's `sigma_F` is the response noise of a SPATIAL GRADIENT
OPERATOR (line 143: "3x3 Sobel scaled by 0.125 -> box_mean radius 13"). Mine is
the noise floor of a BAND-POWER SPECTRUM. Different operators, different
domains, and M69 makes no spectral claim anywhere - it never mentions the
diffraction cutoff, f_sig, 0.2762, MTF or Nyquist.

So the relay's inference does not transfer automatically. But the CONDITIONAL it
poses is a fair question and is worth answering with a number rather than with
that observation:

    "If any part of your spectral analysis assumes a spatially uniform
     response-noise floor, that assumption is now measured false."

Three arms:

  A  Is my floor spatially uniform? Measure the per-patch ratio of the MEASURED
     floor (band b6, above the f/11 cutoff, structure-free by fact 27) to the
     MODELLED photon-transfer variance, and report the within-stack p05-p95
     span - the same statistic M69 reports as 2.0x.

  B  If it is not uniform, is it TEXTURE-driven, which is M69's mechanism? Test
     the per-patch floor ratio against how much structure the patch carries.

  C  Does it matter? The floor sets the band edge. Recompute the headline
     matched-filter gain at the shipped gate's width under four different
     mid-band definitions, including one that extends PAST the cutoff into the
     band fact 27 says is pure noise.
"""

from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import m70lib as M  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402
import s16_null_band as S16  # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")
M69_WITHIN_STACK = 2.0     # M69's reported p05-p95 span for sigma_F
M69_PLANT = 4.06           # M69's reported plant span


def hdr(t):
    print("\n" + "=" * 118)
    print(t)
    print("=" * 118)


def pear(a, b):
    a = np.asarray(a, float) - np.mean(a)
    b = np.asarray(b, float) - np.mean(b)
    d = math.sqrt(float((a * a).sum() * (b * b).sum()))
    return float((a * b).sum() / d) if d > 0 else float("nan")


def main() -> None:
    res = {"m69_within_stack": M69_WITHIN_STACK, "m69_plant": M69_PLANT}

    hdr("ARM A - is my SPECTRAL noise floor spatially uniform within a stack?")
    print("  Per patch: measured floor (band b6, 0.2762-0.34 cyc/px, above the f/11")
    print("  cutoff and structure-free by fact 27) divided by the MODELLED photon-")
    print("  transfer variance at that patch's own level. A perfect model on a")
    print("  uniform floor gives 1.000 everywhere.")
    print(f"\n{'stack':<16}{'median':>9}{'p05':>8}{'p95':>8}{'p05-p95 span':>14}"
          f"{'min':>8}{'max':>8}{'full span':>11}")
    res["arm_a"] = {}
    spans = []
    for st in S16.STACKS:
        d = A5.load(st)
        nvar = M.noise_var_dn2(d["level"], d["iso"])          # (K,P)
        b6 = d["bands"].index("b6_above_f11_cut")
        ratio = d["power"][:, :, b6] / np.clip(nvar, 1e-30, None)
        per_patch = np.median(ratio, axis=0)                   # median over frames
        p05, p95 = np.percentile(per_patch, [5, 95])
        span = float(p95 / p05) if p05 > 0 else float("nan")
        spans.append(span)
        e = {"median": float(np.median(per_patch)), "p05": float(p05),
             "p95": float(p95), "span": span, "min": float(per_patch.min()),
             "max": float(per_patch.max()),
             "full_span": float(per_patch.max() / max(per_patch.min(), 1e-30)),
             "n_patch": int(per_patch.size)}
        res["arm_a"][st] = e
        print(f"{st:<16}{e['median']:>9.3f}{p05:>8.3f}{p95:>8.3f}{span:>14.3f}"
              f"{e['min']:>8.3f}{e['max']:>8.3f}{e['full_span']:>11.3f}")
    sp = np.array(spans)
    print(f"\n  corpus median within-stack p05-p95 span : {np.median(sp):.3f}x")
    print(f"  worst stack                             : {sp.max():.3f}x")
    print(f"  M69's sigma_F within a real stack       : {M69_WITHIN_STACK:.3f}x")
    print(f"  M69's sigma_F on its controlled plant   : {M69_PLANT:.3f}x")
    res["span_median"] = float(np.median(sp))
    res["span_max"] = float(sp.max())

    hdr("ARM B - if it varies, is it TEXTURE-driven (M69's mechanism)?")
    print("  M69's driver is gradient-DIRECTION coherence, a texture property. The")
    print("  analogue here: does a patch's floor ratio track how much STRUCTURE the")
    print("  patch carries? Structure proxy = peak mid-band signal power.")
    print(f"\n{'stack':<16}{'corr(texture, floor ratio)':>28}{'corr(level, ratio)':>21}")
    res["arm_b"] = {}
    cs_t, cs_l = [], []
    for st in S16.STACKS:
        d = A5.load(st)
        nvar = M.noise_var_dn2(d["level"], d["iso"])
        b6 = d["bands"].index("b6_above_f11_cut")
        ratio = np.median(d["power"][:, :, b6] / np.clip(nvar, 1e-30, None), axis=0)
        s, _ = A5.signal(d, 1.0)
        mid = [d["bands"].index(b) for b in M.MID_BANDS]
        tex = s[:, :, mid].sum(axis=2).max(axis=0)             # peak mid-band signal
        lvl = np.median(d["level"], axis=0)
        ct, cl = pear(tex, ratio), pear(lvl, ratio)
        cs_t.append(ct)
        cs_l.append(cl)
        res["arm_b"][st] = {"corr_texture": ct, "corr_level": cl}
        print(f"{st:<16}{ct:>+28.3f}{cl:>+21.3f}")
    print(f"\n  median corr(texture, floor ratio) : {np.median(cs_t):+.3f}   "
          f"({int(sum(1 for c in cs_t if c > 0))}/12 positive)")
    print(f"  median corr(level,   floor ratio) : {np.median(cs_l):+.3f}   "
          f"({int(sum(1 for c in cs_l if c > 0))}/12 positive)")
    res["corr_texture_median"] = float(np.median(cs_t))
    res["corr_level_median"] = float(np.median(cs_l))

    hdr("ARM C - does the band edge change the verdict? Four band definitions.")
    print("  The headline is the matched filter's gain over an EQUAL AVERAGE of the")
    print("  SAME frames at the shipped gate's width (W=3, seven frames; section 18.2).")
    print("  If moving the boundary between 'recoverable band' and 'noise floor'")
    print("  changed that number materially, the band edge would be load-bearing.")
    defs = {
        "b3 only (0.100-0.150)": ("b3_mid",),
        "b3+b4 (0.100-0.200)": ("b3_mid", "b4_mid"),
        "b3+b4+b5 = SHIPPED MID (0.100-0.2762)": ("b3_mid", "b4_mid", "b5_mid"),
        "b3..b6 PAST THE CUTOFF (0.100-0.340)": ("b3_mid", "b4_mid", "b5_mid",
                                                 "b6_above_f11_cut"),
    }
    print(f"\n{'band definition':<40}{'MF / equal avg, W=3':>22}{'vs shipped':>12}")
    res["arm_c"] = {}
    base = None
    for name, bands in defs.items():
        per = []
        for st in S16.STACKS:
            d = A5.load(st)
            s, _ = A5.signal(d, 1.0)
            idx = [d["bands"].index(b) for b in bands]
            tex, _ = A5.classify(d, s, M.noise_var_dn2(d["level"], d["iso"]))
            for p in np.where(tex)[0]:
                for j in idx:
                    c = s[:, p, j].astype(np.float64)
                    i_pk = int(np.argmax(M.smooth3(c)))
                    lo, hi = max(0, i_pk - 3), min(c.size, i_pk + 4)
                    w = c[lo:hi]
                    if w.size < 3 or w.sum() <= 0:
                        continue
                    amp = np.sqrt(np.clip(w, 0.0, None))
                    if amp.sum() <= 0:
                        continue
                    # MF over the window / equal average of the same frames
                    per.append(float(np.sqrt(w.sum()) * math.sqrt(w.size) / amp.sum()))
        v = float(np.median(per)) if per else float("nan")
        if "SHIPPED" in name:
            base = v
        res["arm_c"][name] = {"gain": v, "n": len(per)}
        print(f"{name:<40}{v:>22.4f}"
              f"{('' if base is None else f'{v / base:>11.4f}x'):>12}")
    for k in res["arm_c"]:
        res["arm_c"][k]["vs_shipped"] = res["arm_c"][k]["gain"] / base
    gains = [v["gain"] for v in res["arm_c"].values()]
    print(f"\n  span across all four band definitions: {max(gains) / min(gains):.4f}x")
    print(f"  the report's headline at W=3 is 1.0238; the whole architectural")
    print(f"  prize (P1) is 1.1100. Band-edge choice moves the gain by "
          f"{100 * (max(gains) / min(gains) - 1):.2f}%.")
    res["arm_c_span"] = float(max(gains) / min(gains))

    with open(os.path.join(OUT, "s25_floor_uniformity.json"), "w") as f:
        json.dump(res, f, indent=1)
    print("\nwrote out/s25_floor_uniformity.json")


if __name__ == "__main__":
    main()

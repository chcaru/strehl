"""M70 s11 - the final architectural number, with the noise model's own
uncertainty carried through.

s10 showed that the equal-weight average has an optimum: adding frames whose
|H| is small grows the signal by sum|H| but the noise by sqrt(n), so past a
point a wider equal average gets WORSE (coffee-bubbles falls to 0.755 at +-20).
The matched filter does not degrade - down-weighting weak frames is exactly
what it is for.

So the fair architectural comparison is not "matched filter vs the three-frame
average". It is:

    best_avg  = max over W of the equal-weight average's gain     <- what the
                                                                     shipped
                                                                     merge can
                                                                     reach by
                                                                     moving a
                                                                     gate
    best_mf   = max over W of the matched filter's gain           <- what a
                                                                     focus-axis
                                                                     Wiener
                                                                     merge could
                                                                     reach
    headroom  = best_mf / best_avg

`headroom` is the entire architectural prize on the focus axis. Everything
else the proposal offers - the diffraction inversion - is a different term,
was measured separately by M41, and was refuted there on the noise axis.

Windows are capped at +-10 for the headline because s08 measured that the
unwindowed sum is not stable against fact 29's measured +-9% uncertainty in the
photon-transfer model; +-20 and +-inf are reported but flagged.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402
import s10_architecture as S10  # noqa: E402

OUT = A5.OUT
STACKS = S7.STACKS
APERTURE = S7.APERTURE


def run(sigma_scale, wmax):
    ws = [w for w in S10.WINDOWS if w <= wmax]
    rows = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d, sigma_scale)
        tex, _ = A5.classify(d, s, nvar)
        idx = [p for p in range(s.shape[1]) if tex[p]]
        best_avg, best_mf, arg_a, arg_m = -np.inf, -np.inf, None, None
        per_w = {}
        for W in ws:
            a, t = [], []
            for bd in M.MID_BANDS:
                j = d["bands"].index(bd)
                v = [S10.gains(s[:, p, j], W) for p in idx]
                a.append(A5.med([x[1] for x in v]))
                t.append(A5.med([x[2] for x in v]))
            av, tv = float(np.mean(a)), float(np.mean(t))
            per_w[W] = (av, tv)
            if av > best_avg:
                best_avg, arg_a = av, W
            if tv > best_mf:
                best_mf, arg_m = tv, W
        rows.append({"stack": st, "K": int(s.shape[0]), "F": APERTURE[st],
                     "best_avg": best_avg, "W_avg": arg_a,
                     "best_mf": best_mf, "W_mf": arg_m,
                     "headroom": best_mf / best_avg, "per_w": per_w})
    return rows


def main() -> None:
    out = {}
    for wmax, label in ((10, "windows up to +-10 (stable against the measured "
                             "+-9% noise-model uncertainty)"),
                        (20, "windows up to +-20 (NOT stable; reported, flagged)")):
        print("=" * 112)
        print(f"HEADROOM: matched filter over the best equal-weight average, {label}")
        print("=" * 112)
        print(f"{'stack':16s} {'K':>4s} {'F':>5s} {'best avg':>9s} {'at W':>5s} "
              f"{'best MF':>8s} {'at W':>5s} {'headroom':>9s}")
        for sc in (0.91, 1.00, 1.09):
            rows = run(sc, wmax)
            if sc == 1.00:
                for r in rows:
                    print(f"{r['stack']:16s} {r['K']:4d} {r['F']:5.1f} "
                          f"{r['best_avg']:9.4f} {'+-' + str(r['W_avg']):>5s} "
                          f"{r['best_mf']:8.4f} {'+-' + str(r['W_mf']):>5s} "
                          f"{r['headroom']:9.4f}")
            h = [r["headroom"] for r in rows]
            print(f"  sigma x{sc:.2f}  headroom: min {min(h):.4f}  median "
                  f"{np.median(h):.4f}  max {max(h):.4f}   "
                  f"({100 * (np.median(h) - 1):+.1f}% SNR in the mid band)")
            out[f"w{wmax}_sigma{sc}"] = rows
        print()

    rows = run(1.00, 10)
    print("=" * 112)
    print("SUMMARY OF THE ARCHITECTURAL PRIZE (mid band, 0.100-0.2762 sensor cyc/px)")
    print("=" * 112)
    h = np.median([r["headroom"] for r in rows])
    ba = np.median([r["best_avg"] for r in rows])
    print(f"  a wider equal-weight average, over the best window, buys   "
          f"{100 * (ba - 1):+5.1f}% SNR over a 3-frame average")
    print(f"  a focus-axis matched filter buys, on top of that,          "
          f"{100 * (h - 1):+5.1f}% SNR")
    print(f"  in noise-equivalent terms that is a factor {h:.4f}, i.e. "
          f"{20 * np.log10(h):+.2f} dB")
    print()
    print("  For scale: fact 19 measures the SHIPPED gated mean at 0.534x single-frame")
    print("  noise, a factor of 1.873 (+5.45 dB), in every band it admits.")
    print(f"  The focus-axis matched filter's mid-band-only prize is {20 * np.log10(h):+.2f} dB,")
    print(f"  or {100 * np.log10(h) / np.log10(1.873):.1f}% of what the existing merge already delivers.")

    with open(os.path.join(OUT, "s11_headroom.json"), "w", encoding="utf-8") as fh:
        json.dump({k: [{kk: vv for kk, vv in r.items() if kk != "per_w"} for r in v]
                   for k, v in out.items()}, fh, indent=1)
    print("\nwrote out/s11_headroom.json")


if __name__ == "__main__":
    main()

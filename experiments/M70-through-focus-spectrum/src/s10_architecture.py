"""M70 s10 - the number that decides the architecture.

s09 measured the matched filter's gain over an equal average of the SAME best
three frames: 1.0009-1.0107, median 1.0020. This script generalises it to
every window, and prices the non-deconvolution alternative next to it.

Three quantities per patch and mid band, over the frames within +-W of peak:

  mf_vs_avg(W)   sqrt(n . sum|H|^2) / sum|H|   over the n = 2W+1 frames in the
                 window. This is EXACTLY the SNR gain a matched filter buys
                 over averaging those same frames with equal weights. It is 1
                 when the admitted frames have equal |H|, and it is the entire
                 architectural value of putting a matched filter in the merge.

  avg_vs_avg3(W) [sum_W |H| / sqrt(n)] / [sum_3 |H| / sqrt(3)]. The gain from
                 simply averaging more frames - available to the shipped merge
                 by changing a gate threshold, with no deconvolution anywhere.

  mf_vs_avg3(W)  the product: the full matched-filter gain over the shipped
                 three-frame-equivalent average.

Equal-weight averaging assumes the admitted frames' transfer functions share a
sign. Within +-5 frames of peak the measured relative amplitude is 0.46-0.86,
far from the first OTF zero, so no sign change is in the window. Stated because
it is an assumption, not a measurement.
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

OUT = A5.OUT
STACKS = S7.STACKS
APERTURE = S7.APERTURE
WINDOWS = (1, 2, 3, 5, 10, 20)


def window_slice(s, W):
    i = int(np.argmax(M.smooth3(s)))
    return s[max(0, i - W): min(s.size, i + W + 1)]


def gains(s, W):
    sel = np.clip(window_slice(s, W), 0.0, None)
    n = sel.size
    amp = np.sqrt(sel)
    sa, ss = float(amp.sum()), float(sel.sum())
    if sa <= 0:
        return np.nan, np.nan, np.nan
    mf_vs_avg = float(np.sqrt(n * ss) / sa)
    sel3 = np.clip(window_slice(s, 1), 0.0, None)
    amp3 = np.sqrt(sel3)
    sa3, n3 = float(amp3.sum()), sel3.size
    if sa3 <= 0:
        return mf_vs_avg, np.nan, np.nan
    avg_vs_avg3 = float((sa / np.sqrt(n)) / (sa3 / np.sqrt(n3)))
    return mf_vs_avg, avg_vs_avg3, mf_vs_avg * avg_vs_avg3


def main() -> None:
    rows = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d)
        tex, _ = A5.classify(d, s, nvar)
        idx = [p for p in range(s.shape[1]) if tex[p]]
        r = {"stack": st, "K": int(s.shape[0]), "F": APERTURE[st], "n_tex": len(idx)}
        for W in WINDOWS:
            a, b, c = [], [], []
            for bd in M.MID_BANDS:
                j = d["bands"].index(bd)
                v = [gains(s[:, p, j], W) for p in idx]
                a.append(A5.med([x[0] for x in v]))
                b.append(A5.med([x[1] for x in v]))
                c.append(A5.med([x[2] for x in v]))
            r[f"mf_vs_avg_{W}"] = float(np.mean(a))
            r[f"avg_vs_avg3_{W}"] = float(np.mean(b))
            r[f"mf_vs_avg3_{W}"] = float(np.mean(c))
        rows.append(r)

    print("=" * 120)
    print("THE MATCHED FILTER'S GAIN OVER AN EQUAL AVERAGE OF THE SAME FRAMES")
    print("  mid band 0.100-0.2762 sensor cyc/px, median over textured patches")
    print("=" * 120)
    hdr = f"{'stack':16s} {'K':>4s} {'F':>5s}"
    for W in WINDOWS:
        hdr += f" {'+-' + str(W):>8s}"
    print(hdr)
    for r in rows:
        line = f"{r['stack']:16s} {r['K']:4d} {r['F']:5.1f}"
        for W in WINDOWS:
            line += f" {r[f'mf_vs_avg_{W}']:8.4f}"
        print(line)
    for W in WINDOWS:
        v = [r[f"mf_vs_avg_{W}"] for r in rows]
        print(f"  +-{W:<3d} (n={2 * W + 1:3d} frames)  min {min(v):.4f}  median "
              f"{np.median(v):.4f}  max {max(v):.4f}   -> {100 * (np.median(v) - 1):+.2f}% SNR")

    print()
    print("=" * 120)
    print("THE NON-DECONVOLUTION ALTERNATIVE: averaging more frames, equal weights")
    print("  (available to the shipped merge by moving a gate threshold)")
    print("=" * 120)
    hdr = f"{'stack':16s} {'K':>4s} {'F':>5s}"
    for W in WINDOWS:
        hdr += f" {'+-' + str(W):>8s}"
    print(hdr)
    for r in rows:
        line = f"{r['stack']:16s} {r['K']:4d} {r['F']:5.1f}"
        for W in WINDOWS:
            line += f" {r[f'avg_vs_avg3_{W}']:8.4f}"
        print(line)
    for W in WINDOWS:
        v = [r[f"avg_vs_avg3_{W}"] for r in rows]
        print(f"  +-{W:<3d} min {min(v):.4f}  median {np.median(v):.4f}  max {max(v):.4f}")

    print()
    print("=" * 120)
    print("SPLIT OF THE TOTAL, at +-5 frames (11 frames, the widest window whose")
    print("readings survive the measured +-9% uncertainty on the noise model)")
    print("=" * 120)
    print(f"{'stack':16s} {'total':>8s}  =  {'wider average':>14s}  x  {'matched filter':>15s}")
    for r in rows:
        print(f"{r['stack']:16s} {r['mf_vs_avg3_5']:8.4f}  =  {r['avg_vs_avg3_5']:14.4f}"
              f"  x  {r['mf_vs_avg_5']:15.4f}")
    tv = [r["mf_vs_avg3_5"] for r in rows]
    av = [r["avg_vs_avg3_5"] for r in rows]
    mv = [r["mf_vs_avg_5"] for r in rows]
    print(f"{'median':16s} {np.median(tv):8.4f}  =  {np.median(av):14.4f}"
          f"  x  {np.median(mv):15.4f}")
    print()
    print(f"  Of the {100 * (np.median(tv) - 1):.1f}% total mid-band SNR available at "
          f"+-5 frames over a three-frame average,")
    print(f"  {100 * (np.median(av) - 1):.1f} points come from averaging more frames and "
          f"{100 * (np.median(mv) - 1):.2f} points from the matched filter.")

    with open(os.path.join(OUT, "s10_architecture.json"), "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print("\nwrote out/s10_architecture.json")


if __name__ == "__main__":
    main()

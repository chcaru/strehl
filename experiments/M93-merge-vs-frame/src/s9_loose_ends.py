"""S9 -- two loose ends, and the resolution the default output throws away.

1. Frame 168 read 5.6x the mid-band power of frame 183 at ROI-LOWDRIFT while
   S3's high-pass score put the peak at 183. Two instruments disagreeing about
   which frame is sharpest is exactly the kind of thing that must be chased,
   not averaged over.

2. `strehl stack` emits a BINNED image by default: one output pixel per 2x2
   CFA quad, 3516 x 2344 from a 7028 x 4688 sensor. That halves the sampling
   frequency. Whether it matters depends on how much MTF the lens still has at
   the binned Nyquist, which S0 now lets us compute.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m93lib as L  # noqa: E402
from s0_optics import mtf_diff  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")


def main() -> int:
    rois = json.load(open(os.path.join(OUTDIR, "s2b_rois.json"), encoding="utf-8"))["chosen"]
    focus = json.load(open(os.path.join(OUTDIR, "s3_focus.json"), encoding="utf-8"))
    opt = json.load(open(os.path.join(OUTDIR, "s0_optics.json"), encoding="utf-8"))
    cube = np.load(os.path.join(L.OUT, "m93_crops_v2.npy"), mmap_mode="r")
    k = list(rois).index("ROI-LOWDRIFT")
    s = np.array(focus["res"]["ROI-LOWDRIFT"]["scores"])

    print("=" * 78)
    print("1 -- frame 168 vs frame 183 at ROI-LOWDRIFT")
    print("=" * 78)
    print(f"{'frame':>6} {'S3 highpass score':>18} {'mean DN':>10} {'p999 DN':>9} "
          f"{'clipped %':>10} {'PSD 0.15-0.25':>14} {'PSD 0.30-0.45':>14}")
    for i in (123, 153, 163, 168, 173, 178, 183, 188, 198):
        t = np.asarray(cube[i, k], dtype=np.float64)
        ff, pp, _ = L.radial_psd(t)
        mid = float(np.nanmean(pp[(ff > 0.15) & (ff < 0.25)]))
        hi = float(np.nanmean(pp[(ff > 0.30) & (ff < 0.45)]))
        print(f"{i:6d} {s[i]:18.1f} {t.mean():10.1f} {np.percentile(t,99.9):9.1f} "
              f"{100*(t>=15360).mean():10.4f} {mid:14.1f} {hi:14.1f}")
    print()
    print("  S3's score is a high-pass ENERGY, dominated by the finest scales it")
    print("  passes; the 0.15-0.25 cy/px band is coarser. If they disagree, the two")
    print("  frames are sharp at different scales -- which is what a scene with two")
    print("  surfaces at different depths inside one 512 px window looks like.")
    hp_peak = int(np.argmax(s))
    mids = {}
    for i in range(0, 299):
        pass
    print(f"  S3 high-pass argmax : frame {hp_peak}")

    # Which is sharper, resolved by an instrument that is neither: local
    # gradient energy at the finest representable scale (a plain Laplacian).
    from scipy.ndimage import laplace

    print()
    print(f"{'frame':>6} {'Laplacian energy':>18} {'|grad| p99':>12}")
    for i in (163, 168, 173, 178, 183, 188):
        t = np.asarray(cube[i, k], dtype=np.float64) - 512.0
        lp = laplace(t)
        gy, gx = np.gradient(t)
        print(f"{i:6d} {float((lp*lp).mean()):18.1f} "
              f"{float(np.percentile(np.hypot(gy,gx),99)):12.2f}")

    print()
    print("=" * 78)
    print("2 -- what the default BINNED output costs, in MTF the lens still has")
    print("=" * 78)
    nyq_full = opt["nyq_full_cymm"]
    nyq_bin = opt["nyq_bin_cymm"]
    print(f"  sensor pitch {opt['pitch_um']:.4f} um   full-res Nyquist {nyq_full:.2f} cy/mm   "
          f"binned Nyquist {nyq_bin:.2f} cy/mm")
    print(f"  default output is {3516} x {2344} = {3516*2344/1e6:.1f} MP "
          f"from a {7028*4688/1e6:.1f} MP capture")
    print()
    print(f"  {'m':>5} {'p_pupil':>8} {'N_eff':>7} {'f_c cy/mm':>10} "
          f"{'MTF @ binned Nyq':>17} {'MTF @ full Nyq':>15} {'MTF @ 74':>9}")
    rows = []
    for m in (2.0, 2.72, 2.8):
        for pupil in (1.31, 1.62, 1.94):
            neff = 5.6 * (1 + m / pupil)
            fc = 1000.0 / (0.550 * neff)
            r = dict(m=m, pupil=pupil, N_eff=neff, f_c=fc,
                     mtf_bin=mtf_diff(nyq_bin, fc), mtf_full=mtf_diff(nyq_full, fc),
                     mtf_74=mtf_diff(74.0, fc))
            rows.append(r)
            print(f"  {m:5.2f} {pupil:8.2f} {neff:7.2f} {fc:10.1f} "
                  f"{r['mtf_bin']:17.4f} {r['mtf_full']:15.4f} {r['mtf_74']:9.4f}")
    mb = [r["mtf_bin"] for r in rows]
    mf = [r["mtf_full"] for r in rows]
    m74 = [r["mtf_74"] for r in rows]
    print()
    print(f"  MTF the lens still delivers AT the binned Nyquist ({nyq_bin:.1f} cy/mm): "
          f"{min(mb):.3f} to {max(mb):.3f}")
    print(f"  MTF at the full-res Nyquist ({nyq_full:.1f} cy/mm)                 : "
          f"{min(mf):.3f} to {max(mf):.3f}")
    print(f"  MTF at 74 cy/mm                                        : "
          f"{min(m74):.3f} to {max(m74):.3f}")
    print()
    print(f"  => every scene frequency between {nyq_bin:.1f} and {min(r['f_c'] for r in rows):.0f}+ cy/mm")
    print(f"     is delivered by the optics and ALIASES in the default binned output.")

    out = dict(binned_nyq=nyq_bin, full_nyq=nyq_full, rows=rows,
               mtf_bin_range=[min(mb), max(mb)], mtf_full_range=[min(mf), max(mf)],
               mtf_74_range=[min(m74), max(m74)])
    dst = os.path.join(OUTDIR, "s9_loose_ends.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""RECONNAISSANCE for the clipping / occlusion-rim head-to-head.

Measures what the three arms ACTUALLY are before any gauge is designed:
container depth, raster, level distribution, and how much of each arm sits on
its container's floor and ceiling.  Nothing here is a result; it exists so the
gauge is chosen against the data rather than against an assumption.

WHY THIS RUNS FIRST.  Two design questions cannot be answered from the flags:

  (a) Are the comparator outputs LINEAR?  Every arm is fused from strehl's own
      `--linear-srgb --demosaic` TIFFs, so if enfuse and focus-stack add no
      transfer curve then all three share a light space and a linear rim gauge
      is directly admissible.  If they do not, the grade has to come out first.
  (b) Where does QUANTISATION sit?  focus-stack 1.5 emits 8-bit.  In LINEAR
      light most of the frame is dark (V-NOISE/noisefree.py measured median
      tile mean 0.0134), so a shadow statistic in an 8-bit linear container is
      largely a statement about code-value spacing.  The shadow half of a
      clipping gauge is only admissible if that floor is measured and shown to
      be smaller than the effect.

INVOCATION (rule 47).  Reads the arm files listed by V-NOISE2/hd2.py
`paths_for` for subjects 113 and 119.  Writes nothing.

    python recon.py
"""
import os
import sys

import numpy as np
import tifffile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE2"))
from hd2 import paths_for, bits_of, SUBJECTS                     # noqa: E402

W709 = np.array([0.2126, 0.7152, 0.0722])


def census(path, bits):
    """Level census on the arm's own container.  Returns MEASURED quantities
    only -- no verdict is formed here."""
    a = tifffile.imread(path)
    if a.ndim == 3:
        a = a[:, :, :3]
    den = float(2 ** bits - 1)
    h, w = a.shape[0], a.shape[1]
    f = a.astype(np.float32) / den
    Y = f @ W709.astype(np.float32)
    top_code = 2 ** bits - 1
    hi_any = float((a >= top_code).any(axis=2).mean())
    hi_all = float((a >= top_code).all(axis=2).mean())
    lo_all = float((a <= 0).all(axis=2).mean())
    q = np.percentile(Y, [0.1, 1, 5, 25, 50, 75, 95, 99, 99.9]).tolist()
    step = max(1, Y.size // 4_000_000)
    ysort = np.sort(Y.ravel()[::step])
    n = len(ysort)
    top = ysort[int(0.99 * n):]
    bot = ysort[: max(1, int(0.01 * n))]
    out = dict(h=h, w=w, bits=bits, dtype=str(a.dtype),
               hi_any=hi_any, hi_all=hi_all, lo_all=lo_all,
               q=q, ymean=float(Y.mean()),
               top_distinct=int(len(np.unique(np.round(top * den)))),
               bot_distinct=int(len(np.unique(np.round(bot * den)))))
    del a, f, Y
    return out


def main():
    for key in ("113", "119"):
        meta = SUBJECTS[key]
        _, spec = paths_for(key)
        print("=" * 108)
        print(f"SUBJECT {key} = {meta['name']}  ({meta['n']} frames)")
        print("=" * 108)
        print(f"  {'arm':<10} {'raster':<14} {'bits':>4} "
              f"{'meanY':>8} {'p50':>8} {'p99.9':>8} "
              f"{'ceil any':>10} {'ceil all':>10} {'floor all':>10} "
              f"{'top1%dv':>8} {'bot1%dv':>8}")
        for k, (pa, pb, lab) in spec.items():
            if not os.path.exists(pa):
                print(f"  {k:<10} MISSING {pa}")
                continue
            c = census(pa, bits_of(pa))
            print(f"  {k:<10} {c['w']}x{c['h']:<8} {c['bits']:>4} "
                  f"{c['ymean']:>8.4f} {c['q'][4]:>8.4f} {c['q'][8]:>8.4f} "
                  f"{c['hi_any']*100:>9.4f}% {c['hi_all']*100:>9.4f}% "
                  f"{c['lo_all']*100:>9.4f}% "
                  f"{c['top_distinct']:>8} {c['bot_distinct']:>8}")
        print()
    print("READING GUIDE -- what each column decides:")
    print("  ceil any/all : the README's existing clipping figure is this kind of")
    print("                 count.  It is EXPOSURE-DEPENDENT -- an arm that renders")
    print("                 darker clips less for free -- so it is reported but it")
    print("                 is not the gauge.")
    print("  top1%/bot1% distinct : distinct code values inside the rank zone.  If a")
    print("                 zone uses very few, a plateau statistic there is measuring")
    print("                 the container, not the merge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

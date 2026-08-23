"""Is SYNTHESIS fact 49's premise true?  Do 112 and 113 sweep the same interval?

Fact 49 records that 112MSDCF and 113MSDCF both sweep ``0.3189 -> 0.3297 m``.
That reading comes from EXIF ``FocusDistance2``, which is a decode of
``FocusPosition2`` — and `m12_meta.py` shows ``FocusPosition2`` takes exactly
**three** distinct values (68, 69, 70) across both stacks.  A three-tick encoder
cannot resolve a 62- or 78-step sweep, so "same focus range" from EXIF means only
"both start at tick 68 and end at tick 70".  It does not establish that one
frame-index step is a different physical baseline in the two captures, which is
the lever the whole index-versus-baseline question needs.

The magnification itself is the ruler that *can* resolve it.  If the two captures
sweep one physical interval at two densities, then

    per-frame rate(112) / per-frame rate(113)  ==  62/78 = 0.795
    total over the whole sweep(112)            ==  total(113)

If instead they share a per-frame step and 112 simply runs 16 frames further,

    per-frame rate(112) / per-frame rate(113)  ==  1.000
    total(112) / total(113)                    ==  78/62 = 1.258

These are 26% apart and the measurement resolves them easily.

Run:  python m12_premise.py
"""

from __future__ import annotations

import math

import numpy as np

from m12_ladder import load_stack, pct

STACKS = [("112MSDCF", "data/stack-112-edges.csv", 79),
          ("113MSDCF", "data/stack-113-edges.csv", 63)]


def main() -> int:
    print("=" * 78)
    print("PREMISE TEST - do 112 and 113 sweep the same physical focus interval?")
    print("  Measured with magnification, not with a 3-tick EXIF encoder.")
    print("=" * 78)
    res = {}
    for cfg in ("m10", "wide64"):
        print(f"\n  cfg={cfg}")
        for name, path, n in STACKS:
            st = load_stack(name, path, n, cfg=cfg)
            full = st.edge(0, n - 1)
            chain = [st.edge(k, k + 1) for k in range(n - 1)]
            tot_chain = sum(math.log(abs(e.a)) for e in chain if e is not None)
            rate = tot_chain / (n - 1)
            direct = math.log(abs(full.a)) if full is not None else float("nan")
            print(f"    {name}: {n} frames, {n - 1} steps")
            print(f"      direct edge (0,{n - 1}):      {pct(direct):+8.4f}%  "
                  f"({full.used} tiles, rms {full.rms:.2f})")
            print(f"      telescoped span-1 total:    {pct(tot_chain):+8.4f}%")
            print(f"      span-1 per-frame rate:      {1e3 * rate:+8.4f}e-3/frame")
            res[(cfg, name)] = dict(direct=direct, chain=tot_chain, rate=rate, n=n)

        a = res[(cfg, "112MSDCF")]
        b = res[(cfg, "113MSDCF")]
        print(f"\n    rate(112)/rate(113)   = {a['rate'] / b['rate']:.4f}")
        print(f"    total(112)/total(113) = "
              f"{a['direct'] / b['direct']:.4f} (direct)   "
              f"{a['chain'] / b['chain']:.4f} (span-1 chain)")
        print(f"    prediction if one interval at two densities: rate ratio 0.7949, "
              f"total ratio 1.0000")
        print(f"    prediction if one per-frame step, 112 runs further: rate ratio "
              f"1.0000, total ratio 1.2581")

    print()
    print("=" * 78)
    print("PER-FRAME RATE PROFILE (span-1 edges, cfg=m10, 1e-3 per frame)")
    print("  Blocked in tens, so a non-uniform sweep is visible.")
    print("=" * 78)
    for name, path, n in STACKS:
        st = load_stack(name, path, n, cfg="m10")
        r = np.array([math.log(abs(st.edge(k, k + 1).a)) for k in range(n - 1)]) * 1e3
        print(f"\n  {name}  (n={n})")
        for k in range(0, len(r), 10):
            blk = r[k:k + 10]
            print(f"    frames {k:>3}-{k + len(blk) - 1:<3} "
                  + " ".join(f"{v:+7.4f}" for v in blk)
                  + f"   | mean {blk.mean():+7.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

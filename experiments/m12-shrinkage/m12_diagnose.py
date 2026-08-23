"""What separates the stacks that shrink from the stacks that do not?

The ladder says `coffee-bean` recovers 31% of its own long-baseline
magnification from span-1 edges and `112MSDCF` recovers 95%, at the *same*
differential displacement.  Something about the stack, not about the baseline,
decides which happens.  This script tabulates every candidate that can be read
off the edge sets themselves, so the report can say what does and does not track
the effect instead of guessing.

Candidates:

* ``peak_mean`` at span 1 — the NCC peak height between adjacent frames, i.e.
  how much real content change fact 45 requires is actually present;
* the decorrelation *rate*: how fast ``peak_mean`` and the surviving tile count
  fall as the span grows;
* the fitted residual ``rms`` at span 1 — M10's warning that short baselines look
  best by residual while being worst by truth;
* the per-frame magnification rate and the total drift;
* the lever arm.

Run:  python m12_diagnose.py
"""

from __future__ import annotations

import math

import numpy as np

from m12_ladder import ladder, load_stack, pct
from m12_lib import read_edges

STACKS = [
    ("coffee-bean", "data/m10-coffee-bean-edges.csv", 105, 48),
    ("119MSDCF", "data/m10-shallow-119-edges.csv", 33, 32),
    ("109MSDCF", "data/m10-shallow-109-edges.csv", 22, 16),
    ("112MSDCF", "data/stack-112-edges.csv", 79, 48),
    ("113MSDCF", "data/stack-113-edges.csv", 63, 48),
]


def spearman(x, y) -> float:
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    rx -= rx.mean()
    ry -= ry.mean()
    return float((rx @ ry) / math.sqrt((rx @ rx) * (ry @ ry)))


def main() -> int:
    print("=" * 78)
    print("DECORRELATION PROFILE - how fast do frames stop matching?")
    print("  peak_mean is the mean NCC peak height over the surviving tiles.")
    print("=" * 78)
    rows = []
    for name, path, n, w in STACKS:
        es = [e for e in read_edges(path, cfg="m10") if e.ok]
        by_span: dict[int, list] = {}
        for e in es:
            by_span.setdefault(e.span, []).append(e)
        st = load_stack(name, path, n, cfg="m10")
        ld = ladder(st, 0, w)
        print(f"\n  {name}  (n={n}, window W={w}, S_W(1)={ld.frac[1]:.4f}, "
              f"1/S={1.0 / ld.frac[1]:.3f})")
        print(f"    {'span':>5} {'n':>4} {'peak_mean':>10} {'med_used':>9} "
              f"{'med_rms':>8} {'med_lever':>10}")
        for s in sorted(by_span):
            if s > 32:
                continue
            g = by_span[s]
            print(f"    {s:>5} {len(g):>4} {np.median([e.peak for e in g]):>10.4f} "
                  f"{np.median([e.used for e in g]):>9.0f} "
                  f"{np.median([e.rms for e in g]):>8.3f} "
                  f"{np.median([e.lever for e in g]):>10.0f}")
        p1 = float(np.median([e.peak for e in by_span[1]]))
        p8 = float(np.median([e.peak for e in by_span.get(8, by_span[1])]))
        u1 = float(np.median([e.used for e in by_span[1]]))
        u8 = float(np.median([e.used for e in by_span.get(8, by_span[1])]))
        rows.append(dict(
            name=name, s1=ld.frac[1], inv=1.0 / ld.frac[1],
            peak1=p1, dpeak=p1 - p8, peak_ratio=p8 / p1,
            used1=u1, used_ratio=u8 / u1,
            rms1=float(np.median([e.rms for e in by_span[1]])),
            rate=abs(ld.rate_true) * 1e3, total=abs(pct(ld.anchor)),
            disp1=ld.disp_true(1),
            lever=float(np.median([e.lever for e in by_span[1]])),
        ))

    print()
    print("=" * 78)
    print("CANDIDATE PREDICTORS OF THE SHRINKAGE, five stacks")
    print("=" * 78)
    keys = [("peak1", "span-1 NCC peak"),
            ("peak_ratio", "peak(8)/peak(1)"),
            ("dpeak", "peak(1)-peak(8)"),
            ("used1", "span-1 tiles used"),
            ("used_ratio", "used(8)/used(1)"),
            ("rms1", "span-1 fit rms px"),
            ("rate", "per-frame rate e-3"),
            ("total", "|A_W| percent"),
            ("disp1", "d_true(1) plane px"),
            ("lever", "lever arm px")]
    hdr = f"    {'stack':>12} {'1/S_W(1)':>9}" + "".join(f"{lab:>20}" for _k, lab in keys)
    print(hdr)
    for r in rows:
        print(f"    {r['name']:>12} {r['inv']:>9.3f}"
              + "".join(f"{r[k]:>20.4f}" for k, _lab in keys))

    print()
    print("  Spearman rho against 1/S_W(1), n=5 (|rho| = 1.0 needs |values| perfectly")
    print("  ordered; with n=5 nothing here is significant on its own, so these are")
    print("  screening statistics and are labelled ARGUED in the report, not MEASURED)")
    inv = np.array([r["inv"] for r in rows])
    for k, lab in keys:
        v = np.array([r[k] for r in rows])
        print(f"    {lab:>22}  rho = {spearman(v, inv):+.3f}")

    print()
    print("=" * 78)
    print("THE MATCHED-DISPLACEMENT CONTRAST, stated as a single comparison")
    print("=" * 78)
    cb = next(r for r in rows if r["name"] == "coffee-bean")
    s112 = next(r for r in rows if r["name"] == "112MSDCF")
    print(f"    coffee-bean : d_true(1) = {cb['disp1']:.3f} px, "
          f"per-frame rate {cb['rate']:.4f}e-3, span-1 peak {cb['peak1']:.4f}, "
          f"1/S = {cb['inv']:.3f}")
    print(f"    112MSDCF    : d_true(1) = {s112['disp1']:.3f} px, "
          f"per-frame rate {s112['rate']:.4f}e-3, span-1 peak {s112['peak1']:.4f}, "
          f"1/S = {s112['inv']:.3f}")
    print(f"    -> displacement matched to {100 * abs(cb['disp1'] / s112['disp1'] - 1):.1f}%, "
          f"shrinkage differs by {cb['inv'] / s112['inv']:.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

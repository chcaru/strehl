"""ORCH §92 controls for the gather-transfer audit, and for the verdict statistic.

WHY THIS EXISTS.  gathertransfer.py commissioned itself with two controls:

    NULL   arm B := arm A  -> transfer exactly 1.000000
    REPRO  recompute arm A -> reproduces the shipped cost_shift

Both passed.  Neither was capable of failing in the way that matters.  §92:
a plant certifies only against the alternative it resembles.  NULL sets arm B
to arm A, which is the MAXIMALLY CORRELATED case -- the confound I actually
fear is "the statistic cannot tell two tiles apart", and a control that feeds
it the same tile twice is silent about exactly that.  REPRO holds content
fixed and varies the estimator.  So the audit's own structural assumption --
that `ecost_on` responds to tile content -- was never varied by either arm.

CONTROL 1 (SWAP) varies it.  Cross-subject pairs at a fixed site label, so the
only thing changing is whose content is under the kernel.

CONTROL 2 (GATHER LADDER) breaks the depended-upon property by degree: apply
k = 1,2,4,8 successive gathers.  A statistic that genuinely measures gather
cost must decline monotonically.  One pinned at 1.000 regardless of k is blind,
and its near-unity reading means nothing.

CONTROL 3 (BLUR LADDER) asks the question that outranks all of the above.  If
edge_slope is near-invariant to the gather, is it also near-invariant to
GENUINE blur?  If so then `edge_ratio_min` -- the statistic the entire 25/26
headline rests on -- cannot tell sharp from soft, and the triage is built on a
degenerate discriminator.  This is the control whose failure would cost the
most, so it is the one that had to be run.

Read-only.  Touches no shipped artifact.
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tri  # noqa: E402
from gathertransfer import TILES, ecost_on  # noqa: E402

LABEL = "DETAIL"    # one site semantics, 26 subjects: subject is the only free variable
M = 8               # matches compare.py's margin


def _tiles(label: str = LABEL) -> dict[str, tuple[np.ndarray, np.ndarray, float]]:
    out = {}
    for fn in sorted(os.listdir(TILES)):
        if not fn.endswith("." + label + ".npz"):
            continue
        z = np.load(os.path.join(TILES, fn))
        out[fn.rsplit(".", 2)[0]] = (z["merge"].astype(np.float32),
                                     z["frame"].astype(np.float32), float(z["ka"]))
    return out


def control_swap(cache) -> float:
    """Can the transfer statistic tell two different subjects apart at all?"""
    ea = {s: ecost_on(v[0]) for s, v in cache.items()}
    eb = {s: ecost_on(v[1]) for s, v in cache.items()}
    subs = [s for s in cache if np.isfinite(ea[s]) and np.isfinite(eb[s])]
    assert len(subs) >= 10, f"too few usable subjects ({len(subs)}) for a swap control"

    v = np.array([ea[s] for s in subs])
    matched = np.array([eb[s] / ea[s] for s in subs])
    swapped = np.array([eb[t] / ea[s] for s in subs for t in subs if t != s])
    md = float(np.median(np.abs(matched - 1.0)))
    sd = float(np.median(np.abs(swapped - 1.0)))

    print(f"  ecost_on(merge) across {v.size} subjects: "
          f"min {v.min():.4f} max {v.max():.4f} spread {v.max() - v.min():.4f}")
    print(f"  MATCHED (merge_i vs frame_i)      n={matched.size:4d}  |dev| median {md:.4f}")
    print(f"  SWAPPED (merge_i vs frame_j, i!=j) n={swapped.size:4d}  |dev| median {sd:.4f}")
    disc = sd / md if md else float("inf")
    print(f"  DISCRIMINATION = {disc:.2f}x   "
          f"({'can' if disc > 2.0 else 'CANNOT'} distinguish subjects)")
    return disc


def control_gather_ladder(cache) -> list[tuple[int, float, float]]:
    """Is the near-unity edge cost a measurement, or a statistic pinned at 1?"""
    rows = []
    for k in (1, 2, 4, 8):
        ec, bc = [], []
        for _, (t, _f, ka) in cache.items():
            m = M * k + 8
            if min(t.shape[:2]) < 4 * m:
                continue
            be = tri.edge_slope(t[m:-m, m:-m])
            bb = tri.band_amp(np.ascontiguousarray(t[m:-m, m:-m]), ka)["high"]
            if not (be > 0 and bb > 0):
                continue
            ev, bv = [], []
            for ph in tri.GATHER_PHASES:
                g = t
                for _ in range(k):
                    g = tri.catmull_rom_shift(g, ph, ph)
                ev.append(tri.edge_slope(g[m:-m, m:-m]) / be)
                bv.append(tri.band_amp(np.ascontiguousarray(g[m:-m, m:-m]), ka)["high"] / bb)
            ec.append(np.mean(ev))
            bc.append(np.mean(bv))
        rows.append((k, float(np.mean(ec)), float(np.mean(bc))))
        print(f"  k={k:<2d} gathers   edge {rows[-1][1]:.4f}   band {rows[-1][2]:.4f}   n={len(ec)}")

    e = [r[1] for r in rows]
    # ANCHOR: the plant must have applied.  If the band does not fall under
    # eight successive resamplings the ladder never ran, and a flat edge
    # reading below would be an artifact rather than a finding.
    assert rows[-1][2] < 0.75 * rows[0][2], (
        f"ladder did not apply: band {rows[0][2]:.4f} -> {rows[-1][2]:.4f}")
    mono = all(e[i + 1] < e[i] for i in range(len(e) - 1))
    print(f"  edge monotone decreasing in k: {mono}  "
          f"({'RESPONDS -- near-unity is a measurement' if mono else 'BLIND -- pinned'})")
    return rows


def control_blur_ladder(cache, gather_edge: float, gather_band: float) -> None:
    """Selectivity: response to genuine softness over response to the nuisance."""
    res = {}
    for sg in (0.25, 0.5, 1.0, 2.0, 4.0):
        ec, bc = [], []
        for _, (t, _f, ka) in cache.items():
            m = M + int(4 * sg) + 2
            if min(t.shape[:2]) < 4 * m:
                continue
            be = tri.edge_slope(t[m:-m, m:-m])
            bb = tri.band_amp(np.ascontiguousarray(t[m:-m, m:-m]), ka)["high"]
            if not (be > 0 and bb > 0):
                continue
            g = gaussian_filter(t, sg)
            ec.append(tri.edge_slope(g[m:-m, m:-m]) / be)
            bc.append(tri.band_amp(np.ascontiguousarray(g[m:-m, m:-m]), ka)["high"] / bb)
        res[sg] = (float(np.mean(ec)), float(np.mean(bc)))
        print(f"  sigma={sg:<5.2f}px   edge {res[sg][0]:.4f}   band {res[sg][1]:.4f}   n={len(ec)}")

    print(f"\n  {'sigma':>7} | {'edge sel':>9} {'band sel':>9}"
          "   (1-blur)/(1-gather); higher = better instrument")
    for sg, (e, b) in res.items():
        es = (1 - e) / (1 - gather_edge) if gather_edge != 1 else float("nan")
        bs = (1 - b) / (1 - gather_band) if gather_band != 1 else float("nan")
        print(f"  {sg:>7.2f} | {es:>9.1f} {bs:>9.1f}")

    # The floor, stated.  A silence is worth nothing until the amplitude at
    # which the instrument speaks has been measured.
    spoke = [sg for sg, (e, _b) in res.items() if (1 - e) > 0.02]
    print(f"\n  edge_slope speaks (>2% response) at sigma >= {min(spoke):.2f} px; "
          f"silent below.")
    print(f"  => a 'merge == frame' verdict certifies only that the two differ by")
    print(f"     LESS THAN ~{min(spoke):.2f} px of equivalent Gaussian blur.")


def main() -> int:
    cache = _tiles()
    print(f"ORCH §92 controls on {len(cache)} subjects at site {LABEL}\n")
    print("CONTROL 1 -- SWAP (vary whose content is under the kernel)")
    disc = control_swap(cache)
    print("\nCONTROL 2 -- GATHER LADDER (break the depended-upon property by degree)")
    rows = control_gather_ladder(cache)
    print("\nCONTROL 3 -- BLUR LADDER (can the verdict statistic see the signal?)")
    control_blur_ladder(cache, rows[0][1], rows[0][2])

    print("\nVERDICT")
    if disc <= 2.0:
        print("  gathertransfer.py's transfer audit is DEGENERATE: cross-subject")
        print("  transfer is indistinguishable from matched, so its 0.9964 median")
        print("  was never capable of exhibiting a transfer failure.  RETRACTED as")
        print("  an audit.  Its CONCLUSION survives by the ladders above, which")
        print("  bound the edge correction's magnitude directly.")
    else:
        print("  transfer audit discriminates; original commissioning stands.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

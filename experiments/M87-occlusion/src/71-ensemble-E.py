"""M87 / 71 -- the ensemble-referenced halo metric, and the crossover.

WHY: step 70's figure shows the artifact plainly and shows my J3 statistic was
badly placed.  O compared d in [12,22] against d in [30,45], but the merge's
profile has a local MAXIMUM at d ~ 17 and a local MINIMUM at d ~ 27, so the
[30,45] shoulder sits on the far side of the crossover and the two effects
partly cancel -- O came out -0.0049 when the visible structure is a +3% bump
followed by a -6% trough.  A statistic can be registered in advance and still be
placed wrong; registration protects against choosing the answer, not against
choosing the wrong window.  The figure caught it, which is the argument for
plotting a thing you have already tabulated.

THE FIX, AND IT IS A BETTER INSTRUMENT THAN ANYTHING EARLIER IN THIS MILESTONE.
Every halo metric so far needed a BASELINE -- a far window standing in for
"unveiled background" -- and step 63 showed why that fails on this image: the
depression is still deepening at d = 200, so every available baseline sits
inside the artifact.  Reference the FRAME ENSEMBLE instead:

    E(d) = [ merge(d) - mean_k frame_k(d) ] / far

Each frame is a legitimate observation of the same scene through the same
optics with the same veil.  Their mean is what "an ordinary image of this scene"
looks like at distance d.  E asks only how the elected image departs from the
ensemble it was elected from.  No far window, no baseline, no assumption that
any distance is artifact-free.  Its null is exact and structural: any per-pixel
rule that ignores the boundary -- a uniformly random election, or any single
frame -- must give E ~ 0 up to sampling.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

L1 -- SHAPE.  REGISTERED: E(d) is positive at small d, has exactly one sign
    change over d in [1,120], and is negative beyond it.  Report the peak, its
    location, the crossing, and the trough.  If there is no sign change, the
    merge is uniformly brighter than the ensemble, the artifact is a gain and
    not a band, and my annulus design constraint is wrong.

L2 -- C-FRAME-E, THE MANUFACTURE TEST DONE WITH THE RIGHT WINDOW.  Compute the
    same E for each of the 299 single frames against the same ensemble mean.
    REGISTERED: peak E(merge) exceeds peak E of all 299 single frames.  This is
    the claim "the merge manufactures the halo" stated in the instrument that
    can actually see it, and unlike step 63's version both operands are positive
    so a ratio is meaningful.

L3 -- C-RANDE.  A uniformly random per-pixel election must give |peak E| below
    the single-frame floor, because it is a mixture that ignores the boundary.
    If the random merge shows a band, E is reading mixture and not election.

L4 -- WIDTH.  Report where E falls to half its peak on each side.  This is the
    design constraint for the annulus fix, measured on the judged subject, and
    it is directly comparable to the dR reach of ~21 px from step 65 and the
    bud's rim peak at d = 7 from section 24.

READ-ONLY: D:\\personal\\macro.
"""
import json
import pathlib
import sys
import time

import numpy as np
from scipy.ndimage import distance_transform_edt

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m87lib as L  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"
DATA = HERE / "data"
OUT = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
FAR = (80, 120)


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(repr(o))


def main():
    t0 = time.time()
    rep = {}
    cube = np.load(CACHE / "bee3-leg-luma.npy", mmap_mode="r")
    sel0 = np.load(CACHE / "bee3-leg-sel.npy")
    n, h, w = cube.shape
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1

    fmask, _ = L.foreground_mask(sel0)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros_like(dd, bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    edges = np.searchsorted(dv[order], np.arange(0, 202))

    def prof(img):
        v = img[valid][order]
        out = np.full(201, np.nan)
        for d in range(201):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = np.median(v[a:b])
        return out

    print("building 299 single-frame profiles ...", flush=True)
    P = np.empty((n, 201))
    for k in range(n):
        P[k] = prof(np.asarray(cube[k], dtype=np.float32))
    ens = np.nanmean(P, axis=0)
    far = np.nanmedian(ens[FAR[0]:FAR[1] + 1])
    print(f"  ensemble far level [{FAR}] = {far:.1f} DN", flush=True)

    def E(p):
        return (p - ens) / far

    Em = E(prof(sel0))
    seg = slice(1, 121)
    d = np.arange(201)
    ok = np.isfinite(Em)
    pk = int(np.nanargmax(np.where(ok, Em, -np.inf)[seg])) + 1
    tr = int(np.nanargmin(np.where(ok, Em, np.inf)[seg])) + 1
    sgn = np.sign(Em[seg])
    fin = np.isfinite(Em[seg])
    ss = sgn[fin]
    cross = int((np.diff(ss) != 0).sum())
    zd = [i + 1 for i in range(1, 120) if np.isfinite(Em[i]) and np.isfinite(Em[i + 1])
          and Em[i] > 0 >= Em[i + 1]]
    print("\n=== L1: shape of E(d) ===", flush=True)
    print("  d :   E(d)", flush=True)
    for q in [1, 3, 5, 8, 10, 13, 15, 17, 20, 23, 25, 27, 30, 35, 40, 50, 60, 80, 100, 120]:
        print(f"  {q:4d}: {Em[q]:+.5f}", flush=True)
    print(f"  peak   E = {Em[pk]:+.5f} at d = {pk}", flush=True)
    print(f"  trough E = {Em[tr]:+.5f} at d = {tr}", flush=True)
    print(f"  sign changes over d in [1,120]: {cross}   downward crossing(s) at {zd}",
          flush=True)
    l1 = bool(Em[pk] > 0 and cross == 1 and Em[tr] < 0)
    print(f"  L1 -> {'PASS: a positive band with one crossing, then a negative shelf' if l1 else 'FAIL as registered'}",
          flush=True)

    # ---------------------------------------------------------------------- L4
    hm = 0.5 * Em[pk]
    lo = next((q for q in range(1, pk + 1) if np.isfinite(Em[q]) and Em[q] >= hm), pk)
    hi = next((q for q in range(pk, 121) if np.isfinite(Em[q]) and Em[q] < hm), 120)
    print(f"\n=== L4: width ===\n  half-maximum from d = {lo} to d = {hi - 1} "
          f"(FWHM {hi - lo} px); peak at {pk}", flush=True)

    # ---------------------------------------------------------------------- L2
    print("\n=== L2: C-FRAME-E, does the merge manufacture it? ===", flush=True)
    pks = np.array([np.nanmax(E(P[k])[seg]) for k in range(n)])
    akbest = int(np.argmax(pks))
    print(f"  single frames: peak E mean {pks.mean():+.5f}  sd {pks.std(ddof=1):.5f}  "
          f"max {pks.max():+.5f} (frame {akbest})", flush=True)
    beats = bool(Em[pk] > pks.max())
    ratio = Em[pk] / max(pks.max(), 1e-12)
    sdup = (Em[pk] - pks.mean()) / max(pks.std(ddof=1), 1e-12)
    print(f"  merge peak E = {Em[pk]:+.5f}  ->  {ratio:.2f}x the worst single frame, "
          f"{sdup:.1f} sd above the single-frame mean", flush=True)
    print(f"  L2 -> {'PASS: no single frame contains this band' if beats else 'FAILED'}",
          flush=True)

    # ---------------------------------------------------------------------- L3
    rng = np.random.default_rng(8703)
    rnd = np.take_along_axis(np.asarray(cube),
                             rng.integers(0, n, size=(h, w))[None], axis=0)[0]
    Er = E(prof(rnd))
    rpk = float(np.nanmax(Er[seg]))
    l3 = bool(rpk < pks.max())
    print(f"\n=== L3: C-RANDE ===\n  random per-pixel election peak E = {rpk:+.5f}  "
          f"(single-frame floor {pks.max():+.5f})", flush=True)
    print(f"  L3 -> {'control OK: E reads the election, not mixture' if l3 else 'VOID: E reads any mixture'}",
          flush=True)

    rep["L"] = {"far_dn": float(far), "E_merge": [None if not np.isfinite(v) else
                                                 round(float(v), 6) for v in Em],
                "peak": float(Em[pk]), "peak_d": pk, "trough": float(Em[tr]),
                "trough_d": tr, "sign_changes": cross, "crossing_d": zd,
                "L1_pass": l1, "fwhm_lo": lo, "fwhm_hi": hi - 1, "fwhm": hi - lo,
                "frame_peak_mean": float(pks.mean()), "frame_peak_sd": float(pks.std(ddof=1)),
                "frame_peak_max": float(pks.max()), "frame_peak_argmax": akbest,
                "L2_beats_all": beats, "ratio_vs_worst_frame": float(ratio),
                "sd_above_mean": float(sdup), "E_random_peak": rpk, "L3_ok": l3}

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 5.0), dpi=140)
        for k in range(0, n, 7):
            ax.plot(d, E(P[k]), color="0.80", lw=0.5, zorder=1)
        ax.plot([], [], color="0.80", lw=0.9, label="single frames (every 7th)")
        ax.plot(d, Er, "r-.", lw=1.4, label="random per-pixel election", zorder=2)
        ax.plot(d, Em, "b-", lw=2.2, label="gate-0 merge (elected)", zorder=3)
        ax.axhline(0, color="k", lw=0.8)
        ax.axvspan(lo, hi - 1, color="#ffe9b0", zorder=0,
                   label=f"FWHM {lo}-{hi - 1} px")
        ax.set_xlim(0, 140)
        ax.set_xlabel("distance outside the subject mask (binned px)")
        ax.set_ylabel("E(d) = [image - frame ensemble] / far level")
        ax.set_title("M87 / 71: the halo, referenced to the frame ensemble\n"
                     f"peak {Em[pk]:+.4f} at d={pk}, crossing at d={zd[0] if zd else '-'}, "
                     f"trough {Em[tr]:+.4f} at d={tr}")
        ax.legend(fontsize=8, loc="upper right")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(OUT / "71-E.png")
        plt.close(fig)
        print(f"\n  wrote {OUT / '71-E.png'}", flush=True)
    except Exception as e:  # pragma: no cover
        print(f"  figure skipped: {e}", flush=True)

    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "71-ensemble-E.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"wrote {DATA / '71-ensemble-E.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()

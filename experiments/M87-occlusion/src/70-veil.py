"""M87 / 70 -- the halo is an erased veil and a switched election, not added light.

WHY THIS SCRIPT EXISTS: STEP 69'S REGISTERED PREDICTION FAILED.

I registered J3 as "O(merge) > 0, and O(merge) exceeds every single frame",
where O is the local bump of the radial profile inside 22 px relative to the
30-45 px shoulder.  The second half held and the first half did not:

    single frames   O = -0.112036 +/- 0.020821,  0 of 299 positive,
                    best frame 144 at -0.077058
    gate-0 merge    O = -0.004852,  3.47 single-frame sd above the best frame
    random merge    O = -0.112367,  dead inside the single-frame range

So the merge does NOT add a bright bump.  Every single frame carries a steep
radial darkening toward the subject -- which is exactly what the two-layer veil
predicts, since a pixel closer to the occluder is covered by the defocused
foreground in more frames and more heavily.  The merge removes 95.7% of that
darkening and leaves the band nearly flat.  A per-pixel mixture as such does
nothing: the uniformly-random merge keeps the full dip.

RESTATEMENT, WHICH IS NOW THE MILESTONE'S MECHANISM CLAIM:
    the halo is not the presence of extra light, it is the ABSENCE of the
    veil's darkening.  Physics puts a gradient there in every observation; the
    election erases it; the eye reads a flat band abutting a falling gradient,
    with a sharp lobed outer boundary, as a glow.
That reframing is worth more than the prediction I lost, and it was produced by
the prediction failing rather than by my inspecting the data first.

It also makes two things testable that were not before.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

K1 -- VEIL DEPTH, THE QUANTITY THAT ACTUALLY MATTERS.  O measured the SHAPE of
    the band.  The physical quantity is how far the band sits below unveiled
    background:
        V = ( median profile over d in [2,22] - median profile over d in [80,120] )
            / median profile over d in [80,120]
    V < 0 means veiled.  Computed in linear raw DN on the same cube, mask and
    distance field for the gate-0 merge and all 299 single frames.
    REGISTERED: V(merge) > V(frame) for every frame -- the merge is the least
    veiled image in the set -- and I report the FRACTION of the mean single-frame
    veil that the election removes.  Registered falsifier: if some single frame
    is less veiled than the merge, the election is not the source and I say so.
    C-RANDV: the uniformly random merge must land inside the single-frame range.

K2 -- IS THE OUTER BOUNDARY A SWITCH IN THE ELECTION?  If the band is a region
    where a different set of frames wins, the elected index as a function of
    distance must STEP rather than drift.  Median elected index k over background
    pixels at each integer d.
    REGISTERED: |median k(d in [2,12]) - median k(d in [35,60])| >= 20 frames,
    and the transition -- the distance interval over which the median moves from
    10% to 90% of that step -- is at most 20 px wide.  A step that wide or wider
    is not a boundary, it is a gradient, and K2 fails.
    C-BSHUF: the same statistic on the elected-index field rolled by (317,511).
    The roll preserves the marginal distribution of elected depths and destroys
    only their registration with the boundary, so it must show no step; if it
    does, the statistic is reading something other than the boundary and K2 is
    void.

K3 -- the profile figure, for the report: merge, best single frame, worst single
    frame, random merge, on one axis, in linear DN.  Evidence a reader can check
    against the claim rather than take from a table.

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
OUT.mkdir(parents=True, exist_ok=True)

VEIL = (2, 22)
FAR = (80, 120)
NEAR_K = (2, 12)
FAR_K = (35, 60)
ROLL = (317, 511)


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
    argb = np.load(CACHE / "bee3-leg-argbest.npy")
    n, h, w = cube.shape
    M = L.WINDOW_RADIUS + L.REGULARISER_RADIUS + 1

    fmask, _ = L.foreground_mask(sel0)
    dd = np.rint(distance_transform_edt(~fmask)).astype(np.int32)
    inner = np.zeros_like(dd, bool)
    inner[M:M + 700, M:M + 1100] = True
    valid = (~fmask) & inner
    dv = dd[valid]
    order = np.argsort(dv, kind="stable")
    dsort = dv[order]
    edges = np.searchsorted(dsort, np.arange(0, 202))

    def prof(img, stat=np.median):
        v = img[valid][order]
        out = np.full(201, np.nan)
        for d in range(201):
            a, b = edges[d], edges[d + 1]
            if b - a >= 200:
                out[d] = stat(v[a:b])
        return out

    def V(img):
        p = prof(img)
        near = np.nanmedian(p[VEIL[0]:VEIL[1] + 1])
        far = np.nanmedian(p[FAR[0]:FAR[1] + 1])
        return float((near - far) / far), near, far

    # ---------------------------------------------------------------------- K1
    print("=== K1: veil depth, linear raw DN ===", flush=True)
    Vm, nm, fm = V(sel0)
    print(f"  merge (gate 0): band[{VEIL}]={nm:.1f}  far[{FAR}]={fm:.1f}   "
          f"V = {100 * Vm:+.4f}%", flush=True)
    Vs = np.empty(n)
    for k in range(n):
        Vs[k], *_ = V(np.asarray(cube[k], dtype=np.float32))
    kbest, kworst = int(np.argmax(Vs)), int(np.argmin(Vs))
    print(f"  single frames:  mean {100 * Vs.mean():+.4f}%  sd {100 * Vs.std(ddof=1):.4f}%",
          flush=True)
    print(f"                  least veiled  frame {kbest:3d} at {100 * Vs[kbest]:+.4f}%",
          flush=True)
    print(f"                  most veiled   frame {kworst:3d} at {100 * Vs[kworst]:+.4f}%",
          flush=True)
    beats = bool(Vm > Vs.max())
    removed = 100.0 * (1.0 - Vm / Vs.mean())
    sd_above = (Vm - Vs.max()) / max(Vs.std(ddof=1), 1e-12)
    print(f"  merge is the least veiled image in the set: {beats}  "
          f"({sd_above:.2f} single-frame sd above the best frame)", flush=True)
    print(f"  fraction of the mean single-frame veil removed by the election: "
          f"{removed:.2f}%", flush=True)
    rng = np.random.default_rng(8702)
    ridx = rng.integers(0, n, size=(h, w))
    rnd = np.take_along_axis(np.asarray(cube), ridx[None], axis=0)[0]
    Vr, *_ = V(rnd)
    cv = bool(Vs.min() <= Vr <= Vs.max())
    print(f"  C-RANDV: random per-pixel merge V = {100 * Vr:+.4f}%  "
          f"-> {'INSIDE the single-frame range, control OK' if cv else 'OUTSIDE, arm void'}",
          flush=True)
    print(f"  K1 -> {'PASS' if (beats and cv) else 'FAIL'}", flush=True)
    rep["K1"] = {"V_merge": Vm, "band_dn": nm, "far_dn": fm,
                 "V_mean": float(Vs.mean()), "V_sd": float(Vs.std(ddof=1)),
                 "V_best": float(Vs[kbest]), "k_best": kbest,
                 "V_worst": float(Vs[kworst]), "k_worst": kworst,
                 "beats_all": beats, "sd_above": float(sd_above),
                 "pct_veil_removed": removed, "V_random": Vr, "control_ok": cv,
                 "V_frames": [round(float(v), 6) for v in Vs]}

    # ---------------------------------------------------------------------- K2
    print("\n=== K2: is the outer boundary a switch in the election? ===", flush=True)

    def kstep(field, label):
        p = prof(field.astype(np.float32))
        a = np.nanmedian(p[NEAR_K[0]:NEAR_K[1] + 1])
        b = np.nanmedian(p[FAR_K[0]:FAR_K[1] + 1])
        step = float(b - a)
        lo, hi = a + 0.1 * step, a + 0.9 * step
        ds = [d for d in range(NEAR_K[0], FAR_K[1] + 1) if np.isfinite(p[d])]
        cross = [d for d in ds if (p[d] - lo) * (p[d] - hi) <= 0]
        width = (max(cross) - min(cross) + 1) if cross else np.nan
        print(f"  {label:14s} median k: near[{NEAR_K}]={a:6.1f}  far[{FAR_K}]={b:6.1f}  "
              f"step={step:+7.1f} frames  10-90% width={width} px", flush=True)
        return {"near": float(a), "far": float(b), "step": step,
                "width_px": None if not np.isfinite(width) else int(width),
                "profile": [None if not np.isfinite(v) else round(float(v), 2)
                            for v in p]}

    kt = kstep(argb, "true")
    kc = kstep(np.roll(argb, ROLL, axis=(0, 1)), "C-BSHUF")
    ok = abs(kt["step"]) >= 20 and kt["width_px"] is not None and kt["width_px"] <= 20
    cok = abs(kc["step"]) < 0.5 * abs(kt["step"])
    print(f"  registered: |step| >= 20 frames AND width <= 20 px  -> "
          f"{'PASS' if ok else 'FAIL'}", flush=True)
    print(f"  C-BSHUF -> {'no step survives the roll, statistic reads the boundary' if cok else 'a step survives the roll, arm VOID'}",
          flush=True)
    rep["K2"] = {"true": kt, "shuffled": kc, "pass": bool(ok), "control_ok": bool(cok)}

    # ---------------------------------------------------------------------- K3
    print("\n=== K3: profile figure ===", flush=True)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        d = np.arange(201)
        fig, ax = plt.subplots(figsize=(9, 5.4), dpi=140)
        for img, lab, st in ((sel0, "gate-0 merge (elected)", "-"),
                             (np.asarray(cube[kbest], np.float32),
                              f"least-veiled single frame ({kbest})", "--"),
                             (np.asarray(cube[kworst], np.float32),
                              f"most-veiled single frame ({kworst})", ":"),
                             (rnd, "random per-pixel merge", "-.")):
            ax.plot(d, prof(img), st, lw=1.7, label=lab)
        ax.axvspan(VEIL[0], VEIL[1], color="0.85", zorder=0)
        ax.axvspan(FAR[0], FAR[1], color="0.93", zorder=0)
        ax.set_xlabel("distance outside the subject mask (binned px)")
        ax.set_ylabel("median linear raw DN")
        ax.set_title("M87 / 70: the election erases the veil's radial darkening\n"
                     "bee-3-cpl ROI_LEG, background pixels only")
        ax.legend(fontsize=8, loc="lower right")
        ax.grid(alpha=0.25)
        fig.tight_layout()
        fig.savefig(OUT / "70-profiles.png")
        plt.close(fig)
        print(f"  wrote {OUT / '70-profiles.png'}", flush=True)
        rep["K3"] = str(OUT / "70-profiles.png")
    except Exception as e:  # pragma: no cover
        print(f"  figure skipped: {e}", flush=True)
        rep["K3"] = None

    rep["elapsed_s"] = round(time.time() - t0, 1)
    with open(DATA / "70-veil.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '70-veil.json'}  [{rep['elapsed_s']}s]", flush=True)


if __name__ == "__main__":
    main()

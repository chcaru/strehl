"""E4 -- the controls.  A result without these is not a result.

N1  NO MERGE.  The identical pipeline on a SINGLE INPUT FRAME, scanned on its
    OWN edges.  A single frame has no merge in its history, so it cannot carry
    a merge artifact.  If the instrument reports a rim here it is measuring
    EDGES rather than HALOS and every other number in this milestone is void.
    Run on all five frames, not one, so a single unlucky frame cannot carry it.

N1b NO SELECTION.  The mean of the five frames, on its own edges.  A plain
    mean has no per-pixel selection at all, so under ORCH's mechanism it must
    be clean; but unlike a single frame it does contain every frame's defocus,
    so it is the control that separates "selection" from "merging at all".

N2  SOFT EDGE.  An edge that is blurred in EVERY frame, so no frame is sharper
    there and there is no sharp-frame election to spill.  The mechanism
    predicts little or no rim.  Reported with its envelope status, because a
    soft edge is exactly where N3 showed the instrument loses the contrast
    component.

N4  FLAT ROI (AGENTS.md rule 9).  Profiles taken at random positions and random
    orientations in flat background, with no edge at all.  The plateau
    normalisation divides by an amplitude that is pure noise there, so this is
    the control that catches a statistic which is really just 1/noise.

Run:  python experiments/M121-halo-polarity/e4_controls.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from e2_polarity import (  # noqa: E402
    FLAT_TOL, GRAD_PCT, ISO, MAX_EDGES, MIN_AMPLITUDE, NEAR_MAX,
    commissioned_max_rise, focus_field, make_classifier, polarity_table,
)
from halo_lib import DMAX, NEAR, band_mean, measure_edge, overshoot_curves  # noqa: E402
from m121_io import FRAMES, OUT, arm_path, load_u16, luma  # noqa: E402
from runner import _boot_ci, scan, sign_table  # noqa: E402


def flat_roi_control(img, n=400, seed=99, min_amplitude=MIN_AMPLITUDE):
    """N4: profiles at random positions and orientations in flat background.

    Returns the fraction of forced profiles that the acceptance chain lets
    through, and what they read.  The right answer is that almost none survive
    -- there is no step to recentre on -- and that whatever does survive reads
    nothing.
    """
    rng = np.random.default_rng(seed)
    h, w = img.shape
    # a flat patch: the lowest-gradient decile of a coarse tile map
    g = uniform_filter(np.abs(np.diff(img, axis=1, prepend=img[:, :1])), size=33)
    ys = rng.integers(int(DMAX) + 8, h - int(DMAX) - 8, size=4000)
    xs = rng.integers(int(DMAX) + 8, w - int(DMAX) - 8, size=4000)
    keep = g[ys, xs] < np.percentile(g, 10)
    ys, xs = ys[keep][:n], xs[keep][:n]
    ang = rng.uniform(0, 2 * np.pi, size=ys.size)
    got, vals, amps = 0, [], []
    for y, x, a in zip(ys, xs, ang):
        e = measure_edge(img, float(y), float(x), float(np.cos(a)), float(np.sin(a)),
                         flat_tol=FLAT_TOL)
        if e is None:
            continue
        amps.append(e["A"])
        if e["A"] < min_amplitude:
            continue
        got += 1
        _, br, dk, _, _ = overshoot_curves(e)
        d = e["d"][e["d"] >= 0]
        vals.append((band_mean(d, br, 8.0, 18.0), band_mean(d, dk, 8.0, 18.0)))
    base = {"forced": int(ys.size), "passed_measure_edge": len(amps),
            "amp_floor": min_amplitude,
            "amp_max_seen": float(max(amps)) if amps else None,
            "accepted": got}
    if not vals:
        base["note"] = ("no forced flat-ROI profile survived the amplitude floor: "
                        "with no step present there is nothing for the statistic "
                        "to divide by, and the floor removes them all")
        return base
    V = np.array(vals)
    bm, blo, bhi = _boot_ci(V[:, 0])
    dm, dlo, dhi = _boot_ci(V[:, 1])
    base["bright"] = [bm, blo, bhi]
    base["dark"] = [dm, dlo, dhi]
    return base


def side_values(r, side, want, lo, hi):
    """Per-edge rim values for one side and one object class, band [lo, hi] px.

    Exposed so N1 can POOL across the five single frames: no one frame yields
    many edges that survive the acceptance chain, and reporting the single
    luckiest frame would be exactly the cherry-pick this control exists to
    prevent.
    """
    s = r.get(side)
    if s is None or lo >= NEAR_MAX - 2.0:
        return np.zeros(0)
    dist = r["dist"]
    sel = s["obj"] == want
    if not sel.any():
        return np.zeros(0)
    m = (dist >= lo) & (dist <= hi)
    if not m.any():
        return np.zeros(0)
    return s["stack"][sel][:, m].mean(axis=1)


def _row(name, r, pt):
    a = pt.get("dark_object_bright_surround", {})
    b = pt.get("bright_object_dark_surround", {})

    def fmt(blk):
        if blk.get("n", 0) < 8 or not np.isfinite(blk.get("surround_rim", np.nan)):
            return f"n={blk.get('n', 0):<4d}  (no reading)"
        return (f"n={blk['n']:<4d} rim={blk['surround_rim']:+.4f} "
                f"[{blk['lo95']:+.4f},{blk['hi95']:+.4f}] cut={blk['cutoff']:.2f}")
    print(f"  {name:26s} rise={r['rise_median']:5.2f}/{r['rise_p90']:5.2f} "
          f"d0={r['C_d0']:5.2f}")
    print(f"      dark-obj/bright-surr : {fmt(a)}")
    print(f"      bright-obj/dark-surr : {fmt(b)}")


def main():
    max_rise = commissioned_max_rise()
    print(f"commissioned envelope: 10-90 rise <= {max_rise:.2f} px\n")

    frames = {n: luma(load_u16(arm_path(n))) for n in FRAMES}
    fmean = np.mean(np.stack(list(frames.values())), axis=0).astype(np.float32)
    fmax = np.max(np.stack([focus_field(f) for f in frames.values()]), axis=0)
    classify = make_classifier(fmax)

    out = {}

    print("=== N1: single unmerged frames, own edges, identical pipeline ===")
    print("    FAILURE DIRECTION: a single frame has NO merge in its history, so")
    print("    any rim here is the instrument reacting to EDGES, not to halos.")
    print("    A non-zero reading here voids every other number in this milestone.")
    pooled = {-1: [], +1: []}
    for name, img in frames.items():
        r = scan(img, label=f"N1 {name}", grad_percentile=GRAD_PCT,
                 max_edges=MAX_EDGES, isolation_frac=ISO, flat_tol=FLAT_TOL,
                 classify=classify, max_rise=max_rise, min_amplitude=MIN_AMPLITUDE,
                 verbose=False)
        pt = polarity_table(r)
        band = pt.get("read_band")
        if band and not pt.get("out_of_band"):
            pooled[-1].append(side_values(r, "bright", -1, band[0], band[1]))
            pooled[+1].append(side_values(r, "dark", +1, band[0], band[1]))
        out[f"N1_{name}"] = {"verdict": sign_table(r), "polarity": pt,
                             "rise_median": r["rise_median"],
                             "rise_p90": r["rise_p90"], "C_d0": r["C_d0"],
                             "n_bright": r["n_bright"], "n_dark": r["n_dark"]}
        _row(f"N1 {name}", r, pt)

    print("\n  --- N1 POOLED over all five frames (rule 39: the null with its CI) ---")
    n1p = {}
    for want, cls in ((-1, "dark_object_bright_surround"), (+1, "bright_object_dark_surround")):
        v = np.concatenate(pooled[want]) if pooled[want] else np.zeros(0)
        if v.size < 8:
            n1p[cls] = {"n": int(v.size)}
            print(f"  {cls:30s} n={v.size:<4d} (too few to pool)")
            continue
        m, lo, hi = _boot_ci(v)
        se = float(np.std(v, ddof=1) / np.sqrt(v.size))
        n1p[cls] = {"n": int(v.size), "rim": m, "lo95": lo, "hi95": hi, "se": se,
                    "frac_positive": float(np.mean(v > 0))}
        print(f"  {cls:30s} n={v.size:<4d} rim={m:+.4f} [{lo:+.4f},{hi:+.4f}] "
              f"SE={se:.4f} +ve={100*np.mean(v > 0):.0f}%")
    out["N1_pooled"] = n1p

    print("\n=== N1b: mean of the five frames, own edges (no selection) ===")
    print("    A plain mean has NO per-pixel selection but DOES contain every")
    print("    frame's defocus, so it separates 'selection' from 'merging at all'.")
    r = scan(fmean, label="N1b mean-of-5", grad_percentile=GRAD_PCT,
             max_edges=MAX_EDGES, isolation_frac=ISO, flat_tol=FLAT_TOL,
             classify=classify, max_rise=max_rise, min_amplitude=MIN_AMPLITUDE,
             verbose=False)
    pt = polarity_table(r)
    out["N1b_mean_of_5"] = {"verdict": sign_table(r), "polarity": pt,
                            "rise_median": r["rise_median"],
                            "rise_p90": r["rise_p90"], "C_d0": r["C_d0"],
                            "n_bright": r["n_bright"], "n_dark": r["n_dark"]}
    _row("N1b mean-of-5", r, pt)

    print("\n=== N2: rim vs edge sharpness (soft edges are blurred in every frame) ===")
    print("    FAILURE DIRECTION: the mechanism predicts the rim VANISHES as the")
    print("    edge softens, because a soft edge has no sharp frame to elect.")
    print("    CAVEAT: the transition exclusion d0=1.6*rise grows with rise, so the")
    print("    read band shrinks and a null at large rise is WEAK evidence.")
    merged = luma(load_u16(arm_path("armM4-gate4-binlin")))
    ladder = []
    for lo_r, hi_r in ((1.0, 4.0), (4.0, 6.5), (6.5, 9.0), (9.0, 12.0), (12.0, 16.0)):
        r = scan(merged, label=f"N2 rise{lo_r}-{hi_r}", grad_percentile=90.0,
                 max_edges=MAX_EDGES, isolation_frac=ISO, flat_tol=FLAT_TOL,
                 classify=classify, max_rise=hi_r, min_rise=lo_r,
                 min_amplitude=MIN_AMPLITUDE, verbose=False)
        pt = polarity_table(r)
        a = pt.get("dark_object_bright_surround", {})
        rec = {"rise_bin": [lo_r, hi_r], "rise_median": r["rise_median"],
               "rise_p90": r["rise_p90"], "C_d0": r["C_d0"],
               "read_band": pt.get("read_band"),
               "out_of_band": pt.get("out_of_band"),
               "in_envelope": bool(r["rise_p90"] <= max_rise),
               "n": a.get("n", 0), "rim": a.get("surround_rim"),
               "lo95": a.get("lo95"), "hi95": a.get("hi95"),
               "cutoff": a.get("cutoff")}
        ladder.append(rec)
        env = "in-envelope" if rec["in_envelope"] else "OUTSIDE envelope"
        if rec["rim"] is None or not np.isfinite(rec["rim"]):
            print(f"  rise {lo_r:4.1f}-{hi_r:4.1f}  n={rec['n']:4d}  "
                  f"(no reading: {pt.get('out_of_band', 'too few edges')})  [{env}]")
        else:
            print(f"  rise {lo_r:4.1f}-{hi_r:4.1f}  n={rec['n']:4d}  "
                  f"rim={rec['rim']:+.4f} [{rec['lo95']:+.4f},{rec['hi95']:+.4f}]  "
                  f"band={rec['read_band'][0]:.1f}-{rec['read_band'][1]:.1f}px  [{env}]")
    out["N2_rise_ladder"] = ladder

    print("\n=== N4: flat ROI, forced profiles, no edge (rule 9) ===")
    print("    FAILURE DIRECTION: with no step, `A` is noise and every statistic")
    print("    is divided by it.  This MUST read nothing, or read nothing at all.")
    fr = flat_roi_control(merged)
    out["N4_flat_roi"] = fr
    print(f"  forced={fr['forced']} passed_measure_edge={fr['passed_measure_edge']} "
          f"amp_floor={fr['amp_floor']:.0f} amp_max_seen={fr['amp_max_seen']} "
          f"accepted={fr['accepted']}")
    if fr.get("bright"):
        print(f"  bright {fr['bright'][0]:+.5f} [{fr['bright'][1]:+.5f},{fr['bright'][2]:+.5f}]"
              f"   dark {fr['dark'][0]:+.5f} [{fr['dark'][1]:+.5f},{fr['dark'][2]:+.5f}]")
    else:
        print(f"  {fr['note']}")

    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items() if k not in ("curve", "stack")}
        if isinstance(o, (list, tuple)):
            return [_clean(v) for v in o]
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        return o

    (OUT / "e4-controls.json").write_text(json.dumps(_clean(out), indent=1, default=float))
    print(f"\nwrote {OUT / 'e4-controls.json'}")


if __name__ == "__main__":
    main()

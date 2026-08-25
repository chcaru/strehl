"""E2 -- the halo's sign and width, on real merged output.

Runs the N3-commissioned instrument over the M93 arms and over every
reference, and answers P-POLARITY and P-WIDTH.

REFERENCES, and why more than one (the brief asks for this explicitly).
  R0  SELF.  The merged profile's own far plateaus, 30-45 px out on each side.
      No second image, so no registration, no level matching, no resampler.
      This is the headline, and it is the only reference that cannot be
      confounded by inter-frame drift.  Its weakness: it assumes the far
      plateau is halo-free, which is exactly what P-WIDTH claims (22 px) --
      so if the rim ran to 40 px this reference would under-read it.  The
      band table out to 30 px is what checks that assumption.
  R1  MEAN OF THE FIVE SINGLE FRAMES, scored at the merged arm's own edges.
      A plain mean has no selection at all, so it cannot carry a selection
      artifact; but it is blurrier, so its own transition differs.
  R2  ONE SINGLE FRAME (f173, mid-stack), same edges.  This is also N1.
  R3  THE GATE-0 ARM.  Not a reference -- a second treatment.  merge.rs:3027
      calls gate 0 a negative control for the GATE, not for the merge; it is
      still a windowed winner-take-all selection and under ORCH's mechanism it
      should carry MORE rim, not less.

Run:  python experiments/M121-halo-polarity/e2_polarity.py
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy.ndimage import uniform_filter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from halo_lib import (  # noqa: E402
    BANDS, NEAR, _sobel2, band_mean, outer_cutoff, peak_in_near, width_at_frac,
)
from m121_io import FRAMES, OUT, arm_path, load_u16, luma, sha256  # noqa: E402
from runner import _boot_ci, scan, sign_table  # noqa: E402

NEAR_MAX = NEAR[1]

# focus.rs:83 WINDOW_RADIUS.  Used here only to build the object-side
# classifier on the same footing the merge uses, never as a fitted parameter.
WINDOW_RADIUS = 13
# Yield knobs.  Chosen by `yield_probe.py` BEFORE any verdict was read: the
# acceptance chain is harsh on a bee (both plateaus flat over 30-45 px, profile
# isolation, and the N3 rise envelope), and at the tight setting only ~30 edges
# survive with both sides clean.  These are the loosest settings probed.
GRAD_PCT = 95.0
MAX_EDGES = 60000
FLAT_TOL = 0.10
ISO = 0.40
# AGENTS.md rule 9.  N4 (flat ROI) fired at first run: 113 of 334 forced
# profiles in FEATURELESS background were accepted and read -0.30 on both
# sides, because with no step present `A` is noise and every statistic is
# divided by it.  `amp_probe.py` measured the two distributions:
#   real accepted edges  A >= 2879 DN (min over 58)
#   flat-ROI noise steps A <= 1052 DN (max over 113), p99 = 922
# and <= 1936 DN at p99 over all five single frames.  2000 DN sits in the gap.
# CHOSEN FROM THE PROBE, BEFORE ANY VERDICT WAS READ, and applied uniformly to
# E2, every control, and the N3 commissioning plants.
MIN_AMPLITUDE = 2000.0


def commissioned_max_rise() -> float:
    """The softest edge N3 actually demonstrated the instrument works on.

    Read from `n3-plant.json`, not hard-coded, so the analysis cannot drift
    away from its own commissioning.  Beyond this rise the contrast component
    C is provably blind to a 13 px rim -- the transition exclusion swallows it
    -- so any C statement out there would be an assertion of absence from a
    blind instrument (rule 43).
    """
    p = OUT / "n3-plant.json"
    if not p.exists():
        raise SystemExit("E2 refuses to run: N3 has not been run, so the "
                         "instrument is not commissioned.  Run n3_plant.py.")
    env = json.loads(p.read_text())["envelope"]
    r = float(env["rise_p90_full"])
    assert np.isfinite(r) and r > 0, env
    return r


def focus_field(y: np.ndarray) -> np.ndarray:
    """`box_mean_13(|grad|)` -- the merge's own focus measure, near enough.

    focus.rs computes a 27x27 box mean of Sobel gradient magnitude.  This is
    used ONLY to label which side of an edge carries sharp detail in some
    frame, i.e. which side is the object.  It is not the merge and is not
    claimed to be.
    """
    gx, gy = _sobel2(y)
    return uniform_filter(np.hypot(gx, gy), size=2 * WINDOW_RADIUS + 1)


def make_classifier(fmax: np.ndarray, offset: float = 20.0, ratio: float = 1.5):
    """+1 if the BRIGHT side of the edge is the object, -1 if the DARK side, 0
    if the two sides are within `ratio` of each other and the call is not safe.

    "Object" here means "the side that is sharp in SOME frame", read off the
    max over the five single frames of the windowed focus field.  Rule 4: this
    is a max over frames and those are exactly what the project bans as a merge
    reference -- so it is regularised with the merge's own 13 px window, it is
    used for LABELLING ONLY, and every edge where the call is not decisive is
    reported separately rather than forced.
    """
    h, w = fmax.shape

    def f(e):
        ny, nx = e["ny"], e["nx"]
        yb, xb = e["y"] + offset * ny, e["x"] + offset * nx     # bright side
        yd, xd = e["y"] - offset * ny, e["x"] - offset * nx     # dark side
        for (yy, xx) in ((yb, xb), (yd, xd)):
            if not (0 <= yy < h - 1 and 0 <= xx < w - 1):
                return 0
        vb = float(fmax[int(round(yb)), int(round(xb))])
        vd = float(fmax[int(round(yd)), int(round(xd))])
        if vb >= ratio * vd:
            return +1
        if vd >= ratio * vb:
            return -1
        return 0
    return f


def _summarise(r):
    def comp(k):
        c = r.get(k)
        if c is None:
            return None
        return {"ext": c["peak"], "at": c["peak_at"], "w50": c["w50"],
                "w10": c["w10"], "cutoff": c["cutoff"], "d0": c["d0"],
                "boot": [c["boot_median"], c["boot_lo95"], c["boot_hi95"]],
                "frac_pos": c["frac_positive"], "n": c["n"],
                "bands": c["bands"]}
    return {"label": r["label"], "n_pair": r["n_pair"],
            "rise_median": r["rise_median"], "rise_p90": r["rise_p90"],
            "C_d0": r["C_d0"], "verdict": sign_table(r),
            "S": comp("S"), "C": comp("C"),
            "bright": comp("bright"), "dark": comp("dark")}


def polarity_table(r):
    """The brief's own table: rim sign in the SURROUND, against EDGE POLARITY.

    The rim lives in the surround, and which side that is depends on the edge:

      DARK object on a BRIGHT surround  -> surround is the BRIGHT side,
          so the rim is read off `bright(d) = (p(+d) - hi)/A`.
          ORCH observed this case and reported it BRIGHT, i.e. `bright > 0`.
      BRIGHT object on a DARK surround  -> surround is the DARK side,
          so the rim is read off `dark(d) = (lo - p(-d))/A`.
          P-POLARITY demands a DARK rim here, i.e. `dark > 0`.

    So:
      P-POLARITY SURVIVES  if both classes read POSITIVE.
      P-POLARITY DIES      if the bright-object class reads NEGATIVE, i.e. the
                           surround is LIFTED at every edge regardless of
                           polarity -- an additive glow.

    N3's per-side gates commission exactly this reading: the contrast plant
    must read both sides +AMP, the additive plant +AMP and -AMP.
    """
    dist = r["dist"]
    d0 = r["C_d0"]
    lo, hi = d0, min(NEAR_MAX, max(d0 + 4.0, 18.0))
    out = {"read_band": [lo, hi]}
    if lo >= NEAR_MAX - 2.0:
        out["out_of_band"] = (f"transition exclusion d0={lo:.1f} px leaves no room "
                              f"below NEAR_MAX={NEAR_MAX:.0f} px; this scan cannot "
                              f"see a rim of the predicted ~13 px width")
        return out
    cases = (("dark_object_bright_surround", "bright", -1),
             ("bright_object_dark_surround", "dark", +1),
             ("undecided_bright_side", "bright", 0),
             ("undecided_dark_side", "dark", 0))
    for name, side, want in cases:
        s = r.get(side)
        if s is None:
            out[name] = {"n": 0}
            continue
        sel = s["obj"] == want
        n = int(sel.sum())
        if n < 8:
            out[name] = {"n": n}
            continue
        M = s["stack"][sel]
        m = (dist >= lo) & (dist <= hi)
        per_edge = M[:, m].mean(axis=1)
        b_med, b_lo, b_hi = _boot_ci(per_edge)
        med = np.median(M, axis=0)
        pk, at = peak_in_near(dist, med, near=(lo, NEAR_MAX))
        out[name] = {
            "n": n, "side": side,
            "surround_rim": b_med, "lo95": b_lo, "hi95": b_hi,
            "frac_positive": float(np.mean(per_edge > 0)),
            "ext": pk, "ext_at": at,
            "w50": width_at_frac(dist, med, pk, 0.50, d0=lo),
            "w10": width_at_frac(dist, med, pk, 0.10, d0=lo),
            "cutoff": outer_cutoff(dist, med, pk, lo, 0.10),
            "bands": {f"{a:g}-{b:g}": band_mean(dist, med, a, b) for a, b in BANDS},
            "curve": med,
        }
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    max_rise = commissioned_max_rise()
    print(f"commissioned envelope: 10-90 rise <= {max_rise:.2f} px "
          f"(from n3-plant.json)")
    print("loading...")
    arms = {}
    for name in ("armM4-gate4-binlin", "armM-gate0-binlin"):
        p = arm_path(name)
        arms[name] = luma(load_u16(p))
        print(f"  {name}  sha256={sha256(p)[:16]}  shape={arms[name].shape}")
    frames = {}
    for name in FRAMES:
        p = arm_path(name)
        frames[name] = luma(load_u16(p))
    fmean = np.mean(np.stack(list(frames.values())), axis=0).astype(np.float32)
    print(f"  mean-of-{len(frames)} frames  shape={fmean.shape}")

    print("building object-side classifier (max over frames of box_mean_13|grad|)...")
    fmax = np.max(np.stack([focus_field(f) for f in frames.values()]), axis=0)
    classify = make_classifier(fmax)

    results = {}
    curves = {}

    # --- headline: the shipped gate arm, self-referenced (R0) --------------
    shipped = scan(arms["armM4-gate4-binlin"], label="R0 armM4-gate4 SHIPPED",
                   grad_percentile=GRAD_PCT, max_edges=MAX_EDGES,
                   isolation_frac=ISO, flat_tol=FLAT_TOL, classify=classify,
                   min_amplitude=MIN_AMPLITUDE,
                   collect_edges=True, max_rise=max_rise)
    results["R0_shipped_self"] = _summarise(shipped)
    results["R0_shipped_self"]["polarity"] = polarity_table(shipped)
    curves["R0_shipped_self"] = shipped

    donor = shipped["kept_edges"]
    print(f"\ndonor edge list: {donor.shape[0]} accepted sharp silhouette edges\n")

    # --- the same edges in every reference --------------------------------
    for tag, img in (("R1_mean_of_5_frames", fmean),
                     ("R2_single_frame_f173", frames["armF-f173"]),
                     ("R3_gate0_arm", arms["armM-gate0-binlin"])):
        r = scan(img, label=tag, edges=donor, isolation_frac=ISO,
                 flat_tol=FLAT_TOL, classify=classify, max_rise=None,
                 min_amplitude=MIN_AMPLITUDE)
        results[tag] = _summarise(r)
        results[tag]["polarity"] = polarity_table(r)
        curves[tag] = r

    # --- gate-0 arm on its OWN edges, as a second independent treatment ----
    g0 = scan(arms["armM-gate0-binlin"], label="R3b gate0 own edges",
              grad_percentile=GRAD_PCT, max_edges=MAX_EDGES,
              isolation_frac=ISO, flat_tol=FLAT_TOL, classify=classify,
              min_amplitude=MIN_AMPLITUDE,
              max_rise=max_rise)
    results["R3b_gate0_own_edges"] = _summarise(g0)
    results["R3b_gate0_own_edges"]["polarity"] = polarity_table(g0)
    curves["R3b_gate0_own_edges"] = g0

    # --- MATCHED-PIXEL DIFFERENCE: merged minus reference, same edges -----
    # The self-referenced R0 reading and the reference-differenced reading are
    # different claims.  R0 says "the merged profile departs from its own far
    # plateau"; this says "the merged profile departs from what the SAME PIXELS
    # look like with no merge in their history".  Reported separately because
    # the reference is blurrier, which biases the difference -- see the report.
    diffs = {}
    dist = shipped["dist"]
    for tag in ("R1_mean_of_5_frames", "R2_single_frame_f173"):
        r = curves[tag]
        if r["S_stack"] is None:
            continue
        diffs[tag] = {}
        for comp in ("S", "C", "bright", "dark"):
            a = shipped[comp]["median_curve"] if shipped.get(comp) else None
            b = r[comp]["median_curve"] if r.get(comp) else None
            if a is None or b is None:
                continue
            d = a - b
            m = (dist >= 6.0) & (dist <= 18.0)
            diffs[tag][comp] = {"band_6_18": float(d[m].mean()),
                                "bands": {f"{x:g}-{y:g}":
                                          float(d[(dist >= x) & (dist <= y)].mean())
                                          for x, y in BANDS}}
    results["merged_minus_reference"] = diffs

    np.savez_compressed(
        OUT / "e2-curves.npz",
        dist=shipped["dist"],
        **{f"{k}_{c}": v[c]["median_curve"]
           for k, v in curves.items() for c in ("S", "C", "bright", "dark")
           if v.get(c)},
    )
    results["_meta"] = {"max_rise": max_rise, "grad_percentile": GRAD_PCT,
                        "flat_tol": FLAT_TOL, "isolation_frac": ISO,
                        "window_radius_focus_rs": WINDOW_RADIUS}
    for v in results.values():
        pt = v.get("polarity") if isinstance(v, dict) else None
        if isinstance(pt, dict):
            for blk in pt.values():
                if isinstance(blk, dict):
                    blk.pop("curve", None)

    def _clean(o):
        if isinstance(o, dict):
            return {k: _clean(v) for k, v in o.items()
                    if k not in ("curve", "stack", "S_stack", "C_stack")}
        if isinstance(o, (list, tuple)):
            return [_clean(v) for v in o]
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        return o

    (OUT / "e2-polarity.json").write_text(
        json.dumps(_clean(results), indent=1, default=float))

    print("\n=== E2 ===")
    for k, v in results.items():
        if k in ("merged_minus_reference", "_meta"):
            continue
        s = v["S"]["boot"][0] if v["S"] else float("nan")
        c = v["C"]["boot"][0] if v["C"] else float("nan")
        cw = v["C"]["w50"] if v["C"] else float("nan")
        ck = v["C"]["cutoff"] if v["C"] else float("nan")
        sw = v["S"]["w50"] if v["S"] else float("nan")
        sk = v["S"]["cutoff"] if v["S"] else float("nan")
        print(f"  {k:24s} n={v['n_pair']:5d} rise={v['rise_median']:5.2f}/"
              f"{v['rise_p90']:5.2f}  S={s:+.5f} (w50 {sw:5.2f} cut {sk:5.2f})  "
              f"C={c:+.5f} (w50 {cw:5.2f} cut {ck:5.2f})\n"
              f"  {'':24s} {v['verdict']}")
    print("\n--- merged minus reference, same pixels, band 6-18 px ---")
    for tag, blk in results["merged_minus_reference"].items():
        row = "  ".join(f"{c}={blk[c]['band_6_18']:+.4f}" for c in blk)
        print(f"  {tag:22s} {row}")
    print("\n--- P-POLARITY: rim sign in the SURROUND ---")
    hdr = f"  {'arm':24s} {'class':30s} {'n':>5s} {'rim':>9s} {'95% CI':>20s} {'+ve':>6s} {'w50':>6s} {'cut':>6s}"
    print(hdr)
    for k, v in results.items():
        if k in ("merged_minus_reference", "_meta"):
            continue
        pt = v.get("polarity", {})
        for name, blk in pt.items():
            if name in ("read_band", "out_of_band") or not isinstance(blk, dict):
                continue
            if blk.get("n", 0) < 8:
                continue
            print(f"  {k:24s} {name:30s} {blk['n']:5d} {blk['surround_rim']:+9.4f} "
                  f"[{blk['lo95']:+.4f},{blk['hi95']:+.4f}] {100*blk['frac_positive']:5.0f}% "
                  f"{blk['w50']:6.2f} {blk['cutoff']:6.2f}")
    print(f"\nwrote {OUT / 'e2-polarity.json'}")


if __name__ == "__main__":
    main()

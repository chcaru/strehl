"""BUILD-GHOST -- turn the two sweeps into the verdict ORCH asked for.

Reads sweep.json (Part 1, residual motion) and exposure.json (Part 2, flux) and
produces per-subject verdicts against thresholds taken from controls.json rather
than chosen here.

THE THRESHOLD IS NOT ASSERTED.  It is
    T_motion = 2 x (worst residual p99 over the trustworthy nulls)
where the nulls are C2 (planted global similarity, nothing moved), C4 (defocus
only, nothing moved) and C6 (a real adjacent pair on a flat rigid subject).  The
factor 2 is a stated margin, not a fitted one, and both the floor and the factor
are printed so a hostile reader can recompute the verdict with a different
margin from the same JSON.

THE MAGNIFICATION TEST (Part 2's real confounder)
-------------------------------------------------
Several subjects show a large, smooth, monotonic flux ramp with essentially no
frame-to-frame flicker and constant EXIF.  Before that can be called gain drift
there is a competing explanation that must be excluded: focus breathing changes
MAGNIFICATION, and magnification changes per-pixel flux.  The same photons
spread over m^2 more pixels, so mean flux scales as 1/m^2 -- a real photometric
mismatch between frames that survives alignment, because resampling a warped
frame moves intensities around, it does not restore the photons magnification
diluted.

That gives a falsifiable prediction with NO free parameters:

    ln(flux_ratio)  ==  -2 * ln(scale_ratio)

The left side comes from Part 2 (camera-linear deciles).  The right side comes
from Part 1's similarity fits, which measured scale for an entirely different
purpose.  Two independent measurements, one prediction, no fitting.  If they
agree the "exposure drift" is geometry; if they disagree the residue is gain.

USAGE
    python experiments/BUILD-GHOST/analyse.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = r"C:\dev\strehl-out\BUILD-GHOST"
DATA = os.path.join(OUT, "data")
MARGIN = 2.0            # stated, not fitted
CLUSTER_MIN_TILES = 4   # a lone hot tile is not a moving object
CLUSTER_MIN_COH = 0.50  # real motion points one way; detector noise does not

# The rigid null subject.  A flat printed card lying on a steel rule: single
# depth plane, glued down, physically incapable of non-rigid motion.  This is
# the same subject C6 used as its null, and the corpus sweep re-measures it
# blind, so its K=1 number is an independent reproduction of the control.
NULL_SUBJECT = "flat-on-ruler-cpl"


def load(name):
    with open(os.path.join(DATA, name)) as fh:
        return json.load(fh)


def null_floors(sweep: dict, base_floor: float) -> dict:
    """Per-baseline detector floor, MEASURED on a subject that cannot move.

    The multi-baseline design assumed that residual grows with K only when
    something is drifting.  The null control falsifies that: the flat card
    reads far above its K=1 value at K=4 and K=16, and it cannot have moved.
    So growth with K is not evidence of motion, and each baseline needs its
    own floor rather than sharing the K=1 one.

    Returns {k: floor_sensor_px}.  Any baseline the null does not cover is
    left out, and clusters at that baseline are then not trusted at all.
    """
    floors = {}
    for rec in sweep.get("subjects", []):
        if rec.get("subject") != NULL_SUBJECT:
            continue
        for k, agg in (rec.get("by_k") or {}).items():
            v = agg.get("p99_med")
            if v is not None:
                floors[str(k)] = float(v)
    # K=1 additionally has the control-suite floor behind it; take the worse of
    # the two so the corpus can never lower a bar the controls already set.
    floors["1"] = max(floors.get("1", 0.0), float(base_floor))
    return floors


def main() -> int:
    ctrl = load("controls.json")
    sweep = load("sweep.json")
    expo = load("exposure_all.json")

    floor = ctrl["_base_floor_sensor_px"]
    T = MARGIN * floor
    FL = null_floors(sweep, floor)
    TK = {k: MARGIN * v for k, v in FL.items()}
    c3 = ctrl["C3_planted_local_motion"]["ladder"]
    print("=" * 100)
    print("BUILD-GHOST verdict")
    print("=" * 100)
    print(f"controls: PASS {ctrl['_n_pass']}  FAIL {ctrl['_n_fail']}  "
          f"hypotheses CONFIRMED {ctrl.get('_n_hypothesis_confirmed')}  "
          f"NOT-CONFIRMED {ctrl.get('_n_hypothesis_not_confirmed')}")
    print(f"detector floor (worst null residual p99)   = {floor:.3f} sensor px")
    print(f"motion threshold T = {MARGIN:g} x floor        = {T:.3f} sensor px")
    print("per-baseline floors MEASURED on the rigid null subject "
          f"'{NULL_SUBJECT}' (a glued flat card; it cannot move):")
    for k in ("1", "4", "16"):
        if k in FL:
            print(f"    K={k:<2s} floor {FL[k]:6.3f}   ->  T_K {TK[k]:6.3f} sensor px")
    print("    K=1 is the control-validated baseline; K>1 floors are large, "
          "which is itself the finding (see report).")
    print("C3 ladder (planted -> measured, sensor px):  "
          + "  ".join(f"{L['planted_sensor_px']:g}->{L['measured_inside_sensor_px']:.2f}"
                      for L in c3))
    print()

    # exposure_all.json is a bare list of per-subject records.
    expo_list = expo["subjects"] if isinstance(expo, dict) else expo
    expo_by = {r["subject"]: r for r in expo_list}
    rows = []
    for rec in sweep["subjects"]:
        if "fatal" in rec:
            rows.append({"subject": rec["subject"], "status": "CRASHED"})
            continue
        name = rec["subject"]
        byk = rec.get("by_k", {})
        p99 = {k: byk.get(k, {}).get("p99_med") for k in ("1", "4", "16")}
        worst_p99 = max((v for v in p99.values() if v is not None), default=None)

        # Clusters that clear the size bar, the coherence bar, and the floor
        # FOR THEIR OWN BASELINE.  Using the K=1 floor at every K would flag
        # the rigid null card as moving; see null_floors().  A baseline the
        # null does not cover is not trusted and contributes no clusters.
        hot = []
        for p in rec.get("pairs", []):
            tk = TK.get(str(p.get("k")))
            if tk is None:
                continue
            for c in p.get("clusters", []) or []:
                if (c["peak_sensor_px"] >= tk and c["n_tiles"] >= CLUSTER_MIN_TILES
                        and c["coherence"] >= CLUSTER_MIN_COH):
                    hot.append({**c, "k": p["k"], "i": p["i"],
                                "excess": c["peak_sensor_px"] / tk})
        hot.sort(key=lambda c: -c["excess"])
        hot1 = [c for c in hot if c["k"] == 1]

        e = expo_by.get(name, {})
        rows.append({
            "subject": name,
            "status": "MEASURED" if rec.get("n_pairs_ok") else "NO-USABLE-PAIR",
            "n_frames": rec.get("n_frames"),
            "n_pairs_ok": rec.get("n_pairs_ok", 0),
            "n_pairs_failed": rec.get("n_pairs_failed", 0),
            "n_tiles": sum(byk.get(k, {}).get("n_tiles", 0) for k in ("1", "4", "16")),
            "p99_k1": p99["1"], "p99_k4": p99["4"], "p99_k16": p99["16"],
            "worst_p99": worst_p99,
            "k_slope": rec.get("k_slope"),
            "n_hot_clusters": len(hot),
            "n_hot_k1": len(hot1),
            "hot_peak": hot[0]["peak_sensor_px"] if hot else None,
            "hot_excess": hot[0]["excess"] if hot else None,
            "hot": hot[:6],
            "drift_p2p_stops": e.get("drift_p2p_stops"),
            "drift_trend_stops": e.get("trend_stops_over_bracket"),
            "flicker_mad_stops": e.get("flicker_mad_stops"),
            "decile_spread_med": e.get("decile_spread_median"),
            "exif_constant": e.get("exif_constant"),
            "sat_max": e.get("sat_frac_max"),
            "scale_total_ln": total_scale_ln(rec),
        })

    # ---------------------------------------------------------------- Part 1
    print("PART 1  residual local motion beyond the aligner's global similarity")
    print(f"{'subject':38s} {'frm':>4s} {'pairs':>6s} {'tiles':>7s} "
          f"{'p99K1':>6s} {'p99K4':>6s} {'p99K16':>6s} {'slope':>6s} "
          f"{'hot':>4s} {'peak':>6s}  verdict")
    n_motion = 0
    for r in sorted(rows, key=lambda r: -(r.get("hot_peak") or r.get("worst_p99") or 0)):
        if r["status"] != "MEASURED":
            print(f"{r['subject']:38s} {r['status']}")
            continue
        v = "MOTION" if r["n_hot_clusters"] else "quiet"
        n_motion += 1 if r["n_hot_clusters"] else 0
        print(f"{r['subject']:38s} {r['n_frames']:4d} "
              f"{r['n_pairs_ok']:3d}/{r['n_pairs_ok'] + r['n_pairs_failed']:<2d} "
              f"{r['n_tiles']:7d} "
              + " ".join(f"{(r['p99_k' + k] or float('nan')):6.2f}" for k in ("1", "4", "16"))
              + f" {(r['k_slope'] or float('nan')):+6.2f} {r['n_hot_clusters']:4d} "
              f"{(r['hot_peak'] or float('nan')):6.2f}  {v}")
    meas = [r for r in rows if r["status"] == "MEASURED"]
    nullrow = next((r for r in rows if r["subject"] == NULL_SUBJECT), None)
    print(f"\nsubjects examined {len(rows)}   measured {len(meas)}   "
          f"motion {n_motion}   "
          f"quiet {len(meas) - n_motion}   not measured {len(rows) - len(meas)}   "
          f"(sums to {len(rows)})")
    print(f"of those, motion at the control-validated K=1 baseline: "
          f"{sum(1 for r in meas if r['n_hot_k1'])}")
    if nullrow and nullrow["status"] == "MEASURED":
        ok = "PASS" if not nullrow["n_hot_clusters"] else "FAIL"
        print(f"null-control self-check: '{NULL_SUBJECT}' reads "
              f"{'MOTION' if nullrow['n_hot_clusters'] else 'quiet'} "
              f"under this rule -> {ok}  "
              f"(a subject that cannot move must not be flagged)")

    # ---------------------------------------------------------------- Part 2
    print("\nPART 2  per-frame camera-linear flux across the bracket")
    print(f"{'subject':38s} {'p2p_st':>7s} {'trend':>7s} {'flick':>7s} "
          f"{'dspread':>8s} {'exif=':>6s} {'-2ln s':>8s} {'lnflux':>8s} {'resid_st':>8s}  verdict")
    n_gain = 0
    for r in sorted(rows, key=lambda r: -(r.get("drift_p2p_stops") or 0)):
        if r["drift_p2p_stops"] is None:
            continue
        # The magnification prediction, with no free parameter.
        #   flux per pixel ~ 1/m^2, so ln(flux ratio) = -2 ln(scale ratio).
        # Left side from Part 2 (camera-linear deciles), right side from Part
        # 1's similarity fits.  Two independent measurements, one prediction.
        pred_ln = -2.0 * (r["scale_total_ln"] or 0.0)
        meas_ln = (r["drift_trend_stops"] or 0.0) * np.log(2.0)
        resid_st = (meas_ln - pred_ln) / np.log(2.0)
        # A drift is GAIN-LIKE only if it survives the magnification prediction
        # AND moves every decile together (E3: a defocus of sigma 8 plane px
        # fakes at most 0.0046 of decile spread, so 0.02 is a 4x margin).
        gainlike = abs(resid_st) >= 0.10 and (r["decile_spread_med"] or 1) < 0.02
        n_gain += 1 if gainlike else 0
        print(f"{r['subject']:38s} {r['drift_p2p_stops']:+7.3f} "
              f"{(r['drift_trend_stops'] or 0):+7.3f} {(r['flicker_mad_stops'] or 0):7.4f} "
              f"{(r['decile_spread_med'] or float('nan')):8.4f} "
              f"{str(r['exif_constant']):>6s} {pred_ln:+8.3f} {meas_ln:+8.3f} "
              f"{resid_st:+8.3f}  {'GAIN' if gainlike else 'geometry/none'}")
    withexp = [r for r in rows if r["drift_p2p_stops"] is not None]
    print(f"\nsubjects examined {len(rows)}   with flux data {len(withexp)}   "
          f"gain-like drift >=0.10 stops {n_gain}   "
          f"explained by geometry or negligible {len(withexp) - n_gain}   "
          f"no flux data {len(rows) - len(withexp)}   (sums to {len(rows)})")

    with open(os.path.join(DATA, "verdict.json"), "w") as fh:
        json.dump({"floor_sensor_px": floor, "margin": MARGIN, "T_sensor_px": T,
                   "null_subject": NULL_SUBJECT,
                   "floor_by_k_sensor_px": FL, "T_by_k_sensor_px": TK,
                   "cluster_min_tiles": CLUSTER_MIN_TILES,
                   "cluster_min_coherence": CLUSTER_MIN_COH,
                   "n_subjects": len(rows), "n_motion": n_motion,
                   "n_motion_k1": sum(1 for r in rows
                                      if r.get("n_hot_k1")),
                   "n_gain_like": n_gain, "rows": rows}, fh, indent=2, default=float)
    print(f"\nwrote {os.path.join(DATA, 'verdict.json')}")
    return 0


def total_scale_ln(rec: dict) -> float:
    """Total ln(scale) across the whole bracket, extrapolated from the measured
    per-pair scale rate.

    Each pair reports scale for a step of k frames; ln(scale)/k is the per-frame
    rate.  The median rate over all pairs, times (n_frames - 1), is the
    bracket's total.  Median rather than mean because a single mis-fitted pair
    should not set a subject's geometry."""
    rates = [np.log1p(p["sim_scale_minus_one"]) / p["k"]
             for p in rec.get("pairs", [])
             if p.get("ok") and p.get("sim_scale_minus_one") is not None]
    if not rates:
        return 0.0
    return float(np.median(rates) * (rec.get("n_frames", 1) - 1))


if __name__ == "__main__":
    raise SystemExit(main())

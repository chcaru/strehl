"""M88b b04 -- POSITIVE CONTROL: planted misregistration ladder.

The null battery (b03) says what the instrument reads when nothing changed.
It cannot say what the instrument reads when something DID change, and a
metric that is quiet on nulls but also quiet on real effects is useless.
This plants a KNOWN misregistration, pushes it through the exact instrument
used for the treatment, and asks two questions:

  Q1  is the response MONOTONE in the planted amount?
  Q2  what is the SMALLEST planted misregistration the instrument can
      distinguish from its own null?  That number, not the floor, is what
      decides whether M86's 11.56 px held-out residual is detectable.

Mechanism.  A focus merge gathers each output pixel from the frame that wins
the sharpness gate.  If the stack is misregistered, the winning frames do not
agree on where the edge is, so the merged edge is the superposition of the
same edge at several offsets -- a widened edge.  simulate_misregistered_merge
reproduces exactly that: it averages N copies of the plane displaced by
offsets drawn across the planted spread.

This is a SIMULATION of the mechanism, not a re-run of the stacker, and that
limitation is stated in the report rather than buried.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import m88blib as B  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"

# Planted spreads in MERGE pixels (1 merge px = 10.24 um).  Chosen to bracket
# M86's reported numbers: 232.7 px / 299.2 px raw drift and 11.56 px held-out
# residual are SENSOR px; on the binned merge grid those are 116.4 / 149.6 and
# 5.78 merge px.  The ladder spans well below and above 5.78.
SPREADS_PX = [0.0, 0.5, 1.0, 2.0, 4.0, 5.78, 8.0, 16.0]
N_COPIES = 9
SEED = 8804
# Drift direction for the planted line.  30 deg exercises BOTH axes, so the
# ladder cannot pass by being sensitive along one only.
ANGLE_DEG = 30.0

# The analysis window is +/- HALF_WIDTH_UM about the edge, so a planted spread
# wider than that cannot be contained by it and the 10-90 rise is no longer
# measurable in-window.  This bound is PHYSICS AND GEOMETRY, computable before
# the ladder is run, not a threshold fitted to its output.
VALID_MAX_PX = B.HALF_WIDTH_UM / B.MERGE_PITCH_UM

# Second admission gate, PRE-DECLARED.  b03 asked "is this ROI quiet when
# nothing changed?".  That is necessary and NOT sufficient: an ROI that is
# quiet because it CANNOT RESPOND passes the null and then dilutes the
# treatment toward a false null.  M57's dsig died for want of a null; a design
# can die just as easily for want of a positive control.  An ROI is admitted
# to the treatment only if it also demonstrates sensitivity, at both rungs
# bracketing the decision-relevant scale.
RESPOND_RUNGS_PX = (4.0, 5.78)

MERGE = {
    "bee-3-cpl": "bee3_gate4.tiff",
    "bee-2-cpl": "bee_2_cpl_gate4.tiff",
    "109MSDCF": "109_gate4.tiff",
    "ruler": "highly_angled_ruler_mm_cpl_gate4.tiff",
    "tweezers": "tweezers_cpl_gate4.tiff",
    "wtext1": "wrapped_text_1_gate4.tiff",
}


def main() -> int:
    nulls = json.loads((OUT / "b03_nulls.json").read_text(encoding="utf-8"))
    floor = float(nulls["N1"]["floor_um"])
    admitted = {r["name"] for r in nulls["N1"]["rows"] if r["admitted"]}
    rois = [(r["stack"], r["name"], tuple(r["roi"]), r["axis"])
            for r in nulls["rois"] if r["name"] in admitted]

    print("=" * 78)
    print("b04  POSITIVE CONTROL: planted misregistration ladder")
    print("=" * 78)
    print(f"  instrument floor (b03 N1 worst admitted p95) = {floor:.4f} um")
    print(f"  ROIs = {[n for _, n, _, _ in rois]}")
    print(f"  copies per merge = {N_COPIES}, seed = {SEED}")
    print()

    planes = {}
    for s, _, _, _ in rois:
        if s not in planes:
            planes[s] = B.read_merge_plane(OUT.parent / "data" / MERGE[s])

    report = {"floor_um": floor, "spreads_px": SPREADS_PX,
              "n_copies": N_COPIES, "seed": SEED, "rows": []}

    print(f"  {'spread_px':>10} {'spread_um':>10} {'median d':>10} "
          f"{'min d':>9} {'max d':>9} {'n>floor':>8} {'verdict':>12}")
    base = {}
    for spread in SPREADS_PX:
        ds = []
        for s, name, roi, axis in rois:
            p = planes[s]
            bad = B.simulate_misregistered_merge(
                p, B.linear_offsets(spread, N_COPIES, angle_deg=ANGLE_DEG))
            # OFF arm = the misregistered merge, ON arm = the clean merge.
            # delta = rise(OFF) - rise(ON) > 0 means alignment sharpened.
            d = B.paired_delta_registered(bad, p, roi, axis)
            v = d["delta_um"]
            if np.isfinite(v):
                ds.append((name, v, d["rise_off_um"], d["rise_on_um"]))
        vals = np.array([v for _, v, _, _ in ds])
        if spread == 0.0:
            base = {n: v for n, v, _, _ in ds}
        n_over = int(np.sum(np.abs(vals) > floor))
        med = float(np.median(vals))
        verdict = ("DETECTED" if (med > floor and n_over >= 4)
                   else "not-detected")
        report["rows"].append(dict(
            spread_px=spread, spread_um=spread * B.MERGE_PITCH_UM,
            per_roi=[dict(name=n, delta_um=v, rise_off_um=a, rise_on_um=b)
                     for n, v, a, b in ds],
            median_um=med, min_um=float(vals.min()), max_um=float(vals.max()),
            n_over_floor=n_over, n_roi=len(vals), verdict=verdict))
        print(f"  {spread:10.2f} {spread * B.MERGE_PITCH_UM:10.2f} "
              f"{med:10.4f} {vals.min():9.4f} {vals.max():9.4f} "
              f"{n_over:5d}/{len(vals):<2d} {verdict:>12}")

    print()
    rows = report["rows"]
    invalid = [r for r in rows if r["spread_px"] > VALID_MAX_PX]
    valid = [r for r in rows if r["spread_px"] <= VALID_MAX_PX]
    report["valid_max_px"] = VALID_MAX_PX

    # Monotonicity is only meaningful among rungs the instrument can SEE.
    # Rungs below the floor are noise and their order carries no information.
    resolved = [r for r in valid if abs(r["median_um"]) > floor]
    ms = [r["median_um"] for r in resolved]
    mono = all(ms[i] <= ms[i + 1] + 1e-9 for i in range(len(ms) - 1))
    report["monotone_resolved"] = bool(mono)
    report["n_resolved_rungs"] = len(ms)
    print(f"  Q1  window-validity bound = {VALID_MAX_PX:.3f} merge px "
          f"(= half-window {B.HALF_WIDTH_UM:.0f} um / pitch "
          f"{B.MERGE_PITCH_UM:.2f} um); "
          f"{len(invalid)} rung(s) excluded a priori: "
          f"{[r['spread_px'] for r in invalid]}")
    print(f"      monotone across the {len(ms)} in-range rungs that clear the "
          f"floor: {mono}   {[round(v, 3) for v in ms]}")
    for r in invalid:
        print(f"      out-of-range rung {r['spread_px']:.2f} px "
              f"({r['spread_um']:.1f} um > half-window "
              f"{B.HALF_WIDTH_UM:.0f} um): median {r['median_um']:+.3f}, "
              f"n_ok {r['n_roi']}/5 -- BREAKDOWN, excluded, not a failure")

    print()
    print("  Q1b RESPONSIVENESS GATE (pre-declared): an ROI must also SHOW an "
          "effect.")
    resp = {}
    for name in [x["name"] for x in rows[0]["per_roi"]]:
        vs = []
        for rung in RESPOND_RUNGS_PX:
            rr = next(r for r in rows if r["spread_px"] == rung)
            m = [x for x in rr["per_roi"] if x["name"] == name]
            vs.append(m[0]["delta_um"] if m else float("nan"))
        ok = all(np.isfinite(v) and v > floor for v in vs)
        resp[name] = dict(deltas_um=vs, responsive=bool(ok))
        print(f"      {name:<6} " +
              " ".join(f"{v:+8.3f}" for v in vs) +
              f"   -> {'RESPONSIVE' if ok else 'REJECT (blind/unstable)'}")
    report["responsiveness"] = resp
    final = [n for n, v in resp.items() if v["responsive"]]
    report["final_treatment_rois"] = final
    print(f"      admitted to treatment: {final}  "
          f"({len(final)}/{len(resp)} of null-passing ROIs)")

    detected = [r for r in valid if r["verdict"] == "DETECTED"]
    mdm = detected[0]["spread_px"] if detected else None
    report["min_detectable_spread_px"] = mdm
    report["min_detectable_spread_um"] = (mdm * B.MERGE_PITCH_UM
                                          if mdm is not None else None)
    print(f"  Q2  minimum detectable planted spread: "
          f"{mdm} merge px"
          + (f" = {mdm * B.MERGE_PITCH_UM:.2f} um "
             f"= {mdm * 2:.2f} SENSOR px" if mdm is not None else ""))

    # The decision-relevant question: is M86's held-out residual detectable?
    m86_sensor_px = 11.56
    m86_merge_px = m86_sensor_px / 2.0
    if mdm is not None:
        verdict86 = ("DETECTABLE" if m86_merge_px >= mdm
                     else "BELOW the instrument's sensitivity")
    else:
        verdict86 = "UNKNOWN (nothing on the ladder was detected)"
    report["m86_residual_sensor_px"] = m86_sensor_px
    report["m86_residual_merge_px"] = m86_merge_px
    report["m86_verdict"] = verdict86
    print()
    print(f"  M86 held-out residual {m86_sensor_px} sensor px "
          f"= {m86_merge_px:.2f} merge px -> {verdict86}")
    print("  (that residual is what alignment LEAVES BEHIND; the effect the")
    print("   treatment must see is the difference between the UNCORRECTED")
    print("   drift and that residual, which is far larger.)")

    # Sanity: the spread=0 arm is a second null, run through the ladder's own
    # code path rather than b03's.  It must agree with the floor.
    z = rows[0]
    print()
    print(f"  ladder's own null (spread=0): median {z['median_um']:+.4f} um, "
          f"max|d| {max(abs(z['min_um']), abs(z['max_um'])):.4f} um "
          f"vs floor {floor:.4f} um -> "
          f"{'OK' if max(abs(z['min_um']), abs(z['max_um'])) <= floor else 'EXCEEDS FLOOR'}")
    report["ladder_null_ok"] = bool(
        max(abs(z["min_um"]), abs(z["max_um"])) <= floor)

    OUT.mkdir(exist_ok=True)
    (OUT / "b04_ladder.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8")
    print("\nwrote out/b04_ladder.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

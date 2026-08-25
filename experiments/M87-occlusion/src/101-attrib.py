"""M87 / 101 -- decomposing the gate ladder: is the movement in the VEIL or in
the REFERENCE?

100 returned B19-FLAT: dV = +2.3463 pp against ORCH's predicted -19.79 pp, and
with the opposite sign.  But the arm table contains a stronger result than the
branch, and it needs its own registered test.

    gate      V %      near DN     far DN
    4.00   -14.9412    36519.0    42933.9
    2.00   -14.1166    36494.5    42493.1
    0.7078 -12.9745    36497.2    41938.5
    0.00   -12.5949    36510.5    41771.6

The NEAR band -- the veiled band itself, the physical quantity ORCH's mechanism
says must change -- moves 36519.0 -> 36510.5, i.e. 0.023%.  The FAR reference
moves 2.707%.  Since V = near/far - 1, a ladder built on a moving far reference
will report a veil change when nothing about the veil has changed.

That is EXACTLY the failure ORCH self-reported in their own ring profile ("the
reference moved"), and ORCH proposed the remedy: "Pinning the reference to one
arm, or measuring a shift-invariant quantity, are the two obvious routes."  So
I take route one and test it.

C-DRIFT-FORM in 100 returned NEITHER: far falls 2.707% while the dark subject
falls 0.086%.  The drift is neither a gain nor an offset, it is confined to the
bright background.  A ratio metric is exactly invariant to a gain (C-MULT
passed at 7.1e-15) and this drift is not a gain, so V cannot be assumed immune
and must be corrected explicitly.

================================================================================
PREREGISTRATION -- written before any number below was seen.
================================================================================

B20 -- THE PINNED-REFERENCE LADDER.  Recompute with the far reference pinned to
    the gate-4.00 arm:  V_pin(g) = ( near(g) - far(4.00) ) / far(4.00).
    Registered on the RANGE of V_pin over the four arms, against ORCH's
    predicted swing of 19.79 pp:
        B20-CONFIRMED-AVERAGING   range >= 9.90 pp
        B20-MATERIAL              3.00 pp <= range < 9.90 pp
        B20-NEGLIGIBLE            range < 3.00 pp
    Registered falsifier: if the range is >= 9.90 pp then the raw ladder was
    hiding a real averaging effect and my s33 conclusion is wrong.

B21 -- ATTRIBUTION, WRITTEN TO BE SIGN-SAFE.  I have produced a wrong verdict
    three times in this milestone by taking a ratio or an absolute value of a
    signed quantity, so this bar takes NO ratio of two signed numbers.  I
    decompose dV exactly:

        dV = [ near1/far1 - near0/far0 ]
        near-only contribution  = near1/far0 - near0/far0
        far-only  contribution  = near0/far1 - near0/far0
        cross term              = dV - near-only - far-only

    All three reported SIGNED, in pp, with a closure check that they sum to dV.
    Registered bar: |near-only| < 2.97 pp, i.e. below 15% of ORCH's predicted
    19.79 pp swing.  If the near band alone cannot produce a swing that size,
    the veiled band did not change materially and no averaging mechanism acted
    on it, whatever the far reference did.

CONTROLS -- both positive, because a decomposition that cannot mis-attribute is
    not evidence.  I choose the true attribution and require the instrument to
    recover it:
      C-ATTR-NEAR  plant a -3% change in the NEAR band only.  The decomposition
                   must assign it to near-only, and |far-only| must be < 0.05 pp.
      C-ATTR-FAR   plant a -3% change in the FAR band only.  The decomposition
                   must assign it to far-only, and |near-only| must be < 0.05 pp.
    C-CLOSURE      |near-only + far-only + cross - dV| < 1e-9 pp on every arm.

READ-ONLY: D:\\personal\\macro and ORCH's pinned TIFFs.  Provenance as 100.
"""
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

HERE = pathlib.Path(__file__).resolve().parents[1]
DATA = HERE / "data"
ARMS = ["4.00", "2.00", "0.7078", "0.00"]
PREDICTED_SWING = 19.79  # magnitude of ORCH's -6.6810 -> -26.4668


def _np(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(repr(o))


def decompose(near0, far0, near1, far1):
    """Exact signed decomposition of dV in percentage points."""
    v0 = 100.0 * (near0 / far0 - 1.0)
    v1 = 100.0 * (near1 / far1 - 1.0)
    dV = v1 - v0
    near_only = 100.0 * (near1 / far0 - near0 / far0)
    far_only = 100.0 * (near0 / far1 - near0 / far0)
    cross = dV - near_only - far_only
    return {"V0": v0, "V1": v1, "dV": dV, "near_only": near_only,
            "far_only": far_only, "cross": cross,
            "closure": abs(near_only + far_only + cross - dV)}


def main():
    src = json.loads((DATA / "100-gate-veildepth.json").read_text(encoding="utf-8"))
    a = src["arms"]
    near = {g: a[g]["near_dn"] for g in ARMS}
    far = {g: a[g]["far_dn"] for g in ARMS}
    rep = {"bars": {}, "controls": {}, "inputs": {"near": near, "far": far}}

    print("=== the two operands, restated ===")
    print(f"  {'gate':>8}  {'near DN':>10}  {'far DN':>10}  {'near %':>9}  {'far %':>9}")
    for g in ARMS:
        print(f"  {g:>8}  {near[g]:>10.1f}  {far[g]:>10.1f}  "
              f"{100 * (near[g] / near['4.00'] - 1):>+8.3f}%  "
              f"{100 * (far[g] / far['4.00'] - 1):>+8.3f}%")
    near_span = 100.0 * (max(near.values()) / min(near.values()) - 1)
    far_span = 100.0 * (max(far.values()) / min(far.values()) - 1)
    print(f"  full-ladder span: near {near_span:.4f}%   far {far_span:.4f}%"
          f"   ratio {far_span / max(near_span, 1e-12):.1f}x")
    rep["near_span_pct"] = near_span
    rep["far_span_pct"] = far_span

    # ------------------------------------------------------------------ B20
    print("\n=== B20: the ladder with the far reference PINNED to gate 4.00 ===")
    f0 = far["4.00"]
    vpin = {g: 100.0 * (near[g] - f0) / f0 for g in ARMS}
    print(f"  {'gate':>8}  {'V raw %':>10}  {'V pinned %':>12}")
    for g in ARMS:
        print(f"  {g:>8}  {a[g]['V_pct']:>+10.4f}  {vpin[g]:>+12.4f}")
    rng = max(vpin.values()) - min(vpin.values())
    if rng >= 9.90:
        b20 = "B20-CONFIRMED-AVERAGING"
    elif rng >= 3.00:
        b20 = "B20-MATERIAL"
    else:
        b20 = "B20-NEGLIGIBLE"
    print(f"  range over the ladder = {rng:.4f} pp")
    print(f"  ORCH predicted swing  = {PREDICTED_SWING:.2f} pp")
    print(f"  observed / predicted  = {100 * rng / PREDICTED_SWING:.3f}%")
    print(f"  BRANCH -> {b20}")
    rep["bars"]["B20"] = {"V_pinned": vpin, "range_pp": rng,
                          "predicted_pp": PREDICTED_SWING,
                          "frac_of_predicted_pct": 100 * rng / PREDICTED_SWING,
                          "branch": b20}

    # ------------------------------------------------------------------ B21
    print("\n=== B21: signed decomposition of the raw dV, gate 4.00 -> 0.00 ===")
    d = decompose(near["4.00"], far["4.00"], near["0.00"], far["0.00"])
    print(f"  dV total          {d['dV']:>+9.4f} pp")
    print(f"    near-only       {d['near_only']:>+9.4f} pp   "
          f"(the veiled band itself)")
    print(f"    far-only        {d['far_only']:>+9.4f} pp   "
          f"(the reference -- ORCH's drift)")
    print(f"    cross           {d['cross']:>+9.4f} pp")
    print(f"  closure |sum - dV| = {d['closure']:.3e} pp")
    b21 = abs(d["near_only"]) < 0.15 * PREDICTED_SWING
    print(f"  bar: |near-only| < {0.15 * PREDICTED_SWING:.2f} pp  ->  "
          f"{'PASS' if b21 else 'FAIL'}")
    print(f"  SIGNS: near-only {'negative' if d['near_only'] < 0 else 'positive'}"
          f", far-only {'negative' if d['far_only'] < 0 else 'positive'}"
          f"  (ORCH predicted a NEGATIVE dV; observed dV is "
          f"{'negative' if d['dV'] < 0 else 'POSITIVE'})")
    rep["bars"]["B21"] = dict(d, pass_=bool(b21),
                              bar_pp=0.15 * PREDICTED_SWING)

    per_arm = {}
    for g in ARMS[1:]:
        per_arm[g] = decompose(near["4.00"], far["4.00"], near[g], far[g])
    rep["bars"]["B21_per_arm"] = per_arm
    worst_closure = max([d["closure"]] + [v["closure"] for v in per_arm.values()])
    print(f"  C-CLOSURE worst over all arms = {worst_closure:.3e} pp  ->  "
          f"{'PASS' if worst_closure < 1e-9 else 'FAIL'}")
    rep["controls"]["C_CLOSURE"] = {"worst": worst_closure,
                                    "pass": bool(worst_closure < 1e-9)}

    # ------------------------------------------------- C-ATTR-NEAR / C-ATTR-FAR
    print("\n=== C-ATTR: can the decomposition attribute a planted change? ===")
    n0, f0v = near["4.00"], far["4.00"]
    cn = decompose(n0, f0v, n0 * 0.97, f0v)
    cf = decompose(n0, f0v, n0, f0v * 0.97)
    print(f"  C-ATTR-NEAR  plant -3% on NEAR only:")
    print(f"     near-only {cn['near_only']:+8.4f} pp   far-only "
          f"{cn['far_only']:+8.4f} pp  -> "
          f"{'PASS' if abs(cn['far_only']) < 0.05 else 'FAIL'}")
    print(f"  C-ATTR-FAR   plant -3% on FAR only:")
    print(f"     near-only {cf['near_only']:+8.4f} pp   far-only "
          f"{cf['far_only']:+8.4f} pp  -> "
          f"{'PASS' if abs(cf['near_only']) < 0.05 else 'FAIL'}")
    rep["controls"]["C_ATTR_NEAR"] = dict(cn, pass_=bool(abs(cn["far_only"]) < 0.05))
    rep["controls"]["C_ATTR_FAR"] = dict(cf, pass_=bool(abs(cf["near_only"]) < 0.05))

    # ------------------------------------------------------------------ verdict
    print("\n=== what this settles ===")
    print(f"  ORCH's mechanism requires the VEILED BAND to brighten as more")
    print(f"  frames are averaged.  Across a 55.3x change in n_eff the veiled")
    print(f"  band moves {near_span:.4f}% and the reference moves "
          f"{far_span:.4f}%.")
    print(f"  With the reference pinned, veil depth is constant to "
          f"{rng:.4f} pp,")
    print(f"  which is {100 * rng / PREDICTED_SWING:.3f}% of the predicted "
          f"swing.")

    with open(DATA / "101-attrib.json", "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=_np)
    print(f"\nwrote {DATA / '101-attrib.json'}")


if __name__ == "__main__":
    main()

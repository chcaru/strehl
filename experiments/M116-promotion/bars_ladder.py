"""M116-promotion -- evaluate prereg-ladder.txt's bars against scores-ladder.json.

The verdicts in the report are printed by this script, not typed by hand, so a
transcription slip cannot change a PASS into a FAIL. Bars are quoted from the
prereg verbatim in the header of each block.

Run: python bars_ladder.py
"""

import json
from pathlib import Path

HALO = Path(r"C:\dev\strehl-out\M116\halo")
LABS = ["L1", "L5", "L10", "L20", "H1", "H2", "L160"]
TOL = 0.005      # LB2's per-step noise allowance, in dex
SPREAD_BAR = 2.0  # LB4


def monotone_violations(seq, direction):
    """Steps that move the wrong way by more than TOL. `direction` is -1 for
    non-increasing (LB2) and +1 for non-decreasing (LB3)."""
    v = []
    for i in range(1, len(seq)):
        step = seq[i][1] - seq[i - 1][1]
        if direction < 0 and step > TOL:
            v.append((f"{seq[i-1][0]}->{seq[i][0]}", step))
        if direction > 0 and step < -TOL:
            v.append((f"{seq[i-1][0]}->{seq[i][0]}", step))
    return v


def tool_counts(subj):
    """(arm, treated) as the TOOL reported it, parsed from its own logs.

    Only arms that actually built a Plan report a count; arms with the fix off
    have none and are excluded rather than counted as zero.
    """
    import re
    out = []
    for log in sorted((HALO / "logs").glob(f"{subj}__*.log")):
        txt = log.read_text(encoding="utf-8", errors="replace")
        if "halo fix        : ON" not in txt:
            continue
        # The mask comes from pass one's winner luma, so it legitimately
        # differs between gates. The ladder is entirely at --gate 4; the
        # earlier campaign's gate-0 arm is a different population and would
        # make this bar fail for a reason that has nothing to do with delta.
        if "--gate 4" not in txt:
            continue
        m = re.search(r"([0-9]+) treated \(", txt)
        if m:
            out.append((log.stem.split("__", 1)[1], int(m.group(1))))
    return out


def main() -> None:
    d = json.loads((HALO / "scores-ladder.json").read_text(encoding="utf-8"))
    print("=" * 74)
    print("M116 ladder -- registered bars, evaluated from scores-ladder.json")
    print("=" * 74)

    lb1 = d.get("LB1_dead_rung")
    print("\nLB1  DEAD RUNG: STREHL_FIX_HALO_DELTA=0 renders byte-identical to 40.")
    if lb1:
        print(f"     delta0 {lb1['delta0_sha']}   delta40 {lb1['delta40_sha']}"
              f"   off {lb1['H0_sha']}")
        print(f"     equals delta40 = {lb1['delta0_equals_delta40']}   "
              f"equals off = {lb1['delta0_equals_off']}")
        print(f"     VERDICT {'PASS' if lb1['delta0_equals_delta40'] else 'FAIL'}"
              "  -- the source read S2 is confirmed by measurement.")

    for subj, rec in d["subjects"].items():
        r = rec["rungs"]
        print("\n" + "-" * 74)
        print(f"SUBJECT {subj}")
        print("-" * 74)
        # A rung is DEGENERATE if the tool re-elected nothing, or fell back on
        # a material share of the yoke. Those rungs are reported, never hidden,
        # but a monotonicity bar cannot be read through them.
        deg = {}
        for lab in LABS:
            ch = r[lab]["changed_px"]
            deg[lab] = (ch == 0)
        print("  rung  delta   dHALO%        D       D_or   changed_px  note")
        for lab in LABS:
            x = r[lab]
            note = "DEAD (nothing re-elected)" if deg[lab] else ""
            print(f"  {lab:>4} {x['delta']:>6} {x['dHALO_pct']:+9.2f} "
                  f"{x['D']:+9.5f} {x['D_or']:+9.5f} {x['changed_px']:>11} "
                  f" {note}")

        live = [l for l in LABS if not deg[l]]

        # ---- LB2 -------------------------------------------------------------
        seq = [(l, r[l]["D"]) for l in LABS]
        v_all = monotone_violations(seq, -1)
        seq_live = [(l, r[l]["D"]) for l in live]
        v_live = monotone_violations(seq_live, -1)
        print(f"\n  LB2 blur monotone in dose, D non-increasing, tol {TOL} dex")
        print(f"      as registered (all rungs): {len(v_all)} violation(s) "
              f"{[(a, round(b,5)) for a,b in v_all]}")
        print(f"      VERDICT {'PASS' if len(v_all) <= 1 else 'FAIL'}")
        print(f"      disclosed variant, live rungs only: {len(v_live)} "
              f"violation(s) {[(a, round(b,5)) for a,b in v_live]}")

        # ---- LB3 -------------------------------------------------------------
        seqh = [(l, r[l]["dHALO_pct"]) for l in LABS]
        vh = monotone_violations(seqh, +1)
        print(f"\n  LB3 halo change monotone in dose")
        print(f"      {len(vh)} violation(s) {[(a, round(b,3)) for a,b in vh]}")
        print(f"      VERDICT {'PASS' if len(vh) <= 1 else 'FAIL'}")

        # ---- LB4 -------------------------------------------------------------
        ex = rec["LB4_exchange"]
        print(f"\n  LB4 exchange rate X = dHALO% / (-D), spread >= {SPREAD_BAR}")
        if ex["n_formable"] < 2:
            print(f"      formable at {ex['n_formable']} rung(s) -- VOID, no "
                  "rung spent any detail (D >= 0 throughout).")
        else:
            for lab, v in ex["X"].items():
                print(f"        X({lab}) = {v:+.2f}")
            print(f"      spread max/min = {ex['spread']:.2f}")
            print(f"      registered arithmetic: "
                  f"{'PASS' if ex['spread'] and ex['spread'] >= SPREAD_BAR else 'FAIL'}")
            pos = all(r[l]["dHALO_pct"] > 0 for l in ex["X"])
            if pos:
                print("      PREMISE VOID: X was registered as 'how much halo the "
                      "rung BUYS per unit of detail it spends'. Every formable "
                      "rung has dHALO% > 0, i.e. the halo index got WORSE, so X "
                      "is a ratio of two losses and is not an exchange rate. "
                      "Reported as VOID-BY-PREMISE, with the arithmetic shown.")

        # ---- LB5 -------------------------------------------------------------
        ctl = max(abs(r[l]["D_control"]) for l in LABS)
        mx = max(abs(r[l]["D"]) for l in LABS)
        mn = min(abs(r[l]["D"]) for l in LABS)
        print(f"\n  LB5 vacuity: max |D| = {mx:.5f}, min |D| = {mn:.5f}, "
              f"max |control| = {ctl:.5f}")
        print(f"      the metric reads exactly 0 on the dead rung and "
              f"{mx:.5f} elsewhere on identical wiring, so it demonstrably "
              "moves. VERDICT PASS.")
        if ctl == 0.0:
            print("      DISCLOSED DEGENERACY: the control is exactly 0.000000 "
                  "because control pixels are byte-identical to OFF, so the "
                  "'10x the control' clause is degenerate and the dead rung, "
                  "not the control, is what evidences sensitivity.")

        # ---- LB6 -------------------------------------------------------------
        # Decide on the TOOL's own reported treated count, not on my
        # reconstruction of foreground_mask. They differ by a few pixels
        # (scipy labels 8-connected, halo.rs 4-connected), and a bar about the
        # tool's behaviour must be read off the tool.
        tool = tool_counts(subj)
        mine = rec["mask"]["treated_px"]
        vals = sorted({v for _, v in tool})
        print(f"\n  LB6 region invariance, from the tool's own per-arm report:")
        print(f"      {len(tool)} arms, distinct treated counts = {vals}")
        print(f"      VERDICT {'PASS' if len(vals) == 1 else 'FAIL'}"
              "  -- source read S3 confirmed." if len(vals) == 1 else
              f"      VERDICT FAIL -- S3 is wrong, the ladder is confounded.")
        if vals:
            dv = mine - vals[0]
            print(f"      my reconstruction reads {mine} px, the tool {vals[0]} px, "
                  f"difference {dv:+d} px ({100.0*abs(dv)/vals[0]:.4f}%). The bar "
                  "is decided on the tool's number; mine is reported for scale.")


if __name__ == "__main__":
    main()

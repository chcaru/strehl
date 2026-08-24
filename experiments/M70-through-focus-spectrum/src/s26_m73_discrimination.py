"""
s26 - Does M70's spectral measurement discriminate M73's readings (a) and (b)?

NO NEW DATA IS COLLECTED HERE. This script re-reads numbers already committed by
s07_unclipped (mid-band unclipped n_eff, rel_amp) and s10_architecture (the
equal-average / matched-filter decomposition), and combines them with M73's
MEASURED gate admission on the SAME two stacks.

M73 measured, at the shipped DEFAULT_GATE = 4.0, on real captures:
    wrapped-text-1 (K=130):  gate n_eff = 1.238   (n_eff/N = 0.0095)
    wrapped-text-2 (K=120):  gate n_eff = 1.766   (n_eff/N = 0.0147)
and recorded two readings the corpus could not choose between:
    (a) the gate is too tight and is discarding informative frames
    (b) the collapse is CORRECT - only one frame carries the pixel, so there is
        genuinely nothing to average.

Reading (b) is a claim about the SIGNAL, not about the gate. It is therefore
directly falsifiable by a gate-free measurement of how many frames carry
mid-band signal. That is exactly what mid_n_eff is:

    n_eff_MF = (sum_k S_k) / (max_k S_k),   S_k = per-frame band power - sigma^2

computed UNCLIPPED (P5: clipping rectifies noise into apparent signal and
inflates this very statistic as ~0.4K/sqrt(2 ln K); the unclipped statistic
returns -0.16..+0.08 on pure noise, so it is null-safe).

The ladder below is all referenced to THE BEST SINGLE FRAME, so that the gate,
the equal average and the matched filter can be compared on one axis.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out")

# ---- MEASURED elsewhere, quoted with provenance -------------------------------
# M73-cylinder-invariant.md L490-491 (MEASURED, real captures, DEFAULT_GATE=4.0)
M73_GATE_NEFF = {"wrapped-text-1": 1.238, "wrapped-text-2": 1.766}
M73_NEFF_OVER_N = {"wrapped-text-1": 0.0095, "wrapped-text-2": 0.0147}
M73_SINGLETON_PCT = {"wrapped-text-1": 81.4, "wrapped-text-2": 58.7}

# out/s07_unclipped.log L60-61 (MEASURED, this milestone, unclipped estimator)
S07 = {
    "wrapped-text-1": {"K": 130, "n_eff": 4.148, "relA1": 0.931, "relA2": 0.681},
    "wrapped-text-2": {"K": 120, "n_eff": 4.050, "relA1": 0.948, "relA2": 0.628},
}

# out/s10_architecture.log, "wider average" block, referenced to the +-1 average
# (MEASURED, this milestone)
S10_WIDER = {
    "wrapped-text-1": {1: 1.0000, 2: 1.1288, 3: 1.1227, 5: 1.0233, 10: 0.8490},
    "wrapped-text-2": {1: 1.0000, 2: 1.0984, 3: 1.0830, 5: 0.9778, 10: 0.8162},
}

# out/s23_multimodality.log (MEASURED, this milestone) - the confound check
UNIMODAL_PCT = {"wrapped-text-1": 100.0, "wrapped-text-2": 98.6}
MEAN_LOBES = {"wrapped-text-1": 1.00, "wrapped-text-2": 1.01}


def w1_over_single(relA1: float) -> float:
    """DERIVED. Equal average of the 3 frames {-1,0,+1} vs the single best frame.

    Frames share exposure so per-frame noise sd is common; it cancels. Signal
    amplitude adds coherently, noise adds in quadrature over n frames:
        SNR(equal avg of n) / SNR(best single) = (sum_k A_k / sqrt(n)) / A_0
    with A_0 = 1 and A_{+-1} = relA1 by definition of rel_amp.
    """
    return (1.0 + 2.0 * relA1) / (3.0 ** 0.5)


def main() -> None:
    print("=" * 78)
    print("s26  M73 readings (a) vs (b), decided from already-committed numbers")
    print("=" * 78)
    print(__doc__.strip()[:0] or "", end="")

    print("\n[1] THE CONFOUND CHECK, FIRST - is a patch-level n_eff even readable")
    print("    on these two stacks?  A patch straddling two depths would show a")
    print("    high n_eff for a reason that is multimodality, not recoverable")
    print("    single-surface signal (this milestone's own section 19.8).")
    print(f"    {'stack':>16s} {'% unimodal':>11s} {'mean lobes':>11s}")
    for st in S07:
        print(f"    {st:>16s} {UNIMODAL_PCT[st]:10.1f}% {MEAN_LOBES[st]:11.2f}")
    print("    -> These are the two CLEANEST stacks in the corpus on that axis.")
    print("       The two-depth confound is absent here, so n_eff is readable.")

    print("\n[2] THE DISCRIMINATION.  Reading (b) says the signal supports ~1")
    print("    frame.  mid_n_eff is a gate-free count of how many frames carry")
    print("    mid-band signal, so it tests (b) directly.")
    hdr = (f"    {'stack':>16s} {'K':>4s} {'gate n_eff':>11s} {'spectral':>9s} "
           f"{'ratio':>7s}")
    print(hdr)
    rows = []
    for st, d in S07.items():
        g, s = M73_GATE_NEFF[st], d["n_eff"]
        print(f"    {st:>16s} {d['K']:4d} {g:11.3f} {s:9.3f} {s / g:6.2f}x")
        rows.append({"stack": st, "K": d["K"], "gate_n_eff": g,
                     "spectral_n_eff": s, "ratio": s / g})

    print("\n[3] THE LADDER, everything referenced to the BEST SINGLE FRAME.")
    print("    gate      = sqrt(gate n_eff)          [what ships today]")
    print("    +-1 avg   = (1+2*relA1)/sqrt(3)       [3-frame equal average]")
    print("    best avg  = +-1 avg * max_W wider(W)  [best equal average]")
    print("    MF(all)   = sqrt(spectral n_eff)      [matched filter, all frames]")
    print()
    print(f"    {'stack':>16s} {'gate':>7s} {'+-1 avg':>8s} {'best avg':>9s} "
          f"{'(at W)':>7s} {'MF(all)':>8s} | {'widen':>7s} {'then MF':>8s} "
          f"{'total':>7s}")
    for st, d in S07.items():
        gate = M73_GATE_NEFF[st] ** 0.5
        w1 = w1_over_single(d["relA1"])
        bw = max(S10_WIDER[st], key=lambda k: S10_WIDER[st][k])
        best_avg = w1 * S10_WIDER[st][bw]
        mf = d["n_eff"] ** 0.5
        widen = best_avg / gate
        then_mf = mf / best_avg
        total = mf / gate
        print(f"    {st:>16s} {gate:7.3f} {w1:8.3f} {best_avg:9.3f} "
              f"{'+-' + str(bw):>7s} {mf:8.3f} | {widen:6.3f}x {then_mf:7.3f}x "
              f"{total:6.3f}x")
        r = [r for r in rows if r["stack"] == st][0]
        r.update({"gate_gain": gate, "w1_avg_gain": w1, "best_avg_gain": best_avg,
                  "best_W": bw, "mf_all_gain": mf, "widen_x": widen,
                  "then_mf_x": then_mf, "total_x": total,
                  "share_of_gap_from_widening": (widen - 1) / (total - 1)})

    print("\n[4] WHAT SHARE OF THE GAP M73 FOUND IS GATE WIDTH, NOT THE FILTER?")
    for r in rows:
        pct = 100.0 * (r["widen_x"] - 1.0) / (r["total_x"] - 1.0)
        db_w = 20.0 * (r["widen_x"] ** 0.0) * 0 + 20.0 * __import__("math").log10(r["widen_x"])
        db_m = 20.0 * __import__("math").log10(r["then_mf_x"])
        print(f"    {r['stack']:>16s}  widening {db_w:+5.2f} dB   "
              f"then MF {db_m:+5.2f} dB   -> widening is {pct:5.1f}% of the gap")

    with open(os.path.join(OUT, "s26_m73_discrimination.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1)
    print("\nwrote out/s26_m73_discrimination.json")


if __name__ == "__main__":
    main()

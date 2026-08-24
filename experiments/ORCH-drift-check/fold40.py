"""Fold the resample budget and M98's adjudication into SYNTHESIS.md.

Facts 1287-1290, disciplines 632-633.
Mechanics as fold38/39: splice the discipline block FIRST (it sits below the
fact table, so inserting facts first would shift its index), a fact row is
exactly 5 unescaped pipes, and every assert runs before any write.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1287, "**THE COVERAGE RESCALE ACCOUNTS FOR 64.2% OF THE MERGE'S SHARPNESS DEFICIT, AND IT IS ONE GATHER, NOT TWO.** "
           "Catmull-Rom implemented as a separable 4-tap gather (not scipy's B-spline, which is interpolating and would "
           "understate the loss), measured on the same 40 tiles and normalisation as fact 1286. Cost against the "
           "unresampled single frame, in mean log10 power over 0.30-0.48 cyc/px: **one gather at scale 1/0.9315 = "
           "+0.2392 dex; two gathers in series = +0.7622 dex; the measured merge = +0.3693 dex.** Controls: NULL "
           "(scale 1.0, zero offset) **+0.0000 dex**; DOSE (offset 0/0.125/0.25/0.5 px) **+0.0000 / +0.0527 / +0.1938 / "
           "+0.5249**, monotone with the half-pixel worst, which is the correct Catmull-Rom signature.",
     "Two gathers overshoot the measured deficit by **206%**, so the pipeline demonstrably performs **one** resample "
     "and no milestone should go looking for a second to remove. The remaining **+0.1301 dex** is unexplained and is "
     "NOT claimed to be nothing; the two candidates are the demosaic confound of fact 1286 and election correctness, "
     "both of which require comparing strehl's own single-frame path against its merge from inside the codebase. "
     "Assigned to M95 with a pre-registered bar: after the fix, MERGE must move from +0.3693 to within noise of "
     "+0.1301, and landing anywhere else means the fix did something other than intended.",
     "ORCH (MEASURED, both controls passed before any arm was read); "
     "`experiments/ORCH-drift-check/resample_budget.py`"),

    (1288, "**THE SUB-PIXEL WARP OFFSET COSTS NOTHING ON TOP OF THE SCALE; THE SCALE IS THE ENTIRE COST.** "
           "Adding a 0.5 px offset to the 1.0735x gather changed the cost from **+0.2392 to +0.2369 dex** -- no loss, "
           "and the sign is the wrong way round at that precision. Yet the same offset applied at scale 1.0 costs "
           "**+0.5249 dex**, the most expensive rung of the dose ladder.",
     "The mechanism is that at a **non-integer scale the output pixels already sample every fractional phase**, so the "
     "cost is already phase-averaged and an added constant offset only reshuffles which phase lands where. The "
     "practical consequence is a milestone-saver: improving warp-offset handling, or reducing sub-pixel warp error, "
     "buys **zero** sharpness while the rescale is present. It also means the two effects must never be priced by "
     "adding their separate costs -- +0.5249 and +0.2392 do not sum to anything real.",
     "ORCH (MEASURED); `experiments/ORCH-drift-check/resample_budget.py`"),

    (1289, "**THE OUTPUT IS A +7.35% INTERPOLATED ENLARGEMENT, CONFIRMED PHYSICALLY ON A RULER.** M98 measured "
           "`fit_to_cover` k = **0.9315**, making the registered render an interpolated enlargement at **every pixel, "
           "every gate**, and recovered the aligner's own k from a photograph of a millimetre ruler at **0.68σ**.",
     "This and fact 1287 are the same mechanism reached by two independent routes -- M98's optical and physical, the "
     "orchestrator's spectral and synthetic -- neither author having seen the other's result. The convergence is the "
     "reason this is being acted on rather than investigated further. The fix is to emit the cropped region at its "
     "**native sampling, ~6550 x 4367 (28.6 MP)**, instead of stretching it back to 7032 x 4688; the output is 7% "
     "smaller in each dimension and materially sharper. If a consumer needs fixed dimensions the stretch must become "
     "**opt-in and off by default**. Note this also independently refutes the 8.2 MP framing of fact 1284: nothing on "
     "this path is anywhere near 8 MP.",
     "M98 (MEASURED, external physical anchor); `docs/research/M98-gate-adjudication.md` P10"),

    (1290, "**THE GATE COSTS +0.10366 ± 0.00352 px ACROSS ITS ENTIRE RANGE, AND ALIGNMENT DOES NOT MOVE THE SHARPNESS "
           "ANSWER AT ALL.** M98, on the shipped axis with alignment ON: the whole range n_eff 1.000 -> 6.489 costs "
           "**+0.10366 ± 0.00352 px** (29.41σ, 24/24), excluding M92's claimed 0.61753 px at **58.5σ**, at 9.8σ on "
           "`bee-3-cpl`, and at 16.0σ on a millimetre ruler (+0.0333 ± 0.0366 px). Alignment lowers mean n_eff at every "
           "rung (55.321 vs 60.860, 0.909x) but the paired sharpness difference is **+0.031 ± 0.023 px** -- H1 "
           "falsified. Where detail actually lives the gate is **inert both ways** (noise 1.000 -> 0.944x, HF 1.0000 -> "
           "0.9904x).",
     "The last line is the load-bearing one: **lowering the gate cannot recover sharpness**, which forecloses the most "
     "obvious response to the owner's complaint before anyone spends a night on it. Consistent with fact 1279's "
     "independent finding that the gate costs only +0.28 to +1.26 px of radial smear. M98's verdict was "
     "**R-INCONCLUSIVE** with R-KEEP missed by 0.35σ and 0.39σ, reported as a miss rather than rounded to a pass; "
     "`DEFAULT_GATE` stays at 4. Controls: equivalence 100.000000% with SHA-256, a planted defect drove it to "
     "99.999996% and the bar went RED, and a planted 0.30 px shift was recovered as +0.299824 ± 0.000015.",
     "M98 (MEASURED; verdict INCONCLUSIVE, not a pass); `docs/research/M98-gate-adjudication.md` P1, P4, P5, P8"),
]

DISCIPLINES = [
    (632, "**Two independent routes to the same mechanism is worth more than either measurement's error bar, and it is "
          "what licenses acting instead of measuring again.** The coverage rescale was found twice in one night by "
          "authors who had not seen each other's work: M98 optically, recovering k = 0.9315 from a photograph of a "
          "ruler at 0.68σ, and the orchestrator spectrally, pricing that same operation at 64.2% of a deficit measured "
          "against an independently decoded RAW. Neither alone would have justified changing the output path -- the "
          "orchestrator had already been wrong twice the same night, on the half-drift (fact 1280) and on binning "
          "(fact 1284), each time with a plausible single line of evidence. The rule: **when a mechanism is expensive "
          "to act on, require a second route to it that shares no instrument, no author, and no assumption with the "
          "first**; and when you get one, stop measuring and build. Facts 1287, 1289."),

    (633, "**Verify a subagent's claim that something is ABSENT with the same rigour as a claim that something is "
          "present -- and treat 'retracted' and 'absent' as opposite findings.** M98 reported \"discipline 605 does not "
          "exist in SYNTHESIS\"; it exists at line 3066, struck through and retracted via fact 1250, and is cited as "
          "live corpus in fact 1273. A strikethrough or a stale copy most likely defeated the search. The distinction "
          "is not bookkeeping: an **absent** discipline invites the next milestone to re-derive the claim from "
          "scratch, whereas a **retracted** one forecloses it *and records why*, which is the more valuable artefact. "
          "One grep settled it before the error could propagate into a report. Companion to the standing rule about "
          "confirming a claimed fabrication is actually in the target document."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")

    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1286 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^631\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes, need 5"
        rows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded facts 1287-1290 after line {fact_idx}, "
          f"disciplines 632-633 after line {disc_idx}")


if __name__ == "__main__":
    main()

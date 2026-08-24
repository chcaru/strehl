"""Annotate fact 1427 in place with its retraction, and fold the M104c/M103 results.

Fact 1427 as folded says the exit-code trap is "a race rather than a count".
That is wrong. It came from M104c's un-pre-cleared 50-line arm, which was the
stale-value confound of fact 1429. Both ORCH and M104c have now re-measured with
a verified pre-clear and agree 5/5 in each direction: the mechanism is QUOTA.

This does not delete the fact. Per the corpus's own practice (fact 1402), a
refuted claim is annotated in place with the retraction attached, so a reader
who arrives via a citation sees the correction rather than a clean-looking
wrong statement.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

RETRACTION = (
    " **>>> MECHANISM RETRACTED AND RE-MEASURED (same session). \"A race rather than a count\" is WRONG. "
    "The trap is DETERMINISTIC ON QUOTA: `-First N` loses the exit code whenever `N <= the number of "
    "objects produced`, and preserves it when `N` exceeds them.** Measured independently by ORCH and "
    "M104c, 5/5 reps in each direction: on a 50-line command `-First 3`, `-First 49` and `-First 50` all "
    "read `0`; `-First 51` and `-First 99` all read `1`. **`-First 3` on a FIVE-line command also loses "
    "it**, so there is no volume threshold and no \"small output is safe\" case. Merging stderr with "
    "`2>&1` does not protect it either. **The 50-line arm that produced the race theory was "
    "un-pre-cleared -- it is fact 1429's confound, caught by the very finding folded beside it.** ORCH's "
    "original count framing was right; ORCH broadcast the wrong correction to seven agents and then "
    "re-corrected it. The unconditional instruction never changed and remains correct; only its "
    "justification was wrong, and a wrong justification is dangerous here because an agent told \"small "
    "output finishes first and reports correctly\" will trust a 50-line `-First` pipeline that loses the "
    "code every single time. <<<"
)

FACTS = [
    (1435, "**THE ALIGNMENT SOLVE'S PLACEMENT TRACK IS JITTERY BY ~110x, AND THE MEASUREMENT NEEDS NO "
           "GAUGE.** M103's second difference of the solve over all 297 interior frames of `bee-3-cpl`: "
           "median **0.4829 px**, p90 **1.0772**, max **9.7069**, with **13.8% of adjacent pairs >= 1 px**. "
           "The first-difference-of-error route agrees and does not depend on the truth fit (median "
           "0.5560 / 0.5624 / 0.5669 at degrees 3/4/6). **Controls:** a synthetic track carrying the real "
           "measured curvature reads **0.0044 px median** against a derived ceiling of `8d/N^2` = 0.0092 px, "
           "so curvature cannot be masquerading as jitter; a planted +/-0.5 px alternation was recovered at "
           "**100.0%** of its predicted amplitude; a linear placebo read **exactly 0**. It is **worse where "
           "spans are starved**: median 0.4464 -> 0.6259 and max **1.70 -> 9.71 px (5.7x)** far from the "
           "reference frame.",
     "**Adjacent frames' relative placement is uncertain by 44.2% of the actual motion between them** -- "
     "the mean true inter-frame breathing step is 1.09 plane px. Read with fact 1393 (`n_eff = 1` "
     "everywhere detailed), the consequence is not blur: **two adjacent detailed pixels electing frames "
     "`j` and `j+1` inherit placements differing by a median 0.48 px**, so the output is a mosaic of "
     "individually sharp patches from inconsistently placed sources. **Local geometric incoherence, not "
     "softness.** This is a candidate mechanism for the waxy blobs and it explains the detail M103 §17 "
     "could not -- *why they have hard, closed boundaries*: an election boundary between two frames "
     "disagreeing by >= 1 px **is** a step, and §17.3 measured the artefact as piecewise-flat at 97.4x "
     "separation from optical softness. A second difference is gauge-invariant by construction, so this is "
     "the one alignment number in the corpus that survives discipline 698 without a stated gauge.",
     "M103 R1/R2 with derived-ceiling, positive and placebo controls (MEASURED)"),

    (1436, "**THE `stack` VS `argmax-baseline` SHARPNESS COMPARISON IS CONFOUNDED, AND THE CONFOUND IS "
           "LARGE: -33.0% OF CENTRE HIGH-BAND ENERGY.** `stack` gathers every frame through a resampler; "
           "`argmax-baseline` performs no alignment and resamples nothing. M104c priced the gap on "
           "`coffee-bean --limit 8 --demosaic` using the **`STREHL_ALIGN=zoom` null control that already "
           "existed in the code** (`align_cmd.rs:1032-1038` -- same resampling cost, same field of view, "
           "relative registration discarded): real aligned **0.000174**, zoom-only null **0.000193**, "
           "no-align **0.000289**. So **resample+FOV costs -33.0%** while **registration buys back only "
           "-9.8%** on this shallow bracket. Positive control (1 px gaussian) moved the metric **-98.4%** "
           "against a pre-registered >20% bar.",
     "**On shallow low-drift brackets the estimator carries a net resampling penalty its control never "
     "pays**, and this sits inside every published `stack`-vs-`argmax-baseline` sharpness number, "
     "including folded facts and numbers currently being used to rank merge changes. It is the same order "
     "as M95's 59% kernel figure. **M104c explicitly declined to name contaminated facts on one stack at "
     "one depth**, and flagged that its own metric cannot separate lost detail from suppressed noise, so "
     "**-33.0% is an upper bound on detail loss, not a point estimate**. Two further findings: the "
     "assigned identity-warp design **does not work** -- `cover_or_explain` composes a global cover zoom "
     "onto every placement, so a sidecar cannot express \"identity gather\" (M104c's own pre-registered "
     "prediction of a bit-exact no-op was refuted at 95.03% of pixels differing) -- and "
     "**`STREHL_ALIGN=zoom` still writes a sidecar into the stack directory**, so the null control "
     "everyone is being pointed at re-pollutes the read-only capture library.",
     "M104c, metric+ROI pre-registered, positive control alive at -98.4% (MEASURED)"),
]

DISCIPLINES = [
    (715, "**When two agents produce two different mechanisms for one defect, suspect the shared harness "
          "before either theory.** ORCH said count, M104c said race, and both were reasoning from arms "
          "that inherited a stale `$LASTEXITCODE`. The pre-clear settled it in one run, 5/5 in each "
          "direction, and the answer was the *original* claim. **A disagreement about mechanism is "
          "evidence about the instrument**, and re-measuring with the confound removed is cheaper than "
          "arguing. Facts 1427, 1429."),
    (716, "**Before building a control, grep for one -- this codebase documents controls that milestones "
          "then rebuild.** M104c was assigned an identity-warp null; the null it actually needed already "
          "existed as `STREHL_ALIGN=zoom`, with a comment stating its purpose verbatim, and the assigned "
          "design provably could not have worked because `cover_or_explain` overrides placements "
          "downstream. **The orchestrator specified a mechanism it had not read the code for.** Specify "
          "the *property* the control must have and let the implementer find or build it. Fact 1436."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    m = re.search(r"^\| 1427 \|.*$", text, re.M)
    assert m, "fact 1427 row not found"
    row = m.group(0)
    assert "MECHANISM RETRACTED" not in row, "already annotated"
    cells = re.split(r"(?<!\\)\|", row)
    assert len(cells) == 6, f"fact 1427 has {len(cells)-2} cells, expected 4"
    assert "|".join(cells) == row, "split/join does not round-trip; escape handling is wrong"
    cells[2] = cells[2].rstrip() + RETRACTION + " "
    newrow = "|".join(cells)
    n = newrow.count("|") - newrow.count("\\|")
    assert n == 5, f"annotated 1427 has {n} unescaped pipes"
    text = text[:m.start()] + newrow + text[m.end():]
    print("annotated fact 1427 with its mechanism retraction")

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1434 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^714\. ", l))
    assert disc_idx > fact_idx

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        k = r.count("|") - r.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(r)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print("folded facts 1435-1436, disciplines 715-716")


if __name__ == "__main__":
    main()

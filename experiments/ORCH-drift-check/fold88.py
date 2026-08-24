"""Fold M97: the election map, the StackIdentity blind spot, and a scoped caveat."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1445,
     "**THE ELECTION MAP IS EXPORTABLE AND ITS STRUCTURE IS REAL, NOT AN ARTEFACT OF THE ARITHMETIC: "
     "BOUNDARY DENSITY 3.33% HORIZONTAL / 3.34% VERTICAL AGAINST 77.41% FOR A VALUE-PRESERVING SHUFFLE, "
     "A 23.2x STRUCTURE FACTOR.** Shipped at `b27904a` as `strehl stack --index-map <PATH>` or "
     "`STREHL_DUMP_ELECTION=<PATH>`, reading `FocusStats::best_index()` after pass one's completeness "
     "assertion. **106 insertions, 0 deletions, no merge arithmetic touched**, and the merged bytes are "
     "identical with the flag, without it and via the env var (`F240C193...`), planted against a "
     "13-frame arm (`DBD8CC3E...`). Grid is the **plane grid at half sensor resolution, 3516x2344**, one "
     "election per 2x2 CFA quad; values are literal 0-based frame indices in filename order; `u16::MAX` "
     "is **refused rather than written**. Content: **12 of 12 distinct indices, 0 sentinels**, median "
     "jump of **1 frame** across a boundary, **71.4%** single-frame steps.",
     "**This is the first instrument that can attribute an output artefact to the merge's internal "
     "state rather than to appearance**, and that property is what makes it immune to the control that "
     "killed my last attempt: a joint statistic between the render and the election map **cannot be "
     "reproduced by a single unstacked frame, because a single frame has no election map at all** (fact "
     "1438, discipline 718). The shuffle is a genuine plant -- it can report a structureless map -- so "
     "3.33% measures the merge. **Caveat that invalidates naive reuse: this was measured with "
     "`STREHL_ALIGN=0`**, so any correlation run under alignment must pin the sidecar via "
     "`STREHL_WARPMAP` or the two halves come from different registrations. Handed to M111 with "
     "instructions not to re-derive any of it.",
     "M97-warped-merge, 6/6 bars with both nulls planted (MEASURED)"),

    (1446,
     "**THE STACK CACHE KEY DOES NOT COVER ITS OWN INPUTS: AN IDENTICAL COMMAND LINE PRODUCES "
     "`DB43E708...` OR `ADF81E01...` DEPENDING ONLY ON WHETHER AN UNRELATED `align --reference 40` RAN "
     "FIRST.** `StackIdentity` covers the frame set but **not `reference` and not `resampler`** -- and "
     "`resampler` is the field M95 attributes **59%** of high-band loss to. The un-poisoned path still "
     "reproduces byte-freeze `54A5E20F44255BB5` at HEAD, so the defect is history-dependence, not "
     "corruption.",
     "**This is a validity defect under every measurement the fleet is currently producing, not a "
     "milestone-local bug.** Any A/B comparison can be silently scored against a poisoned cache, which "
     "means a sharpness, halo or merge result can differ between two agents for no reason visible in "
     "either agent's command line. It is the same class as M108's byte-freeze that could not tell "
     "\"verified nothing\" from \"verified everything\" (fact 1437's neighbourhood): **a gate whose key "
     "omits an input cannot distinguish a real change from a stale one.** Assigned to M97 as the FIRST "
     "priority ahead of its own pixel-changing work, because it silently taxes everyone else's numbers "
     "while it stands.",
     "M97-warped-merge (MEASURED)"),

    (1447,
     "**\"`cmd` PRODUCERS ARE IMMUNE TO THE `-First` EXIT-CODE TRAP\" DOES NOT GENERALISE FROM AN INLINE "
     "`cmd /c` TO A `.cmd` SCRIPT FILE.** M97 measured a `cmd /c \"for /L ... echo\"` builtin loop as "
     "immune at every N, **25/25**. I measured the opposite through a `.cmd` **file** invoked with the "
     "call operator -- `experiments/ORCH-drift-check/producer_n.cmd`, a `for /L` echo loop ending in "
     "`exit /b 1` -- which **lost the code** at `-First 3`, `-First 50` and on five-line output, across "
     "four hosts, pre-cleared and warmed.",
     "**Both measurements are believed; the producer form is a third axis and the immunity claim must be "
     "scoped to the exact form measured.** An agent who reads \"cmd is immune\" and builds a harness on "
     "a `.cmd` script gets the trap back with no warning. **This changes no operative rule** -- rule 47 "
     "already says never read `$LASTEXITCODE` after any pipeline containing `-First`, and assert the "
     "exact expected code -- which is precisely the value of a rule stated on the safe side of a "
     "mechanism nobody has fully mapped. **Four wrong or over-general beliefs have now come out of this "
     "one defect**; the rule survived all four because it never depended on the mechanism.",
     "ORCH `exit_code_host.ps1` + `producer_n.cmd` vs M97's inline probe; both MEASURED, on different "
     "producer forms"),
]

DISCIPLINES = [
    (728,
     "**A cache key must cover every input that can change the output bytes, or it silently invalidates "
     "every A/B running against it.** Fact 1446: an unrelated prior command changed a stack's output "
     "hash because `StackIdentity` omitted `reference` and `resampler`. The failure is invisible at the "
     "call site -- the command line is identical -- so no agent can detect it from its own transcript. "
     "**Treat an unkeyed input as a fleet-wide measurement defect, not a local bug**, and prioritise it "
     "above pixel work, because it taxes the credibility of every number produced while it stands."),
    (729,
     "**An agent blocked on a permission I control is idle capacity, and seven unanswered requests is my "
     "failure, not a queue.** M97 asked for the `merge.rs` lane **seven times** across a ten-hour run "
     "while the file sat uncontended, and filled the gap with metrology I had dispatched -- work it "
     "itself summarised as *\"none of them will change a pixel tonight.\"* The lesson is not \"grant "
     "everything\": it is that **a request to enter a file is a scheduling decision only the "
     "orchestrator can make, so leaving it unanswered converts a working agent into a waiting one.** "
     "Ask every long-running agent what it is blocked on; M97's answer named a defect (fact 1446) that "
     "outranked everything else in flight."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1444 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^727\. ", l))
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
    print("folded facts 1445-1447, disciplines 728-729")


if __name__ == "__main__":
    main()

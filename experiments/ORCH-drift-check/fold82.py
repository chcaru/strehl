"""Fold the quota-model confirmation and the cold-invocation exception."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1437,
     "**THE `-First` EXIT-CODE TRAP IS A QUOTA, CONFIRMED AGAINST A PRE-REGISTERED PREDICTION, WITH ONE "
     "COLD-START EXCEPTION MEASURED AT 1/320.** A 14-arm harness declared per-arm predictions under the "
     "model *lost iff `N <= object count`* **before** running, then scored them: **13/14 matched at 5/5 "
     "reps**, including both directions of the exact boundary (`-First 50` LOST, `-First 51` PRESERVED), "
     "the volume test (`5 lines \\| -First 3` LOST, `-First 6` PRESERVED -- **no volume threshold "
     "exists**), and the timing test (a 5 ms/line delay changed nothing -- **not a race**). `-Last 3`, "
     "`-Last 99`, `Out-String` and the no-pipeline control all preserved the true code. The one mismatch, "
     "`50 lines \\| -First 3` reading `1,-1,-1,-1,-1`, was then characterised at 40 reps x 8 values of N: "
     "**1 anomaly in 320 reps, at rep 1 of the first arm, despite an explicit warm-up invocation**; "
     "N = 1,2,3,5,10,25,49,50 each lost 40/40 once warm.",
     "**A cold first invocation can preserve the exit code, and that is exactly how someone \"verifies\" "
     "`-First` is safe** -- run it once, see the right answer, ship the belief. This is the **third "
     "distinct confound** in one defect, after stale-value inheritance (fact 1429) and the un-pre-cleared "
     "arm that produced the retracted race theory (fact 1427). The operative rule is unchanged and "
     "**reinforced**: non-determinism at rep 1 is strictly worse than reliable failure, because a probe "
     "that passes cold will fail warm. Note the harness's own structural blindness: the previous version "
     "used `N=3` against a fixed 200-line probe in **every** `-First` arm, so `N <= count` held "
     "universally and the boundary was never approached -- it measured the trap correctly and could not "
     "have found its cause.",
     "ORCH `exit_code_trap2.ps1` (14 arms x 5 reps, predictions pre-registered in the arm table) + "
     "`exit_code_trap3.ps1` (8 N-values x 40 reps) (MEASURED)"),
]

DISCIPLINES = [
    (717,
     "**Put the pre-registered prediction in the harness's own data structure, and let a mismatch fail the "
     "run.** `exit_code_trap2.ps1` carries a `Pred` column written before execution and bar E4 scores "
     "every arm against it. That is what caught the cold-start anomaly: a harness that merely *printed* "
     "codes would have shown `1,-1,-1,-1,-1` and been read past as noise. **A prediction stored beside "
     "the measurement cannot be quietly revised after seeing it** -- and when E4 went red the correct "
     "response was 320 more reps, not an edited prediction. Pair it with a determinism bar (E5): "
     "unanimity across reps is what distinguishes a mechanism from a tendency. Fact 1437."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1436 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^716\. ", l))
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
    print(f"folded fact 1437, discipline 717")


if __name__ == "__main__":
    main()

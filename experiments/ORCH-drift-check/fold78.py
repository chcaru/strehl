"""Fold the exit-code trap measurement. Facts 1427-1429, disciplines 709-710."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1427, "**`$LASTEXITCODE` IS UNRELIABLE AFTER ANY PIPELINE CONTAINING `Select-Object -First N`, AND THE "
           "MECHANISM IS A RACE RATHER THAN A COUNT.** `-First` throws `StopUpstreamCommandsException` on its "
           "Nth object; the exit code is lost only if that short-circuit lands **while the native process is "
           "still running**. Measured both sides: M104c-verify saw **50 lines** through "
           "`Select-String \\| Select-Object -First 3` -- ~17x more matches than N -- still report the true "
           "`1`; ORCH saw **200 lines** through the same shape misreport. **`-Last N` and `Out-String` are "
           "safe**, measured 3/3 and 3/3, because `-Last` must drain the whole stream to know its tail and so "
           "cannot short-circuit by construction.",
     "**I first stated this rule as a count (\"more than N matches\"), and M104c refuted it by measurement.** "
     "The count framing is actively harmful: it invites an agent to reason about whether its particular "
     "command is \"big enough\" to be exposed, and the answer also flips with stdout-vs-stderr (20,000 lines "
     "on stderr merged with `2>&1` reported correctly). **No such reasoning is sound.** The operative rule is "
     "unconditional: never read `$LASTEXITCODE` after a pipeline containing `-First`; capture first, then "
     "filter.",
     "ORCH `exit_code_trap.ps1` bars E1/E2/E3 all PASS (MEASURED); M104c-verify turn 2 (MEASURED)"),

    (1428, "**THE CORRUPTED EXIT VALUE IS HOST-DEPENDENT: `0` under the agent shell, `-1` under "
           "`powershell -NoProfile -File`.** Same script, same probe command, same true exit code of 1; only "
           "the host differs. Observed 3/3 arms at `-1` in the script host after 3/3 arms at `0` "
           "interactively.",
     "**This falsifies \"it reads 0\" as the statement of the defect, including my own broadcast of it, and "
     "the consequence is a silent gate failure.** A gate written the natural way -- `if ($code -ne 0) "
     "{ fail }` -- **catches the `-1` case and silently PASSES the `0` case**, which is the dangerous half. A "
     "gate written `if ($code -eq 1)` misses both. The only formulation that survives is that the value is "
     "**unusable**, not that it takes any particular wrong value. Corollary for any future report of a "
     "corrupted status: name the host, because the corruption is not portable.",
     "ORCH `exit_code_trap.ps1` E2, agent shell vs `powershell -File` (MEASURED)"),

    (1429, "**MY FIRST PROBE OF THIS TRAP REPORTED ALL SEVEN ARMS SAFE, AND IT WAS A FALSE NEGATIVE FROM MY "
           "OWN HARNESS.** `$LASTEXITCODE` retains the **previous** command's value, so against a probe whose "
           "true code is 1, a stale `1` is indistinguishable from a correct read. Every arm inherited `1` from "
           "the arm before it. Adding `cmd /c exit 0` plus a verified pre-clear before each arm turned 3/3 "
           "`-First` arms red immediately.",
     "**The confound produces false negatives ONLY, and that asymmetry decides what has to be re-tested.** "
     "Stale retention cannot manufacture a *nonzero* from a zero, so every PASS anyone took from an observed "
     "nonzero code is safe, and M104c's positive finding stands exactly as reported. But **any claim of the "
     "form \"pipeline shape X preserves exit codes\" is only as good as its pre-clear** -- including M104c's "
     "own `-Last` result, which was established by watching it report `1` on a true-1 command. ORCH's "
     "pre-cleared run independently re-establishes it on sound ground; without the pre-clear it would have "
     "been unearned.",
     "ORCH first probe (7/7 false PASS) vs `exit_code_trap.ps1` with pre-clear (3/3 RED) (MEASURED)"),
]

DISCIPLINES = [
    (709, "**Pre-clear `$LASTEXITCODE` before every arm of an exit-code experiment, and verify the pre-clear "
          "took.** It is ambient state that survives across commands, so an arm that fails to set it silently "
          "inherits its neighbour's verdict. This is discipline 706 in a new costume: without the pre-clear, "
          "the control could not have gone red, and it did not. Fact 1429."),
    (710, "**When a bar goes red on an unexpected VALUE rather than an unexpected direction, interrogate the "
          "value before touching the bar.** `exit_code_trap.ps1`'s E2 was written as `Code -eq 0` because that "
          "is what the defect had been reported to look like, and it failed against `-1`. The reflex is to "
          "read the bar as too strict and relax it; the correct reading was that the corruption is "
          "host-dependent (fact 1428), which is a finding the loosened bar would have erased. **A bar that "
          "fails for a reason you did not anticipate has just done its job.** Facts 1427, 1428."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1426 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^708\. ", l))
    assert disc_idx > fact_idx, "discipline list must follow the fact table"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        r = f"| {fid} | {claim} | {interp} | {src} |"
        n = r.count("|") - r.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
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
    print(f"folded facts {FACTS[0][0]}-{FACTS[-1][0]}, disciplines "
          f"{DISCIPLINES[0][0]}-{DISCIPLINES[-1][0]}")


if __name__ == "__main__":
    main()

"""Fold the cross-edition exit-code result: my 'nonzero is safe' clause is refuted."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1443,
     "**MY OWN CLAUSE THAT \"A PASS TAKEN FROM AN OBSERVED NONZERO EXIT CODE IS SAFE\" IS REFUTED: UNDER "
     "WINDOWS POWERSHELL 5.1 THE `-First` CORRUPTION VALUE IS `-1`, WHICH IS NONZERO, SO A RED CONTROL'S "
     "GATE PASSES ON THE ARTIFACT IT EXISTS TO DETECT -- 3/3.** The discriminator is the **PowerShell "
     "edition, not the `-File` switch**, which rule 47 had wrong. Four hosts on this box "
     "(`powershell.exe` 5.1.26100.9168, `pwsh.exe` 7.6.5), 3 corrupted arms each, pre-cleared and warmed: "
     "agent shell in-process **0**; `pwsh -File` **0**; `powershell -File` **-1**; `powershell -Command` "
     "**-1**. Clean arms (`-First 51`, `-Last 3`, unfiltered) preserved **1** on every host. **And 5.1 is "
     "silent about it:** PS 7 emitted `The process tried to write to a nonexistent pipe.` **16 times** "
     "during the probe; PS 5.1 emitted it **0 times**.",
     "**`if ($code -ne 0)` is unsafe in BOTH directions and must never be written again**: as a failure "
     "gate it silently passes the `0` under PS 7, and as a **red control** -- `if ($code -ne 0) { pass }`, "
     "the natural shape -- it silently passes the `-1` under 5.1. Only an assertion on the **exact** "
     "expected code survives every host. Windows PowerShell 5.1 is the worst available combination: "
     "**silent corruption plus a value that satisfies the naive gate**, so an agent using "
     "`powershell.exe` for a scratch harness gets no warning on either channel. **This is the fourth "
     "distinct wrong belief this one defect has produced** (stale-value inheritance, the race theory, the "
     "cold-start exception, and now this), and the third that I personally propagated to the fleet before "
     "measuring. M108 caught it and I confirmed it independently rather than adopting its text.",
     "ORCH, `experiments/ORCH-drift-check/exit_code_host.ps1` + `producer_n.cmd`, four hosts; "
     "independently reproduces M108's table cell-for-cell (MEASURED)"),
]

DISCIPLINES = [
    (724,
     "**Never gate on \"nonzero\" -- assert the exact expected exit code.** A red control that accepts any "
     "nonzero code accepts the corruption artifact itself on Windows PowerShell 5.1, where truncation "
     "yields `-1` (fact 1443). The habit that survives is `if ($code -ne 101) { throw \"expected 101, got "
     "$code\" }`. M108's freeze harness was saved by exactly this habit -- it records literal values "
     "(`EXIT=101`, `EXIT=0`) rather than a predicate -- **not by being immune**."),
    (725,
     "**When a subordinate corrects a rule you wrote, reproduce its measurement before adopting its "
     "replacement text -- and then check the replacement against the tree, because your own contrition "
     "can be wrong too.** I confirmed M108's four-host table independently and it held cell-for-cell. But "
     "my first draft of the correction wrote that rule 47 \"used to send you to\" PS 5.1; grepping "
     "AGENTS.md returned **0** occurrences of `powershell -File` or `-Command` as a recommendation. The "
     "old bullet merely *named* the edition while mislabelling the reading safe. **An overstated mea "
     "culpa is still a false statement in the corpus**, and it would have sent the next reader hunting a "
     "recommendation that was never there."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1442 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^723\. ", l))
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
    print("folded fact 1443, disciplines 724-725")


if __name__ == "__main__":
    main()

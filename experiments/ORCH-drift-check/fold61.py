"""Fold the shared-sidecar hazard and the truncating-pipeline exit-code trap.
Facts 1367-1369, disciplines 680-681.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

PIPE = "\\|"

FACTS = [
    (1367, "**THE WARP SIDECAR IS SHARED MUTABLE STATE INSIDE THE READ-ONLY CAPTURE LIBRARY, AND CONCURRENT RUNS "
           "THRASH IT.** MEASURED at `865c1ff`: `strehl align` defaults its output to `<stackdir>/warpmap.txt` "
           "(`align_cmd.rs:376`, `sidecar_path()` `:787`) and `strehl stack` reads that same path, inside "
           "`D:\\personal\\macro\\<stack>\\`. `load_or_solve` (`align_cmd.rs:923-955`) does guard the frame "
           "count -- on a mismatch it prints *\"sidecar has N frames but the bracket has M; re-solving\"* -- but "
           "it then **caches the re-solve back over the shared file**. Observed on `bee-3-cpl` within 20 minutes: "
           "a full render reporting **`reference frame 149, 299 placed`**, then the same file reading "
           "**`frames 40, reference 20`**. M99 independently observed the same file at **299 -> 60 -> 2** "
           "placements.",
     "**The guard is not the weak point; the cache write is.** The residual hazard is narrow and sharp: a "
     "`--limit N` run that finds a sidecar which happens to have N frames accepts it silently, even though it was "
     "solved on a different subset with a different reference frame. **No control can catch this, because it "
     "contaminates treatment and control identically** -- which makes it the most dangerous class of defect this "
     "project can have while 7 agents share one tree. The mitigation already existed and was simply undocumented "
     "in the operating rules: **`STREHL_WARPMAP`** (`merge_cmd.rs:1035`) names an explicit sidecar, is validated "
     "hard on both stack identity and frame count, and **never caches back**. Verified: a missing file and a "
     "wrong-bracket file each exit **1** with a named error and write no output. The author's own comment at "
     "`merge_cmd.rs:1031` states the principle -- re-solving *\"is correct for a cache and wrong for a file the "
     "operator named\"*.",
     "ORCH (MEASURED at `865c1ff`; corroborated independently by M99's 299/60/2 observation)"),

    (1368, "**`$LASTEXITCODE` READS 0 AFTER A FAILING COMMAND WHENEVER `Select-Object -First N` TRUNCATES ITS "
           "OUTPUT.** MEASURED at `865c1ff` on one command whose true exit code is 1, read four ways in the same "
           "shell: no pipeline -> **1**; `" + PIPE + " Select-String` -> **1**; `" + PIPE + " Select-String " +
           PIPE + " Select-Object -First 3` with more than 3 matches -> **0**; the same with `-First 99`, which "
           "never short-circuits -> **1**. The truncating arm also swallowed two lines of error detail that the "
           "non-truncating arm printed.",
     "**The failure is silent, it inverts the result, and it is in the exact idiom every agent in this project "
     "uses to keep output small.** `" + PIPE + " Select-String ... " + PIPE + " Select-Object -First N` appears "
     "throughout this session's own transcripts. It converts a failing command into an apparently successful one, "
     "which is the direction that turns a **red control green** -- and a green control is a claim about the "
     "instrument, not about the code. It cost a false defect report against the CLI: ORCH asserted *\"the tool "
     "prints `Error:` and exits 0\"*, which would have been a serious bug, when the tool's exit codes are in fact "
     "correct (**1** on failure with no output file, **0** on success). The safe form is to capture first and "
     "filter second: `$out = & $exe ... 2>&1; $code = $LASTEXITCODE` and only then pipe `$out` anywhere.",
     "ORCH (MEASURED at `865c1ff`; 4-arm comparison with a non-truncating positive control)"),

    (1369, "**A FIRST HYPOTHESIS FOR FACT 1368 WAS WRONG AND ITS TEST LOOKED LIKE A CLEAN NEGATIVE.** ORCH first "
           "proposed that any pipeline into a cmdlet corrupts `$LASTEXITCODE`, and tested it with four arms that "
           "all returned **1** -- an apparently decisive refutation of the whole effect. **The test was invalid**: "
           "its arms used the search pattern `\"Error\"`, which matches only 1-2 lines, so `-First 3` never "
           "truncated in any arm. The original failing observation used `\"Error" + PIPE + "error" + PIPE +
           "sidecar\"`, which matches "
           "4+. Re-running with the original pattern reproduced **0** immediately.",
     "**A negative result is only as good as the arm that was supposed to go red.** Every arm agreeing is the "
     "signature of an experiment where the mechanism was never actually engaged, and it reads exactly like a "
     "clean null. The bug was in a part of the command nobody was looking at -- the regex, not the pipeline -- "
     "and it had silently disabled the very condition under test. **Same failure mode as discipline 675's "
     "anchoring rule, arriving through a search pattern rather than a mutation target.** The fix that caught it "
     "was reproducing the original observation verbatim before believing a refutation of it.",
     "ORCH (self-disclosed at `865c1ff`)"),
]

DISCIPLINES = [
    (680, "**Never read a pass/fail gate through a truncating pipeline.** `$LASTEXITCODE` reads **0** after a "
          "command that exited **1** whenever `Select-Object -First N` short-circuits the stream, and that is the "
          "standard idiom in this project for keeping tool output small. It fails in the dangerous direction: "
          "failures become successes, and red controls become green. **Capture the output and the code in two "
          "statements, then filter the captured variable** -- `$out = & $exe ... 2>&1; $code = $LASTEXITCODE` -- "
          "and never let a display convenience sit between a process and the status you are about to trust. "
          "Truncation also swallows error detail, so the same mistake hides the diagnosis it just mis-scored. "
          "Facts 1368, 1369."),
    (681, "**Before prescribing a fix, verify that the CONSUMING command can accept it.** ORCH instructed 7 live "
          "agents to isolate themselves with `strehl align --out <scratch>`; the instruction was inert, because "
          "`strehl stack` has no sidecar argument and always reads `<stackdir>/warpmap.txt`. The producing side "
          "took the flag, the consuming side ignored it, and every affected agent would have believed itself "
          "isolated while sharing the same file. **A workaround is not verified until it has been traced through "
          "the reader as well as the writer** -- and here the correct mechanism (`STREHL_WARPMAP`) already "
          "existed, better designed than the one being invented, and was found only by reading the consumer. "
          "Fact 1367."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1366 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^679\. ", l))
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
    print(f"folded facts 1367-1369 after line {fact_idx}, disciplines 680-681 after line {disc_idx}")


if __name__ == "__main__":
    main()

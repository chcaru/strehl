"""Fold the corpus_lint reporter defect. Fact 1412, discipline 702."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1412, "**THE CORPUS'S STRUCTURAL GATE COULD NOT PRINT THE VIOLATIONS IT FOUND, AND FAILED IN A WAY THAT "
           "READ AS A BROKEN TOOL.** `corpus_lint.py` renders each violation with the offending corpus line "
           "attached. Python selects the ANSI codepage (`cp1252` here) for **redirected or piped** stdout, "
           "and cp1252 cannot encode `\\u0394`, `\\u2212`, `\\u2264` or `\\u2192` -- all of which are "
           "ubiquitous in this corpus. `print(v.render())` therefore raised `UnicodeEncodeError` **mid-loop**. "
           "Measured A/B against HEAD with `PYTHONIOENCODING=cp1252` and stdout captured: pre-fix "
           "**rc=1, violations printed = 0, no `FAIL` summary, 656 B of traceback**; post-fix **rc=1, "
           "violations printed = 7, 0 B of stderr**. Both arms agree there are 7 violations; only one arm "
           "can say so.",
     "**The defect was invisible in the only mode a human uses and active in the only mode an agent uses.** "
     "Run interactively on a UTF-8 console it printed all seven; run with output captured -- every agent "
     "invocation, and any CI log -- it printed **none of them** and exited 1. Since the exit code is 1 for "
     "both 'violations found' and 'reporter crashed', **no caller could distinguish a failing corpus from a "
     "failing tool**, and the visible artifact was a traceback, which invites exactly the wrong diagnosis. "
     "The blast radius is not one run: **the reporter could only ever print a violation whose offending text "
     "was pure cp1252**, which in this corpus is the rare case, so this bounded the gate's usefulness for "
     "its whole life. Fixed by reconfiguring stdout/stderr to UTF-8 with `errors='backslashreplace'` at the "
     "top of `main()`, which cannot itself raise. Exit-code contract unchanged and bar-checked.",
     "ORCH `lint_encoding_ab.py`, 6/6 registered bars incl. 2 that reproduce the pre-fix defect (MEASURED)"),
]

DISCIPLINES = [
    (702, "**A checker that cannot print its findings is not a checker, and a shared exit code hides which "
          "of the two failed.** `corpus_lint.py` found seven violations and reported zero of them because "
          "its reporter could not encode the text it was quoting, then exited 1 -- the same code it uses for "
          "'violations found'. **Every gate in this project must be tested in the mode its callers actually "
          "use** (here: stdout piped, not a console), and **must distinguish tool failure from subject "
          "failure in its exit code or its output**, or a green run and a broken run are the same "
          "observation. The A/B that establishes this needs the pre-fix arm to go *red* first; a passing "
          "post-fix arm alone proves nothing about the fix. Fact 1412."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1411 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^701\. ", l))
    assert disc_idx > fact_idx, "discipline list must follow the fact table"

    rows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        n = row.count("|") - row.count("\\|")
        assert n == 5, f"fact {fid}: {n} unescaped pipes"
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
        rows.append(row)
    drows = []
    for did, body in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"
        drows.append(f"{did}. {body}")

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = rows
    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"folded fact 1412 after line {fact_idx}, discipline 702 after line {disc_idx}")


if __name__ == "__main__":
    main()

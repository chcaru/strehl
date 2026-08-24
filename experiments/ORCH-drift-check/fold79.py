"""Fold M101/M105b's process findings. Facts 1430-1431, disciplines 711-712."""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

FACTS = [
    (1430, "**MY OWN BRIEF PREVENTED THE AGENTS BEST PLACED TO FIND THE LINTER DEFECT FROM EVER SEEING IT.** "
           "M105b reports: *\"my brief instructed me to export `PYTHONIOENCODING=utf-8` before every python "
           "call, and I complied -- so I could never have observed this defect, however many times I ran the "
           "linter.\"* The defect is fact 1412: `corpus_lint.py` crashed with `UnicodeEncodeError` on piped "
           "stdout and **exited 1 while printing zero violations**, indistinguishable from a clean "
           "violations-found run. `PYTHONIOENCODING=utf-8` masks it completely.",
     "**A workaround distributed in a brief is a permanent, invisible suppression of the exact signal it "
     "works around, applied to every agent who follows instructions.** I added that line for convenience; its "
     "effect was to immunise the whole fleet against detecting a live defect in the corpus's own structural "
     "gate, for as long as the brief stood. The agents running the linter most often were the ones least able "
     "to see it break. **Any workaround handed down must name the defect it compensates for**, so the "
     "recipient can recognise it, report it, and know when it is fixed. An unexplained workaround converts a "
     "detectable bug into a permanent silent one.",
     "M105b/M101 report PD16, self-reported (DERIVED); fact 1412 (MEASURED)"),

    (1431, "**A HARNESS THAT RETURNS THE SAME EXIT CODE FOR \"THE TOOL BROKE\" AND \"THE SUBJECT FAILED THE "
           "BAR\" CANNOT DISTINGUISH A FAILED EXPERIMENT FROM A SUCCESSFUL ONE.** M105b's "
           "`10-freeze-record.ps1` returned `1` for both; it now returns **0 / 1 / 2** for pass / subject-fail "
           "/ tool-fail. M105b argues this is **a PowerShell default rather than an oversight**: `throw` and "
           "`exit 1` are each the path of least resistance, and both land on the same code.",
     "**The failure is silent in the direction that matters.** A harness whose own plumbing broke reports "
     "exactly what a harness reports when the thing under test genuinely failed its bar, so a red result "
     "gets attributed to the subject and the broken instrument is never suspected -- the same "
     "instrument-vs-tool confusion that produced fact 1412, M104c's clippy retraction, and my own "
     "seven-arms-safe false negative (fact 1429). **Three distinct codes are the cheapest available "
     "defence**, and discipline 702 caught this one before it could mislead anyone.",
     "M105b `10-freeze-record.ps1`, before/after (MEASURED); discipline 702 (DERIVED)"),
]

DISCIPLINES = [
    (711, "**Never hand down a bare workaround: name the defect it compensates for, or you have immunised the "
          "recipient against detecting it.** `PYTHONIOENCODING=utf-8` in a brief looks like a courtesy and "
          "functions as a blindfold -- it suppressed a live defect in the corpus's own gate for every agent "
          "who complied, which is every agent. Write workarounds as **\"do X because Y is broken; if Y ever "
          "works, tell me\"**, never as a bare instruction. Fact 1430."),
    (712, "**Give a harness three exit codes -- pass, subject failed, tool failed -- because two collapses the "
          "distinction that matters.** The default path in both PowerShell and Python leads to one failure "
          "code for both, so this must be done deliberately. Without it, a broken instrument is "
          "indistinguishable from a genuine red, and this corpus's recurring failure mode is precisely "
          "mistaking the instrument for the subject (facts 1412, 1428, 1429). Fact 1431."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1429 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^710\. ", l))
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

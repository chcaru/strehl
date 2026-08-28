"""Bank facts 1921-1925: BUILD-OUTPUT's four proposed rows plus ORCH's taxonomy correction."""
import io
import re
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"
EXPECTED_TAIL = 1920

ROWS = [
    ("MEASURED", "BUILD-OUTPUT",
     "**A p99.x OVER MAD-SCALE RATIO MEASURES TAIL-HEAVINESS, NOT ENERGY, SO IT IS BLIND TO "
     "EXACTLY THE DENSE TEXTURE A SHARPNESS INSTRUMENT EXISTS TO SEE.** In `bandqual.py` a "
     "full-field in-band sinusoid read **R = 0.356**, which is BELOW the **1.003** that pure "
     "noise reads, while sparse in-band ridges of identical amplitude read **5.297**. The "
     "arithmetic is unavoidable: a sine's MAD is **1.048x** its amplitude while its p99.5 is "
     "**1.000x**, so dense structure lifts the floor and the peak together and their ratio "
     "collapses. **Any detectability statistic of this shape will wrongly disqualify a densely "
     "textured subject**, and it will do so most confidently on the subjects with the most "
     "signal. Generalises past this project: a ratio of a high quantile to a scale estimate is a "
     "sparsity statistic wearing an energy statistic's name."),

    ("MEASURED", "BUILD-OUTPUT",
     "**A VERIFIER BUILT ONLY FROM POSITIVE CHECKS IS FULLY SATISFIED BY A DOCUMENT WITH THE "
     "FINDING DELETED, BECAUSE THE CHECK THAT WOULD HAVE FAILED NO LONGER RUNS.** Deletion is not "
     "a weak form of reversal, it is a different attack, and a suite commissioned only against "
     "flipped conclusions has never been tested against it. The repair is to commission deletion "
     "as its own arm, and to add a **specificity** arm that must stay GREEN under an innocuous "
     "wording change so the suite is not merely alarmed by all edits. BUILD-OUTPUT's suite now "
     "reads **arithmetic 3/3, conclusion 2/2, deletion 2/2, specificity 1/1 across 9 arms**, "
     "all through the shipped entry point rather than an internal one. Companion to the earlier "
     "finding that a presence check is satisfied by any duplicate of the value."),

    ("MEASURED", "BUILD-OUTPUT",
     "**BAND QUALIFICATION IS PER-BAND, AND A QUALIFICATION THRESHOLD DOES NOT TRANSFER BETWEEN "
     "INSTRUMENTS - SO TWO LANES DISAGREEING ABOUT A SUBJECT MAY BOTH BE RIGHT.** `112MSDCF` "
     "reads **R = 1.079 FAIL at 0.30-0.35 cyc/px** on V-LINEAR's instrument and **R = 1.694, "
     "qualifying on 100 percent of crops, at 0.077-0.20 cyc/px** on BUILD-RECERT's. Different "
     "bands, different statistics; **neither reading overturns the other and neither should be "
     "quoted as the subject's verdict**. The practical rule is that a qualification number is "
     "meaningless without its band and its instrument attached, and a cross-lane contradiction "
     "should trigger a check of those two before anyone is judged wrong."),

    ("MEASURED", "BUILD-OUTPUT",
     "**A FLAG STRING PINNED IN A HARNESS IS NOT A MEASUREMENT OF WHAT RAN.** `recert.py:69` pins "
     "`FLAGS` as `--srgb --auto-exposure`, which reads as though auto-exposure was exercised in "
     "the regression arms. It was not: on the `--srgb` path the tone stage supersedes it and the "
     "shipped binary prints `--auto-exposure is SUPERSEDED and applies NOTHING`. The decisive "
     "evidence was distributional rather than textual - **p99.9 of 63983 to 64449, so the top of "
     "the real distribution never reaches the 65535 clip point**, which is not what an applied "
     "auto-exposure gain would produce. Read the binary's own report of what it did, not the "
     "command line that invoked it."),

    ("CORRECTED", "ORCH",
     "**THE SESSION'S RUNNING COUNT OF 'INERT KNOBS' WAS A SLOPPY AGGREGATE THAT MERGED FOUR "
     "DIFFERENT THINGS, ONLY TWO OF WHICH ARE DEFECTS - AND ONE OF THE ITEMS COUNTED AGAINST THE "
     "CODEBASE IS GOOD ENGINEERING.** Read out of source rather than inferred from a count. **(1) "
     "SILENTLY INERT AND UNVALIDATED - a real defect:** `STREHL_SOFT_GATE` on the pyramid "
     "default, where unset, `=on` and `=zzznope` all exit 0 with byte-identical output, so a typo "
     "is indistinguishable from a working setting. **(2) BANNER ASSERTS THE OPPOSITE - the worst "
     "kind:** the CA banner prints `lateral CA : CORRECTING` directly above `alignment : "
     "REFUSED`. **(3) INERT BY VALUE, HONESTLY:** `SELECTION_INFLATION` is 1.0 and both branches "
     "return 1.0, which is dormant rather than broken. **(4) DECLARED CONDITIONAL NO-OP - NOT A "
     "DEFECT AT ALL:** `--auto-exposure` under `--srgb`. `merge_cmd.rs:7069` states in terms, "
     "'This is a declared no-op, not a silent one', the binary prints its own supersession at "
     "runtime, and the guard exists because applying it on top of the tone stage multiplies an "
     "already-normalised image by its own gain a second time - **MEASURED at 92.03 percent of "
     "pixels clipped at 65535 with the flag versus 0.00 percent without, which blew 11 of 18 "
     "masters to a white median**. Off the `--srgb` path the flag stays load-bearing and the "
     "guard deliberately does not steal that case. **The lesson is about the metric, not the "
     "code: 'number of dead knobs' is a statistic of the same defective shape this project keeps "
     "catching elsewhere - it counts occurrences of a symptom without conditioning on the "
     "mechanism, so it convicts a correct regression guard and a silent unvalidated variable at "
     "the same rate.** Report the taxonomy, never the count."),
]


def build_row(num, kind, lane, body):
    if "|" in body:
        raise SystemExit(f"fact {num}: raw pipe in body")
    if body.count("*") % 2 != 0:
        raise SystemExit(f"fact {num}: odd asterisk count")
    return f"| {num} | {kind} | {lane} | {body} |\n"


def main():
    with io.open(PATH, "r", encoding="utf-8", newline="") as fh:
        lines = fh.readlines()

    ids = [int(m.group(1)) for m in
           (re.match(r"^\|\s*(\d+)\s*\|", ln) for ln in lines) if m]
    tail = max(ids)
    if tail != EXPECTED_TAIL:
        raise SystemExit(
            f"tail is {tail}, expected {EXPECTED_TAIL} — another lane wrote rows; "
            "re-read SYNTHESIS before banking")

    anchor = f"| {tail} |"
    hits = [i for i, ln in enumerate(lines) if ln.startswith(anchor)]
    if len(hits) != 1:
        raise SystemExit(f"anchor matched {len(hits)} lines, expected exactly 1")
    at = hits[0]

    new = []
    for offset, (kind, lane, body) in enumerate(ROWS, start=1):
        num = tail + offset
        if any(ln.startswith(f"| {num} |") for ln in lines):
            raise SystemExit(f"fact {num} already present")
        new.append(build_row(num, kind, lane, body))

    lines[at + 1:at + 1] = new

    with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
        fh.writelines(lines)

    print(f"inserted {len(new)} rows ({tail + 1}-{tail + len(new)}) after fact {tail}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Fold M23 (metacalibrated edges) into SYNTHESIS.md.

M23 is a clean negative: review item R4 ships nothing. Its facts are proposed as
blockquotes rather than table rows, so this converts them; consequences are the
orchestrator's, which is the one column the milestone author does not own.
"""
import json, re, pathlib

DST = pathlib.Path("docs/research/SYNTHESIS.md")
SRC = pathlib.Path("experiments/m23-metacal/facts.json")

CONSEQUENCE = {
    170: "**R4 is rejected on its premise, before any gate is scored.** The review's #4-ranked proposal has no valid identity to apply. Any future response calibration on this project must first publish `R(δ)` over at least a 4× δ range and show it flat",
    171: "**Every per-edge division must be Jensen-audited.** Report `mean(1/R)` and `1/mean(R)` separately: their gap is the noise-driven inflation, and it is *not* the bias being corrected. A correction whose average effect survives shuffling is magnitude inflation",
    172: "**A plant's own resampler is a first-class confound, with a size-dependent signature.** The self-pair arm — real content, real plant, zero defect — is now mandatory for any planted-increment probe here. Discipline 81",
    173: "**The fix for span dependence is a phase dither or an upsampled correlation peak, not a calibration.** Opens question 25, which is the live thread M23 leaves behind",
    174: "**Fact 45's causal reading is withdrawn; its numbers stand.** Fact 43 and the M12 ruling are unaffected — they rest on the correlation, not the attribution",
    175: "**The per-edge content of R4 is worth 6.7% of an insufficient correction.** Discipline 83: register the null's arithmetic. Without the shuffled arm, 3.26 → 1.91 reads as a large win",
    176: "**Structural, not statistical: a span-independent correction cannot fix a span-dependent defect.** This is the deepest of the nine — no amount of noise reduction in `R` would change it, so R4 could not have worked even measured perfectly",
    177: "**Gate (c) FAILS on the pre-registered criterion. R4 ships nothing.** Fact 47 is now bounded from a second side: the short edges are not recoverable by response calibration",
    178: "**A treatment that random assignment performs better is not the treatment working.** This is the arm that would have been reported as R4's success had the nulls not been run",
}

SOURCE = {170: "M23 §5.1", 171: "M23 §5.4", 172: "M23 §6", 173: "M23 §6", 174: "M23 §6",
          175: "M23 §7(a)", 176: "M23 §5.3/§7", 177: "M23 §7(c)", 178: "M23 §7(c)"}

MARKS = {
    45: "**CAUSAL READING WITHDRAWN by M23 (fact 174):** the numbers reproduce, the attribution to *defocus* does not — a zero-defocus self-pair on the same code reads **0.372**, *further* from unity than the real defocus pair (0.526), and a resampler-free field reads **0.965**. The mechanism is the plant's own bilinear resampler",
    47: "**BOUNDED FROM A SECOND SIDE by M23:** the short edges cannot be rescued by per-edge response calibration either — held-out is **6.758 px unchanged**, and the winning training set still contains no corrected edge",
    52: "**BROADENED by M23 (fact 175):** a *per-edge* correction reduces in measurement to that same scalar — shuffled `R` reproduces 93.3% of its movement and a constant median `R` 93.5% — so M12's refutation is not merely a transfer failure",
}

DISCIPLINES = """80. **When a probe's response approaches unity as the probe gets *larger*, suspect the probe,
     not the scene.** A scene property does not know the plant size. On this project that pattern
     (0.526 at δ=1e-4 → 0.993 at δ=8e-4) was the first visible sign that the measured response was
     a sub-pixel locking artefact of the plant's own resampler rather than the defocus asymmetry it
     was built to calibrate.
81. **A control that removes the *cause* is worth more than a control that removes the *content*.**
     M10's mechanism table compared a real-pair arm against a synthetic-field arm and concluded
     "defocus", but it omitted the arm with real content and no defocus. **Two of the three cells of
     a 2×2 are not a mechanism.** Enumerate the full 2×2 — defect present/absent × instrument
     artefact present/absent — and fill all four.
82. **Before reporting "all arms are identical, so the treatment is inert", check that the winning
     row *could* have differed.** A comparison whose optimum is set by a row the treatment cannot
     touch has zero power: that is a broken instrument, not a null result. M23 caught this in its
     own first held-out script and preserved the broken version in the record (`§9.1`), which is
     the behaviour rule 20 asks for.
83. **Register the null's arithmetic, not just its existence.** `1/S` moving from 3.26 to 1.91 reads
     as a large effect until the shuffled null lands at 2.00. The informative number is the
     **fraction of the movement the null reproduces** (93.3%), and it should be computed and printed
     by the same script, not left for the reader to divide."""

QUESTIONS = """25. **Does the sub-pixel locking artefact of fact 173 also bias the *unplanted* edge measurements
     the pipeline actually uses?** The `1/S` conservation defect is measured with no resampler in
     the path, so it is not the same artefact — but `coffee-bean`'s span-1 edges have a measured
     displacement of ~0.19 px, squarely in the locking zone, while its long edges do not. If locking
     contributes to fact 43's span dependence, the fix is a **phase dither or an upsampled
     correlation peak, not a calibration**. *Testable:* re-measure `coffee-bean` span-1 edges with
     the moving frame pre-shifted by a known integer-plus-half-pixel offset that is then removed
     analytically, and see whether `1/S_48(1)` moves off 3.26. **This is the live thread M23 leaves
     behind, and it is cheap.**
26. **Is R5 (blur-equalised edges) now the better candidate?** It attacks the same defect without
     planting anything, so it is immune to the mechanism that broke R4. Untested."""


def rows():
    facts = {int(k): v for k, v in json.loads(SRC.read_text(encoding="utf-8")).items()}
    for n in sorted(facts):
        kind, txt = facts[n]
        txt = txt.replace("|", r"\|")
        yield f"| {n} | **{kind}.** {txt} | {CONSEQUENCE[n]} | {SOURCE[n]} |"


def insert_after_last(lines, section_prefix, predicate, block):
    cur, last = "", None
    for i, l in enumerate(lines):
        if l.startswith("## "):
            cur = l
        if cur.startswith(section_prefix) and predicate(l):
            last = i
    assert last is not None, section_prefix
    return lines[: last + 1] + block + lines[last + 1 :]


lines = DST.read_text(encoding="utf-8").split("\n")

# 1. in-place marks
cur, hit = "", set()
for i, l in enumerate(lines):
    if l.startswith("## "):
        cur = l
    if cur.startswith("## 4.") and (m := re.match(r"^(\| (\d+) \|.*)\|\s*$", l)):
        n = int(m.group(2))
        if n in MARKS:
            lines[i] = f"{m.group(1).rstrip()} — {MARKS[n]} |"
            hit.add(n)
assert hit == set(MARKS), f"missed {set(MARKS) - hit}"

# 2. new fact rows, appended after the last row of the facts table
lines = insert_after_last(lines, "## 4.", lambda l: re.match(r"\| \d+ \|", l), list(rows()))
# 3. disciplines and questions
lines = insert_after_last(lines, "## 5.", lambda l: re.match(r"\d+\. \*\*", l) or l.startswith("     "),
                          DISCIPLINES.split("\n"))
lines = insert_after_last(lines, "## 10.", lambda l: re.match(r"\d+\. \*\*", l) or l.startswith("     "),
                          QUESTIONS.split("\n"))

DST.write_text("\n".join(lines), encoding="utf-8")
print(f"marked {sorted(hit)}; added facts 170-178, disciplines 80-83, questions 25-26")

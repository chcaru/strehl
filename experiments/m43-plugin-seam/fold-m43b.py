"""Fold M43 steps 2b and 3 — the measured spread of `k`, and a self-correction.

Two results, one of which contradicts a document committed four hours ago.

Step 2b surveys seven textbook focus operators in the shipped configuration and
finds `k` spanning 0.644 to 6.680 — a 10.4x spread, with the two canonical
shape-from-focus operators (Laplacian, sum-modified-Laplacian) at the top. That
answers question 102.

Step 3 corrects fact 437. Its `k` = 5.94 divided FINE_FOCUS_NOISE_SD by
FOCUS_NOISE_SD, and those two constants are not the same kind of quantity: one
is measured with the 17x17 regulariser applied and one without. The honest `k`
for that pair is 1.815. The cost table in M43 section 2 is unaffected because it
was computed from effective gates rather than from the pair — and the survey now
supplies a larger `k` (6.68) from an operator nobody would call adversarial.

Facts 439 (tail of the 432-439 block) and 500-501 (new block, checked free).
Discipline 257. Question 102 marked answered; fact 437 marked corrected in
place, per the fact-243 precedent — the wrong number stays visible.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DOC = "M43-plugin-calibration-seam.md"

ROWS = [
    (
        439,
        "**Across seven textbook focus operators, the noise constant the gate is calibrated in "
        "spans 10.4x.** Measured in the shipped configuration (operator -> 27x27 box -> 17x17 "
        "regulariser), as `k` = SD / `FOCUS_NOISE_SD`: ring(1,3) **0.644**, tenengrad **1.008** "
        "(the shipped operator, so 1.000 by definition — the 0.8% is the instrument's own noise "
        "floor), tenengrad-squared **1.367**, Brenner **1.962**, local variance **2.475**, "
        "Laplacian **6.590**, sum-modified-Laplacian **6.680**",
        "**Answers question 102, and answers it against fact 438.** The two operators at the top "
        "are the canonical shape-from-focus measures — Nayar & Nakagawa's SML is *the* SFF "
        "operator — so they are the most likely third-party contribution there is, not a "
        "strawman. At the intended `--gate 1.0` an SML plugin inheriting the host constant runs "
        "at an effective **0.150**. And ring(1,3), which is **this project's own first shipped "
        "operator**, errs the other way at 0.644, so both failure directions are populated by "
        "operators that actually exist. **The load-time refusal in fact 438 is therefore "
        "mandatory, not tidy**",
        "M43 step 2b (MEASURED — `experiments/m43-plugin-seam/02b-operator-noise-spread.py`, "
        "8 seeds x 2048^2 unit-variance Gaussian planes; the instrument is calibrated against "
        "**both** in-crate constants in **both** of their configurations and refuses to report "
        "if either misses) — **NOT INDEPENDENTLY VERIFIED**",
    ),
    (
        500,
        "**Fact 437's `k` = 5.94 was wrong, and the error was a units conflation in this "
        "project's own two published constants.** `FOCUS_NOISE_SD` = 0.015214 is the SD of the "
        "**regularised** response; `FINE_FOCUS_NOISE_SD` = 0.090400 is the SD of the "
        "**unregularised** fine field. Dividing them mixes a window-radius change with the "
        "presence of a 17x17 box. The honest quantity — that operator as the host would actually "
        "run it, `SD(regularise(box_mean(\\|grad\\|, 2)))` — is **0.027613**, giving "
        "**k = 1.815**. Fact 437 overstated that pair by **3.27x**",
        "**The conclusion survives and is now better supported than the illustration ever made "
        "it.** M43's cost table was computed by running the binary at effective gates, not from "
        "the pair, so every number in it stands; what fails is only the sentence claiming 5.94 "
        "came from two real operators. Fact 439 then supplies a *larger* real `k` — 6.68, from "
        "SML — so the corrected record prices the seam higher than the mistake did. **Recorded "
        "rather than quietly patched because the failure mode is general**: a ratio of two "
        "constants is only meaningful if both were measured in the same configuration, and "
        "nothing in this repository said they were not",
        "M43 step 3 (MEASURED — `experiments/m43-plugin-seam/03-fine-in-gate-path.py`; the "
        "direction was **pre-registered in the script's docstring** before the number was "
        "computed, and held) — **NOT INDEPENDENTLY VERIFIED**",
    ),
    (
        501,
        "**A two-target calibration caught it; a one-target calibration would have shipped it.** "
        "The first instrument (`02-...py`) modelled the coarse field without the regulariser. "
        "Against `FINE_FOCUS_NOISE_SD` it matched to **+0.20%**; against `FOCUS_NOISE_SD` it read "
        "**+24.26%** high. One target passing and one failing localises the fault to exactly what "
        "the two configurations differ in — which was the regulariser, and was the bug",
        "**The pattern of pass and fail carried the diagnosis, not the magnitude of the miss.** A "
        "single target would have been matched by tuning, and the survey built on it would have "
        "been wrong by 24% with nothing to say so. The script was written to refuse to print its "
        "own results when calibration fails, and that refusal is what forced the investigation "
        "instead of a plausible-looking table. Generalised as discipline 257",
        "M43 steps 2/2b (MEASURED — the failing run is preserved at "
        "`experiments/m43-plugin-seam/02-operator-noise-spread.py`, which is kept precisely "
        "because its failure is the useful part) — **NOT INDEPENDENTLY VERIFIED**",
    ),
]

DISCIPLINE = """257. **Calibrate an instrument against at least two targets that differ in a
     known way, and make it refuse to report when calibration fails.** One
     target can be matched by a compensating error; two cannot, and the
     *pattern* of which passed and which failed points at the fault. Fact 501
     is the worked example - a Python model of the focus operator matched the
     fine constant to 0.20% and missed the coarse one by 24.26%, and the one
     thing those two configurations differ in was the bug. This is the cheap
     structural answer to M31-V's standing objection that the Python proxies
     were never checked against the crate: a proxy that reproduces two in-crate
     constants measured in two different configurations has earned a narrow
     licence, and one that reproduces none has earned nothing.
"""

Q_MARK = (
    "\n\n    **ANSWERED by fact 439** (M43 step 2b): `k` spans 0.644 to 6.680 across\n"
    "    seven textbook operators, a 10.4x spread, with the two canonical\n"
    "    shape-from-focus measures at the top. The spread is as wide as the\n"
    "    built-ins', so the load-time refusal is mandatory. The same work found\n"
    "    that fact 437's `k` = 5.94 was itself wrong — see fact 500."
)

F437_MARK = (
    " — **`k` = 5.94 CORRECTED by fact 500**: it divides an unregularised SD by a "
    "regularised one, and the honest value for that pair is **1.815**. The cost table is "
    "unaffected (it was run at effective gates) and fact 439 supplies a larger real `k`"
)


def build_row(n, claim, consequence, provenance):
    row = f"| {n} | {claim} | {consequence} | {provenance} |"
    # Escaped pipes are legal inside a cell and must not count as delimiters.
    if len(re.findall(r"(?<!\\)\|", row[1:-1])) != 3:
        raise SystemExit(f"row {n}: unescaped pipe in text")
    return row


def section_bounds(text, num):
    m = re.search(rf"^## {num}\.", text, re.M)
    if not m:
        raise SystemExit(f"section {num} not found")
    nxt = re.search(r"^## ", text[m.end():], re.M)
    return m.start(), (m.end() + nxt.start() if nxt else len(text))


def append_list_item(text, section, item_text, expect_last):
    lo, hi = section_bounds(text, section)
    seg = text[lo:hi]
    items = list(re.finditer(r"^(\d+)\. \*\*", seg, re.M))
    last_num = int(items[-1].group(1))
    if last_num != expect_last:
        raise SystemExit(f"section {section}: expected last {expect_last}, found {last_num}")
    ins = lo + len(seg.rstrip("\n"))
    return text[:ins] + "\n" + item_text.rstrip("\n") + "\n" + text[ins:]


def main():
    text = SRC.read_text(encoding="utf-8")

    facts = {int(m.group(1)) for m in re.finditer(r"^\| (\d+) \|", text, re.M)}
    want = {r[0] for r in ROWS}
    if facts & want:
        raise SystemExit(f"fact collision: {sorted(facts & want)}")

    lines = text.split("\n")

    # 1. mark fact 437 in place, before inserting anything after it
    idx = [i for i, l in enumerate(lines) if l.startswith("| 437 |")]
    if len(idx) != 1:
        raise SystemExit("expected exactly one fact-437 row")
    row = lines[idx[0]]
    if not row.endswith(" |"):
        raise SystemExit("fact-437 row does not end in a cell delimiter")
    if "CORRECTED by fact 500" in row:
        raise SystemExit("fact 437 already marked")
    lines[idx[0]] = row[:-2] + F437_MARK + " |"
    if len(re.findall(r"(?<!\\)\|", lines[idx[0]][1:-1])) != 3:
        raise SystemExit("marking fact 437 introduced a pipe")

    # 2. insert the new rows after fact 438
    anchor = [i for i, l in enumerate(lines) if l.startswith("| 438 |")]
    if len(anchor) != 1:
        raise SystemExit("expected exactly one fact-438 row")
    lines[anchor[0] + 1 : anchor[0] + 1] = [build_row(*r) for r in ROWS]
    text = "\n".join(lines)

    # 3. discipline 257
    text = append_list_item(text, 5, DISCIPLINE, expect_last=256)

    # 4. mark question 102 answered
    lo, hi = section_bounds(text, 10)
    seg = text[lo:hi]
    m = re.search(r"^102\. \*\*", seg, re.M)
    if not m:
        raise SystemExit("question 102 not found in section 10")
    nxt = re.search(r"^\d+\. \*\*", seg[m.end():], re.M)
    end = (m.end() + nxt.start()) if nxt else len(seg.rstrip("\n"))
    body_end = lo + len(seg[:end].rstrip("\n"))
    text = text[:body_end] + Q_MARK + text[body_end:]

    SRC.write_text(text, encoding="utf-8")
    print(f"inserted facts {sorted(want)}, discipline 257; marked fact 437 and question 102")


if __name__ == "__main__":
    main()

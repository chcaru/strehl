"""Insert facts 1841-1842 after row 1840 of the SYNTHESIS fact table.

Anchored on the full row-1840 prefix and hard-errors if the anchor does not land
exactly once. Avoids raw `|` and stray `*` in cell text -- the previous insert
tripped corpus_lint S1 (unescaped pipes truncate a table row, silently
DISCARDING cells past the header count) and S5 (odd asterisk count leaves an
italic span open). Both are silent-in-the-renderer failures, so they are worth
avoiding by construction rather than catching by lint.
"""

import io
import sys
from pathlib import Path

SYN = Path(__file__).resolve().parents[2] / "docs" / "research" / "SYNTHESIS.md"

ROWS = [
    (
        "1841",
        "MEASURED",
        "ORCH",
        "**THE HALO IS FIXED ON THE SHOWCASE SUBJECTS AND STILL PRESENT ON FOUR OTHERS; "
        "ONE OF THEM IS ESTIMATOR-SCALE ON THE PYRAMID DEFAULT.** The owner's loudest "
        "standing complaint is that halos made earlier output \"entirely unusable\". "
        "Measured across all 26 faithful masters with `halo_profile.py` (commit "
        "`65e1ff92`), which reports overshoot of near-silhouette backdrop above its own "
        "far field, plus `bump`, the largest decrease walking outward, zero on a clean "
        "monotone ramp. **Partition: 7 clean, 4 HALO, 15 skipped, 26 total**, a reason "
        "printed beside every skip. GOOD: `bee-1/2/3-cpl` read overshoot −3666.5 / "
        "−4273.0 / −4212.3 DN with **bump 0.0**, and `flower-bud-alone-cpl` — the subject "
        "on which the estimator backend measured a **4739 DN** aura — now reads **−431.7, "
        "clean**. Corroborated visually: 1:1 crops of `bee-1-cpl` at halo-targeted sites "
        "show backdrop uniformly white against the dark body with single hairs resolved. "
        "STILL FAILING: `flat-on-ruler-cpl` overshoot **+4481.8 DN** (bump 227.0), "
        "`tweezers-cpl` **bump 1542.3** with overshoot −15502.0, `lavendar-cpl` +527.3, "
        "`dry-erase-marker-head-cpl` +236.7 against a 200 DN threshold. Two observations "
        "that shape the fix: `flat-on-ruler-cpl` is **estimator-scale halo surviving on "
        "the pyramid default**, so the backend switch did not close the defect class; and "
        "`tweezers-cpl` fails on a DIFFERENT statistic (non-monotone ramp) than the other "
        "three (bright rim), so this is plausibly two defects and one fix should not be "
        "assumed to cover both. Assigned to V-SPEED with the seven clean subjects as a "
        "no-regression acceptance condition.",
    ),
    (
        "1842",
        "MEASURED",
        "V-LINEAR",
        "**THE SIGNAL/NOISE BAND BOUNDARY IS A PROPERTY OF THE SUBJECT, NOT OF THE CORPUS: "
        "NO LANE MAY USE A FIXED BAND.** Measured on five subjects with linear develops on "
        "disk, the boundary spans **0.17 to 0.48 cyc/px, a 2.8x spread**. "
        "`flower-bud-alone-cpl` (0.17) and `leaf-2-cpl` (0.20) qualify **no** band at or "
        "above 0.20, so the 0.20-0.25 band this project had been quoting is **noise on "
        "those subjects**, while `bee-1-cpl` sits at 0.48. This refutes ORCH's fixed "
        "criterion (band 0 = 0.25-0.50 as NOISE, band 1 = 0.17-0.25 as SIGNAL, corpus-wide) "
        "which had been issued in writing to several lanes; the error runs in BOTH "
        "directions by subject, and on a high-boundary subject it calls signal \"noise\", "
        "which **licenses shipping a softer image**. Controls: the far-ladder 8/20/auto "
        "gives an IDENTICAL boundary on 5/5 subjects at all three rungs, so the spread is "
        "the subjects and not the parameter; but R's MAGNITUDE moves 4.36x on bee against "
        "under 1.13x elsewhere, so **cross-subject R ratios are not licensed**. Two "
        "candidate explanations were REJECTED: stack depth is non-monotone (N=33,63 -> "
        "0.25; N=182,205 -> 0.20,0.17; N=299 -> 0.48), and fine-structure content is 4/10 "
        "concordant and anti-correlated at the extreme, bee having the highest boundary and "
        "the LOWEST fine content. **Nothing measured predicts where a subject's boundary "
        "lands**, which is an open question rather than a lemma. Two instrument defects "
        "were found and fixed before publication, one of which let a wide band certify its "
        "own top edge on content an octave below it.",
    ),
]

ANCHOR = "| 1840 | DISCIPLINE | V-DILUTE |"


def main() -> int:
    text = SYN.read_text(encoding="utf-8")
    lines = text.split("\n")

    hits = [i for i, ln in enumerate(lines) if ln.startswith(ANCHOR)]
    if len(hits) != 1:
        sys.stderr.write(
            f"ANCHOR NOT UNIQUE: {ANCHOR!r} matched {len(hits)} lines; refusing to write.\n"
        )
        return 2

    for _id, _s, _src, txt in ROWS:
        if f"\n| {_id} |" in text:
            sys.stderr.write(f"FACT {_id} ALREADY PRESENT; refusing to write.\n")
            return 2
        if "|" in txt:
            sys.stderr.write(f"FACT {_id} CONTAINS A RAW PIPE; would truncate the row.\n")
            return 2
        if txt.count("*") % 2 != 0:
            sys.stderr.write(f"FACT {_id} HAS AN ODD ASTERISK COUNT; italic never closes.\n")
            return 2

    new_rows = [f"| {i} | {s} | {src} | {t} |" for i, s, src, t in ROWS]
    at = hits[0] + 1
    lines[at:at] = new_rows

    with io.open(SYN, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines))

    print(f"inserted {len(ROWS)} rows after line {hits[0] + 1} (fact 1840)")
    print(f"new tail: {ROWS[-1][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

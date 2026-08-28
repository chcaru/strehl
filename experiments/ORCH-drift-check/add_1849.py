"""Insert facts 1849-1850 after row 1848 of the SYNTHESIS fact table.

Same guards as add_1846.py: unique anchor, no raw `|` in cell text (corpus_lint
S1 silently discards every cell past the header count), even asterisk count (S5,
an odd count leaves an italic span open). Both render invisibly, so they are
prevented by construction.

1849 is MEASURED -- it is a direct tabulation of a line the shipping renderer
already printed for every delivered master, with the meaning taken from the
source that prints it rather than from the name of the field.

1850 is deliberately ARGUED, not MEASURED. It is a rank correlation between that
table and one person's eye on two crops per subject, with N and subject content
both confounded, and it names the confounds rather than burying them.
"""

import io
import sys
from pathlib import Path

SYN = Path(__file__).resolve().parents[2] / "docs" / "research" / "SYNTHESIS.md"

ROWS = [
    (
        "1849",
        "MEASURED",
        "ORCH",
        "**THE SHIPPING MERGE IS IN ITS SELECTING REGIME FOR ESSENTIALLY EVERY "
        "MID-FREQUENCY COEFFICIENT OF EVERY DELIVERED SUBJECT, WHICH IS EXACTLY WHERE THE "
        "SELECTION PREMIUM APPLIES.** `blend-render.rs` already prints, per render and per "
        "pyramid level, what its own comment calls the fraction of coefficients where NO "
        "frame cleared the noise floor and the merge therefore averaged instead of "
        "selecting; the meaning was taken from the source that prints it rather than "
        "inferred from the field name. Tabulated across all 26 delivered masters by "
        "`orch_avgband.py`, as percentages: band 1 mean **0.29** with 23 of 26 subjects "
        "below 1 percent, band 2 mean **0.08**, band 3 mean **0.06**, band 4 mean "
        "**0.03**, bands 5 and 6 **0.00** on every subject, and the residual band 7 at "
        "100.0 by design. **Band 0 is the only band with real spread: 0.0 to 72.5, mean "
        "25.8.** CONSEQUENCE: fact 1843's premium -- selecting rather than averaging "
        "multiplies noise power 2.16x to 24.82x at N=4/9/19 and 23.24x to 240.70x at "
        "N=19/39/79 -- is not an occasional regime entered on hard subjects. It is the "
        "operating regime of the merge across the whole mid-frequency range on all 26 "
        "subjects, eleven of which are N=299. A candidate-set control that only alters "
        "behaviour where the merge currently averages would therefore touch between 0.03 "
        "and 0.29 percent of bands 1-6 and accomplish nothing. IMPORTANT LIMIT ON THIS "
        "READING: the statistic counts coefficients where no frame cleared the floor, so a "
        "low value proves at least one frame cleared and says **nothing** about how many "
        "were admitted or what `n_eff` was among them. It must not be restated as `n_eff` "
        "equal to 1 in bands 1-6; ORCH nearly did so and that is not what the code "
        "measures.",
    ),
    (
        "1850",
        "ARGUED",
        "ORCH",
        "**BAND 0's AVERAGED FRACTION RANK-ORDERS AGAINST AN INDEPENDENT VISUAL VERDICT, "
        "BUT N AND SUBJECT CONTENT ARE BOTH CONFOUNDED AND THE RELATION FAILS IN THE "
        "MIDDLE.** The subjects judged visibly soft or waxy by eye, before this table "
        "existed, are the high-band-0 subjects: `flowers-cpl` **56.5**, `leaf-2-cpl` "
        "**54.4**, `lead-1-cpl` **53.8**, `flower-bud-alone-cpl` **37.3**, "
        "`pencil-flatter-angle-cpl` **24.7**. The subjects judged excellent are the "
        "low-band-0 subjects: `flat-on-ruler-cpl` **0.0**, `highly-angled-ruler-mm-cpl` "
        "**0.1**, `wrapped-text-1` **1.1**, `foam` **5.5**, `coffee-bean` **7.5**, "
        "`bee-3-cpl` **8.4**, `bee-1-cpl` **10.6**, `wrapped-text-2` **11.9**. THREE "
        "CONFOUNDS, NAMED RATHER THAN SET ASIDE. First, it fails precisely in the region "
        "that matters: `lavendar-cpl` at 33.5 and `pencil-steep-angle-cpl` at 32.2 both "
        "look good, and `119MSDCF` at 34.4 and `coffee-bubbles` at 36.4 look acceptable, "
        "so a mid-30s band 0 is compatible with a fine image and the relation is not "
        "monotone where it would need to be. Second, **N is confounded**: the high-band-0 "
        "subjects are mostly the shallower stacks at N=176, 182, 123 and 205 while the "
        "low-band-0 set includes the N=299 group. Third, **content is confounded**: leaves "
        "and petals are genuinely smooth while rulers and printed text are genuinely "
        "high-contrast, and a subject carrying no fine detail SHOULD show a high band-0 "
        "averaged fraction, which would be the merge behaving correctly rather than "
        "failing. THE QUESTION THIS RAISES AND DOES NOT ANSWER: on the high-band-0 "
        "subjects, is there recoverable signal in band 0 that the floor rejects, or is "
        "band 0 genuinely noise there. V-LINEAR has already measured band 0 as noise or "
        "mixed on 5 of 9 qualified subjects, which is consistent with the merge being "
        "right to average on at least some of them. Until those two populations are "
        "separated and counted, no fix may be justified on this correlation, and pooling "
        "them is the reliable way to measure zero effect and conclude nothing is wrong.",
    ),
]

ANCHOR = "| 1848 | MEASURED | ORCH |"


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

    print(f"inserted {len(ROWS)} rows after line {hits[0] + 1} (fact 1848)")
    print(f"new tail: {ROWS[-1][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

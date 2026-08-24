"""Amend fact 1297. The elimination that produced it was incomplete.

Fact 1297 argued the owner's complaint is sharpness, "by elimination", having
eliminated only exposure. M87 then measured a second visible defect -- the
occlusion halo, three orders of magnitude above any single frame, tracing the
entire subject silhouette -- which was never in the list. Discipline 637, written
in the same commit, says an argument from elimination is only as strong as the
completeness of its list. This amends 1297 rather than quietly repairing it.
"""
import io
import re

P = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

MARK = ("**AMENDED BY FACT 1304: the elimination was incomplete.** Exposure was eliminated; the occlusion halo "
        "(fact 1298) was not, and it is a second measured, visible defect in the same renders.")

FACTS = [
    (1304, "**FACT 1297'S ELIMINATION WAS INCOMPLETE, AND THE CORRECTED ANSWER IS THAT TWO MEASURED DEFECTS ARE "
           "VISIBLE, NOT ONE.** 1297 concluded the owner's \"those stacks don't look too good yet\" is about "
           "sharpness, having ruled out exposure. It never ruled out the **occlusion halo**, which M87 subsequently "
           "measured at **three orders of magnitude above any single frame** (fact 1298) and which traces the entire "
           "subject silhouette. The orchestrator had *itself seen* a pronounced halo on `flower-bud-alone-cpl` in "
           "its own contact-sheet review, and still omitted it from the list.",
     "**The corrected attribution: the renders carry at least two independent, measured, visible defects** -- the "
     "**2.34x high-frequency deficit** (fact 1286, 64.2% coverage rescale) and the **occlusion halo** (fact 1298, "
     "the election at veiled boundaries). Exposure remains genuinely eliminated. The two have different fixes, "
     "different owners and different maturity: the rescale fix is cheap and predicted to land the deficit near "
     "+0.1301 dex, while **the halo has no working fix for real captures** (fact 1300). So the honest forecast is "
     "that the next render will be materially sharper and will still look stacked at the silhouettes. **This is the "
     "same error discipline 637 warns about, committed in the same commit that wrote it** -- naming a failure mode "
     "does not confer immunity to it, and the check that would have caught it is mechanical: write the list of "
     "candidate causes down before eliminating any of them, so the ones never considered are visible as blanks.",
     "ORCH (self-correction); amends fact 1297, on evidence from M87 fact 1298; `docs/research/M87-occlusion.md`"),
]

DISCIPLINES = [
    (641, "**Write the candidate list down before eliminating anything, because the causes you never considered are "
          "invisible to an argument from elimination.** Fact 1297 eliminated exposure and concluded \"therefore "
          "sharpness\", in the same commit as discipline 637, which warns that elimination is only as strong as the "
          "list's completeness. The omitted cause -- the occlusion halo -- had already been *seen by the same author* "
          "in their own review artefact. An enumerated list turns an omission into a visible blank; an unenumerated "
          "one turns it into a confident conclusion. Facts 1297, 1304."),
]


def main():
    with io.open(P, encoding="utf-8") as f:
        text = f.read()

    rows = [l for l in text.split("\n") if l.startswith("| 1297 |")]
    assert len(rows) == 1, f"expected exactly one 1297 row, got {len(rows)}"
    old = rows[0]
    assert MARK not in old, "1297 already amended"
    cells = old.split(" | ")
    assert len(cells) == 4, f"unexpected cell count {len(cells)}"
    cells[2] = MARK + " " + cells[2]
    new = " | ".join(cells)
    n = new.count("|") - new.count("\\|")
    assert n == 5, f"amended 1297: {n} unescaped pipes, need 5"
    text = text.replace(old, new, 1)

    lines = text.split("\n")
    fact_idx = max(i for i, l in enumerate(lines) if re.match(r"^\| 1303 \|", l))
    disc_idx = max(i for i, l in enumerate(lines) if re.match(r"^640\. ", l))
    assert disc_idx > fact_idx, f"fact {fact_idx}, disc {disc_idx}"

    frows = []
    for fid, claim, interp, src in sorted(FACTS):
        row = f"| {fid} | {claim} | {interp} | {src} |"
        k = row.count("|") - row.count("\\|")
        assert k == 5, f"fact {fid}: {k} unescaped pipes, need 5"
        frows.append(row)

    drows = [f"{did}. {body}" for did, body in DISCIPLINES]

    for fid, *_ in FACTS:
        assert not re.search(rf"^\| {fid} \|", text, re.M), f"fact {fid} already present"
    for did, _ in DISCIPLINES:
        assert not re.search(rf"^{did}\. ", text, re.M), f"discipline {did} already present"

    out = lines[:]
    out[disc_idx + 1:disc_idx + 1] = drows
    out[fact_idx + 1:fact_idx + 1] = frows

    with io.open(P, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out))
    print(f"amended 1297; folded fact 1304 after line {fact_idx}, discipline 641 after line {disc_idx}")


if __name__ == "__main__":
    main()

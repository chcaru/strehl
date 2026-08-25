"""Fold the patchwork measurement and the PIL 16-bit hazard.

Facts 1615-1620, disciplines 828-829.

This is the first time the project has a measured, instrument-commissioned
statement about its largest visible defect.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1614 |")
disc_line = full_line(raw, "827. ")

NEW_FACTS = [
    (
        1615,
        "MEASURED",
        "ORCH",
        "**`PIL.Image.open()` SILENTLY RETURNS `uint8` FOR A 16-BIT RGB TIFF -- NO "
        "WARNING, NO EXCEPTION, NO FLAG.** Confirmed on a controlled file whose contents "
        "ORCH chose, so it is not a property of one exporter "
        "(`experiments/ORCH-drift-check/pil16_probe.py`): a 16-bit RGB TIFF holding "
        "**4098 distinct levels** reads back through PIL as `uint8`, mode `RGB`, with "
        "**17 distinct levels** -- a **241x** loss. **16-bit GREYSCALE round-trips "
        "exactly** (mode `I;16`, 4096 levels preserved), which is almost certainly why "
        "this survived: anyone who sanity-checked the reader on a single-channel TIFF "
        "saw it work. **27 scripts across 8 milestones open a `.tif` through PIL** "
        "(M103, M114, M87, M95, M96, M97 and ORCH's own). ORCH hit it directly: a "
        "measurement reported `dtype=uint8, max=160` on a file holding `uint16, "
        "max=41188`, and a conclusion was nearly published from it.",
    ),
    (
        1616,
        "MEASURED",
        "ORCH",
        "**THE BACKGROUND PATCHWORK IS PRESENT IN 16-BIT DATA, SO 8-BIT QUANTISATION "
        "CONTOURING IS DEAD AS AN EXPLANATION.** Measured on `armM-gate0-binlin.tif` "
        "read with `tifffile` (`(2344, 3516, 3) uint16`, min 295, max 41188) over 12 "
        "interior background windows of 256 px: **Laplacian excess kurtosis median "
        "14.10, worst 31.24, and 12 of 12 windows above the plant-calibrated bar of "
        "10.** A piecewise-constant field is exactly what produces that signature -- "
        "near-zero Laplacian inside patches, spikes at the boundaries. Fact 1603's "
        "OBSERVED status is hereby upgraded to MEASURED.",
    ),
    (
        1617,
        "MEASURED",
        "ORCH",
        "**THE MERGE MANUFACTURES SPATIAL STRUCTURE THAT IS IN NO INPUT FRAME, IN 12 OF "
        "12 BACKGROUND WINDOWS.** The invariant: in a region where every input frame is "
        "smooth, a merge cannot legitimately create structure. Measured as Laplacian RMS "
        "over identical pixels in the merge and in five single input frames of the same "
        "geometry and dtype, the merge carries **2.134x the fine-scale structure of the "
        "NOISIEST single frame** (median; worst **3.402x**), and 2.268x/3.713x against "
        "the quietest. **Every window violates it.** This is a defect statement that "
        "needs no aesthetic judgement, and it is the first measured account of the "
        "project's largest visible artifact. **It should become a shipped acceptance "
        "invariant.**",
    ),
    (
        1618,
        "MEASURED",
        "ORCH",
        "**THE INSTRUMENT WAS COMMISSIONED IN THE SAME RUN THAT PRODUCED THE RESULT, "
        "AGAINST TWO NULLS AND A PLANT.** At the measured background sd of 1443.87 "
        "counts: **iid gaussian -0.00**, **smooth ramp +0.03**, **planted Voronoi mosaic "
        "+52.99**. The script refuses to print any result unless both nulls read below "
        "1.0 and the plant reads above 10.0, so a green cannot be produced by an "
        "instrument that has not just been shown to respond. **A null alone would only "
        "have shown the metric was quiet; only the plant shows it can move at all.**",
    ),
    (
        1619,
        "MEASURED",
        "ORCH",
        "**AND THE VISUAL COMPARISON IS BIASED AGAINST THE CONCLUSION, WHICH SURVIVES "
        "ANYWAY.** The side-by-side at "
        "`C:\\dev\\strehl-out\\ORCH-morning\\PATCHWORK-16bit-worst*.png` stretches each "
        "panel to its own range: the merge over **8356** counts, the single frame over "
        "**2905**, so **the single frame receives 2.88x MORE contrast amplification than "
        "the merge**. Under that handicap the single frame still shows a smooth, faintly "
        "noisy defocused background, and the merge over the same pixels shows a cellular "
        "mosaic of hundreds of flat blobs. **The panel that should most easily reveal "
        "structure is the one that has none.**",
    ),
    (
        1620,
        "MEASURED",
        "ORCH",
        "**ORCH'S FIRST VERSION OF THIS MEASUREMENT WAS BIASED TOWARD ITS OWN "
        "CONCLUSION, FOR THE FOURTH TIME TONIGHT, AND WAS CAUGHT BEFORE PUBLICATION "
        "RATHER THAN AFTER.** The comparison was originally against the **quietest** of "
        "five single frames -- the reference most likely to make the merge look bad. "
        "Re-run against the **noisiest**, the median ratio falls from **2.268 to "
        "2.134** and the verdict is unchanged. The lesson is not that the bias was "
        "small; it is that its size was unknown until it was measured, and the previous "
        "three instances (facts 1584, 1599) were only found by other agents.",
    ),
]

NEW_DISCS = [
    (
        828,
        "**Assert the dtype and range you expect on the line after you load, because a "
        "reader that silently narrows your data is worse than one that fails.** PIL "
        "returns `uint8` for a 16-bit RGB TIFF and says nothing (fact 1615); the failure "
        "arrives as a **plausible number**, not an error, and nothing downstream can "
        "recover it. The hazard generalises past this library: **any loader that has a "
        "lossy fallback will take it silently**, and the cost of the guard is one line "
        "while the cost of its absence is every measurement built on top. Prefer a "
        "loader that raises over one that copes.",
    ),
    (
        829,
        "**When your comparison has a set of possible references, use the one that "
        "argues against you.** ORCH measured the merge against the **quietest** of five "
        "input frames -- the choice that most flatters the finding -- and only after "
        "switching to the **noisiest** was the result worth reporting (fact 1620). This "
        "is the fourth instance tonight of the same error shape and it is worth naming "
        "precisely: **the bias is not in the metric, it is in the selection of the "
        "reference**, so no amount of validating the metric can catch it. The check is "
        "to ask, before running, which choice of reference would make the answer come "
        "out the way you expect -- and then not make that choice.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for block in (fact_block, disc_block):
    for line in block.split("\n"):
        stripped = _re.sub(r"`[^`]*`", "", line)
        assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

# Fact 1603 was OBSERVED; fact 1616 measures it. Mark the upgrade in place.
row = full_line(out, "| 1603 |")
assert "OBSERVED" in row, "fact 1603 is not OBSERVED any more: %s" % row[:120]
upgraded = row.replace(
    "| 1603 | OBSERVED | ORCH | **",
    "| 1603 | OBSERVED | ORCH | **[UPGRADED to MEASURED by facts 1616-1617.]** **",
    1,
)
assert upgraded != row, "1603 marker did not land"
prev = out
out = out.replace(row, upgraded, 1)
assert out != prev, "1603 replacement did not land"
n = len(full_line(out, "| 1603 |").replace("\\|", "").split("|")) - 1
assert n == 5, "fact 1603 row now has %d pipes" % n

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("marked fact 1603 UPGRADED; row pipes=%d" % n)

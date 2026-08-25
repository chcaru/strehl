"""Fold M111's PIL exposure audit: the bias is directional, toward the null.

Facts 1647-1649, discipline 840. Reuses fold140's section-aware helpers.
"""
import io
import re as _re

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    lines = fh.read().split("\n")


def section_bounds(pattern):
    hits = [i for i, l in enumerate(lines) if _re.match(pattern, l)]
    assert hits, "no section heading matching %r" % pattern
    start = hits[-1]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if _re.match(r"^#{1,3} ", lines[i]):
            end = i
            break
    return start, end


def insert_after_fact_row(number, block):
    hits = [i for i, l in enumerate(lines) if l.startswith("| %d |" % number)]
    assert len(hits) == 1, "fact row %d appears %d times" % (number, len(hits))
    for k, text in enumerate(block):
        lines.insert(hits[0] + 1 + k, text)
    return "fact table"


def insert_after_entry(number, section_pattern, block):
    start, end = section_bounds(section_pattern)
    hits = [i for i in range(start, end) if lines[i].startswith("%d. " % number)]
    assert len(hits) == 1, "entry %d appears %d times in %s" % (
        number, len(hits), lines[start].strip())
    j = hits[0] + 1
    while j < end and lines[j].strip() and not _re.match(r"^\d+\. ", lines[j]):
        j += 1
    for k, text in enumerate(block):
        lines.insert(j + k, text)
    return lines[start].strip()


NEW_FACTS = [
    (
        1647,
        "MEASURED",
        "M111",
        "**M111 IS NOT EXPOSED TO THE PIL HAZARD, AND IT RE-RAN RATHER THAN ARGUED.** "
        "Across all 33 files in the lane there are **zero `Image.open(` call sites**; "
        "every TIFF read is `tifffile.imread`, and the three scripts that import PIL use "
        "it only on the write path for PNG contact sheets. Rather than rest on that, M111 "
        "recomputed its headline `blobB` statistic through **both** readers with every "
        "other line identical. The reported values reproduce exactly through `tifffile` "
        "(interior ratio **0.094** merged / **0.761** control; boundary p90 **1384.04** / "
        "**226.69**), and the level loss on those very files is real -- **62152 -> 256** "
        "distinct levels on the merged render (**243x**), 49028 -> 245 on the control. "
        "Had PIL been used, `blobB` boundary hardness would have read **5.573x** instead "
        "of **6.105x** (**-8.7%**) and `blobA` **2.875x** instead of **3.111x** "
        "(-7.6%): **the defect would still have been detected, but understated**.",
    ),
    (
        1648,
        "MEASURED",
        "M111",
        "**AND THE PIL DISTORTION IS DIRECTIONAL -- IT BIASES TOWARD THE NULL.** Within "
        "the same statistic the *small* term moves about **13x more** than the large one: "
        "the control's soft boundary p90 shifts **+10.5%** where the merged render's hard "
        "boundary shifts **+0.8%**. The mechanism is that quantisation error is an "
        "**absolute** floor, so it is a large fraction of a small quantity and a "
        "negligible fraction of a large one. **Consequence: every large-over-small ratio "
        "compresses toward 1.** That is precisely the direction that manufactures a "
        "**false clean null**, which is the hardest error in this project to catch, "
        "because nobody re-examines an arm that came back showing no effect. The "
        "broadcast hazard's 'most suspect of all' category now has a measured sign and "
        "magnitude.",
    ),
    (
        1649,
        "MEASURED",
        "M111",
        "**EXPOSURE DEPENDS ON THE SHAPE OF THE STATISTIC, NOT ONLY ON THE DTYPE OF THE "
        "FILE.** In one script, on the **same pixels of the same file**, M111's "
        "interior-flatness ratio was nearly immune (**-0.0%**, **+3.0%**) while its "
        "boundary-hardness contrast lost **8.7%**. A ratio of two comparably-sized "
        "quantities largely survives; a contrast between a strong and a weak signal does "
        "not. This splits the hazard's 'suspect' bucket along a line that is not visible "
        "from the input file at all -- `gradient/high-frequency energy` and `retention "
        "ratios` land on **opposite sides** of it depending only on how they are formed.",
    ),
]

NEW_DISCS = [
    (
        840,
        "**Triage a silently-narrowing reader by the shape of the statistic, not only by "
        "the dtype of the input.** The question `was my input 16-bit RGB?` is necessary "
        "and not sufficient: two statistics computed from the same pixels in the same "
        "script diverged by 8.7% against 0.0% (fact 1649). The sharper question is "
        "**`does my statistic divide a small quantity by a large one?`** -- if so it "
        "compresses toward 1 under quantisation and fails toward a clean null (fact "
        "1648). Two practical riders from the same audit: **grep for `Image.open(` call "
        "sites, not for `PIL`**, because a case-insensitive search false-positives on "
        "`compiling`; and when asked whether you are exposed, **re-run both readers "
        "rather than reasoning from having avoided the API** -- `I did not use PIL` is "
        "exactly the class of argument the hazard notice warns against.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = [fact_row(*f) for f in NEW_FACTS]
disc_block = ["%d. %s" % d for d in NEW_DISCS]

for line in fact_block:
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])
for line in fact_block + disc_block:
    stripped = _re.sub(r"`[^`]*`", "", line)
    assert stripped.count("**") % 2 == 0, "odd ** in: %s" % line[:90]
    for ch in line:
        o = ord(ch)
        assert not (o < 0x20 or o == 0x7F), "control char 0x%02X in %s" % (o, line[:60])

s1 = insert_after_fact_row(1646, fact_block)
s2 = insert_after_entry(839, r"^## 5\. ", disc_block)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write("\n".join(lines))

print("facts %s -> %s" % (", ".join(str(f[0]) for f in NEW_FACTS), s1))
print("disciplines %s -> %s" % (", ".join(str(d[0]) for d in NEW_DISCS), s2))

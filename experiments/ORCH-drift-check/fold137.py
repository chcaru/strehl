"""Retract ORCH's kurtosis-based patchwork claims; keep the matched-pixel core.

Facts 1627-1632, disciplines 831-832.
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


fact_line = full_line(raw, "| 1626 |")
disc_line = full_line(raw, "830. ")

NEW_FACTS = [
    (
        1627,
        "MEASURED",
        "ORCH",
        "**THE LAPLACIAN-KURTOSIS PATCHWORK DETECTOR IS NOT SPECIFIC, AND EVERY "
        "'N OF 12 ABOVE THE BAR' COUNT ORCH REPORTED IS WITHDRAWN.** Re-run with "
        "window selection that does **not** consult the arm under test, a **single "
        "unmerged input frame** -- which has no merge anywhere in its history and "
        "therefore cannot contain the defect -- scores **3 of 12 windows above the bar, "
        "worst 103.31**. That is a higher worst-case than the shipped render's 65.35. "
        "**A detector that fires three times on the photograph cannot be used to count "
        "how often it fires on the merge.** Only the **median** separates the two "
        "populations, and it separates them by a factor of about 390: **0.06 for the "
        "single frame against 23.50 for the shipped render.**",
    ),
    (
        1628,
        "MEASURED",
        "ORCH",
        "**AND THE DETECTOR WAS MEASURING THE HALO, NOT THE PATCHWORK.** Laid out as "
        "twelve labelled windows (`experiments/ORCH-drift-check/background_windows.py`, "
        "`BACKGROUND-12-WINDOWS.png`), the shipped render's **high**-kurtosis windows "
        "are precisely the ones containing **haloed hairs** (25.8, 65.4, 29.5, 36.2, "
        "32.4, 23.2), and the windows showing the **mottled curdled background** score "
        "**low** (1.0, 1.1, 1.8, 2.1, 3.9). Kurtosis responds to **sparse hard edges**, "
        "which is what a halo is and what soft mottling is not. This also explains the "
        "otherwise inexplicable ordering in fact 1623's table, where the gate-0 "
        "**negative control** scored *below* the shipped gate: gate 0's mosaic is dense "
        "and broad, gate 4's residual is sparse and hard.",
    ),
    (
        1629,
        "MEASURED",
        "ORCH",
        "**FACT 1622'S HEADLINE COMPARISON WAS BETWEEN TWO DIFFERENT SCENES.** The "
        "'single input frame reads 0.05, the merge reads 34' comparison put "
        "`bee-3-strehl.tif` (7032x4688) against `armF-f173.tif`, which is a frame of a "
        "**different stack of a different subject**. Two images of different scenes may "
        "differ for any reason at all. **The only patchwork evidence in this corpus that "
        "survives is the matched-pixel comparison inside M93**, where the merged arms "
        "and the single frames are the same scene at the same geometry: facts "
        "1624-1625. Everything ORCH inferred about the full-resolution render's "
        "background is unsupported, because no single frame at that geometry exists to "
        "compare it against, and out-of-focus foliage genuinely does look mottled.",
    ),
    (
        1630,
        "MEASURED",
        "ORCH",
        "**THE 'RECTANGULAR TILE SEAM' ORCH THOUGHT IT SAW IN THE SHIPPED RENDER DOES "
        "NOT EXIST.** A seam scan looking for a step that is consistent down a whole "
        "column (`experiments/ORCH-drift-check/seam_scan.py`) reports the shipped "
        "render's strongest column at **z = 18.4** and a **single unmerged photograph's** "
        "at **z = 43.8** -- the photograph has 2.4x the straight-column structure of the "
        "merge. The positive control landed exactly: a seam planted at x=256 with "
        "amplitude 0.25 sd was recovered at **x=256, off by 0 px, z = 33.5** against a "
        "median column z of 5.1, so the scan was demonstrably able to see one. "
        "**Hypothesis killed in one run, by an instrument that had just been shown to "
        "work.**",
    ),
    (
        1631,
        "DERIVED",
        "ORCH",
        "**WHAT SURVIVES THE NIGHT'S RETRACTIONS, STATED ONCE.** (a) Within M93 at "
        "**matched pixels**, the shipped gate manufactures **1.114x** the fine structure "
        "of the noisiest input frame in **7 of 12** background windows, and the gate-0 "
        "negative control manufactures **2.134x** in **12 of 12** (fact 1624). (b) On "
        "one shared stretch the gate visually **removes the mosaic** and leaves the halo "
        "**untouched** (fact 1625). (c) The **halo is the lead defect**, present on every "
        "silhouette in every arm, with no working fix (fact 1626). (d) `PIL` silently "
        "downconverts 16-bit RGB TIFFs (fact 1615). **Everything else ORCH produced "
        "tonight about the patchwork is withdrawn or unsupported.**",
    ),
    (
        1632,
        "ARGUED",
        "ORCH",
        "**THE PATTERN IN ORCH'S SIX ERRORS TONIGHT IS THAT EVERY ONE OF THEM WAS IN THE "
        "SETUP, NOT THE MEASUREMENT.** A tangential placebo that did not perturb what it "
        "claimed to (fact 1584); a bar that printed the same string on success and "
        "failure (fact 1571); a blur confound measured in the wrong direction (facts "
        "1595-1602); a reference chosen from the flattering end of a set (fact 1620); an "
        "arm mistaken for the shipped path (fact 1621); and a comparison between two "
        "different scenes (fact 1629). **In every case the metric was sound, the "
        "instrument was commissioned, and the arithmetic was right.** The corpus already "
        "has strong discipline on validating metrics and almost none on validating "
        "**what is being compared to what** -- and on tonight's evidence that is where "
        "the errors actually live.",
    ),
]

NEW_DISCS = [
    (
        831,
        "**A detector must be run on an instance that CANNOT contain the defect, and if "
        "it fires there the counting statistic is dead.** ORCH's patchwork detector fired "
        "on 3 of 12 windows of an unmerged photograph with a worst case *higher* than the "
        "merge's (fact 1627). The nulls it had passed were synthetic -- iid noise and a "
        "smooth ramp -- and synthetic nulls only prove the metric is quiet on things "
        "nobody was going to measure. **The null that matters is a real instance of the "
        "population you are scoring, minus the mechanism under test**: here, a real "
        "photograph of a real defocused background, with real noise, that simply never "
        "went through a merge.",
    ),
    (
        832,
        "**Before comparing two images, state what is held constant between them; if the "
        "answer is 'nothing', it is not a comparison.** ORCH put a render of one subject "
        "against a frame of a different subject and read a 390x ratio off it (fact "
        "1629). Two images of different scenes differ for any reason at all, and no "
        "amount of rigour in the metric recovers that. This is the same failure shape as "
        "discipline 830 -- **six of ORCH's errors tonight were in what was being "
        "compared, none in how it was measured** (fact 1632) -- so make identifying the "
        "controlled variable a written step, not an assumption.",
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

MARKS = {
    1622: "[WITHDRAWN by fact 1629: the two images compared are different scenes.]",
    1623: "[WITHDRAWN by facts 1627-1628: the counting statistic fires on an unmerged "
          "photograph, and the metric responds to the halo, not the patchwork.]",
}
for fid, mark in MARKS.items():
    row = full_line(out, "| %d |" % fid)
    assert "ORCH | **" in row, "unexpected shape for fact %d" % fid
    marked = row.replace("ORCH | **", "ORCH | **%s** **" % mark, 1)
    assert marked != row, "marker did not land on fact %d" % fid
    prev = out
    out = out.replace(row, marked, 1)
    assert out != prev, "replacement did not land on fact %d" % fid
    n = len(full_line(out, "| %d |" % fid).replace("\\|", "").split("|")) - 1
    assert n == 5, "fact %d row now has %d pipes" % (fid, n)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("withdrew facts %s" % ", ".join(str(k) for k in MARKS))

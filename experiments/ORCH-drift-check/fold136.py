"""Correct the arm-scoping error in facts 1616-1617 and fold the shipped-path numbers.

Facts 1621-1626, discipline 830.
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


fact_line = full_line(raw, "| 1620 |")
disc_line = full_line(raw, "829. ")

NEW_FACTS = [
    (
        1621,
        "MEASURED",
        "ORCH",
        "**FACTS 1616-1617 MEASURED A NEGATIVE CONTROL AND DESCRIBED IT AS THE MERGE.** "
        "`armM-gate0-binlin.tif` is the **gate-0 arm**, and `merge.rs:3027` labels it in "
        "so many words: `gate 0 selector : {r0:.4}x at mean n_eff {n0:.3}  (negative "
        "control)`. The shipped default is `DEFAULT_GATE: f32 = 4.0` (`merge.rs:298`), "
        "which is the `armM4-gate4-binlin.tif` arm. **So the 2.134x invariant violation "
        "is the pure selector's, and the project already knew by construction that the "
        "pure selector is bad.** Facts 1616-1617 stand as written about the arm they "
        "name and must not be quoted as statements about the shipped path. This is "
        "ORCH's fifth error in one night and the second of the same shape.",
    ),
    (
        1622,
        "MEASURED",
        "ORCH",
        "**THE PATCHWORK DETECTOR IS SILENT ON A REAL PHOTOGRAPH AND FIRES ON EVERY "
        "MERGED ARM.** The strongest available negative control is a single unmerged "
        "input frame, which is a real defocused background with real noise and no merge "
        "anywhere in its history. Over its 12 most background-like windows it reads "
        "**median excess kurtosis 0.05, worst 0.08, 0 of 12 above the bar of 10** "
        "(`experiments/ORCH-drift-check/shipped_patchwork.py`). Every merged arm reads "
        "**two to three orders of magnitude higher**. **A detector that reads 0.05 on "
        "the photograph and 34 on the merge of those photographs is not measuring the "
        "scene.**",
    ),
    (
        1623,
        "MEASURED",
        "ORCH",
        "**ON THE SHIPPED FULL-RESOLUTION RENDER THE PATCHWORK IS REAL BUT LOCALISED: "
        "MEDIAN 2.48, WORST 89.94, 3 OF 12 WINDOWS ABOVE THE BAR.** Measured on "
        "`ORCH-morning\\bee-3-strehl.tif` (7032x4688 uint16, the shipped path, 240 "
        "windows scanned), instrument commissioned in-run at that image's own sd "
        "(nulls -0.03 / +0.01, plant +41.81). **The correct headline is therefore not "
        "'the background is a mosaic' but 'a quarter of the background is a mosaic, and "
        "where it is, it is severe'** -- 89.94 against a plant of 41.81 means the worst "
        "window is more patchwork-like than the synthetic Voronoi field built to define "
        "the defect. This supersedes the stronger phrasing in fact 1603 and in "
        "`captures-needed.md`.",
    ),
    (
        1624,
        "MEASURED",
        "ORCH",
        "**THE SHIPPED GATE ROUGHLY HALVES THE MANUFACTURED STRUCTURE BUT DOES NOT "
        "ELIMINATE IT: 7 OF 12 WINDOWS STILL VIOLATE THE INVARIANT.** A/B on **identical "
        "pixels** (both arms scored on window coordinates fixed to one reference arm, "
        "which the tool now takes as an argument precisely so an A/B cannot silently "
        "become a comparison of two different window sets): merged fine-structure "
        "against the **noisiest** single input frame falls from **2.134x to 1.114x** "
        "median (worst 3.402x to 2.864x) and violations from **12/12 to 7/12** going "
        "from gate 0 to the shipped gate 4. **The shipped path is much better than the "
        "selector and still measurably manufacturing structure.**",
    ),
    (
        1625,
        "MEASURED",
        "ORCH",
        "**RENDERED ON ONE SHARED STRETCH, THE GATE REMOVES THE MOSAIC AND LEAVES THE "
        "HALO COMPLETELY UNTOUCHED.** Same 256 px window, one lo/hi applied to all three "
        "panels so a flatter arm looks flatter "
        "(`experiments/ORCH-drift-check/ab_shared_stretch.py`; independent per-panel "
        "stretching would amplify the winner's residual noise until it looked as bad as "
        "the loser). Window sd: **gate0 1455.7 -> gate4 934.4 -> single frame 285.4 "
        "counts**, means agreeing to 8 counts in 18730 so the arms are photometrically "
        "comparable. The mosaic is visually **gone** at gate 4; the bright outlines "
        "around every hair are **identical** in both. **This also explains the kurtosis "
        "rising while the RMS falls (fact 1624): with the mosaic removed, the halo edges "
        "are what is left in the Laplacian, and they are sparse and hard.**",
    ),
    (
        1626,
        "DERIVED",
        "ORCH",
        "**THE HALO IS NOW THE LEAD DEFECT OF THE SHIPPED PATH, ON THE SHIPPED PATH'S "
        "OWN NUMBERS.** Facts 1623-1625 together: the mosaic is localised (3 of 12 "
        "windows) and already largely handled by the gate, while the halo is visible on "
        "**every** silhouette in **both** gate arms, survives the one mechanism that "
        "fixed the mosaic, and has **no working fix** -- F1 is withdrawn as looking "
        "worse (facts 1595-1602, 1606) and F2 is a visual no-op (fact 1607). **The "
        "defect ranking in `captures-needed.md` should be reordered accordingly**, and "
        "the reorder is itself a consequence of the two things nobody had done: looking "
        "at the output (discipline 824), and checking what an arm name means before "
        "building on it (discipline 830).",
    ),
]

NEW_DISCS = [
    (
        830,
        "**An arm's name is not its semantics: look up what a harness arm IS before you "
        "build a conclusion on it.** ORCH measured `armM-gate0-binlin` for an entire "
        "session believing it was the shipped merge; `merge.rs:3027` calls gate 0 a "
        "**negative control** and `merge.rs:298` sets the shipped default to 4.0 (fact "
        "1621). The measurement was correct, the instrument was commissioned, the "
        "conservative reference was chosen -- and the conclusion was still about the "
        "wrong thing, because **no amount of rigour downstream of a mis-identified "
        "input can recover it**. One grep for the arm name would have cost thirty "
        "seconds. Make identifying the arm part of loading it, not part of writing it "
        "up.",
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

# Scope facts 1616 and 1617 in place: both name the gate-0 arm.
for fid in (1616, 1617):
    row = full_line(out, "| %d |" % fid)
    assert "ORCH | **" in row, "unexpected shape for fact %d: %s" % (fid, row[:120])
    marked = row.replace(
        "ORCH | **",
        "ORCH | **[SCOPE CORRECTED by fact 1621: the arm measured here is the gate-0 "
        "NEGATIVE CONTROL, not the shipped path. For the shipped path see facts "
        "1623-1624.]** **",
        1,
    )
    assert marked != row, "scope marker did not land on fact %d" % fid
    prev = out
    out = out.replace(row, marked, 1)
    assert out != prev, "replacement did not land on fact %d" % fid
    n = len(full_line(out, "| %d |" % fid).replace("\\|", "").split("|")) - 1
    assert n == 5, "fact %d row now has %d pipes" % (fid, n)

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded discipline %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("scope-corrected facts 1616, 1617")

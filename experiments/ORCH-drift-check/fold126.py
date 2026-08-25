"""Fold the function-level reachability audit (reachability2.py).

Facts 1576-1578, discipline 813.
Extends the module-level audit of facts 1553-1555 down to `pub fn`.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1575 |")
disc_line = full_line(raw, "812. ")

NEW_FACTS = [
    (
        1576,
        "MEASURED",
        "ORCH",
        "**The reachability audit of facts 1553-1555 extended from modules down to "
        "functions.** Of every `pub fn` in the 107 production `.rs` files at HEAD, exactly "
        "**5** have zero references anywhere in the repository including their own file, "
        "and **3** more are reached only from tests. The dead five are "
        "`align::from_stage`, `merge::tracks_disagreement`, `photometric::fold_u16`, "
        "`through_focus::subframe_peak` and `warpmap::set_resampler`. **Three of the five "
        "are benign wrappers.** The module-level picture -- two dead modules out of "
        "twenty-five -- is therefore not hiding a large population of dead functions "
        "inside live modules.",
    ),
    (
        1577,
        "MEASURED",
        "ORCH",
        "**THE LOAD-BEARING ONE IS `warpmap::set_resampler`, AND IT GUARDS AN UNMEASURED "
        "COST PAID ON EVERY GATHERED PIXEL.** Its own doc comment states that Catmull-Rom "
        "versus bilinear **has never been compared on real frames at merge time**, while "
        "M86 measured an estimator's gain falling **0.98 -> 0.29** through Catmull-Rom. "
        "The default is therefore a choice nobody has priced. **The A/B needs zero code "
        "changes:** the resampler round-trips as text through the warp sidecar "
        "(`warpmap.rs:601` writes `resampler <name>`, `:810` parses it), so an arm is a "
        "text edit to a sidecar file. Dispatched as M118.",
    ),
    (
        1578,
        "MEASURED",
        "ORCH",
        "**A DEFECT IN THIS AUDIT'S OWN FIRST DRAFT, CAUGHT BEFORE IT WAS REPORTED.** "
        "Version 1 excluded each function's **own file** when counting references, on the "
        "theory that a definition should not count as a use. It also excluded every "
        "**call** from a sibling function in the same file, so any helper used only "
        "locally scored zero. It reported **76** dead functions. Counting same-file "
        "references, minus the declaration itself, gives **5**. **The first version was "
        "measuring `pub` that should have been private -- a visibility smell -- and "
        "reporting it as dead code.** The two are different findings with different "
        "remedies and a 15x difference in headline number.",
    ),
]

NEW_DISCS = [
    (
        813,
        "**A dead-code audit that excludes a symbol's own file measures a visibility "
        "smell, not reachability -- and the two differ by 15x here.** Local helpers are "
        "called by their siblings; excluding the file hides exactly those calls, so every "
        "locally-used helper reports as dead (fact 1578). Both quantities are worth "
        "knowing, but they are different questions with different remedies: unreachable "
        "code should be **wired or deleted**, over-`pub` code should be **narrowed**. "
        "State which one the instrument computes, and check a handful of its hits by hand "
        "before believing the total.",
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
    for ch in block:
        o = ord(ch)
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "text contains 0x%02X" % o

out = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert out != raw, "fact insertion did not land"
prev = out
out = out.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert out != prev, "discipline insertion did not land"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))

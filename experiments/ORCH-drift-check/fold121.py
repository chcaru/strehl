"""Fold M97q's photometric-wiring report (0 citations in SYNTHESIS).

Facts 1547-1552, disciplines 800-802.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1546 |")
disc_line = full_line(raw, "799. ")

NEW_FACTS = [
    (
        1547,
        "MEASURED",
        "M97q",
        "**THE MECHANISM BEHIND EVERY UNWIRED INSTRUMENT: `pub` suppresses `dead_code` in "
        "a library crate.** `photometric.rs` carried **1365 lines and 24 passing tests** "
        "with **no caller outside `lib.rs` and `examples/`**. It compiled without warning, "
        "its tests were green, and its results had already been folded into this corpus as "
        "MEASURED -- while **the render never called it**. Every green signal was telling "
        "the truth about code that did nothing. **A green test suite is evidence about a "
        "function, never evidence that the function is reachable from the product.**",
    ),
    (
        1548,
        "MEASURED",
        "M97q",
        "**A pre-registered bar can be VACUOUS in a way only its plant reveals.** Bar F2 "
        "read `0 px re-elected out of 8 250 880` -- and **so did its deliberately broken "
        "plant**. That is not a null, it is a disconnected probe, and it would have shipped "
        "as the headline 'election neutrality confirmed, 0 px' had the plant not been "
        "mandatory. Diagnosis: `merge_cmd.rs:1788` writes the election map from pass one's "
        "`best_index()`, and the photometric fit is built at `:1837`, **after it**. The "
        "instrument was structurally incapable of expressing the quantity being tested.",
    ),
    (
        1549,
        "DERIVED",
        "M97q",
        "**Election neutrality under photometric correction is true BY CONSTRUCTION, not "
        "by the invariance argument the design document gave -- and only the line numbers "
        "distinguish the two explanations.** The election is decided **entirely in pass "
        "one**, which runs with `photometric: None` because per-frame gains cannot exist "
        "until every frame has been read. This is a **stronger and simpler guarantee** "
        "than M99's `contrast/sigma` invariance reasoning, which nothing here tests. "
        "Consequence: **no election-based measurement in the corpus is invalidated by this "
        "wiring.**",
    ),
    (
        1550,
        "MEASURED",
        "M97q",
        "**Noise propagation is connected and load-bearing, proven by a plant that "
        "separates from the signal by 2.6x in the same instrument.** Re-aimed onto "
        "`n_eff` -- a pass-**two** quantity -- the gain moves 289 835 px (**3.51 %**), "
        "while a deliberately mis-propagated build (gain applied, noise model held) moves "
        "**763 987 px (9.26 %)** and drops mean `n_eff` 4.5638 -> 4.5256. Scaling data by "
        "`c` without scaling `sigma^2(S) = g*S + (RN*g)^2` under-estimates sigma by "
        "between `sqrt(c)` and `c`, so the gate misfires on **exactly the frames that were "
        "brightened** -- silently.",
    ),
    (
        1551,
        "MEASURED",
        "M97q",
        "**M99's headline +6.88 % photometric quality figure IS NOT REPRODUCED and is "
        "retracted as an inflated upper bound of unmeasured size.** It was fitted over an "
        "**un-eroded** region which, on a flux-conserving blur sweep whose true answer is "
        "exactly zero, reports **3.63 % spurious gain against a registered 2x bar -- 168x "
        "over** -- because defocus spills light across the mask's long perimeter. With "
        "16 px erosion the same sweep reports **0.0000 %**. Erosion is not a refinement; "
        "without it the estimator measures its own boundary.",
    ),
    (
        1552,
        "MEASURED",
        "M97q",
        "**Auto-exposure defeats whole-frame photometric normalisation, for a measured "
        "physical reason.** The AE meter holds **total** flux roughly constant while "
        "defocus moves light between the sharp core and the smooth surround, so on the two "
        "auto-exposure decks the whole-frame and background flux ladders sit **7.1 % "
        "(`bee-3-cpl`) and 5.5 % (`bee-2-cpl`)** apart. Correcting with the whole-frame "
        "ladder left **44 % and 42 % of the defect standing**. The region must be "
        "subject-**avoiding** and eroded. Separately, the statistic must be the **mean, "
        "never a median**: mean 0.0216 % against median 7.9376 % spurious gain, a factor "
        "of **368.1**, the fourth independent confirmation in this corpus.",
    ),
]

NEW_DISCS = [
    (
        800,
        "**Verify the CALL SITE, never the test suite, when asking whether a capability is "
        "live.** `pub` suppresses `dead_code` in a lib crate, so 1365 lines and 24 green "
        "tests coexisted with zero callers (fact 1547) -- and this corpus folded its "
        "results as MEASURED while the render never ran it. The check is one command: "
        "`git grep <symbol> HEAD -- crates/` and read the hits that are **not** the module "
        "or its own harness. Do this before folding any milestone that claims a product "
        "effect.",
    ),
    (
        801,
        "**Before believing a multi-pass pipeline is invariant under a change, establish "
        "WHICH PASS computes the quantity you are measuring.** M97q's election map was "
        "immune to photometric gain for a **structural** reason (pass one runs before the "
        "gains exist) and not for the physical reason the design document asserted (fact "
        "1549). Both explanations predict the same null. Only the line numbers "
        "distinguish them -- and the structural one is the stronger guarantee, so the "
        "distinction is worth the five minutes.",
    ),
    (
        802,
        "**A region-based estimator must be eroded, and the proof is a flux-conserving "
        "sweep whose true answer is exactly zero.** An un-eroded mask read **3.63 % where "
        "the truth was 0.0000 %**, 168x over its own bar, because blur transports light "
        "across the mask perimeter (fact 1551). Any statistic accumulated inside a "
        "boundary that the physics can cross is measuring the boundary. Erosion is the "
        "cheapest available control and its absence inflated a shipped headline number.",
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

for fid, _, _, _ in NEW_FACTS:
    assert out.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert out.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))

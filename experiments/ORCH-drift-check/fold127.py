"""Fold the DEFAULTS audit -- the static complement to the reachability audit.

Facts 1579-1581, discipline 814.

Reachability (facts 1553-1555, 1576-1578) asks "is this code called?".
This asks the next question: "when it IS called, is it turned on?".
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1578 |")
disc_line = full_line(raw, "813. ")

NEW_FACTS = [
    (
        1579,
        "MEASURED",
        "ORCH",
        "**THE DEFAULTS AUDIT: of the seven environment gates gating quality machinery on "
        "the render path, exactly ONE is on by default.** `STREHL_ALIGN` defaults ON "
        "(`align_cmd.rs:845`, `Err(_) => true`). Every other one defaults OFF: "
        "`STREHL_FIX_HALO` (`halo.rs:99`, `Err(_) => false`), `STREHL_PHOTOMETRIC` "
        "(`main.rs:284`, a bare clap `bool`, plus an env alias), `STREHL_FIX_CA` "
        "(`optics.rs:476`, `None` unless a profile is named), `STREHL_SOFT_GATE` "
        "(`merge.rs:483`), `STREHL_SMOOTH` and `STREHL_SMOOTH_HUBER` "
        "(`align_cmd.rs:504`). **The render the owner is looking at is therefore "
        "registration plus a bare gated average, with essentially every measured quality "
        "instrument switched off.**",
    ),
    (
        1580,
        "MEASURED",
        "ORCH",
        "**THE STANDOUT IS THE HALO CORRECTION, AND IT IS NOT EVEN REACHABLE FROM THE "
        "COMMAND LINE.** `halo.rs:58-77` records that M87 section 6.1 ran the ladder on "
        "**two real stacks with one parameter set and no refitting**, removing **87.9 % "
        "of the halo on `bee-3-cpl`** and **84.6 % on "
        "`flower-bud-with-background-fern-cpl`**; `DELTA = 40` is documented as the "
        "largest value that did not soften hairs and claws. That is a large, "
        "twice-replicated, un-refitted quality win on the exact artifact that makes a "
        "macro stack look wrong -- and `git grep -i halo` over `main.rs` returns "
        "**nothing**, so there is no `--fix-halo` flag. The only switch is an "
        "environment variable that defaults to `false`.",
    ),
    (
        1581,
        "ARGUED",
        "ORCH",
        "**THE PROJECT'S CHARACTERISTIC FAILURE MODE IS NOW MEASURED THREE TIMES OVER, AND "
        "IT IS NOT A RESEARCH FAILURE -- IT IS A CONNECTION FAILURE.** (a) Two modules "
        "totalling 1638 lines with passing tests are **unreachable** (facts 1553-1555). "
        "(b) A `pub fn` guarding an unpriced per-pixel cost has **no caller** (fact 1577). "
        "(c) Six of seven quality gates are **reachable but off** (fact 1579). In all "
        "three the work was done, measured, tested and committed; only the last step -- "
        "making the product actually use it -- was skipped. **This is the most likely "
        "single explanation for the owner's report that the renders 'don't look too good "
        "yet' while the corpus reports large measured wins**, and it predicts that "
        "turning existing machinery on will move the image more than any new research "
        "will. ARGUED, and M116 is measuring it.",
    ),
]

NEW_DISCS = [
    (
        814,
        "**Audit DEFAULTS, not just reachability -- reachable-but-off is the same defect "
        "as unreachable, and a dead-code audit cannot see it.** `halo.rs` is called, "
        "compiles, is tested, and returns immediately because its gate reads `Err(_) => "
        "false` (facts 1579-1580). Every static tool the language provides was satisfied. "
        "The audit that finds this is a different one: enumerate every gate on the "
        "product path and print its **default**, then diff that list against the wins the "
        "corpus claims. **A measured win behind a default-off flag has not shipped**, and "
        "the corpus should not describe it as though it has.",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

# S5: bold spans must balance once code spans are stripped.
import re as _re

for block in (fact_block, disc_block):
    for line in block.split("\n"):
        stripped = _re.sub(r"`[^`]*`", "", line)
        assert stripped.count("**") % 2 == 0, (
            "odd ** count (%d) in: %s" % (stripped.count("**"), line[:90])
        )
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

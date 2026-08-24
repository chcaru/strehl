"""Fold the magenta path-mismatch finding and the ported-fix discipline."""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1482 |")
disc_line = full_line(raw, "758. ")

NEW_FACTS = [
    (
        1483,
        "MEASURED",
        "ORCH",
        "The blown-highlight clip was **measured and fixed on one render path, then ported "
        "to a second where the defect was never demonstrated**. `3e58676` "
        "(*\"clip blown highlights together so neutral white stops rendering magenta\"*) "
        "touches `crates/strehl-cli/src/stack.rs`, which is `Command::ArgmaxBaseline` "
        "(`main.rs:455` -> `stack::run` at `:467`) — the naive per-pixel selector whose own "
        "CLI help reads *\"A REFERENCE ARTIFACT, ON PURPOSE, AND YOU SHOULD NOT SHIP ITS "
        "OUTPUT.\"* `e9ad010` ports the same clip to `crates/strehl-cli/src/merge_cmd.rs`, "
        "which is `Command::Stack` (`main.rs:484` -> `merge_cmd::run` at `:503`), the "
        "default path. The quoted diagnosis (2.002 % of frame, green pinned ~0.10 below red "
        "and blue, argmax-baseline 0.3378 % -> 0.0944 %) belongs to the first path only.",
    ),
    (
        1484,
        "MEASURED",
        "M110",
        "On the **default `strehl stack` path**, four subjects show no magenta defect at a "
        "`clipped` tile selected on the physical condition (R and B >= 99 % full scale, "
        "never on appearance): green offsets bee **+0.0004**, text **+0.0004**, tweezers "
        "**-0.0034**, ruler **-0.0004** — neutral within **0.0034**, about **29x smaller** "
        "than the -0.10 attributed to this path. A whole-frame profile against highlight "
        "brightness found no bin from 0.60 to clipping worse than **+0.0226**. Measured on a "
        "binary predating `e9ad010`, so the defect had every opportunity to appear.",
    ),
    (
        1485,
        "MEASURED",
        "ORCH",
        "M97's report of **byte-freeze 5/5 HOLD** after applying `e9ad010` is an independent "
        "corroboration of fact 1484 by a route sharing nothing with M110's: unchanged output "
        "bytes mean the conditional **never fired** on the frozen stacks. Two instruments, "
        "no common component, same conclusion — the ported clip is inert on the default path "
        "for every stack so far tested.",
    ),
    (
        1486,
        "MEASURED",
        "M110",
        "The magenta readout is **one-sided by construction** and therefore cannot audit the "
        "ported fix for overshoot: green retains only **0.00034** headroom on blown pixels, "
        "with **96.7 %** already at full scale. It recovers a planted **-0.10** as "
        "**-0.100008** but is **blind to green excess**. Found because a sign control "
        "*failed* and the author measured the ceiling rather than loosening the bar; "
        "`neutrality_control.py` 7/7.",
    ),
    (
        1487,
        "ARGUED",
        "ORCH",
        "A hard per-frame clipping artefact should be **diluted by the merge and loud in "
        "argmax**: the default path averages ~55 frames per output pixel (mean `n_eff` "
        "55.3) while `argmax-baseline` selects exactly one. This predicts facts 1484 and "
        "1485 from mechanism rather than coincidence, and predicts that the magenta defect "
        "is real, is an argmax phenomenon, and was never a property of the shipped render.",
    ),
]

NEW_DISCS = [
    (
        759,
        "**A fix ported to a second code path inherits none of the first path's evidence.** "
        "Porting is cheap and usually harmless; the claim that travels with it is neither. "
        "Re-measure the defect on the destination path before asserting the port fixes "
        "anything there, and state which path each number came from every time it is "
        "quoted. ORCH took an `argmax-baseline` measurement and broadcast it to three "
        "agents as a property of `strehl stack` — the fourth instance of this error class in "
        "one night, and roughly an hour after folding discipline 758 against it (facts 1483, "
        "1484).",
    ),
    (
        760,
        "**An instrument that can only fail in one direction cannot audit a fix for "
        "overshoot.** Before a readout is used as the acceptance gate for a change, plant "
        "the defect in **both** signs and report the recovered magnitude for each, not a "
        "pass/fail; and report the statistic's headroom in each direction as a number. A "
        "quantity measured after its value has been pinned at full scale has no room left "
        "to express an excess (fact 1486).",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

raw2 = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert raw2 != raw, "fact insertion did not land"
raw3 = raw2.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert raw3 != raw2, "discipline insertion did not land"

for fid, _, _, _ in NEW_FACTS:
    assert raw3.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw3.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw3)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))

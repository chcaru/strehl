"""Fold the reachability chain for the magenta fix, and the reachability discipline."""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1480 |")
disc_line = full_line(raw, "757. ")

NEW_FACTS = [
    (
        1481,
        "MEASURED",
        "ORCH",
        "The blown-highlight (magenta) clip is **reachable from the default render path**, "
        "verified as a complete call chain against `HEAD` rather than by symbol grep: "
        "`strehl stack` -> `Command::Stack` (`main.rs:484`, alias `merge`) -> "
        "`merge_cmd::run` (`main.rs:503`, defined `merge_cmd.rs:1356`) -> `write_merged` "
        "(sole call site `merge_cmd.rs:2122`, defined `:3245`) -> "
        "`with_ceiling(color::saturation_ceiling(..))` at `:3411` and `:3481`. "
        "`write_merged` has **exactly one caller**. This is the first user-visible quality "
        "fix confirmed to reach the default render since the owner's complaint.",
    ),
    (
        1482,
        "MEASURED",
        "ORCH",
        "Symbol presence and render reachability are independent properties, measured on "
        "two files the same night: `optics.rs` holds a complete, fitted lateral-CA "
        "correction whose **34 references are all inside `optics.rs` itself** (definitions "
        "plus its own unit tests), so `STREHL_FIX_CA=1` set a variable no render path read; "
        "`merge_cmd.rs` holds the highlight clip, whose chain to `strehl stack` closes in "
        "four hops. A grep for either symbol returns hits. Only one of them changes a "
        "photograph.",
    ),
]

NEW_DISCS = [
    (
        758,
        "**Prove a fix reaches the render by tracing the call chain to the CLI dispatch, "
        "not by grepping for the symbol.** Walk it in the direction that can fail: from "
        "the changed line outward to its callers, and stop only at the subcommand match "
        "arm the operator actually types. Count the callers at each hop — a function with "
        "zero callers is the failure this discipline exists to catch, and a function with "
        "several may reach the render on only one of them. This was the dominant failure "
        "mode of the 2026-08-24 build night: three diagnosed defects had finished, "
        "measured fixes, and the worst of them reached no render at all (facts 1481, 1482).",
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

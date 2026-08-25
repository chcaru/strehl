"""Fold M117's cache-poisoning audit.

Facts 1609-1614, disciplines 826-827, plus an inline CORRECTED marker on fact
1562 (whose 48-hour exposure window was wrong by 4.6x).

Verdict: corpus clean, 0 defects -- but the audit found a wider vector than the
milestone that reported the defect, and says so.
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


fact_line = full_line(raw, "| 1608 |")
disc_line = full_line(raw, "825. ")

NEW_FACTS = [
    (
        1609,
        "MEASURED",
        "M117",
        "**THE CACHE-POISONING EXPOSURE WINDOW IS 10 h 26 m, NOT 48 HOURS -- fact 1562 "
        "was wrong by 4.6x and in the alarming direction.** Dated from git rather than "
        "from memory: the consume path landed at `885e9f7` (2026-08-24 03:15:23) and the "
        "fix at `69f7b4c` (13:41:53). The window cannot start on 08-22 because **the "
        "cache did not exist then** -- `strehl stack` could not read it until M86c. "
        "**A defect is dated from when its READ path first existed, not from when the "
        "bug was written**, and dating it by the latter inflated the blast radius of "
        "every report in between.",
    ),
    (
        1610,
        "MEASURED",
        "M117",
        "**THE CORPUS IS CLEAN: of 163 reports, 155 IMMUNE / 8 EXPOSED / 0 UNDETERMINED, "
        "and no poisoning write ever reached the shared cache.** 114 reports landed "
        "before the read path existed at all; **7 of the 8 exposed are the milestones "
        "investigating this very defect**, and the 8th (M105b) named it 3 h 07 m before "
        "the window opened. The write side is clean four independent ways: all 6 live "
        "cache entries carry `reference n/2`; the one in-window entry is **byte-identical "
        "(`1864A370AE92B377`)** to an independent post-fix re-solve; of 234 sidecars on "
        "this machine **104 are poisoning-shaped and zero are in the shared root**; and "
        "all 3 no-`--out` `align` invocations in the corpus are hermetic.",
    ),
    (
        1611,
        "MEASURED",
        "M117",
        "**THE EXPOSURE IS CUMULATIVE RATHER THAN PER-RUN, BECAUSE THE CACHE IS A FILE.** "
        "It lives at `%LOCALAPPDATA%\\strehl\\warpmaps\\...`, and before 10:32:43 it lived "
        "at `<stackdir>\\warpmap.txt` -- **inside the owner's capture drive**. A cache "
        "that persists across runs converts a transient defect into a permanent one: one "
        "poisoning invocation during the window would have contaminated every later run "
        "that hit the same key, including runs made long after the fix landed. This is "
        "the property that made the audit necessary at all.",
    ),
    (
        1612,
        "MEASURED",
        "M117",
        "**THE POSITIVE CONTROL FIRED TWICE AND FOUND A WIDER VECTOR THAN THE MILESTONE "
        "THAT REPORTED THE DEFECT.** M97n reported the hazard as requiring an explicit "
        "non-default reference; M117's control showed `AlignArgs::reference` **defaulted "
        "to 0** until `19f1be0` (13:19:52), so **a plain `strehl align <dir>` with no "
        "flags at all was a poisoning run for 10 h 04 m of the 10 h 26 m window**. The "
        "damage is not subtle -- **98.7 % of pixels change, RMS 1.9 % of mean level** -- "
        "and the determinism arm reads exactly 0, so the instrument is not confusing "
        "poisoning with run-to-run noise. **A control commissioned to confirm a known "
        "hazard enlarged it.**",
    ),
    (
        1613,
        "MEASURED",
        "M117",
        "**THE 449-TEST BYTE-FREEZE REGISTRY COVERS NONE OF THE VULNERABLE PATH, BY "
        "DESIGN -- so citing its green here would be a true statement that misleads.** "
        "The registry passes and the corpus is clean, and neither fact is evidence for "
        "the other. M117 flagged this against its own result rather than letting a "
        "passing suite stand in for coverage it does not have. **A green suite is scoped, "
        "and its scope is never printed next to its result.**",
    ),
    (
        1614,
        "MEASURED",
        "M117",
        "**THE CORPUS SURVIVED THIS BY LUCK AS MUCH AS BY DISCIPLINE.** What actually "
        "prevented contamination was `STREHL_ALIGN=0` and `STREHL_WARPMAP` -- **and both "
        "were adopted for unrelated reasons**, neither as a defence against cache "
        "poisoning. The one unrecoverable gap M117 names against itself: an uncommitted "
        "ad-hoc `strehl align` typed during those ten hours would leave no trace, and its "
        "absence is **argued, not proved**. The honest reading is that the clean verdict "
        "is real and that the process which produced it was not the process that deserves "
        "the credit.",
    ),
]

NEW_DISCS = [
    (
        826,
        "**Before citing a passing suite as reassurance about a specific hazard, check "
        "that the suite's coverage intersects the hazard.** strehl's 449-test byte-freeze "
        "registry is green and covers **none** of the cache-poisoning path (fact 1613). "
        "Quoting it in that context would have been literally true and materially "
        "misleading, which is the most dangerous shape a claim can take because nothing "
        "in the output flags it. **A test result reports its verdict but never its "
        "scope**, so the scope has to be supplied by the person citing it -- and the "
        "citation is worthless without it.",
    ),
    (
        827,
        "**Date a defect from when its read path first existed, not from when the bug was "
        "written -- and if it caches, treat exposure as cumulative rather than per-run.** "
        "Fact 1562 put the cache-poisoning window at 48 hours by dating it from the "
        "write; the read path did not exist for most of that, and the true window is "
        "**10 h 26 m** (fact 1609). The two errors pull opposite ways and both matter: "
        "dating from the write **inflates** the blast radius and wastes an audit, while "
        "ignoring persistence **deflates** it, because a file-backed cache lets a single "
        "bad invocation contaminate runs made long after the fix shipped (fact 1611).",
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

# Mark fact 1562's window as corrected, inside the claim cell so the row keeps 5 pipes.
old_1562 = "| 1562 | DERIVED | "
i = out.index("\n" + old_1562)
j = out.index("|", i + 1 + len(old_1562))  # end of the source cell
marker = (
    " **[CORRECTED by fact 1609: the exposure window stated here is 48 hours; measured "
    "from the git history of the READ path it is 10 h 26 m. The rest of the row stands.]**"
)
head = out[: j + 1]
tail = out[j + 1 :]
prev = out
out = head + marker + tail
assert out != prev, "1562 marker did not land"

row_1562 = full_line(out, "| 1562 |")
n = len(row_1562.replace("\\|", "").split("|")) - 1
assert n == 5, "fact 1562 row now has %d pipes: %s" % (n, row_1562[:160])
assert "CORRECTED by fact 1609" in row_1562, "marker landed on the wrong row"

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(out)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("marked fact 1562 CORRECTED; row pipes=%d" % n)

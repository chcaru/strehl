"""Fold M113's second round: the -Last row that was inference when ORCH folded it as
measurement, verbatim retention on an arbitrary value, and the D:\\ folder whose name
would have been misattributed to the agent that cleared it.

Facts 1520-1523, disciplines 780-781.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1519 |")
disc_line = full_line(raw, "779. ")

NEW_FACTS = [
    (
        1520,
        "MEASURED",
        "M113",
        "**`\\| Select-Object -Last N` is safe, and it is now measured rather than "
        "inferred.** Under adversarial priming in both directions and against a "
        "non-binary primer: primed 0 with a command exiting 3 reads **3**; primed 7 with "
        "a command exiting 0 reads **0**; primed 5 with a command exiting 0 reads **0** "
        "-- live in every case. **When ORCH folded fact 1507 this row was M113's "
        "explicitly-flagged untested inference**, presented in a table beside rows that "
        "were measured. The conclusion did not change, but its standing did, and it was "
        "ORCH's fold that erased the distinction.",
    ),
    (
        1521,
        "MEASURED",
        "M113",
        "**The stale exit code is retained verbatim on an arbitrary value, closing the "
        "last escape route.** Primed **42**, a command that genuinely exited 0 reads "
        "**42**; primed 5, it reads 5. The retained value is not drawn from any small or "
        "guessable set, so **no observed exit code of any value is evidence that the read "
        "was live** -- a gate cannot be cleared by observing that its code looked "
        "plausible. Strengthens fact 1508 from a single primer to an arbitrary one.",
    ),
    (
        1522,
        "MEASURED",
        "M113 + ORCH",
        "**`D:\\Recovered_113MSDCF` is the owner's own recovered camera data, not agent "
        "scratch, despite the `113` in its name.** M113 flagged it; ORCH verified "
        "independently: created **05/09/2026 15:13:34**, last written 15:19:08 -- **three "
        "and a half months before any agent in this fleet existed** -- containing **5 "
        "Sony `.sr2` RAW files** with file-carver-style offset names (`f45124096.sr2`). "
        "Decisively, **`D:\\personal\\macro\\113MSDCF` exists**, alongside the "
        "`109MSDCF`, `112MSDCF` and `119MSDCF` the corpus already cites, so this is a "
        "recovery of that camera folder. The only agent-created directories on `D:\\` "
        "remain `m106-scratch` (466 files, 16.9 GB) and `strehl-scratch-m98` (empty).",
    ),
    (
        1523,
        "MEASURED",
        "M113",
        "**M113's own prefix-anchored edits did not graft.** Discipline 768 warns that an "
        "edit anchored on a sentence prefix silently appends the line's unmatched "
        "remainder to the replacement. M113 re-read the joined result at all three "
        "`str.replace` sites in its `amend.py` / `amend2.py` and found no unmatched "
        "remainder at any of them. Its own assessment is the useful part: **it got this "
        "right by accident rather than by rule**, having written the edits before the "
        "discipline existed.",
    ),
]

NEW_DISCS = [
    (
        780,
        "**A table that mixes measured rows with inferred ones launders the inference "
        "into a measurement.** M113 labelled `-Last` as *not separately tested* in its "
        "report; ORCH folded it into fact 1507 as a row in a table of measurements, and "
        "the label did not survive the fold. Nothing was misquoted -- the provenance was "
        "simply carried by prose that the table format discarded. **Mark provenance per "
        "row, or measure the row before it joins the table.** The risk is highest exactly "
        "where the inference is reasonable, because then nothing looks wrong (facts 1507, "
        "1520).",
    ),
    (
        781,
        "**An agent-ID-shaped substring in a path is not provenance.** `Recovered_113MSDCF` "
        "sat on the owner's drive during an audit for agent-created scratch, and reads "
        "unmistakably as M113's. It is a Sony DCIM folder predating the fleet by three and "
        "a half months (fact 1522). **Check the timestamp against the agent's lifetime "
        "before attributing anything to it** -- one cheap comparison, and the alternative "
        "is accusing an agent of violating a constraint it obeyed, or worse, deleting the "
        "owner's data because its name matched a pattern.",
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
        assert not ((o < 0x20 and ch != "\n") or o == 0x7F), "fold text contains 0x%02X" % o

raw2 = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert raw2 != raw, "fact insertion did not land"
raw3 = raw2.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert raw3 != raw2, "discipline insertion did not land"

# Repair the provenance of the -Last row inside fact 1507 itself, anchored on the
# COMPLETE line (discipline 768) so the correction travels with the claim.
f1507 = full_line(raw3, "| 1507 |")
assert f1507.endswith(" |"), "fact 1507 line does not end as a table row"
marked = f1507[:-1] + "**PROVENANCE CORRECTED (fact 1520): the `-Last` row was M113's " \
                      "explicitly-untested inference when this fact was folded, not a " \
                      "measurement. It has since been measured and holds.** |"
raw4 = raw3.replace(f1507, marked, 1)
assert raw4 != raw3, "fact 1507 provenance marker did not land"
assert raw4.count("PROVENANCE CORRECTED (fact 1520)") == 1, "marker not unique"

for fid, _, _, _ in NEW_FACTS:
    assert raw4.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw4.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw4)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))
print("corrected the provenance of the -Last row in fact 1507")

"""Fold ORCH's false-zero instrument defect and the agent-attribution finding."""
import io
import sys

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()

FACT_ANCHOR = "| 1476 |"
DISC_ANCHOR = "754."

assert raw.count("\n" + FACT_ANCHOR) == 1, "fact 1476 anchor not unique"
assert raw.count("\n" + DISC_ANCHOR + " ") == 1, "discipline 754 anchor not unique"

# locate the full line for each anchor
def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]

fact_line = full_line(raw, FACT_ANCHOR)
disc_line = full_line(raw, DISC_ANCHOR + " ")

NEW_FACTS = [
    (
        1477,
        "MEASURED",
        "ORCH",
        "`Select-String <relative-path>` run from a directory where that path does not "
        "exist emits a non-terminating `Cannot find path` error and produces **no match "
        "output**, which is byte-identical in appearance to a genuine zero-match result. "
        "ORCH ran `Select-String crates/strehl-cli/src/merge_cmd.rs -Pattern "
        "'saturation_ceiling\\|with_ceiling'` from the monorepo root "
        "`C:\\dev\\blog\\death-of-software` **three times** and read 0 each time; "
        "`Test-Path` on that relative path from that directory returns `False`. The same "
        "pattern via `git grep` against `HEAD` returns **2** hits at "
        "`merge_cmd.rs:3411` and `:3481`. The patch was present in `HEAD` for the entire "
        "period it was reported missing.",
    ),
    (
        1478,
        "MEASURED",
        "ORCH",
        "Neither `git status --porcelain` nor `git log -1 -- <file>` attributes an "
        "**uncommitted** edit to an agent in a shared working tree: the first reports "
        "*what* changed with no author, the second reports who last *committed*, which is "
        "a different agent whenever a file changes hands. Measured on "
        "`crates/strehl-cli/src/align_cmd.rs`: `git log -1` attributed it to `69f7b4c` "
        "(M97) while the live uncommitted diff was **M107's** lateral-CA wiring. The only "
        "instrument that attributed it correctly was **reading the diff body** and "
        "recognising the subject matter.",
    ),
    (
        1479,
        "MEASURED",
        "ORCH",
        "The CA correction's real gather call site is `warp_frame_in_place` in "
        "`crates/strehl-cli/src/align_cmd.rs`, **not** `warpmap.rs::gather_frame` as ORCH "
        "instructed M107. M107 followed the call graph to the true site. ORCH's grant of "
        "`align_cmd.rs` to M109 was therefore issued against a stale model of the wiring "
        "site and put two agents with concurrent uncommitted work in one file — the "
        "failure mode rule 11 exists to prevent.",
    ),
    (
        1480,
        "ARGUED",
        "ORCH",
        "M97's correction of ORCH's attribution error contained the **same class of error** "
        "in the same message: it attributed dirty `align_cmd.rs` to an agent id `M112` that "
        "does not exist in the fleet (7 running: M87, M85, M107, M109, M110, M111, M113), "
        "and its own evidence column for that row read `—`. A correct diagnosis of an "
        "instrument's blindness does not confer immunity to it.",
    ),
]

NEW_DISCS = [
    (
        755,
        "**A search that finds nothing and a search that ran nowhere are the same "
        "picture.** Before reporting a zero match as evidence of absence, prove the "
        "search had reach: `Test-Path` the target, or assert a non-zero hit count for a "
        "pattern known to be present in the same file. Prefer `git grep <pattern> HEAD -- "
        "<path>`, which fails loudly on a bad path and pins the revision, over "
        "`Select-String` with a relative path. ORCH gated a fleet-wide lane "
        "redistribution on a zero it never measured (fact 1477).",
    ),
    (
        756,
        "**Attribute an uncommitted edit by reading its diff, never by asking git who "
        "owns the file.** In a shared working tree `git status` has no author column and "
        "`git log -1` answers a question about the past. Both will name the wrong agent "
        "with total confidence at exactly the moment a file is changing hands, which is "
        "the moment attribution matters (fact 1478).",
    ),
    (
        757,
        "**When an agent reports that the site you sent it to was the wrong one, update "
        "every grant that depended on your model of that site.** ORCH told M107 the "
        "gather was in `warpmap.rs`, M107 found it in `align_cmd.rs`, and ORCH then "
        "granted `align_cmd.rs` to a second agent — because the grant was made against "
        "the instruction, not against the discovery (fact 1479).",
    ),
]

def fact_row(fid, status, source, claim):
    assert "|" not in claim.replace("\\|", ""), "unescaped pipe in claim %d" % fid
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)

fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % (d[0], d[1]) for d in NEW_DISCS)

before_facts = raw.count("\n| ")
raw2 = raw.replace(fact_line, fact_line + "\n" + fact_block, 1)
assert raw2 != raw, "fact insertion did not land"

raw3 = raw2.replace(disc_line, disc_line + "\n" + disc_block, 1)
assert raw3 != raw2, "discipline insertion did not land"

# verify every new row has exactly 5 unescaped pipes
for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

for fid, _, _, _ in NEW_FACTS:
    assert raw3.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw3.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw3)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))

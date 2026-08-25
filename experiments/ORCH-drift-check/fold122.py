"""Fold ORCH's systematic reachability audit at HEAD cfe6ac6.

Facts 1553-1555, disciplines 803-804.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1552 |")
disc_line = full_line(raw, "802. ")

NEW_FACTS = [
    (
        1553,
        "MEASURED",
        "ORCH",
        "**SYSTEMATIC REACHABILITY AUDIT AT HEAD `cfe6ac6`: of 25 declared `pub mod`, "
        "exactly TWO are unreachable from the product -- `outlier` (1094 lines) and "
        "`robust` (544 lines), 1638 lines total.** Method "
        "(`experiments/ORCH-drift-check/reachability.py`): enumerate every `pub mod` in "
        "each `lib.rs` at HEAD, count references outside the module's own file and its own "
        "`tests/`, `examples/`, `benches/` harness. Corroborated independently by "
        "`git grep <mod>:: HEAD -- crates/`, and the `outlier` verdict matches M97r's own "
        "independent check exactly. **Also corrects an ORCH error: `softgate` IS wired at "
        "HEAD** (`merge.rs:75`, `use crate::softgate::{SoftGate, WEIGHT_FLOOR}`), not "
        "uncommitted as previously believed. LIMIT: this is a static name-based audit; a "
        "module reached only through dynamic registration would be missed.",
    ),
    (
        1554,
        "MEASURED",
        "ORCH",
        "**THE CORPUS DIAGNOSED THE DEFECT, BUILT THE CURE, AND NEVER CONNECTED IT.** Fact "
        "1189 (M89) established that motion **wins** the focus election -- a frame that "
        "moved presents a displaced edge, a displaced edge is **sharper** than the "
        "correctly-focused stationary alternative, and **4.78 % of `foam`'s output pixels "
        "take their value from a frame more than 8 sigma discrepant**. The same fact "
        "priced the two intervention points: **masking the ELECTION removes 100 % of those "
        "pixels; masking only the AVERAGE recovers 6.0 % of the benefit and removes none "
        "of them.** `robust.rs` implements election-time refusal-and-demotion and is "
        "**unreachable** (fact 1553). M97r's `outlier.rs` is the average-time instrument, "
        "also unreachable, and by fact 1189's own pricing it addresses **6.0 %** of this "
        "defect even once wired.",
    ),
    (
        1555,
        "DERIVED",
        "ORCH",
        "**Wiring order follows from fact 1189's pricing, and it is the opposite of the "
        "order the two modules were built in.** Election-time refusal (`robust.rs`) is "
        "worth ~16.7x the average-time mask on the one defect both address, so it should "
        "be wired first even though `outlier.rs` is the newer, better-instrumented module. "
        "**A better instrument aimed at the wrong stage loses to a cruder one aimed at the "
        "right stage** -- and `robust.rs` was written knowing this, its own header citing "
        "fact 1189 and documenting `Arm::Soft` as demotion-not-exclusion precisely so a "
        "frame that is genuinely the only one resolving a pixel survives the penalty.",
    ),
]

NEW_DISCS = [
    (
        803,
        "**Run a reachability audit over `pub mod` on a schedule, and treat unreachable "
        "line count as a first-class health metric of this project.** Discipline 800 says "
        "verify the call site for one capability; this is its standing form. The audit is "
        "one script and one minute (`experiments/ORCH-drift-check/reachability.py`), and "
        "its first run found 1638 lines of tested, measured, folded capability that the "
        "binary cannot reach (fact 1553) -- including the cure for a defect the corpus had "
        "already diagnosed and priced (fact 1554). **This project's characteristic failure "
        "is not building the wrong thing; it is building the right thing and not "
        "connecting it.**",
    ),
    (
        804,
        "**Price the STAGE before you price the ALGORITHM.** Fact 1189 measured the same "
        "defect at two intervention points and found a **16.7x** difference between them "
        "(100 % of offending pixels removed at the election, 6.0 % of the benefit "
        "recovered at the average). No amount of sophistication in the average-stage "
        "estimator closes that gap, because the wrong frame has already been elected. "
        "**When a fix underperforms its registered bar, ask whether it is aimed at the "
        "right stage before improving it** -- M89's mask failed at -5.21 % against a "
        "+10 % bar, and the stage, not the statistic, was the reason.",
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

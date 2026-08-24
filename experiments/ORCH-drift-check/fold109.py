"""Fold ORCH's own verified facts: the HEAD build, and the soft gate's unreachability.

Facts 1496-1498, disciplines 765-766. Everything here was either measured by ORCH
directly (the build) or read directly out of a subordinate's committed report
(M111-waxy-blobs.md SS15.6/15.7), not relayed second-hand.
"""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1495 |")
disc_line = full_line(raw, "764. ")

NEW_FACTS = [
    (
        1496,
        "MEASURED",
        "ORCH",
        "**`HEAD` = `2ae2944` builds clean: `cargo check --workspace --all-targets`, exit "
        "0, zero `error` lines, zero `warning` lines.** Run in an **isolated `git "
        "worktree`** (`C:\\dev\\strehl-out\\ORCH-headcheck`) precisely so it measures the "
        "commit and not the six uncommitted files other lanes are holding in the shared "
        "tree. Five agents (M97, M107, M109, M111, M113) landed Rust into one tree tonight "
        "and the result integrates.",
    ),
    (
        1497,
        "MEASURED",
        "ORCH",
        "**The green build was itself validated before being believed.** A `cargo check` "
        "returning 0 having compiled nothing is indistinguishable in exit code and in "
        "grep-for-`error` from one that checked the whole workspace. Cold run: **376 "
        "artifacts** in a fresh `target/debug/deps`. Immediate re-run: **0.12 s, one line "
        "(`Finished`)** -- the signature of a warm no-op, which proves the first run was "
        "the cold one that did the work.",
    ),
    (
        1498,
        "MEASURED",
        "M111 report SS15.6-15.7, read directly by ORCH",
        "**The soft admission gate is committed, tested, and unreachable.** `softgate.rs` "
        "landed at `2ae2944` with a cross-language test pinning the Rust kernel against "
        "the Python that produced the published interval (agreeing to seven significant "
        "figures at the tightest rung; a mutation control confirms the test is "
        "load-bearing). M111 **deliberately did not integrate it** -- `merge.rs` is M97's "
        "lane -- so the deliverable is a module plus a seven-row line-numbered spec, and "
        "the waxy-blob defect the owner can see is **still unfixed on every render path**. "
        "Separately: the merge now carries **three distinct kernels over one focus axis at "
        "one calibrated temperature** -- the shipping **top-hat** (`Gate::admits`), an "
        "**exponential** `exp(-gap/T)` already in `through_focus.rs:371-373` (diagnostic, "
        "`--stats` only), and M111's new **Gaussian** `exp(-0.5 (gap/T)^2)`. The "
        "temperature scale was made identical by explicit design; the kernels diverged "
        "silently because neither author had read the other's file.",
    ),
]

NEW_DISCS = [
    (
        765,
        "**A build that exits 0 has not been shown to have built anything.** `cargo check` "
        "on a warm cache, on an empty target set, or on a workspace whose members failed to "
        "resolve can all return 0 with no `error` line to grep. Before citing a green "
        "build, show it did work: artifact count in a cold `target/`, wall-clock, or a "
        "re-run whose sub-second `Finished` proves the previous run was the cold one. This "
        "is disciplines 763-764 applied to the compiler -- a green result is a claim about "
        "your instrument until the instrument is shown to have been running.",
    ),
    (
        766,
        "**Lane discipline manufactures unreachable code, and the orchestrator must count "
        "*reachable* fixes, not *specified* ones.** Forbidding two agents from one file is "
        "correct and prevents silent clobbering, but its consequence is that an agent "
        "diagnosing a defect owned by another lane can only deliver a **spec**. M111 "
        "produced a tested module and a line-numbered integration table for the waxy-blob "
        "defect and correctly stopped at `merge.rs`'s boundary; ORCH briefly recorded the "
        "defect as addressed because a commit existed. A commit is not a code path (cf. "
        "discipline 758). Track *specified* and *reachable* as separate columns, and treat "
        "a hand-off as an open defect until a second agent has applied it and proved the "
        "flag's null with a hash.",
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

for fid, _, _, _ in NEW_FACTS:
    assert raw3.count("\n| %d |" % fid) == 1, "fact %d not unique" % fid
for did, _ in NEW_DISCS:
    assert raw3.count("\n%d. " % did) == 1, "discipline %d not unique" % did

with io.open(PATH, "w", encoding="utf-8", newline="") as fh:
    fh.write(raw3)

print("folded facts %s" % ", ".join(str(f[0]) for f in NEW_FACTS))
print("folded disciplines %s" % ", ".join(str(d[0]) for d in NEW_DISCS))

"""Fold the control-character finding, check S7, and M87's refinement of rule 47."""
import io

PATH = r"C:\dev\blog\death-of-software\projects\strehl\docs\research\SYNTHESIS.md"

with io.open(PATH, "r", encoding="utf-8") as fh:
    raw = fh.read()


def full_line(text, anchor):
    i = text.index("\n" + anchor)
    j = text.index("\n", i + 1)
    return text[i + 1 : j]


fact_line = full_line(raw, "| 1487 |")
disc_line = full_line(raw, "760. ")

NEW_FACTS = [
    (
        1488,
        "MEASURED",
        "M87/ORCH",
        "**PowerShell double-quoted here-strings silently corrupt markdown inline-code "
        "spans, and the damage had reached a fact-table row.** In `@\"...\"@` a backtick is "
        "an escape introducer, so a span written as backtick-b-e-e-3-c-p-l is consumed into "
        "a single **0x08** byte plus `ee-3-cpl`: the backtick **and the letter after it** "
        "both vanish. A corpus-wide scan of **2631** files found exactly one survivor, "
        "`docs/research/M105b-exposure-ship.md` line **1312**, carrying **4** occurrences — "
        "**0x1B** (`experiments` -> ESC+`xperiments`), **0x08** twice (`bee-3-cpl` -> "
        "BS+`ee-3-cpl`), **0x0C** (`foam` -> FF+`oam`) — one of them inside a ledger row. "
        "`b`, `e` and `f` open a great many identifiers in this corpus, which is why this "
        "escape set is so damaging here. Repaired by restoring the eaten letter: **103405 "
        "bytes, length unchanged**, row pipe count still 5.",
    ),
    (
        1489,
        "MEASURED",
        "ORCH",
        "`corpus_lint` gained check **S7**, which rejects any C0 control character (tab "
        "excepted) and DEL across markdown and Rust. Its negative control "
        "(`experiments/ORCH-drift-check/control_s7.py`) plants one **0x0C** on a "
        "**uniqueness-asserted** full-line anchor and measures **green -> RED -> green**: "
        "baseline exit 0, mutated exit **1** naming `S7` at "
        "`M105b-exposure-ship.md:1312` column **607**, restore byte-identical, post-restore "
        "exit 0. The first anchor attempted was **rejected by the control's own uniqueness "
        "assertion** at 3 occurrences before it could mutate the wrong site.",
    ),
    (
        1490,
        "MEASURED",
        "M87",
        "**Rule 47 refined, and its stated mechanism was wrong.** Truncating a native "
        "command's output with `Select-Object -First N` does **not** set `$LASTEXITCODE` to "
        "0 — it leaves the variable **not updated at all**, so it retains the *previous* "
        "command's code. Measured on pwsh **7.6.5** by priming: primed by success, a "
        "truncated **failing** run reads **0** (false GREEN); primed by failure, a "
        "truncated **succeeding** run reads **1** (**false RED**). Windows PowerShell 5.1 "
        "yields **-1**. The trigger is **truncation, not match count** (0.3 s vs 6.1 s "
        "wall-clock). M87's own first probe *refuted* the effect by reading a correct 1 — "
        "itself a stale read.",
    ),
]

NEW_DISCS = [
    (
        761,
        "**Never build corpus text in a PowerShell double-quoted here-string.** `@\"...\"@` "
        "treats backtick as an escape introducer, so every markdown inline-code span is a "
        "mutation site and the corruption is invisible in a renderer. Write the text to a "
        "file with a Python script, or use the single-quoted `@'...'@` form, which does not "
        "interpret escapes. When repairing, **restore the letter the escape ate** rather "
        "than deleting the byte — deletion silently shortens an identifier into a "
        "plausible-looking different one (fact 1488).",
    ),
    (
        762,
        "**A stale `$LASTEXITCODE` can read as either a false pass or a false failure, so a "
        "correct-looking code does not clear a truncated pipeline.** M87 attempted to "
        "refute the effect and its probe returned a correct `1` — because the *previous* "
        "command had also failed. Capture the code immediately after the process, on its "
        "own line, before any filtering; and when auditing past gates, re-run them rather "
        "than reasoning about which direction the error would have taken (fact 1490).",
    ),
]


def fact_row(fid, status, source, claim):
    return "| %d | %s | %s | %s |" % (fid, status, source, claim)


fact_block = "\n".join(fact_row(*f) for f in NEW_FACTS)
disc_block = "\n".join("%d. %s" % d for d in NEW_DISCS)

for line in fact_block.split("\n"):
    n = len(line.replace("\\|", "").split("|")) - 1
    assert n == 5, "row has %d unescaped pipes, need 5: %s" % (n, line[:90])

# this fold is about control characters; it must not contain any
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

"""Fold M17 (dual (mean, max) focus response) into SYNTHESIS.md.

M17's proposals are already table rows, so facts transfer verbatim; disciplines
are 2-column rows converted to the indented list form section 5 uses. No shift:
facts 100-112 and disciplines 50-54 were verified free per-namespace first.
"""
import re, pathlib, textwrap

SRC = pathlib.Path("docs/research/M17-dual-response-measured.md")
DST = pathlib.Path("docs/research/SYNTHESIS.md")


def table_rows(lines, start_heading, lo, hi):
    i = next(i for i, l in enumerate(lines) if l.startswith(start_heading))
    out = []
    for l in lines[i:]:
        if l.startswith("## ") and not l.startswith(start_heading):
            break
        m = re.match(r"\| (\d+) \| (.*?)\s*\|\s*$", l)
        if m and lo <= int(m.group(1)) <= hi:
            out.append((int(m.group(1)), m.group(2)))
    return out


src = SRC.read_text(encoding="utf-8").split("\n")

facts = [f"| {n} | {body} |" for n, body in table_rows(src, "## 9.", 100, 112)]
assert len(facts) == 13, len(facts)

disciplines = []
for n, body in table_rows(src, "## 10.", 50, 54):
    wrapped = textwrap.wrap(body.strip(), width=96, break_long_words=False, break_on_hyphens=False)
    disciplines.append(f"{n}. {wrapped[0]}")
    disciplines += [f"     {w}" for w in wrapped[1:]]
assert sum(1 for d in disciplines if re.match(r"\d+\. ", d)) == 5

QUESTION_100 = (
    "     **ANSWERED by M17.** The baseline is neither the ring nor plain Tenengrad: it is "
    "**`tenengrad-sq-w13`**, `box_mean₂₇(gx²+gy²)/σ²`. It takes the monotone-edge blind spot from "
    "**D = 1.0000 to 0.1860**, is quality-neutral on M13's occluding-edge cells (15/30, p = 1.00), "
    "noise-neutral (ΔN = −0.0015), and **cheaper than the shipped operator (0.96×)** because it "
    "drops a per-pixel `sqrt`. It is now the operator in `crates/strehl-core/src/focus.rs`, with "
    "the ring retained only as the comparison the tests assert against. **Caveat carried forward:** "
    "`w13` was chosen by M13 for the *mean* operator and candidate (c)'s per-shape sign is not "
    "uniform, which is consistent with a window mismatch — the ladder has not been re-run for "
    "`tenengrad-sq`. See owner question in `docs/research/OWNER-QUESTIONS.md`."
)


def insert_after_last(lines, prefix, predicate, block):
    cur, last = "", None
    for i, l in enumerate(lines):
        if l.startswith("## "):
            cur = l
        if cur.startswith(prefix) and predicate(l):
            last = i
    assert last is not None, prefix
    return lines[: last + 1] + block + lines[last + 1 :]


dst = DST.read_text(encoding="utf-8").split("\n")
dst = insert_after_last(dst, "## 4.", lambda l: re.match(r"\| \d+ \|", l), facts)
dst = insert_after_last(dst, "## 5.", lambda l: re.match(r"\d+\. \*\*", l) or l.startswith("     "),
                        disciplines)

# question 100 is answered in place
cur, done = "", False
for i, l in enumerate(dst):
    if l.startswith("## "):
        cur = l
    if cur.startswith("## 10.") and re.match(r"100\. \*\*", l):
        j = i + 1
        while j < len(dst) and dst[j].startswith("     "):
            j += 1
        dst = dst[:j] + [QUESTION_100] + dst[j:]
        done = True
        break
assert done, "question 100 not found"

DST.write_text("\n".join(dst), encoding="utf-8")
print(f"added facts 100-112, disciplines 50-54; answered question 100")

"""Fold M36-VERIFICATION.md's proposed blocks into SYNTHESIS.md.

Facts shift 290-302 -> 285-297 (-5): the verifier proposed 290+, which collides
with the existing facts 300/301/302. Disciplines 200-207 and questions 80-84 are
free in their own namespaces and are folded unshifted.

Internal cross-references of the form "fact NNN" inside the folded text are
shifted by the same -5 so the block stays self-consistent.

Transcribing 13 dense rows by hand is how the M20-V collision happened; this
does it mechanically and the result is checked by tablecheck + foldcheck2.
"""
import re, pathlib

SHIFT = -5
SRC = pathlib.Path("docs/research/M36-VERIFICATION.md")
DST = pathlib.Path("docs/research/SYNTHESIS.md")


def grab(lines, start_pat, row_pat):
    """Rows of the first markdown table after the heading matching start_pat."""
    out, on = [], False
    for l in lines:
        if re.match(start_pat, l):
            on = True
            continue
        if on:
            if l.startswith("## "):
                break
            if re.match(row_pat, l):
                out.append(l)
    return out


def shift_refs(s):
    return re.sub(r"\bfact (29\d|30[012])\b",
                  lambda m: f"fact {int(m.group(1)) + SHIFT}", s)


src = SRC.read_text(encoding="utf-8").split("\n")

facts = []
for row in grab(src, r"^## 5\. New facts", r"^\| \d+ \|"):
    n = int(re.match(r"\| (\d+) \|", row).group(1))
    facts.append(shift_refs(re.sub(r"^\| \d+ \|", f"| {n + SHIFT} |", row)))

disc = grab(src, r"^## 6\. New discipline items", r"^\| \d+ \|")
ques = grab(src, r"^## 7\. New open questions", r"^\| \d+ \|")


def to_item(row):
    """`| N | text |` -> `N. **text**` continuation-indented like the corpus."""
    m = re.match(r"\| (\d+) \| (.*?) \|\s*$", row)
    n, body = m.group(1), shift_refs(m.group(2).strip())
    words, lines, cur = body.split(" "), [], f"{n}."
    pad = " " * (len(n) + 2)
    for w in words:
        if len(cur) + len(w) + 1 > 97:
            lines.append(cur)
            cur = pad + w
        else:
            cur += " " + w
    lines.append(cur)
    return "\n".join(lines)


dst = DST.read_text(encoding="utf-8").split("\n")
out, done = [], set()
for l in dst:
    # facts: after fact 284, the last of the M34 block
    if re.match(r"\| 284 \|", l) and "facts" not in done:
        out.append(l)
        out.extend(facts)
        done.add("facts")
        continue
    # disciplines: immediately before section 6, i.e. at the end of section 5
    if l.startswith("## 6.") and "disc" not in done:
        while out and out[-1].strip() in ("", "---"):
            out.pop()
        out.extend(to_item(d) for d in disc)
        out.extend(["", "---", ""])
        done.add("disc")
    out.append(l)

# questions: append after the last question in section 10
cur, last_q = "", -1
for i, l in enumerate(out):
    if l.startswith("## "):
        cur = l
    if re.match(r"\d+\. \*\*", l) and cur.startswith("## 10."):
        last_q = i
end = last_q + 1
while end < len(out) and out[end].startswith("   "):
    end += 1
out = out[:end] + [to_item(q) for q in ques] + out[end:]
done.add("ques")

assert done == {"facts", "disc", "ques"}, done
DST.write_text("\n".join(out), encoding="utf-8")
print(f"folded {len(facts)} facts (shift {SHIFT}), {len(disc)} disciplines, {len(ques)} questions")
print("fact ids:", [re.match(r"\| (\d+) \|", f).group(1) for f in facts])

"""Repair the markdown emitted by fold-m44.py -- v2, scoped by section.

v1 (`fold-m44-format-repair.py`) aborted without writing, correctly, on
"question 120: no '?' to bound the lead". The diagnosis is the corpus's oldest
trap and rule 25 names it: SYNTHESIS has three independent numbering spaces,
and **disciplines and questions legitimately share numbers**. v1 walked every
line in the file, so `^120\\. ` matched *discipline* 120 in §5 as well as
*question* 120 in §10, and tried to bold-wrap a discipline as if it were a
question. The abort was the guard doing its job.

v2 restricts each repair to the byte range of its own section. Rule 15: v1 is
left as written.

Content is untouched. Two formatting defects, both mine:

  disciplines 276-283  the splitter `^- \\*\\*` in fold-m44.py consumed the
                       opening `**`, breaking the corpus style `N. **Lead.** Body.`
  questions   117-122  the whole item was wrapped in `**...**`; several contain
                       their own inner `**`, giving nested/unbalanced emphasis.
                       House style bolds the lead question only (cf. 110, 116).
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DISC = range(276, 284)
QUES = range(117, 123)


def section_bounds(text, heading):
    start = re.search(heading, text, re.M)
    if not start:
        raise SystemExit(f"section {heading!r} not found")
    nxt = re.search(r"^## ", text[start.end():], re.M)
    return start.start(), (start.end() + nxt.start() if nxt else len(text))


def repair(segment, numbers, kind):
    lines = segment.split("\n")
    fixed = 0
    for i, line in enumerate(lines):
        m = re.match(r"^(\d+)\. (.*)$", line)
        if not m:
            continue
        n, body = int(m.group(1)), m.group(2)
        if n not in numbers:
            continue

        if kind == "discipline":
            if body.startswith("**"):
                continue
            if "**" not in body:
                raise SystemExit(f"discipline {n}: no bold close to pair with")
            lines[i] = f"{n}. **{body}"

        else:
            if not body.startswith("**"):
                continue
            inner, suffix = body, ""
            tail = re.search(r"\*\* \(M44 §8\.\)$", inner)
            if tail:
                inner, suffix = inner[: tail.start()], " (M44 §8.)"
            inner = inner[2:].replace("**", "")
            cut = inner.find("?")
            if cut == -1:
                raise SystemExit(f"question {n}: no '?' to bound the lead")
            lead, rest = inner[: cut + 1], inner[cut + 1 :].strip()
            lines[i] = f"{n}. **{lead}**" + (f" {rest}" if rest else "") + suffix
        fixed += 1

    if fixed != len(numbers):
        raise SystemExit(f"{kind}: fixed {fixed}, expected {len(numbers)}")
    return "\n".join(lines)


def main():
    text = SRC.read_text(encoding="utf-8")

    qlo, qhi = section_bounds(text, r"^## 10\.")
    text = text[:qlo] + repair(text[qlo:qhi], QUES, "question") + text[qhi:]

    dlo, dhi = section_bounds(text, r"^## 5\.")
    text = text[:dlo] + repair(text[dlo:dhi], DISC, "discipline") + text[dhi:]

    dlo, dhi = section_bounds(text, r"^## 5\.")
    qlo, qhi = section_bounds(text, r"^## 10\.")
    for numbers, lo, hi, kind in ((DISC, dlo, dhi, "discipline"), (QUES, qlo, qhi, "question")):
        seg = text[lo:hi]
        for n in numbers:
            m = re.search(rf"^{n}\. (.*)$", seg, re.M)
            if not m:
                raise SystemExit(f"{kind} {n} vanished")
            body = m.group(1)
            if body.count("**") % 2:
                raise SystemExit(f"{kind} {n}: unbalanced bold")
            if not body.startswith("**"):
                raise SystemExit(f"{kind} {n}: lead not bold")

    SRC.write_text(text, encoding="utf-8")
    print(f"repaired disciplines {list(DISC)}, questions {list(QUES)}")


if __name__ == "__main__":
    main()

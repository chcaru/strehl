"""Repair the markdown emitted by fold-m44.py. Numbers and text are untouched.

Two formatting defects, both mine, neither affecting content:

  disciplines 276-283  the splitter `^- \\*\\*` consumed the opening `**`, so the
                       lead sentence lost its bold open and the corpus style
                       `N. **Lead.** Body.` was broken.
  questions   117-122  I wrapped the WHOLE item in `**...**`. Several items
                       contain their own inner `**`, producing nested and
                       unbalanced emphasis. House style bolds the lead question
                       only (see questions 110 and 116).

Rule 15: fold-m44.py has already produced a reported result and is not edited.
"""

import pathlib
import re

SRC = pathlib.Path("docs/research/SYNTHESIS.md")
DISC = range(276, 284)
QUES = range(117, 123)


def main():
    text = SRC.read_text(encoding="utf-8")
    lines = text.split("\n")
    fixed_d = fixed_q = 0

    for i, line in enumerate(lines):
        m = re.match(r"^(\d+)\. (.*)$", line)
        if not m:
            continue
        n, body = int(m.group(1)), m.group(2)

        if n in DISC:
            if body.startswith("**"):
                continue
            if "**" not in body:
                raise SystemExit(f"discipline {n}: no bold close to pair with")
            lines[i] = f"{n}. **{body}"
            fixed_d += 1

        elif n in QUES:
            if not body.startswith("**"):
                continue
            inner = body
            suffix = ""
            tail = re.search(r"\*\* \(M44 §8\.\)$", inner)
            if tail:
                inner, suffix = inner[: tail.start()], " (M44 §8.)"
            inner = inner[2:]
            inner = inner.replace("**", "")
            cut = inner.find("?")
            if cut == -1:
                raise SystemExit(f"question {n}: no '?' to bound the lead")
            lead, rest = inner[: cut + 1], inner[cut + 1 :].strip()
            lines[i] = f"{n}. **{lead}**" + (f" {rest}" if rest else "") + suffix
            fixed_q += 1

    if fixed_d != len(DISC) or fixed_q != len(QUES):
        raise SystemExit(f"fixed {fixed_d} disciplines / {fixed_q} questions - expected {len(DISC)} / {len(QUES)}")

    out = "\n".join(lines)
    for n in list(DISC) + list(QUES):
        seg = re.search(rf"^{n}\. (.*)$", out, re.M).group(1)
        if seg.count("**") % 2:
            raise SystemExit(f"item {n}: unbalanced bold after repair")
        if not seg.startswith("**"):
            raise SystemExit(f"item {n}: lead not bold after repair")

    SRC.write_text(out, encoding="utf-8")
    print(f"repaired disciplines {list(DISC)}, questions {list(QUES)}")


if __name__ == "__main__":
    main()

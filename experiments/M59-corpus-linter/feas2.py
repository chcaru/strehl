"""Scratch: correct cell splitter; probe C7 (provenance labels) and C4
(count-vs-enumeration) feasibility on the live working tree."""
import io
import re
from collections import Counter

SYN = "docs/research/SYNTHESIS.md"
NUM_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}


def cells(row):
    out, buf, i = [], "", 0
    while i < len(row):
        c = row[i]
        if c == "\\" and i + 1 < len(row) and row[i + 1] == "|":
            buf += "|"
            i += 2
            continue
        if c == "|":
            out.append(buf)
            buf = ""
            i += 1
            continue
        buf += c
        i += 1
    out.append(buf)
    if out and out[0].strip() == "":
        out = out[1:]
    if out and out[-1].strip() == "":
        out = out[:-1]
    return out


def sec4(lines):
    s = next(i for i, l in enumerate(lines) if l.startswith("## 4. "))
    e = next(i for i, l in enumerate(lines) if i > s and l.startswith("## 5. "))
    return s, e


def main():
    lines = io.open(SYN, encoding="utf-8", newline="").read().split("\n")
    s, e = sec4(lines)
    rows = [(i + 1, lines[i]) for i in range(s, e) if re.match(r"^\|\s*\d+\s*\|", lines[i])]
    print("fact rows:", len(rows))
    print("sample cells:", [c[:30] for c in cells(rows[0][1])])

    # --- C7: provenance label in the Source cell ---
    lab = re.compile(r"\b(MEASURED|DERIVED|ARGUED|VERIFIED|UNVERIFIED|MEASURED-LOCALLY|REPORTED)\b")
    missing = [(ln, cells(r)[3] if len(cells(r)) > 3 else "<none>") for ln, r in rows
               if not lab.search(cells(r)[3] if len(cells(r)) > 3 else "")]
    print("\nC7: Source cells with no provenance label: %d / %d" % (len(missing), len(rows)))
    for ln, c in missing[:25]:
        print("   line %d  SOURCE=[%s]" % (ln, c.strip()[:110]))

    # --- C4: count-vs-enumeration candidates ---
    print("\n--- C4 probe ---")
    enum_re = re.compile(
        r"\b(facts?|disciplines?|questions?|rows?)\s+(\d+(?:\s*(?:,|;|and|&|/)\s*\d+)+)", re.I)
    count_re = re.compile(
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
        r"\s+(?:of\s+\d+\s+)?(facts?|rows?|fact rows|questions?|disciplines?|sites?|cells?|stacks?)\b", re.I)
    hits = 0
    multi = 0
    for ln, r in rows:
        enums = [(m.start(), len(re.findall(r"\d+", m.group(2)))) for m in enum_re.finditer(r)]
        counts = [(m.start(), NUM_WORDS.get(m.group(1).lower(), None)
                   if not m.group(1).isdigit() else int(m.group(1)), m.group(0))
                  for m in count_re.finditer(r)]
        counts = [c for c in counts if c[1] is not None]
        if not enums or not counts:
            continue
        for pos, n, txt in counts:
            after = [L for p, L in enums if p > pos]
            if not after:
                continue
            if len(after) > 1:
                multi += 1
            if n not in after:
                hits += 1
                print("   line %d  count=%r(%d)  enum lengths after=%s" % (ln, txt.strip(), n, after))
    print("C4 candidate flags: %d   (of which sites with >1 following enum: %d)" % (hits, multi))


if __name__ == "__main__":
    main()

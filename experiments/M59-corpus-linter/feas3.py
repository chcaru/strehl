"""Scratch: C4 variants. Measure precision of three formulations, including a
replay of fact 725's ORIGINAL (defective) wording as a positive control."""
import io
import re

SYN = "docs/research/SYNTHESIS.md"

# an enumeration = >=2 bare integers joined by list separators, no units glued on
INT = r"\d{1,4}(?![\d.,]?\d)(?![%\u00d7]|x\b|\s?(?:px|ms|DN|e-|s\b))"
ENUM = re.compile(r"(?<![\d.\-])" + INT + r"(?:\s*(?:,|;|/|,?\s*and|&)\s*" + INT + r")+")
N_OF_M = re.compile(r"\b(\d{1,4})\s+of\s+(\d{1,5})\s+((?:fact|question|discipline|row|site|cell|stack|frame|pair|test|file|commit)\w*(?:\s+(?:rows?|facts?))?)", re.I)


def enum_lengths(text):
    out = []
    for m in ENUM.finditer(text):
        nums = re.findall(r"\d+", m.group(0))
        out.append((m.start(), len(nums), m.group(0)[:80]))
    return out


def scan(rows, label):
    flags = 0
    sites = 0
    for ln, r in rows:
        es = enum_lengths(r)
        for m in N_OF_M.finditer(r):
            sites += 1
            n = int(m.group(1))
            lens = {L for _p, L, _t in es}
            if n not in lens:
                flags += 1
                print("  [%s] line %d  '%s'  enum lengths in row=%s" %
                      (label, ln, m.group(0), sorted(lens)))
                for _p, L, t in es:
                    print("        len=%d  %s" % (L, t))
    print("[%s] N-of-M sites=%d  flags=%d" % (label, sites, flags))
    return flags


def main():
    lines = io.open(SYN, encoding="utf-8", newline="").read().split("\n")
    s = next(i for i, l in enumerate(lines) if l.startswith("## 4. "))
    e = next(i for i, l in enumerate(lines) if i > s and l.startswith("## 5. "))
    rows = [(i + 1, lines[i]) for i in range(s, e) if re.match(r"^\|\s*\d+\s*\|", lines[i])]
    print("fact rows:", len(rows))
    scan(rows, "HEAD")

    # POSITIVE CONTROL: replay fact 725's original defective wording.
    print("\n--- positive control: fact 725 as originally written ---")
    orig = None
    for ln, r in rows:
        if r.startswith("| 725 |"):
            orig = r.replace("touched only 8 of 515", "touched only 7 of 515")
            break
    if orig is None:
        print("  fact 725 not found")
    else:
        scan([(725, orig)], "CONTROL")


if __name__ == "__main__":
    main()

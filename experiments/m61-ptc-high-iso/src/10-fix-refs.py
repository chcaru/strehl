"""One-off: repair every cross-reference in the M61 report.

Script 08 renumbered my own facts and, in doing so, ALSO shifted five citations
that point at *M48c's* fact numbers, which are not mine to renumber. Script 09
then shifted my headers again. This restores the external citations to M48c's
true numbers (verified by reading M48c) and re-points every internal reference
at the final header list. Each replacement asserts it fired exactly once.
"""

import io
import re
import sys

PATH = "docs/research/M61-ptc-high-iso-measured.md"

# (old, new, expected_count)
FIXES = [
    # --- external citations: restore M48c's OWN numbering ---
    ("M48c fact 18's derived 2.174× step", "M48c fact 17's derived 2.174× step", 1),
    ("§3, facts 12–22.**", "§3, facts 11–22.**", 1),
    ("**`M48c` fact 22 and §9 question 1.**", "**`M48c` fact 21 and §9 question 1.**", 1),
    ("**H1** M48c fact 18, low mode", "**H1** M48c fact 17, low mode", 1),
    ("`M48c` fact 18 (2.174×, DERIVED)", "`M48c` fact 17 (2.174×, DERIVED)", 1),
    ("**M48c fact 22's refusal", "**M48c fact 21's refusal", 1),
    ("M48c fact 18's derived 2.174× conversion-gain step", "M48c fact 17's derived 2.174× conversion-gain step", 1),
    # --- internal references: re-point at the final headers ---
    ("(green planes only — see fact 21)", "(green planes only — see fact 22)", 1),
    ("texture-leakage bias of fact 26", "texture-leakage bias of fact 27", 1),
    ("**The fifth blows up** — see fact 29;", "**The fifth blows up** — see error 8;", 1),
    ("superseded by fact 17.**", "superseded by fact 18.**", 1),
    ("negative** conversion gain (fact 23)", "negative** conversion gain (fact 24)", 1),
    ("hypothesis (fact 19) is testa", "hypothesis (fact 20) is testa", 1),
    ("in this project\n(fact 29).", "in this project\n(fact 30).", 1),
    ("artefacts. Fact 26 records it.", "artefacts. Fact 28 records it.", 1),
]


def main() -> int:
    t = io.open(PATH, encoding="utf-8").read()
    bad = 0
    for old, new, want in FIXES:
        got = t.count(old)
        if got != want:
            print(f"MISS ({got} != {want}): {old!r}", file=sys.stderr)
            bad += 1
            continue
        t = t.replace(old, new)
    if bad:
        print(f"{bad} replacement(s) did not fire; nothing written", file=sys.stderr)
        return 1
    io.open(PATH, "w", encoding="utf-8", newline="\n").write(t)

    heads = [int(x) for x in re.findall(r"\*\*Fact (\d+) \(", t)]
    print("headers sequential 1..%d: %s" % (len(heads),
                                            heads == list(range(1, len(heads) + 1))))
    print()
    for m in re.finditer(r"\bfacts? \d+\b", t):
        s = max(0, m.start() - 60)
        print(f"  ...{t[s:m.end() + 8].replace(chr(10), ' ')}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

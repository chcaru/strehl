"""One-off: shift M61 report fact headers 17..29 up by one after inserting a
second fact 17, WITHOUT touching cross-references (several of the numbers in
running text are references to *M48c's* facts, not mine, and must be inspected
by hand). Prints every reference with its context so they can be checked.
"""

import io
import re
import sys

PATH = "docs/research/M61-ptc-high-iso-measured.md"


def main() -> int:
    t = io.open(PATH, encoding="utf-8").read()

    for n in range(29, 17, -1):
        t = t.replace(f"**Fact {n} (", f"**Fact \x00{n + 1}\x00 (")
    # Two "Fact 17" headers now: the inserted one (first in document order)
    # keeps 17, the original becomes 18.
    parts = t.split("**Fact 17 (")
    if len(parts) == 3:
        t = parts[0] + "**Fact 17 (" + parts[1] + "**Fact \x0018\x00 (" + parts[2]
    else:
        print(f"UNEXPECTED: {len(parts) - 1} 'Fact 17' headers", file=sys.stderr)
        return 1
    t = t.replace("\x00", "")

    io.open(PATH, "w", encoding="utf-8", newline="\n").write(t)

    heads = [int(x) for x in re.findall(r"\*\*Fact (\d+) \(", t)]
    print("headers:", heads)
    print("sequential:", heads == list(range(1, len(heads) + 1)))
    print()
    print("EVERY 'fact N' reference, for hand inspection:")
    for m in re.finditer(r"\bfacts? \d+\b", t):
        s = max(0, m.start() - 70)
        print(f"  ...{t[s:m.end() + 10].replace(chr(10), ' ')}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())

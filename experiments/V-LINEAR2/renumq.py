"""Renumber the discipline entries in docs/research/V-LINEAR2.md sec.13 after a
new fact (Q9) was inserted ahead of them.

Written as a file rather than `python -c` for the reason registered as Q17:
PowerShell's double-quoted strings eat backticks before python sees them.

Shifts Q9..Q16 (disciplines only) up by one, highest first so no renumber
collides with a number not yet moved.  Run with --apply.
"""
import io
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "docs", "research", "V-LINEAR2.md")


def main():
    s = io.open(P, encoding="utf-8", newline="").read()
    for n in range(16, 8, -1):
        old = f"**Q{n} (discipline).**"
        new = f"**Q{n + 1} (discipline).**"
        if old not in s:
            print(f"  {old} not found -- stopping, nothing written")
            return 2
        s = s.replace(old, new)
        print(f"  {old} -> {new}")
    s = s.replace("registered as Q16", "registered as Q17")
    if "--apply" in sys.argv:
        io.open(P, "w", encoding="utf-8", newline="\n").write(s)
        print("  WRITTEN")
    else:
        print("  dry run -- pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())

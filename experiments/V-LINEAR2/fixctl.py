"""Repair the control bytes PowerShell ate out of docs/captures-needed.md sec.33.

Writing markdown through `python -c "..."` inside PowerShell is a trap: the
double-quoted PowerShell string interprets backticks as ITS escape character
before python ever sees them, so a markdown code span like `experiments/...`
arrives as ESC + "xperiments/...".  corpus_lint's S7 check exists precisely to
catch this and it caught it here.

This script prints the damaged lines, then restores backtick + eaten letter.
Run with --apply to write.  Reads and writes only docs/captures-needed.md.
"""
import io
import os
import sys

P = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "..", "docs", "captures-needed.md")

# control byte -> the PowerShell escape it came from -> (backtick, letter)
ESCAPES = {"\x1b": "e", "\x0c": "f", "\x07": "a", "\x08": "b",
           "\n": None, "\r": None, "\t": None, "\x00": "0", "\x0b": "v"}


def main():
    s = io.open(P, encoding="utf-8", newline="").read()
    out = []
    hits = 0
    for i, line in enumerate(s.split("\n"), 1):
        bad = [c for c in line if ord(c) < 32 and c not in "\r\t"]
        if bad:
            hits += len(bad)
            print(f"  line {i}: {len(bad)} control byte(s) "
                  f"{[hex(ord(c)) for c in bad]}")
            print(f"    before: {line[:100]!r}")
            for c in bad:
                rep = ESCAPES.get(c)
                if rep is None:
                    print(f"    !! no known expansion for {hex(ord(c))}")
                    return 2
                line = line.replace(c, "`" + rep)
            print(f"    after : {line[:100]!r}")
        out.append(line)
    print(f"\n  {hits} control byte(s) found")
    if hits and "--apply" in sys.argv:
        io.open(P, "w", encoding="utf-8", newline="").write("\n".join(out))
        print("  WRITTEN")
    elif hits:
        print("  dry run -- pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(main())

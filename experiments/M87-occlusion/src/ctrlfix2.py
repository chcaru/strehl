"""Repair the three stray C0 control characters in M87-occlusion.md.

CAUSE (measured, not guessed).  Prose was appended to the report through a
PowerShell `@"..."@` here-string, which interprets the backtick as an ESCAPE
character.  A code span written as  `verify_s29.py`  is delivered to the file
as  VT + "erify_s29.py" + " " :  the opening `v becomes U+000B and the closing
backtick-before-space collapses to a bare space.  The same mechanism turned
`alpha` into BEL + "lpha".

The file is pure CRLF (4088 CRLF, 0 bare LF), so this works on BYTES and
writes bytes back -- a text-mode round trip would rewrite every line ending
and bury three repairs in a 4088-line diff.

Backs the file up to %TEMP% first and checks it with SHA-256.
Never `git checkout --`.
"""
import hashlib
import os
import pathlib
import shutil
import sys

DOC = pathlib.Path("docs/research/M87-occlusion.md")

REPAIRS = [
    ("\x07lpha below the admission gate", "alpha below the admission gate", 1),
    ("\x0berify_s29.py asserts an", "`verify_s29.py` asserts an", 1),
    ("\x0berify_s29.py re-derives every figure",
     "`verify_s29.py` re-derives every figure", 1),
]

# \r and \n are structure on a CRLF file, not defects.
KEEP = {9, 10, 13}


def ctrl_census(t):
    return sorted({ord(c) for c in t
                   if (ord(c) < 32 and ord(c) not in KEEP) or ord(c) == 127})


def main():
    assert DOC.exists(), DOC
    raw = DOC.read_bytes()
    before = hashlib.sha256(raw).hexdigest()
    bak = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.ctrlfix.bak.md"
    shutil.copy2(DOC, bak)
    assert hashlib.sha256(bak.read_bytes()).hexdigest() == before, "backup differs"
    print(f"backed up to {bak}  sha={before[:16]}")

    t = raw.decode("utf-8")
    print(f"control codes before: {ctrl_census(t)}")
    crlf_before = t.count("\r\n")

    for old, new, n in REPAIRS:
        got = t.count(old)
        if got != n:
            print(f"REPAIR TARGET NOT FOUND ({got} != {n}): {old!r}")
            return 2
        t = t.replace(old, new)
        print(f"  repaired {n}x  ->  {new[:40]!r}")

    codes = ctrl_census(t)
    print(f"control codes after:  {codes}")
    if codes:
        print("FAILED: control characters remain; not writing")
        return 3
    assert t.count("\r\n") == crlf_before, "line endings moved"

    DOC.write_bytes(t.encode("utf-8"))

    fresh = DOC.read_bytes().decode("utf-8")
    assert ctrl_census(fresh) == [], ctrl_census(fresh)
    assert fresh.count("\r\n") == crlf_before, "line endings moved on disk"
    for _, new, n in REPAIRS:
        assert fresh.count(new) == n, (new, fresh.count(new))
    print(f"wrote {DOC}: {len(raw)} -> {len(DOC.read_bytes())} bytes, "
          f"CRLF {crlf_before} unchanged")
    print("OK -- three repairs applied, zero stray control characters remain")
    return 0


if __name__ == "__main__":
    sys.exit(main())

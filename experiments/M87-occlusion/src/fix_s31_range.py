"""Repair two defects my own verifier caught in section 31 before commit.

1. `218x` for the n_eff range was computed by dividing the two ROUNDED
   display values (282.8 / 1.3 = 217.5) instead of the operands
   (282.822 / 1.342 = 210.7). Exactly the compressed-rendering failure the
   milestone is about. Corrected to 211x in both places.
2. Record the slip in 31.8 rather than silently fixing it.
"""
import pathlib
import re

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"
s = DOC.read_bytes().decode("utf-8")
assert s.count("\n") == s.count("\r\n"), "not pure CRLF"
orig = s

n = s.count("218\u00d7")
assert n == 2, f"expected 2 occurrences of 218x, found {n}"
s = s.replace("218\u00d7", "211\u00d7")
assert s.count("211\u00d7") == 2

anchor = ("zero-C0-control-character guard. `control_s31.py` runs the registered")
assert s.count(anchor) == 1, "MUTATION TARGET NOT FOUND: 31.8 anchor"

add = (
    "\r\n\r\nThe verifier earned its place on the first run: it rejected the "
    "`n_eff`\r\n"
    "range I had written as **218\u00d7**. I had divided the two *rounded* display "
    "values\r\n"
    "(282.8 / 1.3) instead of the operands (282.822 / 1.342), which give "
    "**210.7\u00d7**.\r\n"
    "Corrected to 211\u00d7 in `P119` and \u00a731.3. It is a small number and it "
    "changes no\r\n"
    "conclusion, but it is precisely the failure this milestone exists to "
    "catch \u2014 a\r\n"
    "figure derived from a compressed rendering of the data rather than from "
    "the\r\n"
    "data \u2014 and it survived my own reading of the draft."
)
tail = "anchor does not land."
assert s.count(tail) == 1, "MUTATION TARGET NOT FOUND: tail"
s = s.replace(tail, tail + add)

bad = [hex(ord(c)) for c in s if ord(c) < 0x20 and c not in "\r\n"]
assert not bad, f"C0 control characters: {bad[:5]}"
assert s.count("\n") == s.count("\r\n"), "line endings damaged"
assert len(s) > len(orig)
DOC.write_bytes(s.encode("utf-8"))
print(f"patched: {len(s.splitlines())} lines")

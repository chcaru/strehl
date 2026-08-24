"""Repair the four PowerShell-eaten letters in M105b, anchored on context, and assert the result."""
import io

P = "docs/research/M105b-exposure-ship.md"

# (control byte, letter it consumed, unique anchor AFTER repair)
REPAIRS = [
    (b"\x1b", b"e", b"experiments/M105b-exposure-verify/"),
    (b"\x08", b"b", b"bee-3-cpl"),
    (b"\x0c", b"f", b"foam"),
]

with io.open(P, "rb") as fh:
    data = fh.read()

before = data
for ctrl, letter, _ in REPAIRS:
    n = data.count(ctrl)
    assert n > 0, "control byte %r not present -- nothing to repair" % ctrl
    data = data.replace(ctrl, letter)
    assert ctrl not in data, "control byte %r survived replacement" % ctrl
    print("replaced %d occurrence(s) of %r with %r" % (n, ctrl, letter))

assert data != before, "no change made"
assert len(data) == len(before), "length changed: %d -> %d" % (len(before), len(data))

# every repaired word must now be a real word that appears in the file
for _, _, anchor in REPAIRS:
    assert anchor in data, "expected repaired anchor %r not found" % anchor
    print("  anchor present: %r" % anchor)

# and no C0/DEL may remain anywhere in the file
import re

leftover = re.findall(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", data)
assert not leftover, "C0 bytes remain: %r" % leftover

# the fact table's pipe discipline must survive the edit
line = data.split(b"\n")[1311]
pipes = len(line.replace(b"\\|", b"").split(b"|")) - 1
print("repaired row unescaped pipe count: %d" % pipes)
assert pipes == 5, "row now has %d unescaped pipes, need 5" % pipes

with io.open(P, "wb") as fh:
    fh.write(data)

print("OK -- %s repaired, %d bytes unchanged in length" % (P, len(data)))

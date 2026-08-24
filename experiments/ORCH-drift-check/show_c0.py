"""Show the exact bytes around the C0 hits in M105b so the repair is anchored, not guessed."""
import io

P = "docs/research/M105b-exposure-ship.md"
with io.open(P, "rb") as fh:
    data = fh.read()

lines = data.split(b"\n")
ln = 1312
raw = lines[ln - 1]
print("line %d length %d bytes" % (ln, len(raw)))
print("repr:")
print(repr(raw))
print()
print("control positions:")
for i, b in enumerate(raw):
    if b < 0x20 and b not in (0x09,) or b == 0x7F:
        lo = max(0, i - 28)
        hi = min(len(raw), i + 28)
        print("  idx %4d  0x%02X  context: %s" % (i, b, repr(raw[lo:hi])))

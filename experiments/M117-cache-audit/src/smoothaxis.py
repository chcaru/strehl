import sys, hashlib, pathlib, re
A = pathlib.Path(r"C:\Users\chris\AppData\Local\strehl\warpmaps\lavendar-cpl-47e596c1cc69bdfc.warpmap.txt")
B = pathlib.Path(r"C:\dev\strehl-out\M117\rerun\cache-private\lavendar-cpl-7a3c5ecc793d30ac.warpmap.txt")
for p in (A, B):
    if not p.exists():
        sys.exit("MISSING: %s" % p)
a, b = A.read_bytes(), B.read_bytes()
print("A in-window 11:51:27  %d bytes  sha256/16 %s" % (len(a), hashlib.sha256(a).hexdigest()[:16].upper()))
print("B HEAD re-solve       %d bytes  sha256/16 %s" % (len(b), hashlib.sha256(b).hexdigest()[:16].upper()))
print("WHOLE-FILE IDENTICAL: %s" % (a == b))

# placement rows are "<frame-index> placed <a_re> <a_im> <b_re> <b_im>"
ROW = re.compile(r"^\s*\d+\s+(placed|refused)\b")
def rows(raw):
    return [ln.split("#")[0].strip() for ln in raw.decode("utf-8").splitlines() if ROW.match(ln)]
ra, rb = rows(a), rows(b)
print("placement rows parsed: A=%d  B=%d" % (len(ra), len(rb)))
if len(ra) == 0 or len(rb) == 0:
    sys.exit("PROBE DISCONNECTED: parser matched 0 placement rows; a 0-vs-0 comparison proves nothing")
if len(ra) != len(rb):
    sys.exit("ROW COUNT MISMATCH: %d vs %d" % (len(ra), len(rb)))
diff = [i for i, (x, y) in enumerate(zip(ra, rb)) if x != y]
print("rows differing on f64 BIT PATTERNS: %d / %d" % (len(diff), len(ra)))

# negative control: the parser must be able to see a planted 1-ULP change
bits = ra[0].split()
mutated = list(ra); mutated[0] = " ".join(bits[:2] + ["%016x" % (int(bits[2], 16) ^ 1)] + bits[3:])
planted = sum(1 for x, y in zip(mutated, rb) if x != y)
if planted != 1:
    sys.exit("NEGATIVE CONTROL FAILED: planted 1-ULP flip produced %d diffs, expected 1" % planted)
print("negative control: a planted 1-ULP flip in row 0 is detected (1 diff) -- parser is live")
print("=> %d placements bit-identical: the 11:51 solve is unpoisoned on ALL axes" % len(ra))

"""Confirm the committed blob is the file that was actually measured.

Reads git blobs as BYTES via subprocess. Never `git show HEAD:path > tmp`:
on Windows the `>` redirect re-encodes the stream, so the comparison is
against a re-encoded copy rather than the blob.
"""
import hashlib
import re
import subprocess
import sys

PATHS = [
    "experiments/BUILD-GATE/src/negctl_s13.py",
    "experiments/BUILD-GATE/src/negctl_s15.py",
]

rev = sys.argv[1] if len(sys.argv) > 1 else "HEAD"
bad = 0
for p in PATHS:
    blob = subprocess.run(["git", "show", "%s:%s" % (rev, p)],
                          capture_output=True).stdout
    disk = open(p, "rb").read()
    # Compare with line endings normalised: git's autocrlf rewrites them on
    # checkout, so a raw byte compare would report a false mismatch.
    bn = blob.replace(b"\r\n", b"\n")
    dn = disk.replace(b"\r\n", b"\n")
    ok = bn == dn
    bad += 0 if ok else 1
    print("%-16s blob=%s disk=%s match=%s"
          % (p.split("/")[-1], hashlib.sha256(bn).hexdigest()[:16],
             hashlib.sha256(dn).hexdigest()[:16], ok))

print()
# Count only FLIPS table entries. The obvious substring '("control' also
# matches the three `startswith("control")` classification sites, so it read
# 6 for 3 declared arms -- a count satisfied by a duplicate elsewhere, which
# is the exact shape this repo keeps finding in its own instruments. Anchor
# on the table's four-space indent at line start, and require an EXACT
# count, so that adding or losing an arm is a failure rather than noise.
ENTRY = re.compile(r'^    \("(?P<name>[a-z0-9-]+)"', re.MULTILINE)
EXPECT = {"negctl_s13.py": (3, 4), "negctl_s15.py": (3, 16)}
for p in PATHS:
    b = subprocess.run(["git", "show", "%s:%s" % (rev, p)],
                       capture_output=True).stdout.decode("utf-8")
    names = [m.group("name") for m in ENTRY.finditer(b)]
    ctl = sum(1 for n in names if n.startswith("control"))
    real = len(names) - ctl
    part = "PARTITION BROKEN" in b
    infer = "control = (old == new)" in b
    base = p.split("/")[-1]
    want_c, want_r = EXPECT[base]
    ok = (ctl == want_c and real == want_r and part and not infer)
    print("%-16s controls=%d/%d  defects=%d/%d  partition=%s  "
          "old-inference-gone=%s  %s"
          % (base, ctl, want_c, real, want_r, part, not infer,
             "OK" if ok else "FAILED"))
    if not ok:
        bad += 1

print("\n%s" % ("BLOBCHECK OK" if bad == 0 else "BLOBCHECK FAILED (%d)" % bad))
sys.exit(0 if bad == 0 else 1)

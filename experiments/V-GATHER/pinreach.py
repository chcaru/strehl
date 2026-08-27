r"""WITHDRAWAL IN PLACE of this lane's build-identity audit, with the query that
produced it and the reason it missed.

WHAT I REPORTED (preserved verbatim, not deleted -- a withdrawal that erases the
original leaves the next reader unable to see the trap):

    "066A87AB...0437B is NOT FOUND. 78 distinct binaries across 160 paths."

WHAT IS TRUE. The build exists at
    C:\dev\strehl-out\V-REVIEW\bin\strehl-pinned.exe
and every count in that audit was drawn from a population less than half the real
one. Two independent defects, and I introduced the second while correcting the
first:

  1. LEXICAL. The question was physical -- does this build exist on this machine.
     The query was lexical -- is there a file named exactly "strehl.exe". Twenty-
     six other filenames carry strehl builds, including the one being searched for.

  2. SHAPE. Correcting (1) in Python, I used glob(..., recursive=True), which
     silently returns a smaller set than os.walk over the same root.

     I FIRST ASSERTED THE CAUSE WAS DIRECTORY REPARSE POINTS, and reported that
     upward, because 1,317 of them sit under C:\dev and it is a known Windows
     hazard. I never measured it. It is wrong. reachwhy.py classifies every path
     in the miss set and the cause is entirely different: glob's * and ** never
     match a path component that begins with a dot, so .cargo-target-defect\...
     is invisible to it while os.walk descends it normally. Junctions are not
     implicated at all -- glob descends those.

The rule, which is the only part worth carrying forward:

    "Not found" is a statement about the query until the query's reach is
    measured. An absence result needs its own positive control -- a decoy the
    query MUST return -- exactly as an empty text search does. Mine had none.

And the sharper form, since I made the same mistake twice more in one night while
correcting it: a mechanism that sounds right and matches a known hazard is still
an assertion. Measure which of your candidate causes is actually operating, or
you will build a control around a mechanism that never fires.
"""
import fnmatch
import glob as _glob
import hashlib
import os
import sys

ROOT = r"C:\dev"
TARGETS = {
    "15EA7346": "seals PINTEST and SHIP-V3 (pin 740e7056)",
    "44C2F2CD": "seals SHIP-V4 (pin 9b05d0b7)",
    "B50EABC1": "UNSEALED -- the mislabelled PIN-V3",
    "F663B703": "UNSEALED -- sits in this lane's own scratch directory",
    "066A87AB": "UNSEALED -- the build I reported NOT FOUND",
}


def walk_scan(root, pattern):
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if fnmatch.fnmatch(f.lower(), pattern):
                out.append(os.path.join(dirpath, f))
    return out


def glob_scan(root, pattern):
    return [p for p in _glob.glob(os.path.join(root, "**", pattern), recursive=True)
            if os.path.isfile(p)]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else ROOT
    print("REACH OF FOUR QUERIES OVER %s" % root)
    print("%-46s %8s %10s" % ("query", "paths", "distinct"))
    print("-" * 68)
    seen = {}
    for label, fn, pat in (
            ("os.walk   name == strehl.exe   (the audit)", walk_scan, "strehl.exe"),
            ("glob **   name == strehl.exe", glob_scan, "strehl.exe"),
            ("glob **   name matches strehl*.exe", glob_scan, "strehl*.exe"),
            ("os.walk   name matches strehl*.exe (correct)", walk_scan, "strehl*.exe")):
        paths = fn(root, pat)
        hs = {}
        for p in paths:
            try:
                hs.setdefault(sha(p), []).append(p)
            except OSError:
                pass
        print("%-46s %8d %10d" % (label, len(paths), len(hs)))
        seen[label] = hs

    full = seen["os.walk   name matches strehl*.exe (correct)"]
    narrow = seen["os.walk   name == strehl.exe   (the audit)"]
    print("\nBUILDS INVISIBLE TO THE AUDIT'S QUERY: %d of %d distinct."
          % (len(set(full) - set(narrow)), len(full)))

    print("\nTARGETED HASHES -- each stated FOUND or NOT FOUND with its path.")
    for pre, note in sorted(TARGETS.items()):
        hit = [h for h in full if h.startswith(pre)]
        if not hit:
            print("  %s  NOT FOUND   %s" % (pre, note))
            continue
        ps = full[hit[0]]
        print("  %s  FOUND (%d path%s)  %s" % (pre, len(ps), "" if len(ps) == 1 else "s", note))
        for p in sorted(ps)[:4]:
            print("      %s" % p)

    sizes = {}
    for h, ps in full.items():
        try:
            sizes.setdefault(os.path.getsize(ps[0]), set()).add(h)
        except OSError:
            pass
    print("\nSIZE COLLISIONS -- distinct builds sharing one byte count.")
    print("Size and timestamp identify nothing; only the hash does.")
    for sz, hs in sorted(sizes.items(), key=lambda kv: -len(kv[1])):
        if len(hs) < 2:
            continue
        print("  %10d bytes : %d distinct builds  %s"
              % (sz, len(hs), ", ".join(sorted(h[:8] for h in hs))))

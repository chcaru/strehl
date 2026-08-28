"""Bank the V-H2H2 ARW subset manifests, identifying each subset's true source.

V-H2H2 holds 1,375 .ARW files (48.7 GB) that are COPIES of frames from the
read-only originals under D:\\personal\\macro, arranged into N-scaling ladders
(n18/n37/n74/n149, a/b arms), even/odd halves, and an nscale set. The pixels are
not unique. The only irreplaceable thing is the SELECTION: which source frames
went into which subset, and in what order.

This writes that selection out as text, and identifies each subset's source
subject by requiring EVERY filename in the subset to exist in that source
directory with a byte-identical size. That is a real test, not a name guess: an
earlier probe of mine matched `DSC00001.ARW` against the first such file
anywhere under the source root and reported 40/40 size mismatches, because that
filename exists in every subject folder. Matching on the whole set at once
cannot make that error.

Read-only. Writes one text file. Deletes nothing.
"""
import io
import os
import sys

SCRATCH = r"C:\dev\strehl-out\V-H2H2"
SOURCE = r"D:\personal\macro"
OUT = os.path.join(
    r"C:\dev\blog\death-of-software\projects\strehl",
    "experiments", "ORCH-drift-check", "purged", "V-H2H2-arw-manifest.txt",
)


def source_index():
    """subject -> {filename: size} for every source subject."""
    idx = {}
    for sub in sorted(os.listdir(SOURCE)):
        d = os.path.join(SOURCE, sub)
        if not os.path.isdir(d):
            continue
        files = {}
        try:
            for f in os.listdir(d):
                if f.lower().endswith(".arw"):
                    files[f] = os.path.getsize(os.path.join(d, f))
        except OSError:
            continue
        if files:
            idx[sub] = files
    return idx


def main() -> int:
    if not os.path.isdir(SCRATCH):
        raise SystemExit("FATAL: %s not found" % SCRATCH)

    src = source_index()
    if not src:
        raise SystemExit("FATAL: no source subjects found under %s" % SOURCE)

    subsets = {}
    for root, _dirs, files in os.walk(SCRATCH):
        arw = sorted(f for f in files if f.lower().endswith(".arw"))
        if arw:
            subsets[os.path.relpath(root, SCRATCH)] = [
                (f, os.path.getsize(os.path.join(root, f))) for f in arw
            ]
    if not subsets:
        raise SystemExit("FATAL: found 0 ARW subsets -- refusing to write an empty manifest")

    L = []
    L.append("=== V-H2H2 ARW SUBSET MANIFEST")
    L.append("scratch : %s" % SCRATCH)
    L.append("source  : %s  (READ-ONLY, protected)" % SOURCE)
    L.append("")
    L.append("These .ARW files are COPIES of frames from the protected originals. The")
    L.append("pixels are not unique and are not banked. What IS banked is the selection:")
    L.append("for each subset, the exact ordered list of source filenames. To rebuild a")
    L.append("subset, copy those names from the identified source subject.")
    L.append("")
    L.append("A subset's source is only named below when EVERY filename in it exists in")
    L.append("that subject with a byte-identical size. Anything unresolved says so.")
    L.append("")

    total_bytes = 0
    resolved = 0
    unresolved = 0

    for name in sorted(subsets):
        entries = subsets[name]
        nbytes = sum(sz for _f, sz in entries)
        total_bytes += nbytes

        hits = []
        for subj, files in src.items():
            if all(f in files and files[f] == sz for f, sz in entries):
                hits.append(subj)

        if len(hits) == 1:
            verdict = "source subject : %s  (all %d names+sizes match)" % (hits[0], len(entries))
            resolved += 1
        elif len(hits) > 1:
            verdict = "AMBIGUOUS : matches %d subjects -> %s" % (len(hits), ", ".join(sorted(hits)))
            resolved += 1
        else:
            verdict = "UNRESOLVED : no source subject contains all %d names at matching sizes" % len(entries)
            unresolved += 1

        L.append("--- SUBSET %s" % name)
        L.append("  frames : %d   bytes : %d (%.2f GB)" % (len(entries), nbytes, nbytes / 1073741824.0))
        L.append("  %s" % verdict)
        L.append("  files  : %s" % " ".join(f for f, _sz in entries))
        L.append("")

    L.append("subsets : %d   resolved : %d   unresolved : %d" % (len(subsets), resolved, unresolved))
    L.append("total   : %d bytes (%.2f GB)" % (total_bytes, total_bytes / 1073741824.0))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(L))

    back = io.open(OUT, encoding="utf-8").read()
    if "--- SUBSET" not in back:
        raise SystemExit("FATAL: manifest re-read has no subsets")

    print("wrote %s" % OUT)
    print("  subsets %d   resolved %d   unresolved %d   total %.2f GB"
          % (len(subsets), resolved, unresolved, total_bytes / 1073741824.0))
    if unresolved:
        print("  WARNING: %d subset(s) UNRESOLVED -- do not delete those without a closer look" % unresolved)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Derive the pin manifest from the corpora's own seals. Nothing here is by hand.

WHY THIS IS DERIVED AND NOT WRITTEN DOWN. A hand-maintained list of "which
binary is which pin" decays the moment someone rebuilds, and it decays SILENTLY
because nothing compares it to reality. Every entry below is computed at call
time from two physical facts:

  the SHA256 of a binary on disk, and
  the content of the <subject>.tiff.ok seals the corpus carries.

A manifest computed this way cannot disagree with the seals, because it IS the
seals. The cost is that it must be recomputed rather than read, which is the
right trade for a fact that is only useful when it is current.

THE HAZARD THIS EXISTS TO REMOVE. Three binaries on this machine share the size
9,568,768 and two of them are the shipping pins. A third, at a path literally
named PIN-V3, is sealed by nothing. Size, timestamp and directory name identify
nothing; only the hash does.
"""
import argparse
import glob
import hashlib
import os

OUT_ROOT = r"C:\dev\strehl-out"
BARRED = {"SHIP-V2"}     # barred from scoring by standing instruction

PIN_GLOBS = [
    r"acceptance-pins\*\target\release\strehl.exe",
    r"*\strehl.exe",
    r"*\bin\strehl.exe",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def corpora(root=None):
    """corpus name -> {seal hash -> count}. Read from the .ok files, only."""
    root = root or os.path.join(OUT_ROOT, "acceptance")
    out = {}
    if not os.path.isdir(root):
        return out
    for d in sorted(os.listdir(root)):
        p = os.path.join(root, d)
        if not os.path.isdir(p):
            continue
        seals = {}
        for ok in sorted(glob.glob(os.path.join(p, "*.ok"))):
            try:
                v = open(ok, "r", encoding="utf-8", errors="replace").read().strip().upper()
            except OSError:
                continue
            seals[v] = seals.get(v, 0) + 1
        out[d] = seals
    return out


def corpus_seal(seals):
    """The one hash a corpus attests, or a reason it attests none.

    A corpus whose seals DISAGREE is not a corpus with a majority pin. It is a
    corpus of mixed provenance and it cannot certify anything, so this returns
    no seal rather than the most common one.
    """
    if not seals:
        return None, "carries no .ok seals"
    if len(seals) > 1:
        parts = ", ".join("%s x%d" % (h[:8], n) for h, n in sorted(seals.items()))
        return None, "seals DISAGREE (%s) -- mixed provenance" % parts
    (h, n), = seals.items()
    return h, "%d seals agree" % n


def pins(root=None):
    """Every candidate binary, hashed. Deduplicated by real path."""
    root = root or OUT_ROOT
    seen, out = set(), []
    for g in PIN_GLOBS:
        for p in glob.glob(os.path.join(root, g)):
            rp = os.path.normcase(os.path.realpath(p))
            if rp in seen or not os.path.isfile(p):
                continue
            seen.add(rp)
            out.append((p, sha256(p), os.path.getsize(p)))
    return sorted(out, key=lambda t: t[0])


def manifest(root=None, acc_root=None):
    cs = corpora(acc_root)
    seal_to_corpus = {}
    for name, seals in cs.items():
        h, _ = corpus_seal(seals)
        if h:
            seal_to_corpus.setdefault(h, []).append(name)
    rows = []
    for path, h, size in pins(root):
        rows.append((path, h, size, sorted(seal_to_corpus.get(h, []))))
    return cs, rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="scan root for binaries")
    ap.add_argument("--acceptance", default=None, help="root holding corpus dirs")
    a = ap.parse_args()
    cs, rows = manifest(a.root, a.acceptance)

    print("CORPORA  (derived from *.ok seals)")
    print("%-12s %6s  %-64s %s" % ("corpus", "seals", "attests", "note"))
    print("-" * 110)
    for name in sorted(cs):
        h, why = corpus_seal(cs[name])
        bar = "  [BARRED FROM SCORING]" if name in BARRED else ""
        print("%-12s %6d  %-64s %s%s" % (name, sum(cs[name].values()), h or "(none)", why, bar))

    print("\nPINS  (every candidate binary, hashed)")
    print("%-9s %10s  %-22s %s" % ("hash", "bytes", "sealed by", "path"))
    print("-" * 110)
    for path, h, size, corps in rows:
        print("%-9s %10d  %-22s %s"
              % (h[:8], size, ", ".join(corps) if corps else "-- NOTHING --",
                 os.path.relpath(path, OUT_ROOT)))

    unsealed = [r for r in rows if not r[3]]
    bysize = {}
    for path, h, size, _ in rows:
        bysize.setdefault(size, set()).add(h[:8])
    collide = {s: v for s, v in bysize.items() if len(v) > 1}
    print("\n%d binaries, %d sealed by some corpus, %d sealed by nothing."
          % (len(rows), len(rows) - len(unsealed), len(unsealed)))
    for size, hs in sorted(collide.items()):
        print("SIZE COLLISION: %d bytes is shared by %d DIFFERENT builds (%s)."
              % (size, len(hs), ", ".join(sorted(hs))))

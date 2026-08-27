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

TWO REACH DEFECTS WERE FOUND IN THIS FILE'S FIRST VERSION AND BOTH ARE FIXED
HERE. They are recorded rather than quietly repaired, because each is a whole
class and the second only appeared while correcting the first.

  LEXICAL.  The scan matched the exact name `strehl.exe`. Twenty-six other
  filenames -- strehl-pinned.exe, strehl-base.exe, strehl-pre.exe, strehl-cover
  .exe among them -- were invisible to it, including the pinned binary of
  another lane. A physical question ("does this build exist") was asked with a
  lexical query ("is anything named exactly this").

  TOPOLOGICAL.  The correction used glob(**), which reaches 177 paths where
  os.walk and Get-ChildItem -Recurse both reach 305. A query can miss by name
  and it can miss by shape, and fixing one does not fix the other.

  RETRACTED IN PLACE -- the stated CAUSE of the topological miss was wrong, and
  it was wrong in the same way as the miss itself. I wrote, and reported upward,
  that glob does not descend directory reparse points, because 1,317 of them sit
  under C:\\dev and it is a real Windows hazard. I never measured it.
  reachwhy.py classifies every path in the miss set:

      dot-prefixed component in path : 127
      under a directory reparse point:   0
      neither                        :   0
      sum                            : 127   (the entire miss set)

  The cause is that glob's * and ** never match a component beginning with a
  dot, so .cargo-target-defect\\release\\deps\\strehl.exe is invisible to it.
  Junctions are not implicated; glob descends those, as pincommission.py's
  REACH-junction arm records. A plausible mechanism that matches a known hazard
  is still an assertion, and a control built on the wrong mechanism can never
  fire.

Reach is therefore MEASURED and printed, never assumed, and pincommission.py
plants decoys of both kinds that the scan is required to return.
"""
import argparse
import fnmatch
import glob
import hashlib
import os

OUT_ROOT = r"C:\dev\strehl-out"
BARRED = {"SHIP-V2"}     # barred from scoring by standing instruction
PIN_PATTERN = "strehl*.exe"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


def find_binaries(root, pattern=PIN_PATTERN):
    """os.walk, not glob(**): glob's ** never matches a dotted component."""
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if fnmatch.fnmatch(f.lower(), pattern):
                out.append(os.path.join(dirpath, f))
    return out


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


def pins(root=None, pattern=PIN_PATTERN):
    """Every candidate binary, hashed. Deduplicated by real path."""
    root = root or OUT_ROOT
    seen, out = set(), []
    for p in find_binaries(root, pattern):
        rp = os.path.normcase(os.path.realpath(p))
        if rp in seen or not os.path.isfile(p):
            continue
        seen.add(rp)
        try:
            out.append((p, sha256(p), os.path.getsize(p)))
        except OSError:
            continue
    return sorted(out, key=lambda t: t[0])


def manifest(root=None, acc_root=None, pattern=PIN_PATTERN):
    cs = corpora(acc_root)
    seal_to_corpus = {}
    for name, seals in cs.items():
        h, _ = corpus_seal(seals)
        if h:
            seal_to_corpus.setdefault(h, []).append(name)
    rows = [(path, h, size, sorted(seal_to_corpus.get(h, [])))
            for path, h, size in pins(root, pattern)]
    return cs, rows


_ORIG_CORPORA = corpora


def corpora(root=None):
    """Pass-through by default. pinnegctl.py's FROZEN sabotage rebinds this."""
    return _ORIG_CORPORA(root)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="scan root for binaries")
    ap.add_argument("--acceptance", default=None, help="root holding corpus dirs")
    ap.add_argument("--pattern", default=PIN_PATTERN)
    a = ap.parse_args()
    root = a.root or OUT_ROOT
    cs, rows = manifest(root, a.acceptance, a.pattern)

    print("REACH  root %s   pattern %r   os.walk (sees dotted dirs)"
          % (root, a.pattern))
    narrow = [p for p in find_binaries(root, "strehl.exe")]
    print("  %d binaries matched; the exact-name query would have matched %d, "
          "missing %d." % (len(rows), len(narrow), len(rows) - len(narrow)))

    print("\nCORPORA  (derived from *.ok seals)")
    print("%-12s %6s  %-64s %s" % ("corpus", "seals", "attests", "note"))
    print("-" * 112)
    for name in sorted(cs):
        h, why = corpus_seal(cs[name])
        bar = "  [BARRED FROM SCORING]" if name in BARRED else ""
        print("%-12s %6d  %-64s %s%s" % (name, sum(cs[name].values()), h or "(none)", why, bar))

    print("\nPINS  (every candidate binary, hashed)")
    print("%-9s %10s  %-22s %s" % ("hash", "bytes", "sealed by", "path"))
    print("-" * 112)
    for path, h, size, corps in rows:
        print("%-9s %10d  %-22s %s"
              % (h[:8], size, ", ".join(corps) if corps else "-- NOTHING --",
                 os.path.relpath(path, root)))

    unsealed = [r for r in rows if not r[3]]
    bysize = {}
    for path, h, size, _ in rows:
        bysize.setdefault(size, set()).add(h[:8])
    print("\n%d binaries, %d sealed by some corpus, %d sealed by nothing."
          % (len(rows), len(rows) - len(unsealed), len(unsealed)))
    for size, hs in sorted(bysize.items()):
        if len(hs) > 1:
            print("SIZE COLLISION: %d bytes is shared by %d DIFFERENT builds (%s)."
                  % (size, len(hs), ", ".join(sorted(hs))))

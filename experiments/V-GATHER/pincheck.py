"""Refuse to let a binary be compared against a corpus that does not seal it.

    python pincheck.py --exe <path> --corpus SHIP-V4

Exit 0 only when the binary's SHA256 equals the hash every one of that corpus's
*.ok seals carries. Anything else is a REFUSAL with a non-zero exit, not a
warning, because a warning printed into a 400-line render log is a warning
nobody reads and this project has already shipped two numbers off the wrong pin.

It refuses, and says why, when:
  the binary does not exist, or the corpus does not exist
  the corpus carries no seals, so it attests nothing
  the corpus's seals DISAGREE, so it is of mixed provenance
  the corpus is barred from scoring by standing instruction
  the hash simply differs -- and then it names which corpus, IF ANY, does seal
      this binary, because "right build, wrong corpus" is the exact mistake that
      put a wrong pin into circulation and the answer is one line away

EXIT CODES.  0 match   2 refusal   3 asset or usage error
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pinmanifest import BARRED, corpora, corpus_seal, sha256

OK, REFUSE, ERR = 0, 2, 3


def refuse(msg):
    print("REFUSED: " + msg)
    return REFUSE


def check(exe, corpus, acc_root=None):
    if not os.path.isfile(exe):
        print("ERROR: no such binary: %s" % exe)
        return ERR
    cs = corpora(acc_root)
    if corpus not in cs:
        print("ERROR: no such corpus %r. known: %s"
              % (corpus, ", ".join(sorted(cs)) or "(none)"))
        return ERR
    h = sha256(exe)
    print("binary %s\n  sha256 %s" % (exe, h))
    if corpus in BARRED:
        return refuse("%s is barred from scoring by standing instruction; no "
                      "comparison against it is valid regardless of the binary."
                      % corpus)
    seal, why = corpus_seal(cs[corpus])
    if seal is None:
        return refuse("%s %s, so it cannot certify any binary." % (corpus, why))
    print("corpus %s\n  seal   %s  (%s)" % (corpus, seal, why))
    if h == seal:
        print("\nMATCH: this binary produced %s. The comparison is on one gauge."
              % corpus)
        return OK
    others = [n for n, s in cs.items()
              if corpus_seal(s)[0] == h and n not in BARRED]
    tail = ("  This binary IS the pin for: %s -- you have the right build and "
            "the wrong corpus." % ", ".join(sorted(others))) if others else \
           ("  This binary is sealed by NO corpus on this machine. Its renders "
            "reproduce no shipping pipeline and may not be quoted as one.")
    return refuse("hash does not match %s's seal.\n  binary %s\n  seal   %s\n%s"
                  % (corpus, h, seal, tail))


def identify(exe, acc_root=None):
    if not os.path.isfile(exe):
        print("ERROR: no such binary: %s" % exe)
        return ERR
    h = sha256(exe)
    cs = corpora(acc_root)
    hits = sorted(n for n, s in cs.items() if corpus_seal(s)[0] == h)
    print("binary %s\n  sha256 %s\n  bytes  %d" % (exe, h, os.path.getsize(exe)))
    if hits:
        print("  sealed by: %s" % ", ".join(hits))
        return OK
    print("  sealed by: NOTHING. Size and path name identify no build; only this "
          "hash does.")
    return REFUSE


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", required=True)
    ap.add_argument("--corpus")
    ap.add_argument("--identify", action="store_true")
    ap.add_argument("--acceptance", default=None)
    a = ap.parse_args()
    if a.identify or not a.corpus:
        sys.exit(identify(a.exe, a.acceptance))
    sys.exit(check(a.exe, a.corpus, a.acceptance))

"""One-off: renumber this milestone from M93 to M95.

The orchestrator dispatched this milestone as M93, but M93 was already taken by
another live agent (docs/research/M93-election-gate.md, commit 9a17d64). The
renumber has to leave THAT agent's identifiers alone, and it also has to leave
alone the on-disk scratch directory C:\\dev\\strehl-out\\M93-out, because the
orchestrator's own experiments/ORCH-drift-check/m93pair.py reads it by absolute
path and renaming it would break a live script.

So this is not a blind search-and-replace. It is an ordered token map where
some tokens map to themselves. Regex alternation is first-match-wins at a given
position, so the longest / most specific tokens are listed first.

Every substitution is printed with its line so the diff can be audited.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(ROOT))
REPORT = os.path.join(REPO, "docs", "research", "M95-merge-vs-frame-sharpness.md")

# (token, replacement). Identity mapping == protected.
TOKENS = [
    # --- mine, must be listed before the protected M93-election prefix ---
    ("M93-election-map", "M95-election-map"),
    # --- the OTHER agent's milestone: protected ---
    ("M93-election-gate", "M93-election-gate"),
    ("M93-election", "M93-election"),
    ("m93-election", "m93-election"),
    # --- orchestrator's script and the scratch dir it reads: protected ---
    ("m93pair", "m93pair"),
    ("M93-out", "M93-out"),
    ("M93-frames", "M93-frames"),
    ("m93_crops", "m93_crops"),
    ("m93_elected", "m93_elected"),
    ("m93_maxdetail", "m93_maxdetail"),
    # --- mine ---
    ("M93-merged-vs-single-frame", "M95-merged-vs-single-frame"),
    ("M93-merge-vs-frame", "M95-merge-vs-frame"),
    ("M93-pin", "M95-pin"),
    ("m93lib", "m95lib"),
    ("target-m93", "target-m95"),
    ("M93", "M95"),
    ("m93", "m95"),
]

PAT = re.compile("|".join(re.escape(t) for t, _ in TOKENS))
MAP = dict(TOKENS)


def files():
    out = [REPORT]
    for dirpath, _dirnames, filenames in os.walk(ROOT):
        if "__pycache__" in dirpath:
            continue
        for fn in sorted(filenames):
            if fn == os.path.basename(__file__):
                continue
            if os.path.splitext(fn)[1].lower() in (".py", ".md", ".json", ".txt"):
                out.append(os.path.join(dirpath, fn))
    return out


def main():
    apply = "--apply" in sys.argv
    n_files = 0
    n_subs = 0
    n_protected = 0
    for path in files():
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        if not PAT.search(src):
            continue
        changed_lines = []
        subs_here = 0
        prot_here = 0

        def repl(m):
            nonlocal subs_here, prot_here
            tok = m.group(0)
            new = MAP[tok]
            if new == tok:
                prot_here += 1
            else:
                subs_here += 1
            return new

        dst = PAT.sub(repl, src)
        if subs_here:
            for a, b in zip(src.splitlines(), dst.splitlines()):
                if a != b:
                    changed_lines.append((a.strip(), b.strip()))
        rel = os.path.relpath(path, REPO)
        print("%-62s subs=%-4d protected=%-3d" % (rel, subs_here, prot_here))
        for a, b in changed_lines[:400]:
            print("    - %s" % a[:150])
            print("    + %s" % b[:150])
        if apply and dst != src:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(dst)
        n_files += 1
        n_subs += subs_here
        n_protected += prot_here
    print("")
    print("files touched      : %d" % n_files)
    print("substitutions      : %d" % n_subs)
    print("protected untouched: %d" % n_protected)
    print("mode               : %s" % ("APPLIED" if apply else "DRY RUN"))


if __name__ == "__main__":
    main()

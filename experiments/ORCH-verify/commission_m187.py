#!/usr/bin/env python3
"""Commission the M176/M187 route-correction pins added to v2954.py.

WHAT IS BEING GUARDED. STATUS carried two overclaims that lane M176 identified
and lane M187 independently re-derived from primary sources and upheld
(`docs/research/M187-m176-adjudication.md`, committed `948e8720`):

  * Route 1 -- "Every hash pin in this repository is therefore conditioned on a
    worker count" swept in pins that stop before the reduction boundary. M8-R
    and M165 are pre-reduction and were never conditioned.
  * Route 2 -- "Landing it ... makes every hash pin in the repository
    unconditional" treated a code landing as if it settled the evidential status
    of measurements taken before it. It does not; historical pre-D9 hashes are
    not repaired retroactively.

Both original sentences are STRUCK, not deleted, per this file's own rule at
`STATUS:5301-5303`: a silently removed false claim leaves no trace that anyone
was misled by it.

WHY THE PINS COME IN PAIRS. A presence check on the corrected text alone would
stay GREEN if someone un-struck the original and left both standing -- the file
would then assert a claim and its correction simultaneously, which is exactly
the defect that produced STATUS 2.9.80. So each correction is pinned twice: once
on the new statement, and once on the strikethrough marker that withdraws the
old one. Arms 2 and 5 below plant precisely that defect by REMOVING the
withdrawal.

ANCHOR LENGTH IS LOAD-BEARING. v2954's collapse() does not strip '>' and load()
does not unquote, so a needle spanning a line break inside a blockquote
collapses with a stray '> ' in the middle and can never match. Both STATUS-side
corrections live in blockquotes. The first run of these pins went RED on exactly
the two needles that spanned lines, and GREEN on the three that did not.

PRE-FLIGHT IS PART OF THE HARNESS. A mutation is a literal replace on raw bytes
while a check reads collapsed text, so an anchor can be findable by the check and
unreachable by the mutation. Every arm target must occur EXACTLY ONCE in the raw
file before any arm runs; missing or duplicated is a hard error, not a pass.

v2954 pins GIT_ROOT to the real repository independently of ROOT, so this must
invoke the REAL v2954.py with a TEMP root -- never a TEMP copy of it, whose
HEAD: blob reads would all fail.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
V = REAL / "experiments" / "ORCH-verify" / "v2954.py"

STATUS_REL = "docs/STATUS.md"
M187_REL = "docs/research/M187-m176-adjudication.md"

# (pin label, relative path, exact raw text, replacement)
ARMS = [
    # ---- Route 1 ----
    ("m187 route1 fix", STATUS_REL,
     "Only Pyramid final-render byte/hash claims from pre-D9",
     "Only Pyramid final-render byte/hash claims from post-D9"),
    # The defect here is REMOVING A WITHDRAWAL, so the mutation un-strikes the
    # original overclaim and leaves the correction standing beside it.
    ("m187 route1 struck", STATUS_REL,
     "~~**Every hash pin in this repository is therefore",
     "**Every hash pin in this repository is therefore"),
    ("m187 route1 boundary", STATUS_REL,
     "M8-R and M165 stop *before*",
     "M8-R and M165 stop *after*"),

    # ---- Route 2 ----
    ("m187 route2 fix", STATUS_REL,
     "hashes are not repaired retroactively",
     "hashes are repaired retroactively"),
    ("m187 route2 struck", STATUS_REL,
     "~~Landing it", "Landing it"),

    # ---- cross-document: the correction claims to be M187's ----
    ("m187 artifact route1", M187_REL,
     "M8-R and M165 stop before that boundary",
     "M8-R and M165 stop after that boundary"),
    ("m187 artifact route2", M187_REL,
     "Historical pre-D9 hashes are not repaired retroactively",
     "Historical pre-D9 hashes are repaired retroactively"),
]

# Must change nothing. Without it, a harness that reddened on every input would
# score a perfect 7/7 and look identical to a working one.
INERT = (STATUS_REL,
         "The error was treating a code landing as if it",
         "The mistake was treating a code landing as if it")


def run(root):
    """Return (m187 reds, green, all reds) from the REAL v2954 under `root`."""
    p = subprocess.run([sys.executable, str(V), str(root)],
                       capture_output=True, text=True)
    reds, all_reds = set(), set()
    for line in p.stdout.splitlines():
        m = re.match(r"^(?:XFAIL|RED)\s+(.+?)\s{2,}", line)
        if m:
            lab = m.group(1).strip()
            all_reds.add(lab)
            if lab.startswith("m187 "):
                reds.add(lab)
    return reds, "VERDICT: GREEN" in p.stdout, all_reds


def apply_mutation(path, old, new):
    body = path.read_text(encoding="utf-8", errors="replace")
    if old not in body:
        raise SystemExit(
            "FATAL: mutation target not found in %s\n  looking for: %r\n"
            "A mutation that does not land is a harness failure, not a pass."
            % (path, old))
    if old == new:
        raise SystemExit("FATAL: no-op mutation for %s" % path)
    mutated = body.replace(old, new, 1)
    if mutated == body:
        raise SystemExit("FATAL: replace() changed nothing in %s" % path)
    path.write_text(mutated, encoding="utf-8")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="orch-m187-"))
    try:
        shutil.copytree(REAL / "docs", tmp / "docs")
        (tmp / "experiments").mkdir(parents=True, exist_ok=True)
        for sub in ("M-PHASE0-PHASE", "M134-kernel-frontier",
                    "M152-site-census", "M175-fork-arm", "M172-worker-memory",
                    "M136-m8o-bar", "M163-m10-uncertainty", "ORCH-verify"):
            shutil.copytree(REAL / "experiments" / sub,
                            tmp / "experiments" / sub)
        for rel in ("crates/strehl-cli/src/align_cmd.rs",
                    "crates/strehl-core/src/restore.rs"):
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REAL / rel, dst)

        bad = []
        for label, rel, old, _new in ARMS + [("INERT", INERT[0], INERT[1], "")]:
            n = (tmp / rel).read_text(encoding="utf-8",
                                      errors="replace").count(old)
            if n != 1:
                bad.append("%-24s occurs %d times in %s: %r"
                           % (label, n, rel, old))
        if bad:
            print("FATAL: arm targets are not raw-unique. A missing target "
                  "cannot mutate; a duplicated one leaves a copy that "
                  "satisfies the pin.")
            for b in bad:
                print("  " + b)
            raise SystemExit(2)
        print("pre-flight: all %d arm targets are raw-unique" % (len(ARMS) + 1))

        reds, green, all_reds = run(tmp)
        if not green or reds:
            raise SystemExit(
                "FATAL: TEMP baseline is not GREEN.\n  m187 reds: %s\n"
                "  all reds: %s" % (sorted(reds), sorted(all_reds)))
        print("TEMP baseline VERDICT: GREEN, no m187 reds")

        caught = missed = dup = 0
        for label, rel, old, new in ARMS:
            target = tmp / rel
            original = target.read_text(encoding="utf-8", errors="replace")
            apply_mutation(target, old, new)
            reds, _green, _all = run(tmp)
            target.write_text(original, encoding="utf-8")

            if reds == {label}:
                print("CAUGHT    %s" % label)
                caught += 1
            elif not reds:
                print("MISSED    %s  <-- DECORATIVE: defect planted, pin silent"
                      % label)
                missed += 1
            else:
                print("DUPLICATE %s  <-- reddened %s" % (label, sorted(reds)))
                dup += 1

        rel, old, new = INERT
        target = tmp / rel
        original = target.read_text(encoding="utf-8", errors="replace")
        apply_mutation(target, old, new)
        inert_reds, _g, _a = run(tmp)
        target.write_text(original, encoding="utf-8")
        inert_ok = not inert_reds
        print("INERT     %s" % ("held (no pin reddened)" if inert_ok
                                else "FAILED, reddened %s" % sorted(inert_reds)))

        post_reds, post_green, _ = run(tmp)
        restored = post_green and not post_reds
        print("post-restore TEMP: %s" % ("GREEN" if restored else "RED"))

        live_reds, live_green, _ = run(REAL)
        live_ok = live_green and not live_reds
        print("live tree: %s" % ("GREEN" if live_ok else "RED"))

        print()
        print("ARMS %d / CAUGHT %d / MISSED %d / DUPLICATE %d"
              % (len(ARMS), caught, missed, dup))
        ok = (missed == 0 and dup == 0 and inert_ok and restored and live_ok)
        print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
        sys.exit(0 if ok else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()

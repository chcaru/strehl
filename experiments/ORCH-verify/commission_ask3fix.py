#!/usr/bin/env python3
"""Commission the four Ask 3 correction pins added to vowner0906.py.

vowner0906 resolves its ROOT from __file__ rather than argv, so a TEMP-root run
is not available here. This mutates the LIVE owner sheet, runs the verifier, and
restores from an in-memory copy taken before the first mutation -- never via
`git checkout --`, which reverts to HEAD and would destroy the uncommitted
correction this is commissioning.

The restore is verified by SHA-256 against the pre-mutation bytes after every
arm, and again at the end. If any restore fails the script says so loudly rather
than exiting quietly, because a half-restored owner sheet is worse than a failed
commissioning.
"""

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHEET = ROOT / "docs" / "OWNER-ACTIONS.md"
V = ROOT / "experiments" / "ORCH-verify" / "vowner0906.py"

ARMS = [
    # Presence pins: break the claim, the pin must go RED.
    ("owner d not sufficient",
     "is *necessary* for eight axes and *sufficient* for none",
     "is *necessary* for eight axes and *sufficient* for all"),
    ("owner d never alone",
     "No axis anywhere on the board has `(d)` as its only blocker.",
     "Several axes on the board have `(d)` as their only blocker."),
    ("owner b is the free half",
     "What actually stands between your `$289` and a moving scoreboard is free",
     "What actually stands between your `$289` and a moving scoreboard is costly"),
    # Absence pin: restoring the WITHDRAWN wording must go RED. Without this arm
    # the correction could be silently reverted alongside its own correction.
    ("owner drops only-unblocker",
     "*Necessary for eight axes, sufficient for none.",
     "*Necessary either way, and the only thing on the board that unblocks an axis. Sufficient for none."),
]

INERT = ("needs no capture and no licence",
         "needs no capture and no license")


def run():
    p = subprocess.run([sys.executable, str(V)], capture_output=True, text=True)
    reds = set()
    for line in p.stdout.splitlines():
        m = re.match(r"^RED\s+\S+\s+(.+?)(?:\s{2,}|$)", line)
        if m:
            reds.add(m.group(1).strip())
        for lab, _o, _n in ARMS:
            if re.search(r"^RED\s+\S+\s+" + re.escape(lab) + r"(?:\s|$)", line):
                reds.add(lab)
    return reds, "VERDICT: GREEN" in p.stdout


def main():
    original = SHEET.read_bytes()
    base = hashlib.sha256(original).hexdigest()
    print("pre-mutation sheet sha256 %s (%d bytes)" % (base[:16], len(original)))

    text = original.decode("utf-8")
    for lab, old, _new in ARMS + [("INERT", INERT[0], "")]:
        n = text.count(old)
        if n != 1:
            sys.exit("FATAL: %r occurs %d times, expected 1 (arm %s)"
                     % (old[:50], n, lab))
    print("pre-flight: all %d arm targets raw-unique" % (len(ARMS) + 1))

    reds, green = run()
    if not green or reds:
        sys.exit("FATAL: baseline not GREEN. reds=%s" % sorted(reds))
    print("baseline VERDICT: GREEN, no arm reds")

    caught = missed = dup = 0
    try:
        for lab, old, new in ARMS:
            SHEET.write_text(text.replace(old, new, 1), encoding="utf-8")
            reds, _ = run()
            SHEET.write_bytes(original)
            if hashlib.sha256(SHEET.read_bytes()).hexdigest() != base:
                sys.exit("FATAL: restore failed after arm %s" % lab)
            if reds == {lab}:
                print("CAUGHT    %s" % lab)
                caught += 1
            elif not reds:
                print("MISSED    %s  <-- DECORATIVE" % lab)
                missed += 1
            else:
                print("DUPLICATE %s  <-- reddened %s" % (lab, sorted(reds)))
                dup += 1

        SHEET.write_text(text.replace(INERT[0], INERT[1], 1), encoding="utf-8")
        inert_reds, _ = run()
        SHEET.write_bytes(original)
        inert_ok = not inert_reds
        print("INERT     %s" % ("held" if inert_ok
                                else "FAILED, reddened %s" % sorted(inert_reds)))
    finally:
        SHEET.write_bytes(original)

    final = hashlib.sha256(SHEET.read_bytes()).hexdigest()
    print("post-restore sha256 %s  %s"
          % (final[:16], "IDENTICAL" if final == base else "MISMATCH"))
    reds, green = run()
    print("live: %s" % ("GREEN" if green and not reds else "RED %s" % sorted(reds)))

    print()
    print("ARMS %d / CAUGHT %d / MISSED %d / DUPLICATE %d"
          % (len(ARMS), caught, missed, dup))
    ok = (missed == 0 and dup == 0 and inert_ok and final == base
          and green and not reds)
    print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

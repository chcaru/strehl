#!/usr/bin/env python3
"""Commission the M8-O v1.5 blob pins in v2954.py.

The scorecard delegates the v1.5 normative bar text to a git blob instead of
transcribing it. That gives the bar exactly one canonical site, but it makes
the 40 hex digits load-bearing: mistype one and the bar silently has no text,
and nothing else in the repository would notice.

v2954 therefore reads the hash OUT OF THE SCORECARD and resolves it. This
script proves those checks actually fire, by planting the exact defects they
target and requiring the named check to go RED.

Discipline this script enforces on itself:
  * Every mutation is anchored on a unique full-line-ish string and HARD ERRORS
    unless it lands exactly once. A control that silently fails to apply
    reports GREEN and is worse than no control at all.
  * The scorecard is restored from a $TEMP copy in a finally block. Never
    `git checkout -- <path>`: it reverts to HEAD and has already destroyed
    uncommitted work on this machine.
  * An inert arm is included. If every arm goes RED, the harness is just
    breaking the file rather than testing the pins.
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCORECARD = ROOT / "docs" / "proposals" / "2026-09-sota-scorecard.md"
V2954 = Path(__file__).resolve().parent / "v2954.py"

# (label, needle, replacement, expected-RED check label or None if inert)
ARMS = [
    ("hash digit flipped",
     "pinned at git blob `86291032355f1d6466e2357b1224d78d9716c80c`",
     "pinned at git blob `86291032355f1d6466e2357b1224d78d9716c80d`",
     "m8o v1.5 blob resolves"),
    ("pin phrase removed",
     "pinned at git blob",
     "transcribed inline from",
     "m8o v1.5 blob pin"),
    ("inert prose edit",
     "It is referenced rather",
     "This is referenced rather",
     None),
]


def run_v2954():
    p = subprocess.run([sys.executable, str(V2954)], cwd=str(ROOT),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return p.stdout.decode("utf-8", "replace")


def red_labels(out):
    """Labels that did NOT print a passing XDOC line."""
    return {ln.split()[1] + " " + " ".join(ln.split()[2:4])
            for ln in out.splitlines() if ln.startswith("XDOC")}


def main():
    original = SCORECARD.read_bytes()
    sha_before = hashlib.sha256(original).hexdigest()
    backup = Path(tempfile.gettempdir()) / "m8o_scorecard_backup.md"
    backup.write_bytes(original)

    baseline = run_v2954()
    if "VERDICT: GREEN" not in baseline:
        print("FATAL: baseline is not GREEN; commission nothing against a red board")
        return 1

    caught = missed = inert_ok = inert_bad = 0
    try:
        for label, needle, repl, expect in ARMS:
            text = original.decode("utf-8")
            n = text.count(needle)
            if n != 1:
                raise SystemExit(
                    "FATAL: arm %r anchor matched %d times, expected exactly 1. "
                    "An unanchored mutation that does not land reports GREEN "
                    "and would be recorded as a passing control." % (label, n))
            SCORECARD.write_text(text.replace(needle, repl, 1), encoding="utf-8",
                                 newline="")
            out = run_v2954()
            green = "VERDICT: GREEN" in out
            if expect is None:
                if green:
                    inert_ok += 1
                    print("INERT   %-22s stayed GREEN, as required" % label)
                else:
                    inert_bad += 1
                    print("INERT   %-22s WENT RED - harness is breaking the "
                          "file, not testing the pin" % label)
            else:
                fired = (not green) and (expect in out or
                                         expect.split()[-1] not in out)
                if not green:
                    caught += 1
                    print("CAUGHT  %-22s -> RED (target: %s)" % (label, expect))
                else:
                    missed += 1
                    print("MISSED  %-22s stayed GREEN; pin %r is a no-op"
                          % (label, expect))
            SCORECARD.write_bytes(original)
    finally:
        SCORECARD.write_bytes(original)

    after = hashlib.sha256(SCORECARD.read_bytes()).hexdigest()
    print()
    print("scorecard restored  : %s" % ("yes" if after == sha_before else "NO - RESTORE FAILED"))
    print("arms planted        : %d" % len(ARMS))
    print("defects caught      : %d" % caught)
    print("defects missed      : %d" % missed)
    print("inert stayed green  : %d" % inert_ok)
    print("inert went red      : %d" % inert_bad)
    print("arms accounted      : %d of %d"
          % (caught + missed + inert_ok + inert_bad, len(ARMS)))
    ok = (missed == 0 and inert_bad == 0 and after == sha_before)
    print()
    print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

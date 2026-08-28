#!/usr/bin/env python3
"""Commission 73-verify-s21.py by planting known defects in section 21.

WHY
---
A verifier that prints 51/51 has said nothing until it has been shown to say
something else on a document it should reject.  Another lane's checker ran 37/37
green and then caught 5 of 13 plants.  This script is the arm that would have
found that.

TWO PROPERTIES EVERY PLANT MUST HAVE
------------------------------------
1. It must LAND.  Each plant is anchored on a string asserted to occur exactly
   once in the report.  A bare `replace(x, y, 1)` can silently hit an earlier
   occurrence and mutate a different sentence, in which case a RED reading is
   evidence about the wrong claim.  If the anchor count is not 1, this script
   raises UNANCHORED and refuses to score that plant, which is a third outcome
   distinct from caught and missed.

2. It must EXCEED THE TOLERANCE of the check that is supposed to catch it.
   Several checks in the verifier compare with a relative tolerance -- 1e-8 on
   the image means, 1e-5 on the tone ratios, 0.5% on the seal means.  A plant
   smaller than its check's tolerance tests nothing and banks a false MISS.  So
   the plants below are sized against the tolerances in 73-verify-s21.py, and
   the size rationale is recorded per plant in the `why` field.

CLEAN CONTROL
-------------
Before any plant, the unmodified report is run and required to read PASS.  If
the clean control reads FAIL, every subsequent RED is unattributable -- the
verifier would be failing for a reason that has nothing to do with the plant --
and this script aborts.

RESTORATION
-----------
The report is copied to %TEMP% and restored from that copy.  Never
`git checkout --`, which reverts to HEAD and destroys uncommitted work.  The
final restoration is verified by SHA-256 against the copy taken at the start.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "docs", "research", "BUILD-DEFECT.md"))
VERIFIER = os.path.join(HERE, "73-verify-s21.py")

# (label, anchor -> replacement, the check that must name it, sizing rationale)
PLANTS: list[tuple[str, str, str, str, str]] = [
    ("samples-differ count",
     "pin  +2.60 vs 0         2.60      6.1x        451,463   0.4565%          1      1.0000",
     "pin  +2.60 vs 0         2.60      6.1x        451,464   0.4565%          1      1.0000",
     "samples differ", "exact check; any change suffices"),
    ("max |d| on the positive control",
     "HEAD +2.60 vs 0         2.60      6.1x     98,855,406  99.9569%      65535  14023.2383",
     "HEAD +2.60 vs 0         2.60      6.1x     98,855,406  99.9569%      65534  14023.2383",
     "max |d|", "exact check; any change suffices"),
    ("mean |d| on the positive control",
     "98,855,406  99.9569%      65535  14023.2383",
     "98,855,406  99.9569%      65535  14123.2383",
     "mean |d|", "check is rel 1e-4; 100 DN on 14023 is 0.7%, well clear"),
    ("percent-differ",
     "451,463   0.4565%",
     "451,463   0.4665%",
     "pct differ", "check is rel 1e-2; 0.01 on 0.4565 is 2.2%, clear"),
    ("commanded linear ratio",
     "pin  +3    vs -3        6.00     64.0x",
     "pin  +3    vs -3        6.00     70.0x",
     "commanded ratio", "check is rel 1e-2; 6.0 on 64 is 9.4%, clear"),
    ("the plane size in the headline",
     "**Those two files are different bytes and the same image. Zero of 98,898,048\nsamples differ.**",
     "**Those two files are different bytes and the same image. Zero of 98,898,049\nsamples differ.**",
     "plane size", "exact check; any change suffices"),
    ("the identical means",
     "eight significant figures: 47719.088 against 47719.088.",
     "eight significant figures: 47719.098 against 47719.088.",
     "mean A", "check is rel 1e-8; 0.01 on 47719 is 2.1e-7, 21x the tolerance"),
    ("the first differing byte offset",
     "Eleven bytes differ, at file offsets 339 through 359",
     "Eleven bytes differ, at file offsets 340 through 359",
     "first offset", "exact check; any change suffices"),
    ("the pixel payload size",
     "runs to\n197,796,096 bytes",
     "runs to\n197,796,097 bytes",
     "pixel payload size", "exact check; any change suffices"),
    ("a recorded tone point",
     "exposure=+3 : ... Tone rendering: black 0.037985, white 1.311591 (linear, ...",
     "exposure=+3 : ... Tone rendering: black 0.037986, white 1.311591 (linear, ...",
     "+3 black", "exact check; any change suffices"),
    ("the black tone ratio",
     "black ratio +3 / -3 = 63.9478",
     "black ratio +3 / -3 = 63.9578",
     "black ratio", "check is rel 1e-5; 0.01 on 63.95 is 1.6e-4, 16x the tolerance"),
    ("the agreement percentage",
     "commanded 2^6 = 64.0000    agreement 0.082%",
     "commanded 2^6 = 64.0000    agreement 0.200%",
     "black agreement", "check is rel 2e-2; 0.118 on 0.082 is 144%, far clear"),
    ("a reproduced SHA-256 prefix",
     "its hashes exactly \u2014 `D749F1FDCD07355F` and `A5846DD2B0ACDC3A` \u2014 so this is the",
     "its hashes exactly \u2014 `D749F1FDCD07355E` and `A5846DD2B0ACDC3A` \u2014 so this is the",
     "pin-epos3.tiff", "string equality; anchored on the canonical sentence, since "
                       "the prefixes also appear in 21.1 and a presence test would be "
                       "satisfied by that second copy"),
    ("the INERT threshold",
     "`INERT <= 2 DN`, `LIVE >= 256 DN`",
     "`INERT <= 3 DN`, `LIVE >= 256 DN`",
     "INERT_MAX_DN", "exact check against the instrument source"),
    ("the LIVE threshold",
     "`INERT <= 2 DN`, `LIVE >= 256 DN`",
     "`INERT <= 2 DN`, `LIVE >= 257 DN`",
     "LIVE_MIN_DN", "exact check against the instrument source"),
    ("the partition",
     "partition as 4 measured + 0 missing-input + 0 failed",
     "partition as 3 measured + 0 missing-input + 0 failed",
     "sums to declared", "exact check; any change suffices"),
    ("a seal mean",
     "SHIP-V4 seal                     mean 47719.1   clipped 0.0012%",
     "SHIP-V4 seal                     mean 48719.1   clipped 0.0012%",
     "SHIP-V4 seal mean", "check is rel 1e-5 with a 0.06 floor, so tol is 0.48; "
                          "1000 DN is 2000x clear"),
    ("a seal clip fraction",
     "HEAD           --exposure=+2.60  mean 61821.3   clipped 85.5234%",
     "HEAD           --exposure=+2.60  mean 61821.3   clipped 85.7234%",
     "clip", "check is rel 1e-3 with a 1e-4 floor, so tol is 0.0855 pp; "
             "0.2 pp is 2.3x clear. The earlier sizing note said 'abs 0.05' and "
             "was wrong about the verifier's own semantics -- the argument was "
             "relative, tol was 4.3 pp, and this plant was MISSED"),
    ("the plant partition in 21.8",
     "declared 22 = caught 22 + missed 0 + unanchored 0     (after the repairs below)",
     "declared 22 = caught 21 + missed 0 + unanchored 0     (after the repairs below)",
     "all plants caught", "exact check against the static PLANTS table"),
    ("the pre-repair caught figure",
     "were run through it and it caught 16.",
     "were run through it and it caught 15.",
     "pre-repair caught", "exact; internal arithmetic, that run's plants minus the two defects"),
    ("the current suite size",
     "grown to\n22 plants, four of them covering this subsection's own figures",
     "grown to\n21 plants, four of them covering this subsection's own figures",
     "current suite size", "exact check against the static PLANTS table"),
    ("the derived slack figure",
     "is **4.3 percentage points** of",
     "is **5.3 percentage points** of",
     "slack = 5% of the clip fraction", "exact; 5% of the parsed clip fraction, rounded to 1 dp"),
]


def run_verifier() -> tuple[int, str]:
    p = subprocess.run([sys.executable, VERIFIER], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def main() -> int:
    print("=" * 100)
    print("COMMISSIONING 73-verify-s21.py")
    print("=" * 100)

    backup = os.path.join(tempfile.gettempdir(), "BUILD-DEFECT.md.s21commission.bak")
    shutil.copyfile(REPORT, backup)
    original = open(REPORT, encoding="utf-8", newline="").read()
    orig_sha = hashlib.sha256(open(REPORT, "rb").read()).hexdigest()
    print("backed up to %s  sha256 %s" % (backup, orig_sha[:16]))
    print()

    print("CLEAN CONTROL (must read PASS, or no RED below is attributable)")
    rc, out_clean = run_verifier()
    if rc != 0:
        print("  ABORT: the unmodified report does not verify. rc=%d" % rc)
        print(out_clean[-1500:])
        return 2
    m = re.search(r"declared (\d+) = matched (\d+) \+ mismatched (\d+) \+ unresolved (\d+)", out_clean)
    print("  PASS -- %s" % (m.group(0) if m else "verified"))
    print()

    caught: list[str] = []
    missed: list[str] = []
    unanchored: list[str] = []

    print("%-36s %-9s %s" % ("plant", "verdict", "evidence"))
    print("-" * 100)
    for label, anchor, replacement, must_name, why in PLANTS:
        n = original.count(anchor)
        if n != 1:
            unanchored.append("%s: anchor occurs %d times, not 1" % (label, n))
            print("%-36s %-9s anchor occurs %d times -- not scored" % (label, "UNANCHORED", n))
            continue
        mutated = original.replace(anchor, replacement, 1)
        if mutated == original:
            unanchored.append("%s: replacement is identical to the anchor" % label)
            print("%-36s %-9s replacement is a no-op -- not scored" % (label, "UNANCHORED"))
            continue
        with open(REPORT, "w", encoding="utf-8", newline="") as fh:
            fh.write(mutated)
        rc, out = run_verifier()
        named = must_name in out
        if rc != 0 and named:
            caught.append(label)
            hit = [ln.strip() for ln in out.splitlines() if must_name in ln and "MISMATCH" in ln]
            print("%-36s %-9s %s" % (label, "CAUGHT", (hit[0][:56] if hit else "named in output")))
        elif rc != 0:
            missed.append("%s: verifier failed but never named %r" % (label, must_name))
            print("%-36s %-9s failed for the WRONG reason (%r absent)" % (label, "MISATTRIB", must_name))
        else:
            missed.append("%s: verifier still passed" % label)
            print("%-36s %-9s verifier still reads PASS" % (label, "MISSED"))
        with open(REPORT, "w", encoding="utf-8", newline="") as fh:
            fh.write(original)

    with open(REPORT, "w", encoding="utf-8", newline="") as fh:
        fh.write(original)
    final_sha = hashlib.sha256(open(REPORT, "rb").read()).hexdigest()

    print("-" * 100)
    declared = len(PLANTS)
    total = len(caught) + len(missed) + len(unanchored)
    assert total == declared, (
        "partition does not sum: %d caught + %d missed + %d unanchored != %d declared"
        % (len(caught), len(missed), len(unanchored), declared))
    print("declared %d = caught %d + missed %d + unanchored %d"
          % (declared, len(caught), len(missed), len(unanchored)))
    for x in missed:
        print("  MISSED      %s" % x)
    for x in unanchored:
        print("  UNANCHORED  %s" % x)
    print()
    print("restoration: sha256 %s  %s"
          % (final_sha[:16], "byte-identical to the original" if final_sha == orig_sha else "DIFFERS -- RESTORE FAILED"))

    if final_sha != orig_sha:
        print("VERDICT: FAIL -- the report was not restored.")
        return 3
    if missed or unanchored:
        print("VERDICT: FAIL -- the verifier does not catch every planted defect.")
        return 1

    # ---- provenance: does 21.8 describe THIS run? -------------------------
    # 73-verify-s21.py deliberately does not check these, because it is invoked
    # by this script and a check there would be circular. This is the process
    # that knows the truth of them, so it is the one that checks.
    sec = re.search(r"^### 21\.8.*?(?=^### 21\.9|\Z)", original, re.M | re.S)
    prov_bad: list[str] = []
    if not sec:
        prov_bad.append("section 21.8 not found in the report")
    else:
        body = sec.group(0)
        want = ("declared %d = caught %d + missed %d + unanchored %d"
                % (declared, len(caught), len(missed), len(unanchored)))
        if want not in body:
            m = re.search(r"declared \d+ = caught \d+ \+ missed \d+ \+ unanchored \d+", body)
            prov_bad.append("partition line: report says %r, this run produced %r"
                            % (m.group(0) if m else "<absent>", want))
        ms = re.search(r"restoration   : byte-identical to the original, verified by SHA-256", body)
        if not ms:
            prov_bad.append("restoration line absent from 21.8")
        # The report deliberately states restoration QUALITATIVELY. A report
        # that quoted its own restoration hash would be an unreachable fixed
        # point: writing the hash into the file changes the file's hash. The
        # claim that matters is "restored byte-identically", and this run
        # measured that above by comparing orig_sha to final_sha.
        mc = re.search(r"clean control : PASS -- (declared \d+ = matched \d+ \+ "
                       r"mismatched \d+ \+ unresolved \d+)", body)
        if not mc:
            prov_bad.append("clean-control line absent from 21.8")
        else:
            m2 = re.search(r"declared (\d+) = matched (\d+) \+ mismatched (\d+) \+ unresolved (\d+)", out_clean)
            got = m2.group(0) if m2 else "<unparsed>"
            if mc.group(1) != got:
                prov_bad.append("clean-control line: report says %r, this run produced %r"
                                % (mc.group(1), got))

    print()
    if prov_bad:
        print("PROVENANCE: FAIL -- section 21.8 does not describe this run:")
        for p in prov_bad:
            print("  - %s" % p)
        print("VERDICT: FAIL")
        return 4
    print("PROVENANCE: section 21.8's partition, clean control and restoration hash all describe this run.")
    print("VERDICT: PASS -- %d/%d plants caught, each naming its own check." % (len(caught), declared))
    return 0


if __name__ == "__main__":
    sys.exit(main())

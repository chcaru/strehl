#!/usr/bin/env python3
"""Commission the M12-retraction checks added to vowner0906.py.

These 15 checks guard figures that now sit in an owner-facing file directly
next to a $289 spending decision. Ask 3 previously told the owner that axis M12
sat behind that purchase; lane M178 removed the clause that claim rested on, so
the chain was retracted in place. The retraction quotes six values and asserts
six arithmetic identities.

A check that has never been observed to go RED is a claim about the check, not
about the document. So each of the 15 gets the exact defect it reads planted
under it, one at a time, and must go RED alone:

  * MISSED     -- the mutation landed and the check stayed green: decorative.
  * DUPLICATE  -- the mutation reddened a check other than its own, or more
                  than one: the checks are not discriminating.

Two mutation surfaces are used, and they isolate cleanly:
  * presence arms mutate the OWNER DOCUMENT, breaking the owner side of a
    two-sided check while its lane source stays intact;
  * derivation arms mutate the EXPECTED LITERAL inside vowner0906.py rather
    than the shared constants, because mutating PEAK would redden three checks
    at once and prove nothing about any of them individually.

A mutation that fails to land is a harness failure, not a pass, and is a hard
error. Everything happens in a TEMP copy; the live tree is never written,
because ~25 other agents read it concurrently.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
VNAME = "vowner0906.py"

OWNER_REL = "docs/OWNER-ACTIONS.md"
V_REL = "experiments/ORCH-verify/" + VNAME

# (check label, relative path to mutate, exact text, replacement)
ARMS = [
    # ---- presence arms: mutate the owner document ----
    ("m12 repaired peak", OWNER_REL,
     "3,074,797,568 B", "3,074,797,569 B"),
    ("m12 headroom", OWNER_REL,
     "3,367,653,376 B", "3,367,653,375 B"),
    ("m12 unrepaired red", OWNER_REL,
     "38,286,897,152 B", "38,286,897,153 B"),
    ("m12 scorecard peak", OWNER_REL,
     "35.65745162963867 GiB", "35.65745162963868 GiB"),
    ("m12 clause unratified", OWNER_REL,
     "unratified addition", "ratified amendment"),
    ("m12 clause commit", OWNER_REL,
     "986c4653", "986c4654"),
    ("retraction present", OWNER_REL,
     "RETRACTION", "REVISION"),
    ("retraction names M178", OWNER_REL,
     "M178", "M999"),
    ("original claim left standing", OWNER_REL,
     "So M12-S sits behind this purchase",
     "So M12-S once appeared to sit behind this purchase"),

    # ---- derivation arms: mutate the expected literal, not the constant ----
    ("headroom re-derives", V_REL,
     "PEAK + HEADROOM == BAR", "PEAK + HEADROOM == BAR + 1"),
    ("unrepaired GiB identity", V_REL,
     '"35.65745162963867"', '"35.65745162963868"'),
    ("peak GiB quoted", V_REL, '"2.8636"', '"2.8637"'),
    ("headroom GiB quoted", V_REL, '"3.1364"', '"3.1365"'),
    ("peak is under bar", V_REL, "PEAK < BAR", "PEAK > BAR"),
    ("unrepaired is over bar", V_REL, "UNREPAIRED > BAR", "UNREPAIRED < BAR"),
]

# Must change nothing. If this reddens a check, the checks are keyed on
# incidental prose rather than on the measured claim.
INERT = (OWNER_REL,
         "The control fired on the real defect.",
         "The control fired on the actual registered defect.")


def run(root):
    """Return (reds, green) where reds is the set of RED check labels."""
    v = root / "experiments" / "ORCH-verify" / VNAME
    p = subprocess.run([sys.executable, str(v), str(root)],
                       capture_output=True, text=True)
    reds = set()
    for line in p.stdout.splitlines():
        m = re.match(r"^RED\s+m12(?:ret|der)\s+(.+)$", line)
        if m:
            lab = m.group(1).strip()
            # The verifier appends a diagnostic after the label. With a label
            # at or over the padding width only ONE space separates them, so a
            # `\s{2,}` split silently folds the diagnostic into the label and
            # the arm reads as MISSED when the check in fact fired. Strip the
            # known diagnostics explicitly rather than relying on padding.
            for suffix in (" ABSENT", " DID NOT RE-DERIVE"):
                if lab.endswith(suffix):
                    lab = lab[:-len(suffix)]
            lab = re.split(r"\s{2,}|\s+source=|\s+SOURCE MISSING", lab)[0]
            reds.add(lab.strip())
        elif line.startswith("CTLFAIL"):
            reds.add("CTL:" + line[8:60].strip())
    green = "VERDICT: GREEN" in p.stdout
    if not p.stdout.strip():
        raise SystemExit("FATAL: verifier produced no output\n" + p.stderr[-2000:])
    return reds, green


def apply_mutation(path, old, new):
    """Replace every occurrence of `old`, hard-erroring on miss or no-op."""
    body = path.read_text(encoding="utf-8", errors="replace")
    n = body.count(old)
    if n == 0:
        raise SystemExit(
            "FATAL: mutation target not found in %s\n  looking for: %r\n"
            "A mutation that does not land is a harness failure, not a pass."
            % (path, old))
    out = body.replace(old, new)
    if out == body:
        raise SystemExit("FATAL: mutation was a no-op in %s: %r" % (path, old))
    path.write_text(out, encoding="utf-8")
    return n


def main():
    tmp = Path(tempfile.mkdtemp(prefix="orch-m12ret-"))
    try:
        shutil.copytree(REAL / "docs", tmp / "docs")
        (tmp / "experiments").mkdir(parents=True, exist_ok=True)
        shutil.copytree(REAL / "experiments" / "ORCH-verify",
                        tmp / "experiments" / "ORCH-verify")

        reds, green = run(tmp)
        if not green or reds:
            raise SystemExit(
                "FATAL: TEMP baseline is not GREEN.\n  reds: %s\n"
                "The copy is not a faithful mirror, so every result below "
                "would be uninterpretable." % sorted(reds))
        print("TEMP baseline VERDICT: GREEN, no m12 reds")

        caught = missed = dup = 0
        for label, rel, old, new in ARMS:
            target = tmp / rel
            original = target.read_text(encoding="utf-8", errors="replace")
            hits = apply_mutation(target, old, new)
            reds, _ = run(tmp)
            target.write_text(original, encoding="utf-8")

            if reds == {label}:
                print("CAUGHT     %-30s (%d site%s)"
                      % (label, hits, "" if hits == 1 else "s"))
                caught += 1
            elif label not in reds:
                print("MISSED     %-30s -> %s  DECORATIVE"
                      % (label, sorted(reds) or "none"))
                missed += 1
            else:
                print("DUPLICATE  %-30s -> %s" % (label, sorted(reds)))
                dup += 1

        rel, old, new = INERT
        target = tmp / rel
        original = target.read_text(encoding="utf-8", errors="replace")
        apply_mutation(target, old, new)
        reds, green_i = run(tmp)
        target.write_text(original, encoding="utf-8")
        inert_ok = not reds and green_i
        print("%-10s INERT prose reword           reds=%s"
              % ("INERT-OK" if inert_ok else "INERT-BAD", sorted(reds) or "none"))

        reds, green = run(tmp)
        print("\npost-restore TEMP VERDICT: %s"
              % ("GREEN" if green and not reds else "RED " + str(sorted(reds))))
        live_reds, live_green = run(REAL)
        print("live tree VERDICT: %s"
              % ("GREEN" if live_green and not live_reds
                 else "RED " + str(sorted(live_reds))))

        print("\nARMS %d  CAUGHT %d  MISSED %d  DUPLICATE %d"
              % (len(ARMS), caught, missed, dup))
        ok = (caught == len(ARMS) and missed == 0 and dup == 0
              and inert_ok and green and live_green)
        print("COMMISSIONED" if ok else "NOT COMMISSIONED")
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

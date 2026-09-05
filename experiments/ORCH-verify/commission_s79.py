"""Commission the STATUS 2.9.79 cross-document pins in v2954.py.

Section 2.9.79 quotes numbers out of five files this orchestrator does not own.
M182, M186 and M164 are live lanes. If one of them revises its own document, my
quotation silently ceases to exist in its source and 2.9.79 becomes an
unsupported assertion that still reads GREEN. The `s79 ` pins exist to stop
that -- but a pin that has never been observed to go RED is a claim about the
pin, not about the document.

So each pin gets the exact defect it reads planted under it, one at a time, and
must go RED alone. Two failure modes are checked for explicitly:

  * MISSED       -- the mutation landed and the pin stayed green. The pin is
                    decorative.
  * DUPLICATE    -- the mutation landed and reddened a pin other than its own,
                    or more than one pin. The anchors are not discriminating,
                    which is the defect that made the three `133` bench pins
                    useless until they were split onto distinct needles.

A mutation that fails to land is a harness failure, not a pass, and is a hard
error -- a green from a mutation that never applied is exactly the false
negative this file exists to prevent.

Everything is mutated inside a TEMP copy. The live tree is never written to,
because ~25 other agents are reading it concurrently.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
V = Path(__file__).resolve().parent / "v2954.py"

# (pin label, relative path, exact unique text to break)
# The replacement must preserve length-ish shape but change the pinned token,
# so the check reads a genuinely absent quote rather than a malformed file.
ARMS = [
    ("s79 mem bar ruling", "docs/research/M182-memory-budget.md",
     "not 6 GiB per process or per worker",
     "not 6 GiB per socket or per worker"),
    ("s79 mem estimand gap", "docs/research/M182-memory-budget.md",
     "12,288 B", "12,289 B"),
    ("s79 mem w2 predict", "docs/research/M182-memory-budget.md",
     "4,771,634,216", "4,771,634,217"),
    ("s79 mem w2 fresh", "docs/research/M182-memory-budget.md",
     "M182's fresh W2 Job peak is `4,804,800,512 B`",
     "M182's fresh W2 Job peak is `4,804,800,513 B`"),
    ("s79 mem w2 residual", "docs/research/M182-memory-budget.md",
     "0.690274%", "0.690275%"),
    ("s79 mem bounded meas", "docs/research/M182-memory-budget.md",
     "bounded canonical recycling is independently measured at `3,074,797,568 B`",
     "bounded canonical recycling is independently measured at `3,074,797,569 B`"),
    ("s79 mem headroom", "docs/research/M182-memory-budget.md",
     "leaving `3,367,653,376 B` headroom",
     "leaving `3,367,653,377 B` headroom"),
    ("s79 tiling not a pass", "docs/research/M182-memory-budget.md",
     "this is still diagnostic evidence, not a formal M12 pass",
     "this is sufficient evidence for a formal M12 pass"),
    ("s79 mem n7 red", "docs/research/M182-memory-budget.md",
     "already RED on unrepaired `8009447e` at",
     "already GREEN on unrepaired `8009447e` at"),
    ("s79 m186 byte order", "docs/research/M186-m10-definition-audit.md",
     "a probe selected x=`03,05,07` big-endian versus `02,00,07` little-endian",
     "a probe selected x=`03,05,07` big-endian versus `03,05,07` little-endian"),
    ("s79 m171 usm reward", "docs/research/M164-aperture-identifiability.md",
     "1.409469446x", "1.409469447x"),
    ("s79 m171 airy match", "docs/research/M164-aperture-identifiability.md",
     "1.11e-15", "1.11e-14"),
    ("s79 m171 kill", "docs/research/M164-aperture-identifiability.md",
     "KILL the claim that the three-point aperture ordering alone unblocks the",
     "KEEP the claim that the three-point aperture ordering alone unblocks the"),
    ("s79 flat freeze rule", "experiments/M152-site-census/m4-freeze.json",
     "no_cross_capture_or_cross_category_substitution",
     "cross_capture_and_cross_category_substitution_allowed"),
    ("s79 burn 484", "docs/captures-needed.md",
     "484 ARW frames in three directories",
     "484 ARW frames in four directories"),
]

# An arm that must change nothing. If this reddens a pin, the pins are keyed on
# incidental prose rather than on the measured claim.
INERT = ("docs/research/M182-memory-budget.md",
         "I accept the planner's narrow",
         "I accept the memory planner's narrow")


def run(root):
    """Return the set of s79 labels reported XFAIL by v2954 under `root`."""
    p = subprocess.run([sys.executable, str(V), str(root)],
                       capture_output=True, text=True)
    reds = set()
    all_reds = set()
    for line in p.stdout.splitlines():
        m = re.match(r"^(?:XFAIL|RED)\s+(.+?)\s{2,}", line)
        if m:
            lab = m.group(1).strip()
            all_reds.add(lab)
            if lab.startswith("s79 "):
                reds.add(lab)
    green = "VERDICT: GREEN" in p.stdout
    return reds, green, all_reds


def apply_mutation(path, old, new):
    """Replace `old` with `new`, hard-erroring on a miss or a no-op."""
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
    tmp = Path(tempfile.mkdtemp(prefix="orch-s79-"))
    try:
        shutil.copytree(REAL / "docs", tmp / "docs")
        (tmp / "experiments").mkdir(parents=True, exist_ok=True)
        # v2954 reads these four experiment trees in addition to docs/. A copy
        # missing any of them reads RED on unrelated pins and makes every arm
        # below uninterpretable.
        for sub in ("M-PHASE0-PHASE", "M134-kernel-frontier",
                    "M152-site-census", "M175-fork-arm", "M172-worker-memory",
                    "M136-m8o-bar", "M163-m10-uncertainty",
                    "ORCH-verify"):
            shutil.copytree(REAL / "experiments" / sub,
                            tmp / "experiments" / sub)
        # Two Rust sources are read for 2.9.76's premise. Copy just these files
        # rather than the whole crates/ tree, which is large and irrelevant here.
        for rel in ("crates/strehl-cli/src/align_cmd.rs",
                    "crates/strehl-core/src/restore.rs"):
            dst = tmp / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REAL / rel, dst)

        reds, green, all_reds = run(tmp)
        if not green or reds:
            raise SystemExit(
                "FATAL: TEMP baseline is not GREEN.\n"
                "  s79 reds: %s\n  all reds: %s\n"
                "The copy is not a faithful mirror, so every result below "
                "would be uninterpretable."
                % (sorted(reds), sorted(all_reds)))
        print("TEMP baseline VERDICT: GREEN, no s79 reds")

        caught = missed = dup = 0
        for label, rel, old, new in ARMS:
            target = tmp / rel
            backup = target.read_text(encoding="utf-8", errors="replace")
            apply_mutation(target, old, new)
            reds, _, _ = run(tmp)
            target.write_text(backup, encoding="utf-8")

            if reds == {label}:
                print("CAUGHT     %-24s -> %s" % (label, sorted(reds)))
                caught += 1
            elif label in reds:
                print("DUPLICATE  %-24s -> %s  (reddened others too)"
                      % (label, sorted(reds)))
                dup += 1
            else:
                print("MISSED     %-24s -> %s  (PIN IS DECORATIVE)"
                      % (label, sorted(reds)))
                missed += 1

        rel, old, new = INERT
        target = tmp / rel
        backup = target.read_text(encoding="utf-8", errors="replace")
        apply_mutation(target, old, new)
        reds, _, _ = run(tmp)
        target.write_text(backup, encoding="utf-8")
        inert_ok = not reds
        print("INERT-%s  INERT prose reword         reds=%s"
              % ("OK " if inert_ok else "BAD", sorted(reds) or "none"))

        reds, green, _ = run(tmp)
        print("\npost-restore TEMP VERDICT: %s"
              % ("GREEN" if (green and not reds) else "RED -- copy not restored"))

        live_reds, live_green, _ = run(REAL)
        print("live tree VERDICT: %s"
              % ("GREEN" if (live_green and not live_reds) else "RED"))

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

"""Commission the STATUS 2.9.78 structural checks and the HEAD-pin machinery.

Six checks were added to v2954.py and none of them had ever been observed to
fail. A check that has never fired may be a silent no-op, so each is proved
here by planting the exact defect it reads.

Two of the six are unusual and worth stating plainly, because their polarity is
the opposite of the rest:

  - `m12 is the disambiguating row` asserts M12 shows `blocker (d)` in the Fork
    comparator column WHILE its own blocker set is `(e) none`. That pair is the
    proof the column is not a per-axis attribute. It is the check that would
    have stopped the orchestrator writing a repair for a correct document.

  - `withdrawal pending: M176 -> M184` goes RED when the divergence ENDS. A
    HEAD pin is only defensible while the working tree genuinely disagrees;
    once the lane restores the text or the retraction is ruled on, the entry
    must be retired rather than left as a standing excuse. Its arm therefore
    plants a RESTORATION, not a corruption.

The live tree is never written. v2954.py takes a repo root as argv[1], so docs/
and experiments/ORCH-verify/ are copied into TEMP and everything else is
junctioned read-only. Junctions are created with `mklink /J`, which needs no
administrator rights; they are only ever read through.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REAL = Path(__file__).resolve().parents[2]
V = REAL / "experiments" / "ORCH-verify" / "v2954.py"

REL_STATUS = "docs/STATUS.md"
REL_SCORE = "docs/proposals/2026-09-sota-scorecard.md"
REL_M176 = "docs/research/M176-worker-invariance.md"
REL_PEND = "experiments/ORCH-verify/pending-withdrawals.json"

# (arm, relative path, mutate(text)->text, labels that must go RED)
def sub_once(old, new):
    """Replace `old` exactly once, tolerating Markdown line wrapping.

    Hard-errors when the anchor does not match exactly once. A bare
    replace() that silently matches nothing produces a green arm that proves
    only that the harness missed.
    """
    pat = re.compile(r"[\s>]+".join(re.escape(t) for t in old.split()))

    def go(text):
        n = len(pat.findall(text))
        if n != 1:
            raise SystemExit("MUTATION TARGET NOT FOUND (%d matches): %r"
                             % (n, old))
        return pat.sub(lambda _: new, text)
    return go


def restore_withdrawn(text):
    """Put M176's withdrawn figures back, as if the lane had restored them."""
    return text + ("\n\nRESTORED FOR COMMISSIONING: REDUCTION_ORDER, "
                   "3,430 of 8,241,504 pixels, 0.041619 percent, "
                   "lattice [5,5,5,4].\n")


def drop_pending(text):
    data = json.loads(text)
    if not data:
        raise SystemExit("MUTATION TARGET NOT FOUND: pending list already empty")
    return json.dumps([], indent=2)


ARMS = [
    ("table header renamed", REL_SCORE,
     sub_once("| ID | Metric | strehl | Zerene Stacker (PMax + DMap) |",
              "| ID | Axis | strehl | Zerene Stacker (PMax + DMap) |"),
     {"m10 readiness table parses", "m10 fork column is uniform, not per-axis",
      "m12 is the disambiguating row"}),
    ("M10 fork cell changed", REL_SCORE,
     sub_once("| M10 | Physical depth accuracy | **DEFINITION BLOCKED beyond "
              "uncertainty repair** | **UNMEASURED** | **UNMEASURED — blocker "
              "(d).**",
              "| M10 | Physical depth accuracy | **DEFINITION BLOCKED beyond "
              "uncertainty repair** | **UNMEASURED** | **UNMEASURED — blocker "
              "(b).**"),
     {"m10 fork column is uniform, not per-axis"}),
    ("M12 fork cell changed", REL_SCORE,
     sub_once("| M12 | Memory / determinism / scaling invariance |",
              "| M12x | Memory / determinism / scaling invariance |"),
     {"m12 is the disambiguating row"}),
    ("correction reverted to false conflict", REL_STATUS,
     sub_once("there is no contradiction, and the scorecard is right",
              "those lines disagree about whether M10 carries it"),
     {"2.9.78 records the correction, not the false conflict"}),
    ("named failure mode deleted", REL_STATUS,
     sub_once("uniform per-column annotation read as a per-row attribute",
              "column annotation read as a row attribute"),
     {"2.9.78 records the correction, not the false conflict"}),
    ("pending registration emptied", REL_PEND, drop_pending,
     {"every HEAD-pinned source is registered"}),
    ("withdrawal reversed by the lane", REL_M176, restore_withdrawn,
     {"withdrawal pending: M176 -> M184"}),
    # INERT: a real edit to the same STATUS paragraph, in prose no pin reads.
    ("INERT status prose reworded", REL_STATUS,
     sub_once("The tell was available and I walked past it",
              "The tell was there and I walked straight past it"), set()),
]

RED_RE = re.compile(r"^(?:RED|XFAIL)\s+(.+?)\s{2,}", re.M)

# Every label any arm expects. Parsing the failure channel by whitespace does
# NOT work: check() prints "XFAIL %-24s %s", so a label longer than 24
# characters is followed by a single space and a width-based parser silently
# reads it as no failure at all -- which reports a landed mutation as a no-op
# and would have retired seven working checks as broken.
ALL_LABELS = sorted({lab for _, _, _, exp in ARMS for lab in exp})


def run(root):
    p = subprocess.run([sys.executable, str(V), str(root)],
                       capture_output=True)
    return (p.stdout + p.stderr).decode("utf-8", "replace")


def reds(out):
    """Labels reported failing, matched by name rather than by column width."""
    bad = set()
    for line in out.splitlines():
        for pre in ("XFAIL ", "RED   "):
            if line.startswith(pre):
                rest = line[len(pre):]
                for lab in (ALL_LABELS or ()):
                    if rest.startswith(lab):
                        bad.add(lab)
    return bad


def junction(link, target):
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                   capture_output=True, check=True)


tmp = Path(tempfile.mkdtemp(prefix="orch-2978-"))
caught = missed = 0
restored_ok = False
try:
    shutil.copytree(REAL / "docs", tmp / "docs")
    (tmp / "experiments").mkdir()
    shutil.copytree(REAL / "experiments" / "ORCH-verify",
                    tmp / "experiments" / "ORCH-verify")
    for d in (REAL / "experiments").iterdir():
        if d.is_dir() and d.name != "ORCH-verify":
            junction(tmp / "experiments" / d.name, d)
    for name in ("crates", "scripts"):
        if (REAL / name).exists():
            junction(tmp / name, REAL / name)

    base = run(tmp)
    if "VERDICT: GREEN" not in base:
        fails = sorted(reds(base))
        tail = [l for l in base.splitlines()
                if l.startswith(("RED", "XFAIL", "controls fail",
                                 "xdoc derived fail", "not asserted"))]
        raise SystemExit("FATAL: TEMP baseline is not GREEN, so no arm below "
                         "would mean anything.\nfailing labels: %s\n%s"
                         % (fails or "none parsed", "\n".join(tail[:40])))
    print("TEMP baseline VERDICT: GREEN")
    print("live tree written: NO (mutations under %s)\n" % tmp)

    for label, rel, mutate, expect in ARMS:
        f = tmp / rel
        orig = f.read_bytes()
        try:
            mutated = mutate(orig.decode("utf-8")).encode("utf-8")
            # A mutation that changes nothing produces a green arm proving only
            # that the harness missed. sub_once already hard-errors on a bad
            # anchor; this catches the rest.
            if mutated == orig:
                raise SystemExit("MUTATION WAS A NO-OP: %s on %s"
                                 % (label, rel))
            f.write_bytes(mutated)
            out = run(tmp)
            got = reds(out)
        finally:
            f.write_bytes(orig)

        if not expect:
            ok = "VERDICT: GREEN" in out
            print(("INERT-OK   " if ok else "INERT-FAIL ") + "%-34s reds=%s"
                  % (label, sorted(got) or "none"))
            caught += 1 if ok else 0
            missed += 0 if ok else 1
        elif expect <= got:
            extra = got - expect
            print("CAUGHT     %-34s -> %s%s"
                  % (label, sorted(expect),
                     "  (also %s)" % sorted(extra) if extra else ""))
            caught += 1
        else:
            print("MISSED     %-34s expected %s got %s"
                  % (label, sorted(expect), sorted(got) or "NOTHING (no-op)"))
            missed += 1

    after = run(tmp)
    restored_ok = "VERDICT: GREEN" in after
    print("\npost-restore TEMP VERDICT: "
          + ("GREEN" if restored_ok else "RED -- copy not restored"))
finally:
    # Remove junctions before the tree, so rmtree cannot descend into the real
    # repository through them.
    for p in list((tmp / "experiments").glob("*")) + [tmp / "crates",
                                                      tmp / "scripts"]:
        if p.is_dir() and p.is_symlink() or (p.exists() and os.path.isdir(p)
                                             and p.name not in ("ORCH-verify",)):
            try:
                os.rmdir(p)
            except OSError:
                pass
    shutil.rmtree(tmp, ignore_errors=True)

live = run(REAL)
print("live tree VERDICT: "
      + ("GREEN" if "VERDICT: GREEN" in live else "RED -- LIVE TREE DISTURBED"))
print("\nARMS %d  CAUGHT %d  MISSED %d" % (len(ARMS), caught, missed))
ok = missed == 0 and restored_ok and "VERDICT: GREEN" in live
print("COMMISSIONED" if ok else "NOT COMMISSIONED")
sys.exit(0 if ok else 1)

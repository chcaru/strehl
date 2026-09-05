"""Commission the cross-document ratification checks in vowner0906.py.

These four checks guard the numbers the OWNER acts on: how many axes the
licence gates under his plan (1), how many my unratified rule adds (7), how
many shed the blocker if he rejects it (6), and how many become newly scoreable
(0). They are the reason he would or would not spend money, so a check that
merely reports GREEN without ever having been made to fail is not acceptable
here.

Four things are proved:

  1. Mutating the value on the OWNER's side is caught.
  2. Mutating the value on lane M169's side is caught. This is the arm that
     matters most and the one a naive harness omits: it proves the source
     document is genuinely re-read on every run rather than the owner document
     being compared against a constant baked into the checker. A source quote
     silently going stale when its owning lane revises it is exactly the
     failure that has already occurred once in this program.
  3. Removing the row anchor is caught as 'row not found' rather than passing
     vacuously -- a check that cannot find its subject must fail, not skip.
  4. An unrelated edit is NOT caught, so the suite is not merely reacting to
     any change at all.

Nothing is written to the live tree; docs/ is copied to a scratch root and
vowner0906.py is pointed at the copy through argv[1].
"""
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VOWNER = ROOT / "experiments" / "ORCH-verify" / "vowner0906.py"
OWNER_REL = Path("docs") / "OWNER-ACTIONS.md"
M169_REL = Path("docs") / "research" / "M169-ratification-stakes.md"


def build_scratch():
    scratch = Path(tempfile.mkdtemp(prefix="orat-"))
    shutil.copytree(ROOT / "docs", scratch / "docs")
    src_exp = ROOT / "experiments"
    for p in src_exp.rglob("*"):
        if not p.is_file() or p.suffix.lower() not in (".md", ".json"):
            continue
        dst = scratch / "experiments" / p.relative_to(src_exp)
        if len(str(dst)) > 240:
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dst)
    return scratch


def run(root):
    p = subprocess.run([sys.executable, "-B", str(VOWNER), str(root)],
                       capture_output=True, text=True)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def red_has(out, fragment):
    """Did a RED line mentioning this check appear?"""
    return any(ln.startswith("RED") and fragment in ln
               for ln in out.splitlines())


def red_count(out):
    m = re.search(r"(?m)^GREEN:\s*(\d+)\s+RED:\s*(\d+)\s*$", out)
    if m is None:
        raise SystemExit("FATAL: could not read the verifier's GREEN/RED "
                         "summary; no arm below would be interpretable")
    return int(m.group(2))


def edit_once(path, old, new, label):
    text = path.read_text(encoding="utf-8", errors="replace")
    n = text.count(old)
    if n != 1:
        raise SystemExit("FATAL [%s]: anchor matched %d times, need exactly "
                         "1: %r" % (label, n, old))
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


# (label, target file, anchor, replacement, expected RED fragment or None)
CONTROLS = [
    ("owner-side value drift", OWNER_REL,
     "| **1 of 12** | M1 |",
     "| **4 of 12** | M1 |",
     "ratify plan licence prerequisite"),
    ("SOURCE-side value drift", M169_REL,
     "| Axes that lose `(d)` entirely | **6 of 12** |",
     "| Axes that lose `(d)` entirely | **8 of 12** |",
     "ratify axes shedding (d)"),
    ("owner row anchor removed", OWNER_REL,
     "become **newly scoreable**",
     "become newly countable",
     "ratify newly scoreable"),
    ("source row anchor removed", M169_REL,
     "Axes that become newly scoreable",
     "Axes that become newly tallied",
     "ratify newly scoreable"),
    ("INERT unrelated owner prose", OWNER_REL,
     "Read the last row before the others.",
     "Consider the last row before the others.",
     None),
]


def main():
    scratch = build_scratch()
    rc0, out0 = run(scratch)
    base = red_count(out0)
    shutil.rmtree(scratch, ignore_errors=True)
    print("baseline: rc=%d, RED=%d" % (rc0, base))
    if base != 0:
        print("NOTE: baseline is not clean; arms below are still read "
              "differentially by expected-fragment, but investigate.")
    print()

    caught = missed = inert_ok = inert_bad = 0
    for label, rel, old, new, expect in CONTROLS:
        scratch = build_scratch()
        edit_once(scratch / rel, old, new, label)
        rc, out = run(scratch)
        if expect is not None:
            hit = red_has(out, expect)
            print("%-28s %-16s [%r %s]"
                  % (label, "CAUGHT" if hit else "*** MISSED ***", expect,
                     "went RED" if hit else "STAYED GREEN"))
            caught += 1 if hit else 0
            missed += 0 if hit else 1
        else:
            n = red_count(out)
            quiet = n == base
            print("%-28s %-16s [RED %d vs baseline %d]"
                  % (label, "inert, survived" if quiet
                     else "*** INERT TRIPPED ***", n, base))
            inert_ok += 1 if quiet else 0
            inert_bad += 0 if quiet else 1
        shutil.rmtree(scratch, ignore_errors=True)

    planted = sum(1 for c in CONTROLS if c[4] is not None)
    inert = len(CONTROLS) - planted
    print("\ncaught %d, missed %d  (of %d planted)" % (caught, missed, planted))
    print("inert survived %d, inert tripped %d  (of %d inert)"
          % (inert_ok, inert_bad, inert))
    ok = (missed == 0 and inert_bad == 0
          and caught == planted and inert_ok == inert)
    print("VERDICT: " + ("COMMISSIONED" if ok else "NOT COMMISSIONED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

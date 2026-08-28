"""COMMISSION MY OWN VERIFIER AGAINST CONCLUSION FLIPS.

ORCH's item 3: a presence test cannot detect a reversed conclusion. V-LINEAR
tested its own harness and found the defect. This does the same to vr_recheck.py.

DESIGN. Six arms, each restoring from a $TEMP backup afterwards. Never
`git checkout --`. Every string mutation is anchored on a UNIQUE full line and
HARD-ERRORS if it does not land exactly once -- a mutation that silently fails
to apply produces a green that means nothing.

  NULL        no mutation                      -> must be GREEN, else harness dead
  FLIP-ROW    one row's verdict ACQUIT->CONVICT -> ?
  FLIP-HEAD   the headline count reversed       -> ?
  FLIP-NUM    report ratio 0.885 -> 1.885       -> ?   (report now contradicts
                                                        its own baseline AND
                                                        reverses the finding)
  POS-BASE    baseline master stat +10%         -> must be RED (potency)
  POS-DIR     masters dir empty                 -> must be RED (potency)

A planted defect that is CAUGHT proves the instrument can move. A conclusion
flip that is MISSED is the defect being hunted.
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "report.md")
BASE = os.path.join(HERE, "vr_baseline.json")
ONLY = "foam,coffee-bubbles"
TMP = os.environ.get("TEMP", tempfile.gettempdir())
BK_REPORT = os.path.join(TMP, "V-REVIEW.report.md.BAK")
BK_BASE = os.path.join(TMP, "V-REVIEW.vr_baseline.json.BAK")

FOAM_ROW = (b"| foam | blotch | 0.46075 | 0.52049 (max of 12) | **0.885** | ACQUIT |")
HEADLINE = b"**Nine ACQUIT, zero CONVICT.**"


def anchored(path, old, new, label):
    """Replace `old` with `new`, requiring EXACTLY ONE occurrence."""
    data = open(path, "rb").read()
    n = data.count(old)
    if n != 1:
        raise SystemExit(
            "MUTATION TARGET NOT FOUND (%s): %d occurrences of %r in %s. "
            "A mutation that does not land makes the arm meaningless."
            % (label, n, old[:70], os.path.basename(path)))
    open(path, "wb").write(data.replace(old, new, 1))
    after = open(path, "rb").read()
    assert new in after and old not in after, "mutation did not persist: " + label
    return True


def run(masters=None):
    cmd = [sys.executable, os.path.join(HERE, "vr_recheck.py"), "--only", ONLY]
    if masters:
        cmd += ["--masters", masters]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    tail = [l for l in r.stdout.splitlines() if l.startswith(("GREEN", "RED", "PARTITION"))]
    return r.returncode, " | ".join(tail)


shutil.copy2(REPORT, BK_REPORT)
shutil.copy2(BASE, BK_BASE)
print("backups: %s , %s\n" % (BK_REPORT, BK_BASE))

results = []
try:
    rc, tail = run()
    results.append(("NULL", "GREEN", rc, tail))

    anchored(REPORT, FOAM_ROW, FOAM_ROW.replace(b"ACQUIT", b"CONVICT"), "FLIP-ROW")
    rc, tail = run()
    results.append(("FLIP-ROW", "?", rc, tail))
    shutil.copy2(BK_REPORT, REPORT)

    anchored(REPORT, HEADLINE, b"**Zero ACQUIT, nine CONVICT.**", "FLIP-HEAD")
    rc, tail = run()
    results.append(("FLIP-HEAD", "?", rc, tail))
    shutil.copy2(BK_REPORT, REPORT)

    anchored(REPORT, FOAM_ROW, FOAM_ROW.replace(b"**0.885**", b"**1.885**"), "FLIP-NUM")
    rc, tail = run()
    results.append(("FLIP-NUM", "?", rc, tail))
    shutil.copy2(BK_REPORT, REPORT)

    b = json.load(open(BASE))
    old = b["subjects"]["foam"]["master"]["blotch"]
    b["subjects"]["foam"]["master"]["blotch"] = old * 1.10
    json.dump(b, open(BASE, "w"), indent=2)
    rc, tail = run()
    results.append(("POS-BASE", "RED", rc, tail))
    shutil.copy2(BK_BASE, BASE)

    empty = os.path.join(TMP, "vp_empty_masters")
    os.makedirs(empty, exist_ok=True)
    rc, tail = run(masters=empty)
    results.append(("POS-DIR", "RED", rc, tail))
finally:
    shutil.copy2(BK_REPORT, REPORT)
    shutil.copy2(BK_BASE, BASE)
    print("RESTORED report.md and vr_baseline.json from $TEMP backups\n")

print("%-11s %-8s %-5s %-8s %s" % ("arm", "expect", "exit", "verdict", "detail"))
missed = 0
for name, expect, rc, tail in results:
    green = (rc == 0)
    if expect == "GREEN":
        v = "OK" if green else "HARNESS-DEAD"
    elif expect == "RED":
        v = "CAUGHT" if not green else "BLIND"
    else:
        v = "MISSED" if green else "CAUGHT"
    if v in ("MISSED", "BLIND", "HARNESS-DEAD"):
        missed += 1
    print("%-11s %-8s %-5d %-8s %s" % (name, expect, rc, v, tail[:88]))
print("\narms that failed to do their job: %d of %d" % (missed, len(results)))

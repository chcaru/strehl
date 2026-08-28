"""RE-COMMISSION vr_recheck.py after the report binding. Eleven arms.

Each arm restores from a $TEMP backup. Every mutation is anchored on a unique
full line and HARD-ERRORS if it does not land exactly once.

The arm that matters most is RE-LICENSE. It flips the verdict AND the ratio
together so the report is INTERNALLY self-consistent under the 1.3x rule -- the
shape V-LINEAR found, where a flip re-licensed an arm with every number left
looking correct. Only a check bound to the MEASURED baseline can catch it; a
rule-consistency check alone cannot.
"""
import json, os, shutil, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.join(HERE, "report.md")
BASE = os.path.join(HERE, "vr_baseline.json")
ONLY = "foam,coffee-bubbles"
TMP = os.environ.get("TEMP", tempfile.gettempdir())
BK_R = os.path.join(TMP, "V-REVIEW.report.md.BAK2")
BK_B = os.path.join(TMP, "V-REVIEW.vr_baseline.json.BAK2")

ROW = b"| foam | blotch | 0.46075 | 0.52049 (max of 12) | **0.885** | ACQUIT |"
HEAD = b"**Nine ACQUIT, zero CONVICT.**"


def mutate(path, old, new, label):
    data = open(path, "rb").read()
    n = data.count(old)
    if n != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND (%s): %d occurrences" % (label, n))
    open(path, "wb").write(data.replace(old, new, 1))
    assert new in open(path, "rb").read(), "did not persist: " + label


def drop_line(path, marker, label):
    data = open(path, "rb").read()
    if data.count(marker) != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND (%s)" % label)
    i = data.index(marker)
    s = data.rfind(b"\n", 0, i) + 1
    e = data.index(b"\n", i) + 1
    open(path, "wb").write(data[:s] + data[e:])
    assert marker not in open(path, "rb").read(), "did not persist: " + label


def run(masters=None):
    cmd = [sys.executable, os.path.join(HERE, "vr_recheck.py"), "--only", ONLY]
    if masters:
        cmd += ["--masters", masters]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    key = [l.strip() for l in r.stdout.splitlines()
           if l.startswith(("GREEN", "RED", "   !")) or "bound" in l]
    return r.returncode, " | ".join(key)


shutil.copy2(REPORT, BK_R); shutil.copy2(BASE, BK_B)
res = []


def arm(name, expect, fn, masters=None):
    try:
        if fn:
            fn()
        rc, tail = run(masters)
    finally:
        shutil.copy2(BK_R, REPORT); shutil.copy2(BK_B, BASE)
    res.append((name, expect, rc, tail))


try:
    arm("NULL", "GREEN", None)
    arm("FLIP-ROW", "RED", lambda: mutate(REPORT, ROW, ROW.replace(b"ACQUIT", b"CONVICT"), "FLIP-ROW"))
    arm("FLIP-HEAD", "RED", lambda: mutate(REPORT, HEAD, b"**Zero ACQUIT, nine CONVICT.**", "FLIP-HEAD"))
    arm("FLIP-NUM", "RED", lambda: mutate(REPORT, ROW, ROW.replace(b"**0.885**", b"**1.885**"), "FLIP-NUM"))
    arm("SUBTLE-RATIO", "RED", lambda: mutate(REPORT, ROW, ROW.replace(b"**0.885**", b"**0.985**"), "SUBTLE"))
    arm("FLIP-SOURCE", "RED", lambda: mutate(REPORT, ROW, ROW.replace(b"0.52049", b"0.62049"), "FLIP-SRC"))
    arm("FLIP-NSRC", "RED", lambda: mutate(REPORT, ROW, ROW.replace(b"max of 12", b"max of 20"), "FLIP-N"))
    arm("DELETE-ROW", "RED", lambda: drop_line(REPORT, ROW, "DELETE-ROW"))
    # internally consistent: ratio 1.500 > 1.3 so CONVICT is "correct" by the rule
    arm("RE-LICENSE", "RED", lambda: mutate(
        REPORT, ROW,
        ROW.replace(b"**0.885**", b"**1.500**").replace(b"ACQUIT", b"CONVICT"), "RE-LIC"))

    def bump():
        b = json.load(open(BASE))
        b["subjects"]["foam"]["master"]["blotch"] *= 1.10
        json.dump(b, open(BASE, "w"), indent=2)
    arm("POS-BASE", "RED", bump)

    empty = os.path.join(TMP, "vp_empty_masters"); os.makedirs(empty, exist_ok=True)
    arm("POS-DIR", "RED", None, masters=empty)
finally:
    shutil.copy2(BK_R, REPORT); shutil.copy2(BK_B, BASE)
    print("RESTORED report.md and vr_baseline.json\n")

print("%-13s %-7s %-5s %-8s %s" % ("arm", "expect", "exit", "result", "why"))
bad = 0
for name, expect, rc, tail in res:
    green = rc == 0
    ok = green if expect == "GREEN" else not green
    v = ("OK" if expect == "GREEN" else "CAUGHT") if ok else ("HARNESS-DEAD" if expect == "GREEN" else "MISSED")
    if not ok:
        bad += 1
    print("%-13s %-7s %-5d %-8s %s" % (name, expect, rc, v, tail[:96]))
print("\narms failing to do their job: %d of %d" % (bad, len(res)))
sys.exit(1 if bad else 0)

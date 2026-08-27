"""Negative control for vn_verify65.py: plant defects, require RED on each.

vn_verify65 returning 44/44 green proves nothing on its own -- a checker that
cannot fail returns exactly the same output as one that has verified
everything. This plants one defect at a time into RESULT.md section 6.5 and
requires the checker to catch every one, plus a placebo edit OUTSIDE the
checked section that it must NOT flag.

Three rules learned from this lane's earlier negative controls, all of which
were themselves defective before they worked:

  * anchor every mutation on a UNIQUE FULL-LINE string and hard-error if it
    does not land exactly once -- a bare replace() can hit a different
    occurrence and report a green that means nothing;
  * key detection on the `FAILED:` block, never on a line containing the word
    MISMATCH or FAIL, because the checker's own summary line contains it and
    the placebo then reads as a false positive on every green run;
  * copy the file to %TEMP% and restore from that copy -- never
    `git checkout --`, which reverts to HEAD and destroys uncommitted work.

  python vn_negctl65.py
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DOC = os.path.join(HERE, "RESULT.md")
CHECKER = os.path.join(HERE, "vn_verify65.py")

# (label, unique full-line-or-cell anchor, mutated form)
PLANTS = [
    ("bee-2 blotch ratio", "| 0.00133 | 2.7897x", "| 0.00133 | 2.7898x"),
    ("bee-2 band ratio", "2.7897x | 2.6685x", "2.7897x | 2.6686x"),
    ("bee-2 abs blotch", "`bee-2-cpl` | 0.00133", "`bee-2-cpl` | 0.00134"),
    ("bee-2 excess", "| 1.948 | 1.675 | **+16%**", "| 1.949 | 1.675 | **+16%**"),
    ("bee-2 detail bound", "1.948 | 1.675 | **+16%**", "1.948 | 1.676 | **+16%**"),
    ("bee-2 over-bound pct", "**+16%** | 21 / 12 / 299", "**+17%** | 21 / 12 / 299"),
    ("flowers excess", "| 1.456 | 1.302 | **+12%**", "| 1.457 | 1.302 | **+12%**"),
    ("coffee-bubbles pct", "**+8%** | 19 / 19 / 19", "**+9%** | 19 / 19 / 19"),
    ("coffee-bean bound", "| 1.544 | 1.504 | **+3%**", "| 1.544 | 1.505 | **+3%**"),
    ("bee-2 admitted count", "| 21 / 12 / 299 |", "| 21 / 13 / 299 |"),
    ("bubbles full-stack row", "| 19 / 19 / 19 |", "| 19 / 18 / 19 |"),
    ("sample cap prose", "**21 frames per stack**", "**20 frames per stack**"),
    ("deep admitted prose", "**12, 17 and 18**", "**12, 17 and 19**"),
    ("deep depth prose", "stacks of 299, 176 and 105", "stacks of 299, 176 and 106"),
    ("draw-range prose", "12 to 18 draws", "12 to 17 draws"),
    ("subject substitution", "| `coffee-bean` | 0.00082", "| `foam` | 0.00082"),
    ("bubbles PROSE pct", "it still\nshows +8%", "it still\nshows +7%"),
]
# must NOT be caught: a real edit, outside the checked span
PLACEBO = ("placebo (outside 6.5)",
           "| `vn_negctl23.py` | negative control for that checker",
           "| `vn_negctl23.py` | NEGATIVE CONTROL for that checker")


def run():
    p = subprocess.run([sys.executable, CHECKER], capture_output=True,
                       text=True, cwd=HERE)
    out = p.stdout + p.stderr
    # Three states, not two. A CRASH is not a pass: the first version of this
    # control keyed only on the FAILED: block, so when a planted subject
    # substitution made the checker raise IndexError before printing anything,
    # the plant was scored green. Any traceback is now its own verdict.
    if "Traceback (most recent call last)" in out:
        return "CRASH", p.returncode, out
    if "FAILED:" in out:
        return "RED", p.returncode, out
    return "green", p.returncode, out


def main():
    backup = os.path.join(tempfile.gettempdir(), "vn_negctl65_RESULT.md.bak")
    shutil.copyfile(DOC, backup)
    with open(DOC, encoding="utf-8") as f:
        original = f.read()

    state0, rc0, _ = run()
    if state0 != "green" or rc0 != 0:
        print("FATAL: baseline is not green (%s rc=%d); fix the document first"
              % (state0, rc0))
        return 2

    rows, caught = [], 0
    try:
        for label, old, new in PLANTS + [PLACEBO]:
            n = original.count(old)
            if n != 1:
                print("FATAL: anchor %r occurs %d times, need exactly 1 "
                      "(%s)" % (old, n, label))
                return 2
            with open(DOC, "w", encoding="utf-8") as f:
                f.write(original.replace(old, new, 1))
            state, rc, out = run()
            want = "green" if label == PLACEBO[0] else "RED"
            ok = (state == want)
            if ok and want == "RED":
                caught += 1
            first = ""
            if state == "RED":
                tail = out.split("FAILED:", 1)[1].strip().splitlines()
                first = tail[0].strip()[:52] if tail else ""
            elif state == "CRASH":
                first = "checker raised; it did not report"
            rows.append((label, state, want,
                         "ok" if ok else "**DEFECT**", rc, first))
    finally:
        shutil.copyfile(backup, DOC)
        os.remove(backup)

    with open(DOC, encoding="utf-8") as f:
        if f.read() != original:
            print("FATAL: restore did not reproduce the original byte-for-byte")
            return 2

    print("%-24s %-6s %-6s %-11s %s" % ("plant", "got", "want", "verdict",
                                        "first finding"))
    for r in rows:
        print("%-24s %-6s %-6s %-11s %s" % (r[0], r[1], r[2], r[3], r[5]))
    bad = [r for r in rows if "DEFECT" in r[3]]
    crashes = [r for r in rows if r[1] == "CRASH"]
    print("\n%d/%d plants caught; placebo %s; %d crash(es); restore verified "
          "byte-identical"
          % (caught, len(PLANTS),
             "clean" if not any(r[0] == PLACEBO[0] and "DEFECT" in r[3]
                                for r in rows) else "FALSE POSITIVE",
             len(crashes)))
    state1, rc1, _ = run()
    if state1 != "green" or rc1 != 0:
        print("FATAL: document is not green again after restore")
        return 2
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

"""Can this lane's section 14 gates detect a REVERSED CONCLUSION?

ORCH's broadcast: V-NEVERWORSE's verifier tested for the PRESENCE of the
string "refuted" in a section, and flipping that section's verdict to
"confirmed" -- leaving every number intact -- passed 712 green checks. A
presence test cannot detect a reversed conclusion.

This lane's section 14 is guarded by two instruments, and they fail this test
in DIFFERENT ways, which is the point of running it:

  s14_splice.py --check  re-renders section 14 from `s14_body.md` plus the
                         generated tables and diffs it against the report. It
                         therefore catches a flip made in the REPORT alone --
                         but it compares the report to a source file, so a
                         flip made in BOTH moves the source and the copy
                         together and it sees nothing.

  verify_s14.py          re-derives every typed NUMBER from section 14's own
                         tables. A conclusion flip changes no number, so on
                         its own it is blind to all of these.

So the arms below are deliberately paired: ARM `report-only` should be caught
by the splice check, and ARM `both` is the real hole -- the mutation an author
would actually make, because an author edits the source and regenerates.

Every mutation is anchored on a UNIQUE full-line string and hard-errors if it
does not land. A negative control that silently fails to plant its defect
reports the instrument as healthy, which is the failure it exists to prevent.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.abspath(os.path.join(HERE, "..", "..", "..",
                                      "docs", "research", "BUILD-GATE-4.md"))
BODY = os.path.join(HERE, "s14_body.md")
TMP = os.environ["TEMP"]

# (name, file-set, unique anchor, replacement, what conclusion it reverses)
FLIPS = [
    ("orch-inference-report-only", ["report"],
     "   `k`=0.9 and `k`=1.0 arms, and `k` still moves grain by up to 3.89% and",
     "   `k`=0.9 and `k`=1.0 arms, and `k` still moves grain by up to 3.89% and",
     "control: identical text, must stay GREEN"),
    ("retraction-report-only", ["report"],
     "**I retract the sharpness cost I reported for the measured-floor fix.** I told",
     "**I CONFIRM the sharpness cost I reported for the measured-floor fix.** I told",
     "turns the section's retraction into a confirmation"),
    ("orch-holds-report-only", ["report"],
     "   threshold, it is the floor subtracted inside the weight law at every level.",
     "   threshold, it is the floor subtracted inside the weight law at no level.",
     "reverses where k acts"),
    ("retraction-both", ["report", "body"],
     "**I retract the sharpness cost I reported for the measured-floor fix.** I told",
     "**I CONFIRM the sharpness cost I reported for the measured-floor fix.** I told",
     "THE REAL HOLE: flips the retraction in the source AND the report"),
    ("reconciliation-both", ["report", "body"],
     "ORCH offered four reconciliations and asked which was right. It was **(a)**:",
     "ORCH offered four reconciliations and asked which was right. It was **(d)**:",
     "THE REAL HOLE: reverses which of ORCH's reconciliations was correct"),
]


def read(p):
    return open(p, encoding="utf-8", errors="strict").read()


def write(p, t):
    open(p, "w", encoding="utf-8", newline="").write(t)


def plant(path, old, new):
    t = read(path)
    n = t.count(old)
    if n != 1:
        raise SystemExit("MUTATION TARGET NOT FOUND (%d occurrences) in %s:\n"
                         "  %r" % (n, os.path.basename(path), old[:70]))
    write(path, t.replace(old, new, 1))


def gates():
    """Both section 14 gates. Returns (splice_ok, verify_ok)."""
    a = subprocess.run([sys.executable, os.path.join(HERE, "s14_splice.py"),
                        "--check"], capture_output=True, cwd=HERE)
    b = subprocess.run([sys.executable, os.path.join(HERE, "verify_s14.py")],
                       capture_output=True, cwd=HERE)
    return a.returncode == 0, b.returncode == 0


def main():
    bak = {"report": os.path.join(TMP, "negctl_concl_report.md"),
           "body": os.path.join(TMP, "negctl_concl_body.md")}
    src = {"report": REPORT, "body": BODY}
    for k in bak:
        shutil.copy2(src[k], bak[k])
    print("backed up report and body to %s\n" % TMP)

    base = gates()
    print("baseline: splice=%s verify=%s\n"
          % ("OK" if base[0] else "RED", "OK" if base[1] else "RED"))
    if not all(base):
        print("baseline is not green; aborting so a pre-existing failure is "
              "not read as a caught defect.")
        for k in bak:
            shutil.copy2(bak[k], src[k])
        return 1

    caught = missed = 0
    try:
        for name, files, old, new, what in FLIPS:
            control = (old == new)
            for f in files:
                plant(src[f], old, new)
            sp, ve = gates()
            ok = sp and ve
            by = []
            if not sp:
                by.append("splice")
            if not ve:
                by.append("verify")
            if control:
                verdict = "GREEN (correct: no change planted)" if ok \
                    else "RED -- CONTROL FAILED"
            elif ok:
                verdict = "**MISSED**"
                missed += 1
            else:
                verdict = "caught by %s" % "+".join(by)
                caught += 1
            print("%-28s %-52s %s" % (name, what[:52], verdict))
            for f in files:
                shutil.copy2(bak[f], src[f])
    finally:
        for k in bak:
            shutil.copy2(bak[k], src[k])

    post = gates()
    same = (read(REPORT) == read(bak["report"])
            and read(BODY) == read(bak["body"]))
    print("\nrestored byte-identical: %s   post-restore gates: splice=%s "
          "verify=%s" % (same, "OK" if post[0] else "RED",
                         "OK" if post[1] else "RED"))
    real = [f for f in FLIPS if f[3] != f[2]]
    print("%d caught / %d MISSED of %d conclusion flips"
          % (caught, missed, len(real)))
    if missed:
        print("\nVERDICT: the section 14 gates are BLIND to a reversed "
              "conclusion in the cases above.")
        return 1
    print("\nVERDICT: every conclusion flip was caught.")
    return 0 if same and all(post) else 1


if __name__ == "__main__":
    sys.exit(main())

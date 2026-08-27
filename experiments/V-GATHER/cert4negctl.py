r"""Negative controls for the four-axis certificate.

A verifier that has never been caught failing is not known to work. Each arm
plants a defect that SHOULD change the certificate and requires the change to
appear. Rules learned the hard way and enforced here:

  ANCHOR ON A UNIQUE FULL LINE. A bare substring replacement can land somewhere
  else entirely and produce a green that means nothing. Every mutation asserts
  its anchor occurs exactly once and hard-errors otherwise.

  REQUIRE THE MUTANT TO COMPILE. An earlier suite reported a catch that was
  really a SyntaxError: the harness saw a non-zero exit and called it detection.
  A crash is not a catch.

  RESTORE FROM A TEMP COPY, NEVER FROM GIT. `git checkout --` reverts to HEAD and
  has destroyed uncommitted work on this machine before.
"""
import hashlib
import io
import os
import py_compile
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CERT = os.path.join(HERE, "printcert4.py")

MUTS = [
    ("RIM-THRESH", os.path.join(HERE, "rimaxis.py"),
     "RIM_MAX = FLOOR_MAX_FWD = 0.02",
     "RIM_MAX = FLOOR_MAX_FWD = 0.90",
     "a rim threshold of 90% of the edge step cannot be exceeded by anything"),
    ("RIM-CI", CERT,
     "    if c > thr and lo > thr:",
     "    if c > thr or lo > thr:",
     "weakening the FAIL conjunction to a disjunction admits unresolved rims"),
    ("RIM-SMALLN", CERT,
     "RIM_SMALLN_ALLOW = 0.015",
     "RIM_SMALLN_ALLOW = 0.500",
     "a 50-point small-sample allowance excuses every small-n subject"),
    ("SHARP-THRESH", os.path.join(HERE, "sharpaxis.py"),
     "SHARP_MAX = 0.032",
     "SHARP_MAX = 0.900",
     "a 90% softness threshold cannot be exceeded"),
    ("DUST-THRESH", os.path.join(HERE, "dustaxis.py"),
     "DUST_MAX = 1.05",
     "DUST_MAX = 0.50",
     "a threshold below every measured ratio makes every subject fail"),
    ("REFUSED-AS-PASS", CERT,
     '        return "REFUSED", v["refused"]\n    d = v["deficit_median"]',
     '        return "PASS", v["refused"]\n    d = v["deficit_median"]',
     "a refusal reported as a pass is the exact defect this gate was built to "
     "avoid"),
    # A PLANTED DEFECT MUST LAND ON A BRANCH THAT ACTUALLY EXECUTES. The first
    # version of this arm mutated dust_verdict's REFUSED return -- but no
    # subject is REFUSED on the dust axis, so the mutation was inert and the
    # arm reported MISSED against a certificate that was in fact guarded. It
    # now mutates the PASS return, which all 26 subjects take.
    # A guard is commissioned by breaking the DATA IT PROTECTS, not by breaking
    # the guard. The first version of this arm disabled the sum check while the
    # partition was still correct, and correctly reported MISSED: there was
    # nothing to catch. These two arms are paired -- the truncation must be
    # caught, and must go unnoticed once the guard is removed. Only the pair
    # shows the guard is the thing doing the catching.
    ("PARTITION-TRUNCATE", CERT,
     '    return "PASS", "no trails at or above this axis\'s power limit: %s" % tail',
     '    return "OFF-PARTITION", "no trails at or above this axis\'s power limit: %s" % tail',
     "a verdict outside the declared partition must not vanish from the census"),
]

PAIRED = (
    "PARTITION-GUARD-IS-LOAD-BEARING",
    [(CERT,
      '    return "PASS", "no trails at or above this axis\'s power limit: %s" % tail',
      '    return "OFF-PARTITION", "no trails at or above this axis\'s power limit: %s" % tail'),
     (CERT,
      '    for a, t in zip(AXES, tot):\n        if t != n:',
      '    for a, t in zip(AXES, tot):\n        if t != n and False:')],
    "with the sum check removed the same truncation must survive undetected",
)


def run():
    p = subprocess.run([sys.executable, CERT], capture_output=True, text=True)
    return p.returncode, p.stdout


def partition(out):
    keep = []
    for ln in out.splitlines():
        t = ln.strip()
        if t.startswith(("PASS", "FAIL", "SUBJECT", "REFUSED", "NOT EXAMINED",
                         "TOTAL", "clean on all", "FAIL on at least")):
            keep.append(t)
    return "\n".join(keep)


def main():
    touched = sorted({m[1] for m in MUTS} | {e[0] for e in PAIRED[1]})
    pre = {f: hashlib.sha256(io.open(f, "rb").read()).hexdigest()
           for f in touched}
    rc, base = run()
    if rc != 0:
        print("BASELINE DOES NOT RUN (rc=%d); cannot commission" % rc)
        print(base[-800:])
        return 1
    bp = partition(base)
    if not bp.strip():
        raise SystemExit("BASELINE PARTITION EMPTY -- the probe reads nothing, "
                         "so a 'no change' result would be meaningless")
    print("baseline partition captured, %d significant lines\n"
          % len(bp.splitlines()))

    caught, missed = [], []
    tmp = tempfile.mkdtemp(prefix="v-gather-negctl-")
    try:
        for name, path, old, new, why in MUTS:
            src = io.open(path, encoding="utf-8").read()
            if src.count(old) != 1:
                raise SystemExit("MUTATION TARGET NOT FOUND for %s: anchor occurs "
                                 "%d times in %s" % (name, src.count(old), path))
            backup = os.path.join(tmp, name + "-" + os.path.basename(path))
            shutil.copy2(path, backup)
            try:
                io.open(path, "w", encoding="utf-8", newline="\n").write(
                    src.replace(old, new, 1))
                try:
                    py_compile.compile(path, doraise=True)
                except py_compile.PyCompileError as ex:
                    raise SystemExit("MUTANT %s DOES NOT COMPILE -- a crash is "
                                     "not a catch: %s" % (name, ex))
                mrc, mout = run()
                changed = (mrc != 0) or (partition(mout) != bp)
                (caught if changed else missed).append(name)
                print("  %-16s %s  %s" % (name, "CAUGHT " if changed else "MISSED ",
                                          why))
                if not changed:
                    print("       partition identical to baseline -- this "
                          "instrument is blind to the defect")
            finally:
                shutil.copy2(backup, path)
                py_compile.compile(path, doraise=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n  paired arm -- is the sum check load-bearing?")
    name, edits, why = PAIRED
    backups = []
    try:
        for path, old, new in edits:
            src = io.open(path, encoding="utf-8").read()
            if src.count(old) != 1:
                raise SystemExit("PAIRED ANCHOR NOT FOUND in %s: %d occurrences"
                                 % (path, src.count(old)))
            b = os.path.join(tempfile.gettempdir(),
                             "vg-paired-%d-%s" % (len(backups),
                                                 os.path.basename(path)))
            shutil.copy2(path, b)
            backups.append((path, b))
            io.open(path, "w", encoding="utf-8", newline="\n").write(
                src.replace(old, new, 1))
            py_compile.compile(path, doraise=True)
        prc, pout = run()
        survived = (prc == 0) and (partition(pout) != bp)
        print("  %-16s %s  %s" % (name, "CONFIRMED" if survived else "REFUTED ",
                                  why))
        if survived:
            print("       the truncated census exits 0 without the guard, so "
                  "the guard is what caught it")
            caught.append(name)
        else:
            print("       the truncation was still caught with the guard "
                  "removed, so something else is catching it and the guard is "
                  "not proven")
            missed.append(name)
    finally:
        for path, b in reversed(backups):
            shutil.copy2(b, path)
            os.remove(b)
            py_compile.compile(path, doraise=True)

    bad = [f for f in touched
           if hashlib.sha256(io.open(f, "rb").read()).hexdigest() != pre[f]]
    if bad:
        raise SystemExit("RESTORE FAILED -- these files do not hash to their "
                         "pre-mutation contents and the tree is CORRUPT:\n  "
                         + "\n  ".join(bad))
    print("\nrestore verified by SHA256: all %d mutated files byte-identical to "
          "their pre-mutation contents" % len(touched))
    rc2, after = run()
    if partition(after) != bp:
        print("NOTE: the certificate's partition moved during this run while the\n"
              "      sources were byte-identical, so a measurement file changed\n"
              "      underneath it (a sweep is still writing). Not a restore\n"
              "      failure; re-run the controls once the sweep has finished.")
    print("%d/%d arms caught" % (len(caught), len(MUTS) + 1))
    if missed:
        print("MISSED: " + ", ".join(missed))
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())

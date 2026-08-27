r"""Negative controls on printcert.py. Anchored mutations, hard-error on a miss.

A green from a mutation that silently failed to apply means nothing, so every
anchor here is a UNIQUE FULL LINE and a miss raises rather than warns. This lane
has already watched a control read GREEN because its anchor matched an earlier
line than intended, and watched an ORACLE arm read "ok" because a padding bug in
the harness meant the planted blur was not really blurred.

Each arm names the specific way the certification could be wrong, plants exactly
that, and requires the output to move. An arm that does not move under its own
mutation is testing nothing.
"""
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "printcert.py")

ARMS = [
    ("LABEL    rule flipped min->max",
     'BEST_RULE = "min over focus-qualified registered source frames"',
     'BEST_RULE = "max over focus-qualified registered source frames"',
     "master/worst-source",
     "the operator label must be DERIVED from the rule. If the header still "
     "reads best-source after the rule says max, the label is typed and can "
     "disagree with what was computed -- the defect that produced 9 acquittals."),

    ("LABEL    rule made underivable",
     'BEST_RULE = "min over focus-qualified registered source frames"',
     'BEST_RULE = "whatever the previous lane meant"',
     "cannot derive a label",
     "an unparseable rule must REFUSE, not fall through to a default label."),

    # NOTE: this anchor is the CLOSING line of a two-line statement. The first
    # version anchored the opening line and produced a SyntaxError instead of a
    # truncated population, so the arm reported MISS for a reason unrelated to
    # the check it was probing. A mutation must produce a RUNNING program that
    # is wrong, not a broken one -- a crash is indistinguishable from a catch.
    ("POP      population truncated to 20",
     "                        if f.endswith(\"--SHIP-V4.tiff\"))",
     "                        if f.endswith(\"--SHIP-V4.tiff\"))[:20]",
     "POPULATION DISAGREES WITH SEALS",
     "a short population must be caught by the independent seal census, not "
     "quietly re-normalised so that 20 of 20 reads complete."),

    ("PERMIT   unmeasured treated as passing",
     '            bucket, why = "REFUSED", "visible (%s) but no matched-gauge attribution measured" % "; ".join(vis)',
     '            bucket, why = "PASS", "visible (%s) but no matched-gauge attribution measured" % "; ".join(vis)',
     None,
     "a subject that is visibly mottled and has NO attribution evidence must "
     "not be certified. This arm requires the REFUSED count to fall and PASS "
     "to rise -- i.e. that the refusal is load-bearing."),

    ("MARGIN   margin raised beyond reach",
     "    margin, bias_rows = price_sampling_bias(cert)",
     "    margin, bias_rows = 1e9, []",
     None,
     "with an unreachable margin nothing can ever be attributed. If FAIL was "
     "already 0 this arm proves only that, and it says so."),
]


def run(path):
    p = subprocess.run([sys.executable, path], capture_output=True, text=True,
                       cwd=HERE)
    return p.returncode, p.stdout + p.stderr


def counts(out):
    d = {}
    for k in ("PASS", "FAIL", "SUBJECT", "REFUSED", "NOT EXAMINED"):
        m = re.search(r"^  %s\s+(\d+)$" % re.escape(k), out, re.M)
        if m:
            d[k] = int(m.group(1))
    return d


def main():
    rc0, base = run(SRC)
    if rc0 != 0:
        raise SystemExit("BASELINE DOES NOT RUN; controls would be meaningless\n" + base[-800:])
    c0 = counts(base)
    if not c0:
        raise SystemExit("BASELINE PARTITION NOT PARSEABLE -- controls cannot be scored")
    print("baseline partition: %s\n" % c0)

    src = io.open(SRC, encoding="utf-8").read()
    ok = True
    tmp = tempfile.mkdtemp(prefix="vg-negctl-")
    try:
        for name, anchor, repl, expect, why in ARMS:
            n = src.count(anchor)
            if n != 1:
                raise SystemExit("MUTATION TARGET NOT FOUND: %s occurs %d times, need 1\n  %r"
                                 % (name, n, anchor[:90]))
            path = os.path.join(tmp, "printcert.py")
            io.open(path, "w", encoding="utf-8", newline="\n").write(src.replace(anchor, repl))
            for extra in ("delivered.json", "cert.json"):
                s2 = os.path.join(HERE, extra)
                if os.path.exists(s2):
                    shutil.copy2(s2, os.path.join(tmp, extra))
            import py_compile
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as ex:
                raise SystemExit("MUTANT DOES NOT COMPILE: %s\n  %s" % (name, ex))
            rc, out = run(path)
            c = counts(out)

            if expect is not None:
                good = expect in out
                detail = "found %r" % expect if good else "expected %r, absent" % expect
            elif name.startswith("PERMIT"):
                good = c.get("REFUSED", -1) < c0.get("REFUSED", 0) and \
                    c.get("PASS", -1) > c0.get("PASS", 0)
                detail = "REFUSED %s->%s  PASS %s->%s" % (
                    c0.get("REFUSED"), c.get("REFUSED"), c0.get("PASS"), c.get("PASS"))
            else:
                moved = c != c0
                good = moved or c0.get("FAIL", 0) == 0
                detail = ("partition moved %s->%s" % (c0, c)) if moved else \
                    "partition unchanged; FAIL was already 0 so this arm is INERT here"
            ok = ok and good
            print("%-40s %-4s %s" % (name, "ok" if good else "MISS", detail))
            print("    %s" % why)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n%s" % ("ALL %d CONTROLS LANDED" % len(ARMS) if ok else
                    "A CONTROL DID NOT LAND -- the instrument is not commissioned"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

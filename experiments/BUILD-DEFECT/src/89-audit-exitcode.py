"""Commission the PASS/FAIL CHANNEL of every verifier this lane ships.

WHY THIS EXISTS, AND WHAT IT IS NOT.

`82-verify-s22.py --commission` and `88-verify-s23.py --commission` plant defects
and require them caught. Both do it by calling `verify()` IN-PROCESS and reading
the returned counters. Neither ever runs the thing an operator runs.

That is a hole with a name. If `main()` computed `ok` wrongly, or raised before
`SystemExit(2)`, or a caller invoked the script and read a zero exit that the
script could never have made non-zero, every in-process arm would still report
COMMISSIONED and every shipped invocation would report success on a corrupt
document. An inert plant and a dead instrument give the identical green, and an
in-process commissioning cannot tell them apart because it never touches the
channel the green travels on.

So each verifier is run HERE AS A SUBPROCESS, exactly as `python <script>` runs
it, and only its EXIT CODE is read. Three arms, which is the 2x2 with the two
zero-cells collapsed:

  CLEAN      the real document                     must exit 0
  PLANTED    one number changed in its section     must exit NON-ZERO
  INNOCUOUS  a sentence added that asserts nothing must exit 0

The third arm is the one that is usually missing, and it is the one ORCH named:
commissioning SENSITIVITY is not commissioning SPECIFICITY. Planting a defect
and seeing RED says nothing about whether the instrument is simply RED at
everything it is shown. A verifier that fails the INNOCUOUS arm is not strict,
it is broken -- it would block every future edit to its own section.

THE SEARCH FOR A PLANTED ANCHOR CAN FAIL, AND SAYS SO.

Sections 22 and 23 declare their own defect sets, so this script imports them
and uses the first entry that lands. Sections 18, 20 and 21 declare none -- they
have never been shown able to fail at all -- so an anchor is SEARCHED for among
the numbers in the section, bounded at MAX_CANDIDATES. If the bound is exhausted
without a single mutation turning the verifier red, that is reported as
NO-RED-FOUND and counted as a failure of that verifier, not as a pass of this
one. A search that cannot fail returns its least-bad candidate and calls it a
find.

THE DOCUMENT IS RESTORED FROM A COPY, NEVER FROM GIT.

`git checkout -- <path>` reverts to HEAD and would silently destroy any
uncommitted work in the file, including another arm's in-flight edit. The
original bytes are copied to the temp directory first and written back in a
`finally`, then compared byte-for-byte and reported.
"""
import filecmp

import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DOC = os.path.join(ROOT, "docs", "research", "BUILD-DEFECT.md")
OUTD = os.path.abspath(os.path.join(HERE, "..", "out"))

MAX_CANDIDATES = 14

# (script, section number). Every verifier this lane ships, none omitted: a
# harness audit that skipped the unaudited ones would be measuring only the
# instruments already known to be good.
VERIFIERS = [
    ("45-verify-s18.py", 18),
    ("63-verify-s20.py", 20),
    ("73-verify-s21.py", 21),
    ("82-verify-s22.py", 22),
    ("88-verify-s23.py", 23),
]

CONTROL_SENTENCE = (
    "\n\nThis paragraph is a specificity control inserted by "
    "`89-audit-exitcode.py`. It asserts no measurement, cites no artifact and "
    "changes no verdict, so a verifier that reddens on it is red at everything "
    "rather than strict.\n"
)

log = []


def say(s=""):
    print(s)
    log.append(s)


def read_doc():
    return io.open(DOC, encoding="utf-8", newline="").read()


def write_doc(text):
    with io.open(DOC, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def section_span(text, n):
    """Offsets of section n, from its heading to the next one (or EOF)."""
    a = text.find("\n## %d." % n)
    if a < 0:
        raise SystemExit("section %d not found in %s" % (n, DOC))
    b = text.find("\n## %d." % (n + 1), a)
    return a, (len(text) if b < 0 else b)


def run(script):
    """Run a verifier exactly as an operator would.

    Returns (exit_code, crashed). `crashed` separates two things that both
    arrive as a non-zero exit and are not the same fact:

      a TYPED REFUSAL   the verifier declined to certify because an input it
                        needs is absent, and said so. `73-verify-s21.py` does
                        this when the probe renders are missing. That is
                        correct behaviour -- the alternative is reporting
                        perfect agreement over zero comparisons -- but it means
                        the section is currently UNCERTIFIED, which must not be
                        allowed to read as either a pass or a broken verifier.

      a CRASH           an unhandled exception. Python prints a traceback, and
                        that is the only reliable way to tell the two apart:
                        `SystemExit("msg")` prints `msg` alone.

    A third signal is needed and the first version lacked it. `88-verify-s23.py`
    exits 2 to mean FAIL, with a full report on stdout and nothing on stderr --
    which the traceback rule alone mislabelled as a typed refusal. A verifier
    that got far enough to PRINT ITS REPORT was exercisable; it ran, and it said
    no. So the discriminator is whether a report was produced at all, and a
    refusal is only credited when the verifier never got that far.

    Collapsing these is the same error as collapsing FAIL with BINARY-DRIFTED in
    the reproduction check: one accusation covering two different facts, of
    which only one is a defect in the thing accused.
    """
    p = subprocess.run([sys.executable, os.path.join(HERE, script)],
                       cwd=ROOT, capture_output=True, text=True)
    crashed = "Traceback (most recent call last)" in (p.stderr or "")
    reported = bool((p.stdout or "").strip())
    return p.returncode, crashed, reported


def declared_defects(script):
    """A verifier's own DEFECTS list, read STATICALLY.

    The first version imported the module with `importlib` and caught
    `Exception`. Running it against `63-verify-s20.py` terminated this audit
    mid-run: that script has no `if __name__ == "__main__"` guard, so importing
    it EXECUTED it -- its output appeared on this process's stdout and its
    `SystemExit` propagated, because `SystemExit` derives from `BaseException`
    and not from `Exception`. The audit reported exit 0 having checked one
    verifier of five, which is the worst possible failure: a partial run wearing
    a success.

    Reading the literal out of the AST cannot execute anything, so it cannot be
    killed by what it is reading. That is the property worth having here, not
    the convenience of an import.
    """
    import ast
    src = io.open(os.path.join(HERE, script), encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "DEFECTS"
                   for t in node.targets):
            continue
        try:
            return list(ast.literal_eval(node.value))
        except (ValueError, SyntaxError):
            return []
    return []


def numeric_candidates(chunk):
    """Unique numbers in the section, as (old, new) last-digit mutations.

    Restricted to tokens of four digits or more. Short tokens recur by chance --
    a `2`, a `19`, a `0.5` -- and a mutation that lands on an unintended
    occurrence would report the verifier red for a reason this script did not
    choose, which is a plant that did not land wearing a pass.
    """
    out = []
    for tok in re.findall(r"\d[\d,]{3,}(?:\.\d+)?|\d+\.\d{3,}", chunk):
        tok = tok.rstrip(",")
        if not tok or not tok[-1].isdigit() or chunk.count(tok) != 1:
            continue
        last = tok[-1]
        new = tok[:-1] + ("0" if last == "9" else str(int(last) + 1))
        if (tok, new) not in out:
            out.append((tok, new))
    return out[:MAX_CANDIDATES]


def audit_one(script, sec, original):
    a, b = section_span(original, sec)
    chunk = original[a:b]
    row = {"script": script, "section": sec}

    # -- CLEAN ---------------------------------------------------------
    write_doc(original)
    row["clean_exit"], row["clean_crashed"], row["clean_reported"] = run(script)

    # -- INNOCUOUS (specificity) ---------------------------------------
    write_doc(original[:b] + CONTROL_SENTENCE + original[b:])
    row["innocuous_exit"], _, _ = run(script)

    # -- PLANTED (sensitivity), searched, and able to return nothing ----
    tried = 0
    planted_exit = None
    used = None
    cands = []
    for old, new, label in declared_defects(script):
        if original.count(old) == 1:
            cands.append((old, new, "declared: %s" % label))
    for old, new in numeric_candidates(chunk):
        cands.append((old, new, "searched: %s -> %s" % (old, new)))
    for old, new, label in cands:
        if tried >= MAX_CANDIDATES:
            break
        tried += 1
        mutated = original[:a] + chunk.replace(old, new, 1) + original[b:]
        if mutated == original:
            tried -= 1
            continue
        write_doc(mutated)
        planted_exit, _, _ = run(script)
        if planted_exit != 0:
            used = label
            break
        used = None
    row["planted_exit"] = planted_exit
    row["candidates_tried"] = tried
    row["anchor"] = used
    row["declared_own_defects"] = bool(declared_defects(script))

    write_doc(original)

    if row["clean_exit"] != 0:
        # A verifier that will not certify a clean document certifies nothing.
        # Which KIND of refusal it is decides whose defect it is: a crash, or a
        # verifier that ran and said no, are both the verifier's or the
        # document's -- but a refusal issued BEFORE any report was printed is
        # the evidence's, and naming it separately is the difference between
        # "this instrument is broken" and "this instrument has nothing to read".
        unexercisable = (not row["clean_crashed"]) and (not row["clean_reported"])
        row["verdict"] = "UNEXERCISABLE" if unexercisable else "BROKEN-CLEAN"
    elif row["innocuous_exit"] != 0:
        row["verdict"] = "RED-AT-EVERYTHING"
    elif planted_exit is None or planted_exit == 0:
        row["verdict"] = "NO-RED-FOUND"
    else:
        row["verdict"] = "OK"
    return row


def main():
    say("=== commission the pass/fail CHANNEL of every verifier, as a subprocess ===")
    say()
    original = read_doc()
    backup = os.path.join(tempfile.gettempdir(), "89-audit-BUILD-DEFECT.md.bak")
    shutil.copy2(DOC, backup)
    say("  original copied to %s  (restore is from this file, never from git)" % backup)
    say()

    rows = []
    try:
        for script, sec in VERIFIERS:
            r = audit_one(script, sec, original)
            rows.append(r)
            say("  %-20s clean %d | innocuous %d | planted %s (%d tried) -> %s"
                % (script, r["clean_exit"], r["innocuous_exit"],
                   "none" if r["planted_exit"] is None else str(r["planted_exit"]),
                   r["candidates_tried"], r["verdict"]))
            if r["anchor"]:
                say("      %-16s %s" % ("", r["anchor"]))
    finally:
        shutil.copy2(backup, DOC)

    identical = filecmp.cmp(backup, DOC, shallow=False)
    say()
    say("  document restored byte-identical: %s" % identical)

    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    parts = " + ".join("%d %s" % (v, k) for k, v in sorted(tally.items()))
    say("  %d verifiers = %s" % (len(rows), parts))
    if sum(tally.values()) != len(rows):
        raise SystemExit("partition does not sum")

    n_own = sum(1 for r in rows if r["declared_own_defects"])
    say("  %d of %d declare their own defect set; %d were commissioned here for "
        "the first time" % (n_own, len(rows), len(rows) - n_own))

    ok = identical and tally.get("OK", 0) == len(rows)
    say()
    say("VERDICT: %s" % ("CHANNEL-LIVE" if ok else "CHANNEL-SUSPECT"))
    io.open(os.path.join(OUTD, "89-audit-exitcode.json"), "w",
            encoding="utf-8").write(json.dumps(
                dict(rows=rows, restored_identical=identical, tally=tally,
                     declare_own=n_own,
                     verdict="CHANNEL-LIVE" if ok else "CHANNEL-SUSPECT"),
                indent=2))
    io.open(os.path.join(OUTD, "89-audit-exitcode.log"), "w",
            encoding="utf-8").write("\n".join(log) + "\n")
    if not ok:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

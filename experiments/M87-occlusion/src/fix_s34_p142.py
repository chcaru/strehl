"""M87 -- fold the exit-code engine result into the report.

Three edits, each anchored on a unique single line and each hard-erroring if
its anchor does not land (a mutation that silently does nothing is how a
"green" gets manufactured):

  1. annotate `P141` in place -- its race clause was measured under
     `powershell -File` and is true there, but it was stated as a property of
     PowerShell.  Scoped, not deleted.
  2. add fact `P142`.
  3. add the §34.9 paragraph, before the "Three limits" anchor so the
     disclosures accumulate in order.

Every figure here is printed by verify_exitcode_2x2.py from the probe JSON;
none is transcribed from a terminal by hand.
"""
import os
import pathlib
import shutil
import sys

DOC = pathlib.Path(__file__).resolve().parents[3] / "docs" / "research" / "M87-occlusion.md"

MINUS = "\u2212"

P141_ANCHOR = (
    "which confirms the race framing over the count framing by direct "
    "observation. | MEASURED |"
)
P141_NEW = (
    "which confirms the race framing over the count framing by direct "
    "observation. **Scoped by `P142`:** both readings are properties of "
    "`PSVersion 5.1`, not of PowerShell -- on 7.6.5 the loss is deterministic "
    "and the corrupted value is 0. Annotated, not retracted. | MEASURED |"
)

P142_ROW = (
    "| P142 | **Which mechanism governs `-First`'s exit-code loss is decided "
    "by the PowerShell engine -- not by counts, races, or process style: "
    "2880 observations across a 2x2 and a causal manipulation.** The strict "
    "quota model holds at **720 of 720** observations on PowerShell 7.6.5 and "
    "**587 of 720** on Windows PowerShell 5.1.26100.9168, failing in the same "
    "6 of 9 arms whether run as a child process or dot-sourced in-process. "
    "Quota is necessary in both engines: the arms it predicts safe lost "
    "**0 of 1040**. Making the emitter sleep 300 ms after its last line drives "
    "5.1 from 80.00% and 75.00% to **100.00%** at both volumes, while 7.6.5 "
    "stays flat at 100.00%. | Both published mechanisms are right about their "
    "own host and neither generalises, so `P141`'s race clause is scoped "
    "rather than retracted. The consequence that bites is the corrupted "
    "*value*, not the rate: 7.6.5 yields **0** and 5.1 yields **&#8722;1**, so "
    "the guard `if ($code -ne 0) { throw }` catches the trap on one engine and "
    "silently passes it on the other -- the one the agent shell runs. A guard "
    "verified on a single host is not verified. | MEASURED |"
)

PARA_ANCHOR = "Three limits, stated rather than buried."

PARA = """**And the race framing I just certified is itself engine-scoped.** The rule
was corrected a second time -- deterministic on quota, no volume threshold,
`-First 51` over 50 objects safe -- which contradicts the run-to-run variation
above. Rather than pick an authority, the disagreement was measured as a 2x2:
engine (Windows PowerShell **5.1.26100.9168** against PowerShell **7.6.5**)
crossed with process style (child `-File` against dot-sourced in-process),
nine arms each, 40 repetitions, **1440 observations**.

**The engine is the whole variable and process style contributes nothing.** On
7.6.5 the strict quota model holds at **720 of 720** observations, in a child
and in-process alike. On 5.1 it holds at **587 of 720**, and fails in the same
**6 of 9** arms in both process styles. Quota is **necessary in both**: across
every arm the model predicts safe -- `-First 51` over 50 objects, and
`-Last 3` -- **0 of 320** observations lost the code.

That reconciles the two rules, but only by naming the 5.1 variation rather
than explaining it. The race account says the loss needs the short-circuit to
land while the native process is **still running**, and that is manipulable:
make the emitter sleep after its last line but before it exits. Four
predictions were registered before the data existed -- that on 5.1 the rate
rises with sleep and reaches 100%, that on 7.6.5 sleep changes nothing, and
that the non-quota arms stay at zero at every sleep, because a manipulation
that makes a *safe* shape start losing is not selective and would invalidate
the rest.

**All four held.** On 5.1, `-First 3` loses the code at **80.00% -> 96.67% ->
100.00%** at 5 lines and **75.00% -> 98.33% -> 100.00%** at 50 lines, for
sleeps of 0, 50 and 300 ms. On 7.6.5 it is 100.00% at every sleep.
The six negative-control arms lost **0 of 720**. So on 5.1 the loss is
quota-gated *and* racy, and forcing the process to still be running collapses
it onto exactly the determinism 7.6.5 shows unconditionally. Volume is a proxy
for the same thing and a poor one: pooled over both 5.1 styles the rate runs
**60.00%** at 5 lines, **82.50%** at 10, **77.50%** at 50, **76.25%** at 200
and **100.00%** at 5000 -- ordered at the extremes, flat and out of order in
the middle, which is why no volume threshold was ever going to be found.

**The operationally dangerous half of this is the value, not the rate.** 7.6.5
corrupts the code to exactly **0**; 5.1 corrupts it to **""" + MINUS + """1**. The guard
published with the rule, `if ($code -ne 0) { throw }`, therefore *catches* the
trap on 5.1 and is *guaranteed* to pass it silently on 7.6.5 -- and 7.6.5 is
the shell these milestones are driven from. The two engines fail in opposite
directions, so no single-host test can establish that a guard is safe, and the
gates in §29-§34 are safe for the stronger reason that they never form the
pipeline at all.

**What this costs me.** `P141`'s race clause was measured under `powershell
-File`, so it is true where it was taken and it is not retracted; but it was
written as a property of PowerShell when it is a property of 5.1, and it is
annotated in place. The same holds in the other direction for the rule I was
given: its quota table is correct in the shell it was measured in. Neither
reading was wrong about its own data. Both generalised one host to the
platform -- the same error, in the same week, from opposite sides, and the
only thing that separated them was crossing the factor instead of arguing
about it."""


def check_row(row):
    bare = row.replace("\\|", "")
    npipe = bare.count("|")
    if npipe != 5:
        sys.exit("FACT ROW has %d unescaped pipes, need 5" % npipe)
    if row.count("`") % 2 != 0:
        sys.exit("FACT ROW has an odd backtick count (%d)" % row.count("`"))


def main():
    if not DOC.exists():
        sys.exit("%s not found" % DOC)

    raw = DOC.read_bytes().decode()
    assert raw.count("\n") == raw.count("\r\n"), "document is not pure CRLF"

    if "| P142 |" in raw:
        print("P142 already present -- nothing to do")
        return

    check_row(P142_ROW)
    if PARA.count("`") % 2 != 0:
        sys.exit("PARAGRAPH has an odd backtick count (%d)" % PARA.count("`"))

    backup = pathlib.Path(os.environ["TEMP"]) / "M87-occlusion.before-p142.md"
    shutil.copy2(DOC, backup)
    print("backed up to %s" % backup)

    # --- 1. scope P141 -------------------------------------------------
    if raw.count(P141_ANCHOR) != 1:
        sys.exit("P141 ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(P141_ANCHOR))
    raw = raw.replace(P141_ANCHOR, P141_NEW, 1)

    # --- 2. add the paragraph, before the "Three limits" anchor --------
    if raw.count(PARA_ANCHOR) != 1:
        sys.exit("PARA ANCHOR NOT FOUND EXACTLY ONCE (%d)" % raw.count(PARA_ANCHOR))
    body = "\r\n".join(PARA.split("\n"))
    raw = raw.replace(PARA_ANCHOR, body + "\r\n\r\n" + PARA_ANCHOR, 1)

    # --- 3. add P142 directly beneath the P141 row ---------------------
    lines = raw.split("\r\n")
    idx = [n for n, l in enumerate(lines) if l.startswith("| P141 |")]
    if len(idx) != 1:
        sys.exit("expected exactly one P141 row, found %d" % len(idx))
    lines.insert(idx[0] + 1, P142_ROW)
    raw = "\r\n".join(lines)

    assert raw.count("\n") == raw.count("\r\n"), "CRLF broken by amendment"
    DOC.write_bytes(raw.encode())

    after = DOC.read_bytes().decode()
    assert after.count("\n") == after.count("\r\n"), "CRLF broken on disk"
    for probe in ("| P142 |", "**Scoped by `P142`:**",
                  "The engine is the whole variable"):
        if probe not in after:
            sys.exit("POST-WRITE CHECK FAILED: %r missing" % probe)
    print("added P142 and the 34.9 paragraph; %d lines" % (after.count("\n") + 1))


if __name__ == "__main__":
    main()

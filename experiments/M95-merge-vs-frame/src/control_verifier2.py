"""Negative control for verify_report.py -- discipline 594 applied to the checker.

A verifier that passes is only evidence if it could have failed. This plants a
single wrong digit into a copy of the report, runs the verifier against the
copy, and requires a RED.

Three lessons are baked in, each of which this control found the hard way:

1. The anchor must be UNIQUE and must HARD-ERROR when it does not land. A
   mutation that silently misses produces a green that means nothing. An early
   run mutated the headline's "0 DN" and stayed green, because the verifier was
   checking a bare substring that also occurred in a table lower down -- the
   single most load-bearing number in the report was uncovered.

2. The anchor must tolerate LINE WRAP. Report prose is hard-wrapped, so
   'spans **3.2015x** across the stack' does not exist as a literal: the break
   falls between 'across' and 'the'. Anchors are therefore compiled to regexes
   with every whitespace run replaced by \\s+, and the substitution is spliced
   back into the matched span so the original wrapping survives.

3. The report is copied to $env:TEMP and restored from that copy -- never
   `git checkout --`, which reverts to HEAD.
"""
from __future__ import annotations
import os, re, shutil, subprocess, sys, tempfile

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
REPORT = os.path.join(ROOT, "docs", "research", "M95-merge-vs-frame-sharpness.md")
VERIFY = os.path.join(ROOT, "experiments", "M95-merge-vs-frame", "src", "verify_report.py")

# (anchor, old token inside the anchor, new token, label)
MUTATIONS = [
    ("maximum difference 0 DN of 65535", "0 DN", "1 DN", "P1 headline max-diff"),
    ("combinations, 100.0000 % exact", "100.0000", "100.0001", "P1 headline exact-pct"),
    ("180,697 pixels across 47 frame/ROI", "180,697", "180,698", "P1 headline pixel count"),
    ("180,697 pixels across 47 frame/ROI", "47", "46", "P1 headline pair count"),
    ("| **2.65×** | **85.8 %** |", "2.65", "2.66", "P5 G1-G2 ratio"),
    ("| **2.65×** | **85.8 %** |", "85.8", "85.9", "P5 scene share"),
    ("**σ = 0.2558 px**", "0.2558", "0.2559", "P9 resample sigma"),
    ("**99.9763 %** exact, residual rms", "99.9763", "99.9764", "P15 loader (control site)"),
    ("to **99.9763 %** exact, max **1 DN**", "99.9763", "99.9764", "P15 loader (fact site)"),
    ("spans **3.2015×** with focus", "3.2015", "3.2016", "P8 plateau (prose site)"),
    ("it spans **3.2015×** across the stack", "3.2015", "3.2016", "P8 plateau (fact site)"),
    ("**0.421–0.616 at the binned Nyquist**", "0.616", "0.617", "P6 MTF at binned Nyquist"),
    ("| MTF @ 74 cy/mm (M85's floor) | **0.175** | **0.432** |", "0.175", "0.176", "P6 MTF@74 table"),
    ("minimum fraction exact **1.000000**", "1.000000", "1.000001", "P1 fact min-exact"),
    ("| **1.09×** | 15.1 %", "1.09", "1.10", "P5 flat control ratio (table)"),
    ("against **1.09×** in a defocused control", "1.09", "1.10", "P5 flat ratio (headline)"),
    ("flat control reads **1.09×** (15.1 %)", "1.09", "1.10", "P5 flat ratio (fact)"),
    ("the same statistic reads 1.09×", "1.09", "1.10", "P5 flat ratio (prose)"),
]


def run_verifier():
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, VERIFY], capture_output=True, env=env,
                       cwd=os.path.dirname(os.path.dirname(VERIFY)))
    return p.returncode, (p.stdout + p.stderr).decode("utf-8", "replace")


def _rx(s):
    """Compile a literal into a regex tolerant of line wrap AND of an
    intervening blockquote marker. The report's headline is a blockquote, so a
    wrapped phrase there reads 'in a\\n> defocused control'; joining tokens on
    \\s+ alone matches zero times and the control then reports a bogus
    'anchor not unique'."""
    return re.compile(r"\s+(?:>\s*)?".join(re.escape(t) for t in s.split()))


def mutate(text, anchor, old, new, label):
    """Locate `anchor` tolerant of line wrap; replace `old` with `new` inside it."""
    hits = list(_rx(anchor).finditer(text))
    if len(hits) != 1:
        raise SystemExit(
            f"MUTATION ANCHOR NOT UNIQUE for {label!r}: matched {len(hits)} times")
    span = hits[0].group(0)
    orx = _rx(old)
    if len(list(orx.finditer(span))) != 1:
        raise SystemExit(
            f"MUTATION TOKEN NOT UNIQUE inside anchor for {label!r}: {old!r} in {span!r}")
    mutated_span = orx.sub(new, span, count=1)
    assert mutated_span != span, label
    return text[: hits[0].start()] + mutated_span + text[hits[0].end():]


def main() -> int:
    backup = os.path.join(tempfile.gettempdir(), "M95-report-backup.md")
    shutil.copyfile(REPORT, backup)
    print(f"backup -> {backup}")
    original = open(REPORT, encoding="utf-8").read()

    rc, out = run_verifier()
    print(f"\nBASELINE (unmutated): rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    if rc != 0:
        print(out[-2000:])
        raise SystemExit("baseline is not green -- fix the report before controlling")

    missed = []
    try:
        for anchor, old, new, label in MUTATIONS:
            open(REPORT, "w", encoding="utf-8").write(
                mutate(original, anchor, old, new, label))
            rc, out = run_verifier()
            red = rc != 0
            n = len(re.findall(r"^  FAIL", out, re.M))
            print(f"  {'OK  ' if red else 'MISS'}  {label:32s} {old!r} -> {new!r}: "
                  f"{'RED' if red else 'GREEN'} ({n} FAIL line(s))")
            if not red:
                missed.append(label)
            open(REPORT, "w", encoding="utf-8").write(original)
    finally:
        open(REPORT, "w", encoding="utf-8").write(original)
        assert open(REPORT, encoding="utf-8").read() == original, "restore failed"
        print("\nreport restored byte-identical to pre-control state")

    rc, _ = run_verifier()
    print(f"POST-RESTORE: rc={rc}  {'GREEN' if rc == 0 else 'RED'}")
    if missed or rc != 0:
        print(f"\nCONTROL FAILED -- mutations the verifier did not catch: {missed}")
        return 1
    print(f"\nCONTROL PASSED: {len(MUTATIONS)}/{len(MUTATIONS)} planted wrong digits "
          f"caught, and the report is green when unmutated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Append section 25.7 to the M95 report, byte-safe, refusing to duplicate."""
import io
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
REPORT = os.path.join(ROOT, "docs", "research", "M95-kernel.md")
MARKER = "### 25.7 The audit's best finding was against the auditor"

SECTION = """
### 25.7 The audit's best finding was against the auditor

Appending §25 broke `verify_s24.py`. It exited **2** with
`TOOL FAILURE: expected exactly 1 results row for C1, found 2`.

The immediate cause was a label collision: §25's control table originally named
its six controls `A1`/`B1`/`C1`/`A2`/`A3`/`B2`, and `verify_s24.py` finds a §24
results row by scanning for a line that begins with the bar's name between
pipes. The new table supplied a second such line for `C1`.

**But the collision is the symptom, not the defect.** The gate sliced the report
from §24's heading to the *end of the file*. Its docstring promised to match a
line in section 24; what it actually matched was a line in section 24 or in
anything ever appended below it. **A verifier of that shape is a time bomb: it
passes every run until someone adds the next section, and then it indicts a
report that has not changed.** This report has had sections appended five times.

Both layers are fixed. The slice is now bounded at the next top-level heading,
and the controls are renamed `G-A1` through `G-B2` so the token cannot recur.

**The gate failed closed, which is the only reason this is a finding and not a
silent corruption.** It exited 2 -- tool failure -- rather than 0 or 1, refusing
to report on a table it could not uniquely identify. That behaviour was installed
in §24.9 after a measured miss, and this is the first time it has paid.

**Guard against a fix that is really a weakening.** Narrowing a gate's search
window is exactly the edit that makes a red turn green for the wrong reason, so
the negative control was re-run afterwards: `negctl_s24.py` catches **7/7 subject
defects and 2/2 tool defects** and restores the report **byte-exact**. The gate is
narrower and no less sensitive.

There is a lesson here that generalises past this repository. **The audit I ran to
check ORCH's discipline 768 found nothing wrong with the thing it was pointed at
and something wrong with two of my own instruments** -- check A's pipe handling in
§25.2, and this. Both were invisible while the reports were static. Neither would
have been found by re-reading the prose.
"""


def main():
    with io.open(REPORT, "r", encoding="utf-8", newline="") as fh:
        body = fh.read()

    if MARKER in body:
        print("ALREADY APPENDED -- refusing to duplicate")
        return 2

    crlf = body.count("\r\n")
    lf_only = body.count("\n") - crlf
    nl = "\r\n" if crlf > lf_only else "\n"

    draft = SECTION.replace("\r\n", "\n").replace("\n", nl)
    if not body.endswith(nl):
        body += nl
    out = body + draft

    with io.open(REPORT, "w", encoding="utf-8", newline="") as fh:
        fh.write(out)

    ctrl = [c for c in out if ord(c) < 32 and c not in "\r\n\t"]
    print(f"line ending: {'CRLF' if nl == chr(13) + chr(10) else 'LF'}")
    print(f"before {len(body)} bytes, draft {len(draft)}, after {len(out)}")
    print(f"section 25.7 present: {MARKER in out}")
    print(f"control bytes introduced: {len(ctrl)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

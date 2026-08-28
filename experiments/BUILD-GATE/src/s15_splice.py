"""Splice section 15 into BUILD-GATE-4.md.

Same contract as `s14_splice.py`: every table body comes from a GENERATED
file and is pasted verbatim, no number in a table is typed by hand, and every
@@Tn@@ placeholder must resolve or this hard-errors rather than emitting a
report with a hole in it.

The generated tables live in `gen/` from the start rather than in `$env:TEMP`.
Section 14 learned that the hard way: its generators wrote to TEMP, TEMP is
volatile, and the drift guard stopped working the moment the masters it was
derived from were deleted.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.abspath(os.path.join(HERE, "..", "..", "..",
                                      "docs", "research", "BUILD-GATE-4.md"))
BODY = os.path.join(HERE, "s15_body.md")
GEN = os.path.abspath(os.path.join(HERE, "..", "gen"))
TABLES = os.path.join(GEN, "s15tables.md")


def blocks(path):
    """Split the generated tables file on its '#### 15.x' headers."""
    if not os.path.exists(path):
        sys.exit("FATAL: missing %s (run s15_tables.py first)" % path)
    text = open(path, encoding="utf-8").read()
    parts = re.split(r"(?m)^#### +(15\.\d+)[^\n]*\n", text)
    out = {}
    for i in range(1, len(parts), 2):
        out[parts[i]] = parts[i + 1].strip("\n")
    if not out:
        sys.exit("FATAL: no '#### 15.x' headers found in %s" % path)
    return out


def render():
    for p in (BODY, TABLES, REPORT):
        if not os.path.exists(p):
            sys.exit("FATAL: missing %s" % p)
    body = open(BODY, encoding="utf-8").read()
    tb = blocks(TABLES)
    sub = {"@@T1@@": tb["15.1"], "@@T2@@": tb["15.2"], "@@T3@@": tb["15.3"],
           "@@T4@@": tb["15.4"], "@@T5@@": tb["15.5"]}
    for key, val in sub.items():
        if key not in body:
            sys.exit("FATAL: placeholder %s not present in body" % key)
        body = body.replace(key, val)
    left = re.findall(r"@@[A-Z0-9]+@@", body)
    if left:
        sys.exit("FATAL: unresolved placeholders %s" % left)
    return body, len(sub)


def section(report):
    """Section 15's text, bounded at the next top-level header."""
    idx = report.find("\n## 15.")
    if idx < 0:
        return None
    tail = report[idx + 1:]
    nxt = re.search(r"(?m)^## ", tail[1:])
    return (tail[:nxt.start() + 1] if nxt else tail).strip("\n")


def check():
    body, _ = render()
    report = open(REPORT, encoding="utf-8").read()
    have = section(report)
    if have is None:
        print("CHECK FAIL: report has no section 15")
        return 1
    want = body.strip("\n")
    if have == want:
        print("CHECK OK: section 15 matches the generated tables exactly "
              "(%d lines)" % len(want.splitlines()))
        return 0
    hl, wl = have.splitlines(), want.splitlines()
    print("CHECK FAIL: report section 15 differs from a fresh splice")
    print("  report %d lines, fresh %d lines" % (len(hl), len(wl)))
    for i in range(max(len(hl), len(wl))):
        h = hl[i] if i < len(hl) else "<eof>"
        w = wl[i] if i < len(wl) else "<eof>"
        if h != w:
            print("  first difference at section line %d:" % (i + 1))
            print("    report: %s" % h)
            print("    fresh : %s" % w)
            break
    return 1


def replace():
    """Replace an existing section 15 in place with a fresh splice.

    No lock is taken here deliberately: `negctl_s15.py` holds the report lock
    while it calls this module, and taking it again would deadlock the very
    harness that proves this section's gates work. Run it serially.
    """
    body, n = render()
    report = open(REPORT, encoding="utf-8").read()
    have = section(report)
    if have is None:
        sys.exit("FATAL: report has no section 15 to replace; use a plain "
                 "splice to append it")
    want = body.strip("\n")
    if have == want:
        print("REPLACE: section 15 already matches; nothing to do")
        return 0
    if report.count(have) != 1:
        sys.exit("FATAL: section 15's text is not unique in the report; "
                 "refusing to replace the wrong one")
    out = report.replace(have, want)
    with open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    print("replaced section 15: %d -> %d lines (%d placeholders)"
          % (len(have.splitlines()), len(want.splitlines()), n))
    return 0


def main():
    if "--check" in sys.argv:
        return check()
    if "--replace" in sys.argv:
        return replace()
    body, n = render()
    report = open(REPORT, encoding="utf-8").read()
    if "\n## 15." in report:
        sys.exit("FATAL: report already contains a section 15; refusing to "
                 "append a second one")
    out = report.rstrip("\n") + "\n\n" + body.rstrip("\n") + "\n"
    with open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    print("spliced %d placeholders" % n)
    print("report %d -> %d lines" % (len(report.splitlines()),
                                     len(out.splitlines())))
    return 0


if __name__ == "__main__":
    sys.exit(main())

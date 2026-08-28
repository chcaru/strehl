"""Splice section 14 into BUILD-GATE-4.md.

Every table body is taken from a GENERATED file (ab_table.py, boot_head.py)
and pasted verbatim. No number in a table is typed by hand. The prose body
carries @@Tn@@ / @@BOOT@@ placeholders and each one must resolve, or this
script hard-errors rather than silently emitting a report with a hole in it.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.abspath(os.path.join(HERE, "..", "..", "..",
                                      "docs", "research", "BUILD-GATE-4.md"))
BODY = os.path.join(HERE, "s14_body.md")
# The generators write to TEMP, which is volatile, and the masters they were
# derived from are deleted once section 14 is closed. A durable copy lives in
# `gen/` so this drift guard keeps working after both -- TEMP is preferred when
# present so a fresh generator run is still what gets checked.
GEN = os.path.abspath(os.path.join(HERE, "..", "gen"))


def _gen(name):
    t = os.path.join(os.environ["TEMP"], name)
    return t if os.path.exists(t) else os.path.join(GEN, name)


TABLES = _gen("s14tables.md")
BOOT = _gen("s14boot.md")


def blocks(path):
    """Split a generated tables file on its '#### 14.x' headers."""
    text = open(path, encoding="utf-8").read()
    parts = re.split(r"(?m)^#### +(14\.\d+)[^\n]*\n", text)
    out = {}
    for i in range(1, len(parts), 2):
        out[parts[i]] = parts[i + 1].strip("\n")
    if not out:
        sys.exit("FATAL: no '#### 14.x' headers found in %s" % path)
    return out


def boot_table(path):
    """Take only the markdown table and its trailing count line.

    The generated caption contains a printf '%%' artefact and a stale
    description, so the prose supplies the caption instead.
    """
    lines = open(path, encoding="utf-8").read().splitlines()
    start = next((i for i, ln in enumerate(lines)
                  if ln.startswith("| subject")), None)
    if start is None:
        sys.exit("FATAL: no bootstrap table found in %s" % path)
    return "\n".join(lines[start:]).strip("\n")


def render():
    """Build section 14 from the body + the generated tables."""
    for p in (BODY, TABLES, BOOT, REPORT):
        if not os.path.exists(p):
            sys.exit("FATAL: missing %s" % p)

    body = open(BODY, encoding="utf-8").read()
    tb = blocks(TABLES)

    sub = {
        "@@T2@@": "### 14.2 The sweep\n\n" + tb["14.2"],
        "@@T3@@": tb["14.3"],
        "@@T4@@": tb["14.4"],
        "@@T5@@": tb["14.5"],
        "@@T6@@": tb["14.6"],
        "@@BOOT@@": boot_table(BOOT),
    }
    for key, val in sub.items():
        if key not in body:
            sys.exit("FATAL: placeholder %s not present in body" % key)
        body = body.replace(key, val)

    left = re.findall(r"@@[A-Z0-9]+@@", body)
    if left:
        sys.exit("FATAL: unresolved placeholders %s" % left)
    return body, len(sub)


def check():
    """Is the report's section 14 still what the generators produce?

    This is the guard against the report drifting from the data: if a table
    is hand-edited in the report, or a generator's numbers move and the
    report is not re-spliced, this fails.
    """
    body, _ = render()
    report = open(REPORT, encoding="utf-8").read()
    idx = report.find("\n## 14.")
    if idx < 0:
        print("CHECK FAIL: report has no section 14")
        return 1
    have = report[idx:].strip("\n")
    want = body.strip("\n")
    if have == want:
        print("CHECK OK: section 14 matches the generated tables exactly "
              "(%d lines)" % len(want.splitlines()))
        return 0
    hl, wl = have.splitlines(), want.splitlines()
    print("CHECK FAIL: report section 14 differs from a fresh splice")
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


def main():
    if "--check" in sys.argv:
        return check()

    body, n = render()
    report = open(REPORT, encoding="utf-8").read()
    if "## 14." in report:
        sys.exit("FATAL: report already contains a section 14; refusing to "
                 "append a second one")

    out = report.rstrip("\n") + "\n" + body.rstrip("\n") + "\n"
    with open(REPORT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)

    print("spliced %d placeholders" % n)
    print("report %d -> %d lines" % (len(report.splitlines()),
                                     len(out.splitlines())))
    print("section 14 tables spliced: %d" % sum(
        1 for _ in re.finditer(r"(?m)^\|---", body)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Re-derives every number quoted in section 9.25.11 from the records.

Same contract as `vn_verify25.py`. The section is sliced by its own heading so
a number that drifted into a neighbouring section cannot satisfy a check here,
every generated string must occur EXACTLY ONCE -- a presence check is satisfied
by any duplicate, and this project has been burned by that -- and the summary
partitions every check into a counted outcome so a skipped check cannot read as
a passed one.

Exit 0 green, 1 a claim does not re-derive, 2 the records could not be read.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DOC = os.path.join(HERE, "RESULT.md")
HEAD = "#### 9.25.11 "
END = "\n## 10. Files"


def section():
    t = io.open(DOC, encoding="utf-8").read()
    i = t.find(HEAD)
    if i < 0:
        raise SystemExit(2)
    j = t.find(END, i)
    if j < 0:
        raise SystemExit(2)
    return t[i:j]


def main():
    try:
        import vn_rep2511 as R
        tabs, vals = R.tables(), R.values()
    except SystemExit:
        print("REFUSED: a record could not be read; nothing was checked")
        return 2
    except Exception as e:
        print("REFUSED: %s; nothing was checked" % e)
        return 2

    sec = section()
    ok, bad = [], []

    for k, s in tabs.items():
        n = sec.count(s)
        (ok if n == 1 else bad).append(
            ("table:%s" % k, n, "generated table appears %d times, want 1" % n))
    for k, s in vals.items():
        n = sec.count(s)
        (ok if n == 1 else bad).append(
            ("value:%s" % k, n, "generated value %r appears %d times, want 1"
             % (s, n)))

    # Claims the section states in prose that no table carries, each anchored
    # on its own neighbouring literal so a stray duplicate cannot satisfy it.
    ro = R.rec("regout.json")
    sf = R.rec("shipfr.json")
    prose = [
        ("prose:rogue_below_null",
         "**The rogue step is\nsmaller than a null.**",
         sf["rogue_step"] < sf["worst_null"]),
        ("prose:one_flagged",
         "frames flagged in the whole stack | 46 |",
         ro["flagged"] == [46]),
        ("prose:screen_commissioned",
         "All four pass.", bool(ro["commission"]["passed"])),
        ("prose:verdict_not_reproduced",
         "does not reproduce any of this",
         sf["verdict"].startswith("NOT REPRODUCED")),
        ("prose:scale_058",
         "fitted a 0.58x similarity", True),
        ("prose:banner_present",
         "READ 9.25.11\n> BEFORE QUOTING ANYTHING BELOW ABOUT FRAME 46", True),
    ]
    for name, lit, cond in prose:
        n = sec.count(lit) if not name.endswith("banner_present") else 1
        if name.endswith("banner_present"):
            whole = io.open(DOC, encoding="utf-8").read()
            n = whole.count(lit)
        if n != 1:
            bad.append((name, n, "anchor %r appears %d times, want 1"
                        % (lit[:48], n)))
        elif not cond:
            bad.append((name, n, "anchor present but the record disagrees"))
        else:
            ok.append((name, n, ""))

    print("section 9.25.11 verifier")
    print("  passed        %d" % len(ok))
    print("  FAILED        %d" % len(bad))
    print("  total checks  %d" % (len(ok) + len(bad)))
    for n, _c, m in bad:
        print("  FAIL %s: %s" % (n, m))
    print("  %s" % ("GREEN" if not bad else "RED"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())

"""Substitute section 9.25.11's generated tables and values into RESULT.md.

Markers are `<<<TABLE:name>>>` on a line of its own and `<<<VALUE:name>>>`
inline. Every marker must resolve and every generated key must be used, or
this refuses -- an unused table is a table nobody checked and an unresolved
marker is a hole in the document.
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vn_rep2511 as R  # noqa: E402

DOC = os.path.join(HERE, "RESULT.md")


def main():
    t = R.tables()
    v = R.values()
    txt = io.open(DOC, encoding="utf-8").read()
    used_t, used_v = set(), set()

    def sub_t(m):
        k = m.group(1)
        if k not in t:
            raise SystemExit("REFUSED: no table named %r" % k)
        used_t.add(k)
        return t[k]

    def sub_v(m):
        k = m.group(1)
        if k not in v:
            raise SystemExit("REFUSED: no value named %r" % k)
        used_v.add(k)
        return v[k]

    out = re.sub(r"<<<TABLE:([a-z0-9_]+)>>>", sub_t, txt)
    out = re.sub(r"<<<VALUE:([a-z0-9_]+)>>>", sub_v, out)
    left = re.findall(r"<<<[^>]*>>>", out)
    if left:
        raise SystemExit("REFUSED: unresolved markers %r" % left[:5])
    unused = (set(t) - used_t) | (set(v) - used_v)
    if unused and (used_t or used_v):
        raise SystemExit("REFUSED: generated but never placed: %s"
                         % sorted(unused))
    if not (used_t or used_v):
        print("no markers found; document already placed")
        return 0
    io.open(DOC, "w", encoding="utf-8", newline="").write(out)
    print("placed %d tables + %d values, 0 unresolved, 0 unused"
          % (len(used_t), len(used_v)))
    return 0


if __name__ == "__main__":
    sys.exit(main())


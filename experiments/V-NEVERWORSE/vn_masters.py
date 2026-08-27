r"""Render every SHIP-V4 master into the measurement space.

Same pin, same source directory, same environment, same merge -- the ONLY
change is the output colour space, and `vn_gauge.py` arm G2 proves that change
is downstream of the merge by re-rendering a shipped `--srgb` master
BYTE-IDENTICALLY with this binary and this environment.

  python vn_masters.py [subject ...]
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_lib as L                                            # noqa: E402


def main():
    L.check_pin()
    want = sys.argv[1:] or L.subjects()
    print("rendering %d linear-sRGB masters with %s" % (len(want), L.MEASURE_FLAGS))
    t0 = time.time()
    for i, s in enumerate(want, 1):
        p = L.lin_master_path(s)
        if os.path.exists(p) and os.path.exists(p[:-5] + ".log"):
            print("%2d/%d %-38s cached" % (i, len(want), s))
            continue
        t = time.time()
        L.ensure_linear_master(s)
        print("%2d/%d %-38s %6.1f s  %d bytes"
              % (i, len(want), s, time.time() - t, os.path.getsize(p)))
        sys.stdout.flush()
    print("total %.1f min" % ((time.time() - t0) / 60.0))


if __name__ == "__main__":
    main()

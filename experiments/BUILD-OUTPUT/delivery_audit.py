"""delivery_audit.py -- does every delivered PNG say what colour it is and how big it prints?

Partitions EVERY png under the delivery root into counted outcomes that sum to
the total found.  A summary that reports only successes cannot distinguish a
file that passed from a file that was never examined, so the four buckets below
are exhaustive by construction and the script asserts that they add up.

Usage:  python delivery_audit.py [root] [--want-md5 HEX]
"""

import hashlib
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from png_probe import probe, dpi_of  # noqa: E402

ROOT = Path(r"C:\dev\strehl-out\DELIVER-V5")
WANT_DPI = 300.0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    root = Path(args[0]) if args else ROOT
    want = None
    if "--want-md5" in sys.argv:
        want = sys.argv[sys.argv.index("--want-md5") + 1]

    files = sorted(root.rglob("*.png"))
    if not files:
        print(f"no PNGs under {root}")
        return 2

    buckets = Counter()
    by_dir = {}
    profiles = Counter()
    bad = []
    for p in files:
        r = probe(p)
        d = p.parent.name
        by_dir.setdefault(d, Counter())
        ok_icc = r["state"] == "ICCP"
        md5 = r["icc"]["md5"] if r["icc"] else None
        ok_md5 = (want is None) or (md5 == want)
        ok_dpi = (r["phys"] is not None
                  and abs(r["phys"][0] * 0.0254 - WANT_DPI) < 0.5
                  and abs(r["phys"][1] * 0.0254 - WANT_DPI) < 0.5)
        if ok_icc and ok_md5 and ok_dpi:
            k = "profile+dpi OK"
        elif not ok_icc:
            k = "NO PROFILE"
        elif not ok_md5:
            k = "WRONG PROFILE"
        else:
            k = "NO/WRONG DPI"
        buckets[k] += 1
        by_dir[d][k] += 1
        if md5:
            profiles[(md5, r["icc"]["desc"])] += 1
        if k != "profile+dpi OK":
            bad.append((str(p), k, r["state"], md5, dpi_of(r)))

    print(f"delivery root : {root}")
    print(f"PNGs found    : {len(files)}\n")
    print(f"{'directory':<22}{'n':>5}  breakdown")
    print("-" * 78)
    for d in sorted(by_dir):
        c = by_dir[d]
        print(f"  {d:<20}{sum(c.values()):>5}  "
              + ", ".join(f"{k} x{v}" for k, v in sorted(c.items())))

    print("\ndistinct profiles embedded:")
    for (md5, desc), n in profiles.most_common():
        print(f"    {md5}  x{n:<4} {desc}")

    print("\n  === exact partition ===")
    tot = 0
    for k in ("profile+dpi OK", "NO PROFILE", "WRONG PROFILE", "NO/WRONG DPI"):
        print(f"    {k:<18}: {buckets[k]}")
        tot += buckets[k]
    print(f"    {'-' * 18}: {tot} == {len(files)} found")
    assert tot == len(files), "partition does not sum -- a file went uncounted"

    for row in bad[:20]:
        print("    BAD", row)

    green = buckets["profile+dpi OK"] == len(files)
    print(f"\n  {'GREEN' if green else 'RED'} -- "
          f"{buckets['profile+dpi OK']}/{len(files)} delivered PNGs declare "
          f"their colour space and print size")
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""M76 Q3 -- independent enumeration of B6 pooled/per-subject redundancy.

Imports neither spec_v1 nor M55's e16 enumeration.
"""
import itertools
import math

SIZES = (4, 8, 12)
NEED = 0.90


def main():
    rows = []
    grand = 0
    first_sole = None
    print("=" * 78)
    print("M76 E19 -- independent pooled-clause enumeration")
    print("subjects 4, 8, 12; need >= 90%; every k=0..24")
    print("=" * 78)
    print(" k          placements        pooled_fail       subject_fail       pooled_only")
    for k in range(sum(SIZES) + 1):
        total = pooled_fail = subject_fail = pooled_only = 0
        for failures in itertools.product(*(range(n + 1) for n in SIZES)):
            if sum(failures) != k:
                continue
            ways = math.prod(math.comb(n, f) for n, f in zip(SIZES, failures))
            pf = (sum(SIZES) - k) / sum(SIZES) < NEED
            sf = any((n - f) / n < NEED for n, f in zip(SIZES, failures))
            total += ways
            pooled_fail += ways * int(pf)
            subject_fail += ways * int(sf)
            pooled_only += ways * int(pf and not sf)
        rows.append((k, total, pooled_fail, subject_fail, pooled_only))
        grand += total
        if pooled_only and first_sole is None:
            first_sole = k
        print(f"{k:2d} {total:19d} {pooled_fail:18d} "
              f"{subject_fail:18d} {pooled_only:17d}")

    boundary = sum(row[1] for row in rows if row[0] in (1, 2, 3))
    checks = [
        ("all placements sum to 2^24", grand == 2 ** 24),
        ("k=1 total is C(24,1)", rows[1][1] == math.comb(24, 1)),
        ("k=2 total is C(24,2)", rows[2][1] == math.comb(24, 2)),
        ("k=3 total is C(24,3)", rows[3][1] == math.comb(24, 3)),
        ("k=1..3 sum is 2324", boundary == 2324),
        ("pooled-only count is zero at every k",
         all(row[4] == 0 for row in rows)),
    ]
    print()
    bad = 0
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL':4s} {name}")
        bad += int(not ok)
    print(f"  first k with a pooled-only placement: {first_sole}")
    print(f"  -> {len(checks)-bad}/{len(checks)} assertions hold")
    if bad:
        raise SystemExit(f"{bad} assertion(s) failed")


if __name__ == "__main__":
    main()

"""P39 -- how many corpus stacks have the active-area geometry the map was
measured on?

WHY THIS EXISTS.  The shipping binary refused to render `leaf-2-cpl` with the
correction on by default:

    Error: defect correction on frame 0
    Caused by: defect map was measured on a 7032x4688 active area but is being
    applied to a 7040x4688 one

That refusal is correct in principle -- a sensor-coordinate map applied to a
different geometry corrects the wrong photosites -- but it surfaced at frame 0
of the fold rather than at preflight, and it means a DEFAULT-ON correction can
hard-fail a render.  Before deciding what to do about it, count how many stacks
it affects.  A guess is not a count.

PARTITION: every stack is assigned to exactly one geometry bucket, and the
buckets sum to the number examined.  A stack that cannot be decoded is its own
bucket, not a silent omission.
"""

import collections
import pathlib
import sys

import rawpy

LIB = pathlib.Path(r"D:\personal\macro")
MAP_ACTIVE = (7032, 4688)


def first_raw(d: pathlib.Path):
    for pat in ("*.ARW", "*.arw"):
        got = sorted(d.glob(pat))
        if got:
            return got[0]
    return None


def main() -> int:
    stacks = sorted(p for p in LIB.iterdir() if p.is_dir())
    buckets: dict[object, list[str]] = collections.defaultdict(list)
    examined = 0

    for s in stacks:
        raw_path = first_raw(s)
        if raw_path is None:
            buckets["no raw frames"].append(s.name)
            examined += 1
            continue
        try:
            with rawpy.imread(str(raw_path)) as r:
                vis = r.raw_image_visible
                buckets[(vis.shape[1], vis.shape[0])].append(s.name)
        except Exception as e:  # noqa: BLE001
            buckets[f"undecodable: {type(e).__name__}"].append(s.name)
        examined += 1

    print(f"map was measured on {MAP_ACTIVE[0]}x{MAP_ACTIVE[1]} active area")
    print()
    total = 0
    for key in sorted(buckets, key=lambda k: (-len(buckets[k]), str(k))):
        names = buckets[key]
        total += len(names)
        if isinstance(key, tuple):
            label = f"{key[0]}x{key[1]}"
            verdict = "MATCHES the map" if key == MAP_ACTIVE else "DOES NOT MATCH -> refused"
        else:
            label, verdict = str(key), "not applicable"
        print(f"{label:>24}  {len(names):3d} stacks  {verdict}")
        for n in sorted(names):
            print(f"{'':>26}{n}")
        print()

    print(f"examined {examined}, bucketed {total}")
    if examined != total:
        print("PARTITION VIOLATED")
        return 2
    matched = len(buckets.get(MAP_ACTIVE, []))
    print(f"matching {matched} / {examined}   refused {examined - matched} / {examined}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

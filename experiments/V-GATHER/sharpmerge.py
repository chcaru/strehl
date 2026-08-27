r"""Join the two sharpness workers' outputs, refusing on conflict.

Two workers wrote two files. Merging them by dict.update() would silently prefer
whichever was applied last if a subject appeared in both -- and a silent
preference between two disagreeing measurements is a fabricated result. This
refuses instead, and prints a census so the merged file's coverage is a measured
number rather than an assumption.
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import certmeasure as cm

A = os.path.join(HERE, "sharp.json")
B = os.path.join(HERE, "sharp2.json")


def load(p):
    return json.load(io.open(p, encoding="utf-8")) if os.path.exists(p) else {}


def main():
    a, b = load(A), load(B)
    both = sorted(set(a) & set(b))
    for s in both:
        ka = "refused" if "refused" in a[s] else "%.6f" % a[s]["deficit_median"]
        kb = "refused" if "refused" in b[s] else "%.6f" % b[s]["deficit_median"]
        if ka != kb:
            raise SystemExit("CONFLICT on %s: worker1 %s, worker2 %s -- refusing "
                             "to pick one" % (s, ka, kb))
    merged = dict(a)
    merged.update(b)
    subs = cm.subjects()
    miss = [s for s in subs if s not in merged]
    extra = [s for s in merged if s not in subs]
    if extra:
        raise SystemExit("merged file carries subjects not in the census: %s" % extra)
    json.dump(merged, io.open(A, "w", encoding="utf-8"), indent=1)
    ref = [s for s in merged if "refused" in merged[s]]
    print("worker1 %d, worker2 %d, overlap %d (all agreed)" % (len(a), len(b), len(both)))
    print("merged %d of %d subjects; %d refused, %d measured, %d not examined"
          % (len(merged), len(subs), len(ref), len(merged) - len(ref), len(miss)))
    if len(merged) + 0 != len(subs):
        print("NOT EXAMINED: " + ", ".join(sorted(miss)))
    tot = len(ref) + (len(merged) - len(ref)) + len(miss)
    if tot != len(subs):
        raise SystemExit("census does not sum: %d != %d" % (tot, len(subs)))
    print("census sums: %d = %d refused + %d measured + %d not examined"
          % (tot, len(ref), len(merged) - len(ref), len(miss)))


if __name__ == "__main__":
    main()

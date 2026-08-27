r"""Second sharpness worker, writing to its OWN file.

sharpaxis.main() does load-modify-write on sharp.json. Two workers sharing that
file would each write back a document missing the other's entries, and the
result would look complete while silently dropping subjects -- a partition that
sums to 26 with fabricated contents is worse than one that admits a gap. This
worker writes sharp2.json; sharpmerge.py joins them and refuses on conflict.
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import certmeasure as cm
import sharpaxis as sa

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sharp2.json")


def main():
    cm.check_binary()
    os.makedirs(cm.WORK, exist_ok=True)
    doc = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    other = {}
    if os.path.exists(sa.OUT):
        other = json.load(io.open(sa.OUT, encoding="utf-8"))
    todo = [s for s in sys.argv[1:] if s not in doc and s not in other]
    print("worker 2: %d subjects, writing %s" % (len(todo), OUT))
    for s in todo:
        rec = sa.measure_subject(s)
        doc[s] = rec
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        if "refused" in rec:
            print("  %-38s REFUSED %s" % (s, rec["refused"][:70]))
        else:
            print("  %-38s deficit med %+.1f%% over %d sites"
                  % (s, 100 * rec["deficit_median"], rec["n_qualified"]))
        sys.stdout.flush()
    print("done")


if __name__ == "__main__":
    main()

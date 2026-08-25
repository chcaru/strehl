"""M115 s01b -- find a run of flat-field frames at one setting.

Rule 9's null wants a REAL capture of a genuinely featureless scene through the
same optics and sensor.  M71 measured this corpus: PRNU kappa = 0.3096 %, and it
bounded the paper-fibre confound at 0.09-0.14 %.  A run of repeats at one
setting is therefore a stack with no detail and no focus variation -- the
adversarial input rule 20 asks for.
"""
import os, sys, json, glob
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L

D = r"D:\personal\macro\flat-fields\flat-fields"


def main():
    files = sorted(glob.glob(os.path.join(D, "*.ARW")))
    print(f"{len(files)} flat-field frames")
    rows = []
    for f in files[::4]:
        try:
            iso = L.iso_of(f)
            fn = L.fnumber_of(f)
        except Exception as e:
            iso, fn = None, None
        rows.append((os.path.basename(f), iso, fn))
    # group consecutive samples by (iso, fn)
    groups = []
    cur = None
    for nm, iso, fn in rows:
        key = (iso, fn)
        if cur is None or cur[0] != key:
            cur = [key, nm, nm, 1]
            groups.append(cur)
        else:
            cur[2] = nm
            cur[3] += 1
    for key, a, b, c in groups:
        print(f"  ISO {key[0]}  f/{key[1]}   {a} .. {b}   ({c} sampled = ~{c*4} frames)")
    json.dump([[list(g[0]), g[1], g[2], g[3]] for g in groups],
              open(os.path.join(L.OUT, "s01b_flatfield_groups.json"), "w"), indent=2)


if __name__ == "__main__":
    main()

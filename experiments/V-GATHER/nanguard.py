r"""Commission the non-finite guards by making each verdict swallow a NaN.

Both arms are required and neither alone means anything:

  WITH the guard   -- a NaN-bearing record must return REFUSED.
  WITHOUT it       -- the SAME record must return PASS.

The second arm is the load-bearing one. If a NaN record returned REFUSED for
some unrelated reason -- a missing key, an earlier branch -- the first arm would
read green while the guard did nothing. Only showing that removing the guard
turns the refusal into a PASS proves the guard is what produced it.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import printcert4 as p4

NAN = float("nan")


def rim_rec(val):
    return {"corrected_bright": val, "n_sel": 4000, "isolated_frac": 0.5,
            "floor": {"resid_bright": 0.0},
            "master": {"ci_bright": [val, val], "null_bright": 0.0}}


def sharp_rec(val):
    return {"deficit_median": val, "n_qualified": 20, "n_sites_offered": 40,
            "n_frames_used": 12}


def dust_rec(val):
    return {"ratio": val, "n_sites_used": 300, "n_control": 8}


CASES = [
    ("rim", lambda v: p4.rim_verdict("x", {"x": rim_rec(v)})),
    ("sharp", lambda v: p4.sharp_verdict("x", {"x": sharp_rec(v)})),
    ("dust", lambda v: p4.dust_verdict("x", {"x": dust_rec(v)})),
]


def main():
    print("clean values first -- if these do not PASS the NaN arm proves nothing")
    clean = {"rim": 0.0, "sharp": 0.0, "dust": 1.0}
    bad = False
    for name, fn in CASES:
        k = fn(clean[name])[0]
        print("  %-6s clean -> %-8s %s" % (name, k, "ok" if k == "PASS" else "UNEXPECTED"))
        if k != "PASS":
            bad = True
    if bad:
        print("\nthe clean control does not pass; the NaN arm is uninterpretable")
        return 1

    print("\nwith the guard in place")
    for name, fn in CASES:
        k, why = fn(NAN)
        ok = k == "REFUSED"
        print("  %-6s NaN   -> %-8s %s" % (name, k, "REFUSED as required" if ok
                                           else "NOT REFUSED -- DEFECT"))
        if not ok:
            bad = True

    print("\nwith the guard removed -- the same records must become PASS")
    real = p4.finite
    p4.finite = lambda *a: True
    try:
        for name, fn in CASES:
            k, why = fn(NAN)
            print("  %-6s NaN   -> %-8s %s" % (name, k,
                  "PASS: the guard was load-bearing" if k == "PASS"
                  else "still " + k + " -- guard NOT proven load-bearing"))
            if k != "PASS":
                bad = True
    finally:
        p4.finite = real

    k = p4.rim_verdict("x", {"x": rim_rec(NAN)})[0]
    print("\nguard restored, rim NaN -> %s" % k)
    if k != "REFUSED":
        print("RESTORE FAILED")
        bad = True
    print("\n%s" % ("DEFECTS FOUND" if bad else
                    "all three guards commissioned: they refuse NaN, and "
                    "removing them turns that refusal into a PASS"))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

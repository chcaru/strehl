"""M116-promotion — the CA controls, printed before any positive.

CB1 (null), CB2 (placebo) and the green-invariance diagnostic. A campaign whose
harness is not sound has no results, so these are read first and reported
first.

Run: python ca_controls.py
"""

import json
import sys
from pathlib import Path

CA = Path(r"C:\dev\strehl-out\M116\ca")


def main() -> int:
    d = json.loads((CA / "scores-ca.json").read_text(encoding="utf-8"))
    disp = json.loads((CA / "scores-ca-disp.json").read_text(encoding="utf-8"))

    print("CB1 NULL  -- same arm, cold PRIVATE cache, must be byte-identical")
    print("CB2 PLACEBO -- same config, different output path, ANOTHER ARM'S cache")
    print()
    n_ok = p_ok = 0
    n_tot = p_tot = 0
    for s, r in d["subjects"].items():
        c1 = r.get("CB1_identical")
        c2 = r.get("CB2_identical", None)
        if c1 is not None:
            n_tot += 1
            n_ok += bool(c1)
        if c2 is not None:
            p_tot += 1
            p_ok += bool(c2)
        print(f"  {s:<38} CB1={'IDENTICAL' if c1 else 'DIFFERENT'}"
              f"   CB2={'IDENTICAL' if c2 else ('DIFFERENT' if c2 is not None else 'n/a')}")
    print(f"\n  CB1: {n_ok}/{n_tot} byte-identical    "
          f"CB2: {p_ok}/{p_tot} byte-identical")

    print("\nGREEN INVARIANCE (post-hoc diagnostic, disclosed as such).")
    print("Green is the profile's reference channel and has no coefficient, so")
    print("a correct implementation must not move it at all.")
    for s, r in d["subjects"].items():
        t = r["treated"]
        print(f"  {s:<38} max|dG| = {t['green_max_abs_delta']:.1f} DN"
              f"   fraction of pixels moved = {t['green_frac_moved']:.5f}")
    for s, r in disp["subjects"].items():
        gd = r["green_null_off"][0]["rd_px"]
        print(f"  {s:<38} green-vs-green displacement = {gd:+.4f} px (zero by construction)")

    print("\nCD2 TRAP -- |RD(centre)| <= 0.10 px in BOTH arms")
    ok = True
    for s, r in disp["subjects"].items():
        a, b = r["centre_rd_off"], r["centre_rd_on"]
        good = abs(a) <= 0.10 and abs(b) <= 0.10
        ok &= good
        print(f"  {s:<38} off {a:+.4f}  on {b:+.4f}   {'PASS' if good else 'FAIL'}")
    print(f"  CD2 overall: {'PASS' if ok else 'FAIL'}")

    print("\nCD7 DO-NO-HARM -- D >= -0.02 dex, worst of R / B / luminance")
    for s, r in disp["subjects"].items():
        w = r["D_worst"]
        print(f"  {s:<38} D_R={r['D_R']:+.5f}  D_B={r['D_B']:+.5f}"
              f"  D_L={r['D_L']:+.5f}  worst={w:+.5f}"
              f"   {'PASS' if w >= -0.02 else 'FAIL'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

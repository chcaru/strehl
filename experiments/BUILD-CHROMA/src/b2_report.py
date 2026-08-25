"""B2 report printer -- gate ladder and headline table from the saved summary."""
import json
import os
import sys

OUT = r"C:\dev\strehl-out\BUILD-CHROMA"


def main():
    p = os.path.join(OUT, "json", "b2_summary.json")
    d = json.load(open(p))
    for o in d:
        print(f"\n===== {o['stack']} =====")
        print("  GATE LADDER (is the answer a property of the threshold?)")
        print("   thr        n    frac       dR       dB     NULL  sign_dR sign_null")
        for g in o["gate_ladder"]:
            f = lambda v: "    n/a" if v is None else f"{v:+8.4f}"
            s = lambda v: "   n/a" if v is None else f"{v*100:5.1f}%"
            print(f"   {g['thr']:.1f} {g['n']:8d} {g['frac']*100:6.2f}% "
                  f"{f(g['dR'])} {f(g['dB'])} {f(g['null'])} "
                  f"{s(g['sign_dR'])} {s(g['sign_null'])}")
        if "tilewise" not in o:
            print("  " + o.get("verdict", "-"))
            continue
        tw = o["tilewise"]
        print(f"  HEADLINE dR {tw['dR']['median']:+.4f} +- {tw['dR']['se']:.4f}  "
              f"dB {tw['dB']['median']:+.4f} +- {tw['dB']['se']:.4f}  "
              f"NULL {tw['null']['median']:+.4f} +- {tw['null']['se']:.4f}")
        if "radial_fit" in o:
            for nm, fq in o["radial_fit"].items():
                print(f"  RADIAL {nm:4s} R2 {fq['r2']:.4f}  p {fq['perm_p']:.4f}  "
                      f"centre->corner {fq['predicted_change_centre_to_corner']:+.4f}")


if __name__ == "__main__":
    main()

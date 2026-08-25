"""M115 s01c -- level census of the flat-field run, to pick a null cube whose
exposure level (and therefore whose modelled sigma) is comparable to the real
stacks' detail ROIs."""
import os, sys, glob, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L

D = r"D:\personal\macro\flat-fields\flat-fields"
CX, CY, CB = 1600, 1000, 384          # central patch, quad px


def main():
    files = sorted(glob.glob(os.path.join(D, "*.ARW")))
    rows = []
    for f in files[::6]:
        q = L.quad_green_full(f)
        p = q[CY:CY + CB, CX:CX + CB]
        rows.append((os.path.basename(f), float(p.mean()), float(p.std())))
    for nm, mu, sd in rows:
        print(f"  {nm}  mean {mu:8.1f} DN  sd_s {sd:7.2f}")
    json.dump(rows, open(os.path.join(L.OUT, "s01c_flat_levels.json"), "w"), indent=2)


if __name__ == "__main__":
    main()

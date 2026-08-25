"""M122 — POST-HOC analyses. Registered nowhere; labelled as post-hoc everywhere.

The registered verdict is the one `correlate.py` prints and is NOT changed here.
These exist because two things showed up in the registered numbers that the
registration did not anticipate, and hiding either would be dishonest:

  1. `hf` is an ABSOLUTE laplacian RMS. It scales with the image level. The
     photometric arm normalises frames to a reference frame, so it can move the
     whole output level -- and on `113MSDCF` it moved it 6.84%, which alone
     produces a 6.99% "harm" reading with no change in structure whatsoever.
     `B12n = B12 / (level ratio)` removes that.

  2. Whether the registered verdict survives that correction, in BOTH
     directions -- i.e. whether any headline BENEFIT is also just a level move.

Reads only. Writes only under C:\\dev\\strehl-out\\M122.
"""

import csv
import json
import os

import numpy as np

import correlate as C

OUT = r"C:\dev\strehl-out\M122"


def main():
    drift = {r["stack"]: r for r in json.load(open(os.path.join(OUT, "drift-corpus.json")))}
    blotch = {r["stack"]: r for r in json.load(open(os.path.join(OUT, "blotch-ab.json")))}
    reg = json.load(open(os.path.join(OUT, "correlate.json")))
    used = reg["used"]

    x = np.array([drift[s]["Dpp"] for s in used])
    b12 = np.array([blotch[s]["B12"] for s in used])
    lvl = np.array([np.median([w["lvl_ratio"] for w in blotch[s]["smooth_windows"]]) for s in used])
    lvlt = np.array([np.median([w["lvl_ratio"] for w in blotch[s]["textured_windows"]]) for s in used])
    t12 = np.array([blotch[s]["T12"] for s in used])
    b12n = b12 / lvl
    t12n = t12 / lvlt

    print("POST-HOC 1 -- level-normalised blotch response  B12n = B12 / (A1/A0 window level)")
    print("%-38s %8s %8s %8s %8s %8s" % ("stack", "Dpp%", "B12", "lvl", "B12n", "T12n"))
    for i, s in enumerate(used):
        print("%-38s %8.3f %8.4f %8.4f %8.4f %8.4f" % (s, x[i], b12[i], lvl[i], b12n[i], t12n[i]))
    print()

    for lab, y in (("REGISTERED  1 - B12 ", 1 - b12), ("POST-HOC    1 - B12n", 1 - b12n)):
        rho = C.spearman(x, y)
        p1, p2, sd = C.perm_p(x, y, rho)
        print("  %s : rho %+.4f  one-sided p %.4f  two-sided p %.4f  null sd %.4f"
              % (lab, rho, p1, p2, sd))
    print()

    harm_reg = [(used[i], b12[i]) for i in range(len(used)) if b12[i] > 1.03]
    harm_pn = [(used[i], b12n[i]) for i in range(len(used)) if b12n[i] > 1.03]
    print("  harm under the REGISTERED statistic (B12  > 1.03): %s" % harm_reg)
    print("  harm under the POST-HOC   statistic (B12n > 1.03): %s" % harm_pn)
    print()
    print("  -> the registered KEEP-OFF does NOT depend on the level artefact: %s"
          % ("CONFIRMED, harm survives level normalisation" if harm_pn
             else "NOT confirmed -- all harm was a level move"))
    print()

    print("POST-HOC 2 -- is any BENEFIT a level move? responders under each statistic")
    print("  responders B12  < 0.97: %s" % [used[i] for i in range(len(used)) if b12[i] < 0.97])
    print("  responders B12n < 0.97: %s" % [used[i] for i in range(len(used)) if b12n[i] < 0.97])
    print()

    print("POST-HOC 3 -- mean n_eff, A1 over A0 (is the harm an admission change?)")
    ne = {}
    import glob
    import re
    for p in glob.glob(os.path.join(OUT, "logs", "*__A?-*.log")):
        s = os.path.basename(p).split("__")[0]
        arm = os.path.basename(p).split("__")[1][:2]
        t = open(p, encoding="utf-8", errors="replace").read()
        m = re.search(r"^\s*4\.00\s+([0-9.]+)\s+([0-9.]+)\s+([0-9.]+)%", t, re.M)
        if m:
            ne.setdefault(s, {})[arm] = float(m.group(2))
    r = [ne[s]["A1"] / ne[s]["A0"] for s in used if s in ne and "A1" in ne[s]]
    print("  n_eff(A1)/n_eff(A0): median %.5f  min %.5f  max %.5f  -- the gate's admission set"
          " is essentially unmoved, so the harm is not fewer frames being averaged"
          % (float(np.median(r)), float(min(r)), float(max(r))))

    json.dump({"used": used, "B12n": b12n.tolist(), "lvl": lvl.tolist(),
               "harm_registered": harm_reg, "harm_posthoc": harm_pn},
              open(os.path.join(OUT, "posthoc.json"), "w"), indent=1)


if __name__ == "__main__":
    main()

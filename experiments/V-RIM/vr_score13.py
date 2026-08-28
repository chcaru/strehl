r"""ORCH job 1, final scoring -- the thirteen against a DIRECTLY MEASURED
rim-free floor, with nothing clamped and nothing extrapolated.

Every master's shoulder sd lies inside 0.0175-0.3930, the span of the extended
ladder, so np.interp only ever interpolates here.  The comparison is made on
the coherent excursion, not on the headline number, because the headline number
is a max over six samples and a rim can only live in the coherent part.

  coherent = max over t in +2..+7 of (median profile - isotonic projection)
  z        = coherent * sqrt(n_edges) / shoulder_sd

z is used for the read-across because the coherent floor falls as 1/sqrt(n) and
the masters carry very different edge counts.  The planted-rim series fixes the
other end of the scale: z is converted into the rim amplitude, as a fraction of
the edge step, that would produce it.
"""
import io
import json
import os
import sys

import numpy as np

import vr_lib as V

L2 = json.load(io.open(os.path.join(V.SCRATCH, "ladder2.json"), encoding="utf-8"))
L3 = json.load(io.open(os.path.join(V.SCRATCH, "ladder3.json"), encoding="utf-8"))

# corrected_bright as printcert4 reported it on SHIP-V4, from rim.json
REPORTED = {
    "bee-1-cpl": 3.13, "couch-fibers-cpl": 3.50, "lead-1-cpl": 3.36,
    "flowers-cpl": 5.18, "pencil-steep-angle-cpl": 6.77,
    "wrapped-text-1": 7.48, "lavendar-cpl": 8.01, "wrapped-text-2": 10.93,
    "flat-on-ruler-cpl": 14.84, "coffee-bean": 33.25, "leaf-2-cpl": 37.07,
    "112MSDCF": 12.62, "113MSDCF": 17.28,
    "109MSDCF": -2.25, "119MSDCF": -2.16,
}


def main():
    fl = [r for r in L3["floor"] if r.get("n")]
    fsd = np.array([r["shoulder_sd"] for r in fl])
    fco = np.array([r["excursion"] for r in fl])
    fz = np.array([r["excursion"] * np.sqrt(r["n"]) / r["shoulder_sd"]
                   for r in fl])
    o = np.argsort(fsd)
    fsd, fco, fz = fsd[o], fco[o], fz[o]

    pl = L3["plant"]
    pz = np.array([r["excursion"] * np.sqrt(r["n"]) / r["shoulder_sd"]
                   for r in pl])
    pa = np.array([r["rim_over_step"] for r in pl])
    o2 = np.argsort(pz)
    pz, pa = pz[o2], pa[o2]

    print("rim-free ladder spans shoulder sd %.4f .. %.4f  (every master is inside)"
          % (fsd.min(), fsd.max()))
    print("planted-rim ladder spans z %.1f .. %.1f  for rim/step %.3f .. %.3f"
          % (pz.min(), pz.max(), pa.min(), pa.max()))
    print()
    print("=" * 108)
    print("%-26s %7s %8s %9s %10s %8s %8s %10s %s"
          % ("subject", "sd", "reads", "coherent", "rimfree", "z", "z_free",
             "implied", "call"))
    print("=" * 108)
    rows = []
    for r in L2["inplace"]:
        s = r["subject"]
        sd = r["shoulder_sd"]
        z = r["excursion"] * np.sqrt(r["n"]) / sd
        zf = float(np.interp(sd, fsd, fz))
        cf = float(np.interp(sd, fsd, fco))
        imp = float(np.interp(z, pz, pa)) if z > pz.min() else 0.0
        clamped = (z >= pz.max())
        if r["excursion"] <= cf:
            call = "artifact"
        elif z <= zf:
            call = "artifact"
        else:
            call = "above floor"
        print("%-26s %7.4f %7.2f%% %8.3f%% %9.3f%% %8.1f %8.1f %9.3f%s %s"
              % (s, sd, REPORTED.get(s, float("nan")), 100 * r["excursion"],
                 100 * cf, z, zf, imp, "+" if clamped else " ", call))
        rows.append(dict(subject=s, sd=sd, coherent=r["excursion"], rimfree=cf,
                         z=z, z_free=zf, implied_rim_over_step=imp,
                         call=call, n=r["n"]))
    print("=" * 108)
    print("implied = the planted rim amplitude, as a fraction of the edge step,")
    print("          that reproduces this z on the synthetic scene. '+' means the")
    print("          planted ladder tops out below this z and the figure is a")
    print("          LOWER BOUND, not a value.")
    json.dump(rows, io.open(os.path.join(V.SCRATCH, "score13.json"), "w",
                            encoding="utf-8"), indent=1, default=float)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

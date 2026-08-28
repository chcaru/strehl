r"""ORCH job 1, stage 4 -- the RIM-FREE FLOOR for the coherent excursion,
measured across the whole sd range the masters occupy, so nothing is clamped.

Stage 3 gave each master a 'coherent' number: max over t in +2..+7 of
(median profile - its isotonic non-decreasing projection). That is the part of
the reading that is coherent across edges, which is the only part a rim can
live in.  A rim-free image does not read zero there, because the median of a
finite number of rough edges wanders off monotone by chance.  This measures how
much, at each roughness, on the same synthetic scene where no rim exists.

The floor scales as sd/sqrt(n_edges), so both are recorded and the comparison
is made on the dimensionless z = coherent * sqrt(n) / sd.  A master whose z
matches the rim-free scene has no coherent excursion beyond chance.

MATCHED CONTROL: the planted-rim series from stage 3C is scored on the same z,
so the scale has a known non-zero end as well as a known zero end.
"""
import io
import json
import os
import sys

import numpy as np

import vr_lib as V
import vr_specificity as S
from vr_ladder import iso_pedestal
import rimv6

OUT = os.path.join(V.SCRATCH, "ladder3.json")


def z_of(ip):
    return ip["coherent_z"]


def enrich(ip):
    ip["coherent_z"] = ip["excursion"] * np.sqrt(ip["n"]) / max(ip["shoulder_sd"], 1e-9)
    return ip


def main():
    doc = {"floor": [], "plant": []}
    base = S.scene()

    print("=" * 86)
    print("RIM-FREE FLOOR FOR THE COHERENT EXCURSION -- synthetic, no rim exists")
    print("=" * 86)
    print("%9s %9s %8s %10s %10s %8s" % ("amp", "sd", "n_edges", "coherent",
                                         "raw", "z"))
    for amp in (0.0, 0.012, 0.048, 0.090, 0.130, 0.170, 0.200, 0.240):
        g = S.roughen(base, amp, seed=S.SEED + 1)
        rec, sel, ref, em = V.run_pipeline(g, np.zeros(g.shape, bool), ntile=40)
        ip = iso_pedestal(em)
        if ip is None:
            print("%9.4f  no profiles (%s)" % (amp, rec.get("refused")))
            continue
        enrich(ip)
        print("%9.4f %9.4f %8d %9.3f%% %9.3f%% %8.2f"
              % (amp, ip["shoulder_sd"], ip["n"], 100 * ip["excursion"],
                 100 * ip["raw"], ip["coherent_z"]))
        ip["amp"] = amp
        doc["floor"].append(ip)

    print()
    print("=" * 86)
    print("SAME z ON A PLANTED RIM -- the known non-zero end of the scale")
    print("=" * 86)
    rough = S.roughen(base, 0.012, seed=S.SEED + 1)
    print("%9s %9s %8s %10s %8s %10s" % ("rim/step", "sd", "n_edges",
                                         "coherent", "z", "raw"))
    for amp in (0.0, 0.003, 0.006, 0.012, 0.024, 0.048):
        g = S.plant_rim(rough, amp)
        rec, sel, ref, em = V.run_pipeline(g, np.zeros(g.shape, bool), ntile=40)
        ip = iso_pedestal(em)
        if ip is None:
            print("%9.4f  no profiles (%s)" % (amp / 0.30, rec.get("refused")))
            continue
        enrich(ip)
        print("%9.4f %9.4f %8d %9.3f%% %8.2f %9.3f%%"
              % (amp / 0.30, ip["shoulder_sd"], ip["n"], 100 * ip["excursion"],
                 ip["coherent_z"], 100 * ip["raw"]))
        ip["amp"] = amp
        ip["rim_over_step"] = amp / 0.30
        doc["plant"].append(ip)

    json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1, default=float)
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

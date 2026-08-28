r"""ORCH job 1, stages 2 and 3 -- close the clamp two ways.

Stage 2 BISECTION.  Hit each named shoulder sd by bisecting the roughness
amplitude, so the pedestal at that sd is DIRECTLY MEASURED and not read off a
curve.  Targets are the sds measured on the masters in stage 3, plus round
numbers spanning 0.20-0.35.

Stage 3 IN-PLACE PEDESTAL.  No synthetic scene, therefore no extrapolation is
possible.  For each master, take rimv6's own (n_edges x 25) profile array,
split it into the median profile m and the per-edge residual R, replace m by
its isotonic non-decreasing projection, and re-read the statistic.  Each edge
keeps its residual row bit-exact, so shoulder sd and t-correlation are
unchanged; the only thing removed is the coherent bump.  The result is the
reading this master would give with monotone edges and untouched texture.

Stage 3 carries its own matched control: the same operation on a PLANTED rim,
where the raw reading must rise with amplitude and the pedestal must not.
"""
import io
import json
import os
import sys

import numpy as np

import vr_lib as V
import vr_specificity as S
from vr_ladder import pav, iso_pedestal, sd_of, THIRTEEN, CONTROLS
import rimaxis
import rimv6

OUT = os.path.join(V.SCRATCH, "ladder2.json")


def main():
    doc = {}
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"

    if stage in ("all", "3"):
        print("=" * 78)
        print("STAGE 3 -- IN-PLACE RIM-FREE PEDESTAL ON EACH MASTER (no synthetic)")
        print("=" * 78)
        print("%-34s %8s %10s %10s %9s %7s" % ("subject", "sd", "reads",
                                               "pedestal", "coherent", "call"))
        doc["inplace"] = []
        for name in THIRTEEN + CONTROLS:
            p = os.path.join(V.SHIP, name + "--SHIP-V4.tiff")
            g, clip = V.read_lum(p)
            rec, sel, ref, em = V.run_pipeline(g, clip)
            ip = iso_pedestal(em)
            if ip is None:
                print("%-34s  no profiles (%s)" % (name, rec.get("refused")))
                continue
            call = "artifact" if ip["pedestal"] >= ip["raw"] else "ABOVE PEDESTAL"
            print("%-34s %8.4f %9.3f%% %9.3f%% %8.3f%% %7s"
                  % (name, ip["shoulder_sd"], 100 * ip["raw"],
                     100 * ip["pedestal"], 100 * ip["excursion"], call))
            ip["subject"] = name
            ip["corrected_bright"] = rec.get("corrected_bright")
            doc["inplace"].append(ip)
            del g, clip, em
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)

    if stage in ("all", "C"):
        print()
        print("=" * 78)
        print("STAGE 3 CONTROL -- same operation on a PLANTED rim")
        print("  raw must climb with amplitude; pedestal must not.")
        print("=" * 78)
        base = S.scene()
        rough = S.roughen(base, 0.012, seed=S.SEED + 1)
        print("%9s %10s %10s %9s" % ("rim amp", "raw", "pedestal", "coherent"))
        doc["plantctl"] = []
        for amp in (0.0, 0.006, 0.024, 0.090):
            g = S.plant_rim(rough, amp)
            rec, sel, ref, em = V.run_pipeline(g, np.zeros(g.shape, bool),
                                               ntile=40)
            ip = iso_pedestal(em)
            if ip is None:
                print("%9.4f  REFUSED %s" % (amp, rec.get("refused")))
                continue
            print("%9.4f %9.3f%% %9.3f%% %8.3f%%"
                  % (amp, 100 * ip["raw"], 100 * ip["pedestal"],
                     100 * ip["excursion"]))
            ip["amp"] = amp
            doc["plantctl"].append(ip)
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)

    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

r"""Is the rim reading COHERENT along the edge, or is it the max-of-6 bias?

Runs the unmodified rimaxis pipeline on a subject, then reports the same
quantity under both reduction orders on the identical selected pixels.
Matched control in every run: the smoothed reference (rim-free by
construction) goes through the identical two reductions.
"""
import io
import json
import os
import sys
import time

import numpy as np

import vr_lib as V

OUT = os.path.join(V.SCRATCH, "coherence.json")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "ship"
    subs = sys.argv[2:]
    base = V.SHIP if which == "ship" else V.DELIV
    suf = "--SHIP-V4.tiff" if which == "ship" else ".tiff"
    allsubs = sorted(f[:-len(suf)] for f in os.listdir(base) if f.endswith(suf))
    if not subs:
        subs = allsubs
    doc = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for s in subs:
        key = which + "/" + s
        if key in doc:
            continue
        t0 = time.time()
        g, clip = V.read_lum(os.path.join(base, s + suf))
        rec, sel, ref, em = V.run_pipeline(g, clip)
        del g, clip, ref
        rec["seconds"] = round(time.time() - t0, 1)
        rec["verdict"] = V.verdict(rec)[0]
        doc[key] = rec
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        cm = rec.get("coh_master")
        if cm is None:
            print("%-8s %-38s %-8s %s" % (which, s, rec["verdict"],
                                          rec.get("refused", "")))
            continue
        cf = rec["coh_floor"]
        print("%-8s %-38s %-8s corr %+7.3f%% | max-then-med %+7.3f%%  "
              "MED-THEN-MAX %+7.3f%%  shoulder sd %6.4f  predicted bias "
              "%+6.3f%% | floor med-then-max %+7.3f%%  [%.0fs]"
              % (which, s, rec["verdict"], 100 * rec["corrected_bright"],
                 100 * cm["max_then_median"], 100 * cm["median_then_max"],
                 cm["shoulder_sd_median"], 100 * cm["predicted_bias"],
                 100 * cf["median_then_max"], rec["seconds"]))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

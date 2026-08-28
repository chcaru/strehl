r"""THE CONTROL THAT IS NOT OURS.

Same scene, same instrument, four producers:

  ZERENE      Zerene Stacker PMax, a commercial stacker, on the same 63 frames.
  STREHL      this project's render of the same 63 frames.
  SOURCE-N    an INDIVIDUAL Lightroom-developed source frame -- never stacked,
              never merged, so it cannot carry a merge rim by construction.
  SOURCE-M    a second source frame, so a difference between the two source
              frames prices the frame-to-frame variability of the statistic.

If an unstacked single frame reads at the same amplitude as the masters, the
statistic is not measuring anything a stacker did. If Zerene reads there too,
it is measuring focus stacking in general or the scene, not strehl.
"""
import io
import json
import os
import sys

import numpy as np
import tifffile

import vr_lib as V

OUT = os.path.join(V.SCRATCH, "external.json")

ARMS = [
    ("ZERENE-PMax", r"D:\edited\macro\test2\2026-05-09-12.12.17 ZS PMax.tif"),
    ("STREHL-test2", r"C:\dev\macro\out\stack_test2_rec2020.tif"),
    ("SOURCE-frame30", r"D:\edited\macro\test2\20260507-DSC00030.tif"),
    ("SOURCE-frame45", r"D:\edited\macro\test2\20260507-DSC00045.tif"),
]


def load(path):
    """clip is computed against the file's OWN full-scale, not a hardcoded
    65535: two of these arms are float32 and a uint16 test would mark nothing
    clipped, silently admitting saturated edges the uint16 arms exclude."""
    a = tifffile.imread(path)
    import rimaxis
    g = rimaxis.lum_of(a)
    if a.dtype == np.uint16:
        hi, lo = 65535, 0
    else:
        hi, lo = 1.0, 0.0
        if a.max() > 1.5:
            hi = float(a.max())
    clip = (a.max(axis=2) >= hi) | (a.min(axis=2) <= lo)
    print("    %s  %s %s  range %.4f..%.4f  clip %.4f%%"
          % (os.path.basename(path), a.shape, a.dtype, float(a.min()),
             float(a.max()), 100.0 * clip.mean()))
    del a
    return g, clip


def main():
    doc = json.load(io.open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    for name, path in ARMS:
        if name in doc:
            continue
        print("\n== %s" % name)
        g, clip = load(path)
        rec, sel, ref, em = V.run_pipeline(g, clip)
        del g, clip, ref
        rec["path"] = path
        rec["verdict"] = V.verdict(rec)[0]
        doc[name] = rec
        json.dump(doc, io.open(OUT, "w", encoding="utf-8"), indent=1)
        cm = rec.get("coh_master")
        if cm is None:
            print("    %-8s %s" % (rec["verdict"], rec.get("refused", "")))
            continue
        print("    %-8s corrected %+7.3f%%  dark %+7.3f%%  n=%d  iso %.1f%%"
              % (rec["verdict"], 100 * rec["corrected_bright"],
                 100 * rec["corrected_dark"], rec["n_sel"],
                 100 * rec["isolated_frac"]))
        print("    max-then-med %+7.3f%%  MED-THEN-MAX %+7.3f%%  shoulder sd "
              "%6.4f  predicted max-of-6 bias %+7.3f%%"
              % (100 * cm["max_then_median"], 100 * cm["median_then_max"],
                 cm["shoulder_sd_median"], 100 * cm["predicted_bias"]))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()

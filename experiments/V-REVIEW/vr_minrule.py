"""Is the gate's min-over-frames chroma baseline just the blurriest frame?

orch_chroma.py's header says the source baseline is the MINIMUM over frames.
If per-frame chroma tracks per-frame sharpness, then that minimum IS the most
defocused frame in the bracket, and no in-focus image -- merged or not -- can
meet it.  Measured, not argued: Pearson r between each frame's chroma and its
relHF (the same sharpness proxy vr_source.py already records).
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V

SUBJ = ["109MSDCF","112MSDCF","113MSDCF","coffee-bubbles","couch-fibers-cpl",
        "flat-on-ruler-cpl","flower-inner-edge-cpl","foam","lead-1-cpl","leaf-2-cpl"]
print("%-22s %3s %8s %8s %8s %8s %8s" %
      ("subject","n","corr","c_min","c_max","hf@min","hf@max"))
for s in SUBJ:
    d = json.load(open(os.path.join(V.OUT, "source_%s.json" % s)))
    ok = [r for r in d["rows"] if r["state"] == "OK"]
    if len(ok) < 4:
        continue
    c  = np.array([r["chroma"] for r in ok])
    hf = np.array([r["relhf"]  for r in ok])
    r  = float(np.corrcoef(c, hf)[0, 1])
    i, j = int(c.argmin()), int(c.argmax())
    print("%-22s %3d %8.3f %8.6f %8.6f %8.5f %8.5f"
          % (s, len(ok), r, c[i], c[j], hf[i], hf[j]))

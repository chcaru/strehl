import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V

subj, k = sys.argv[1], int(sys.argv[2])
tif = os.path.join(V.OUT, "%s--f%04d.tiff" % (subj, k))
if not os.path.exists(tif):
    t = time.time(); log = V.render_frame(subj, k, tif)
    print("rendered in %.1fs" % (time.time() - t))
    for l in log.splitlines():
        if any(w in l for w in ("coverage", "alignment", "exposure", "wrote", "ONLY_FRAME")):
            print("   ", l.strip())
m = V.read_rgb(V.master_path(subj)); ml = V.lum_of(m); del m
s = V.read_rgb(tif); sl = V.lum_of(s)
print("master lum", ml.shape, ml.min(), ml.max(), ml.mean())
print("source lum", sl.shape, sl.min(), sl.max(), sl.mean())
t = time.time(); A, diag = V.register(ml, sl); print("register %.1fs" % (time.time() - t))
print("diag", diag)
print("A", A)

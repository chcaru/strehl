"""Focus-sweep direction, from the warp sidecar.

If the per-channel offset is optical, its sign is tied to the physical direction
of the focus sweep: a bracket shot near-to-far and one shot far-to-near must
give k_R - k_G with OPPOSITE signs.  If instead it is an artefact of the
estimator, the sign is a property of the code and does not care.

The sidecar carries the per-frame similarity z' = a z + b.  Racking focus on a
macro lens changes magnification monotonically, so sign(d|a|/dk) recovers the
sweep direction without touching the capture library's metadata.
"""
import sys, os, json
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump
from e3_argmax import read_warpmap

R = r"C:\dev\strehl-out\M107-chroma\renders"

if __name__ == "__main__":
    out = []
    for name in sorted(os.listdir(R)):
        if not name.endswith("-warpmap.txt"):
            continue
        meta, warps = read_warpmap(os.path.join(R, name))
        k = np.array([i for i, w in enumerate(warps) if w is not None], float)
        m = np.array([abs(w[0]) for w in warps if w is not None], float)
        if k.size < 10:
            continue
        slope = float(np.polyfit(k, m, 1)[0])
        # correlation, so a noisy fit cannot masquerade as a trend
        r = float(np.corrcoef(k, m)[0, 1])
        rec = {"stack": name.replace("-warpmap.txt", ""),
               "frames": int(meta["frames"]), "n_placed": int(k.size),
               "mag_first": float(m[0]), "mag_last": float(m[-1]),
               "slope_per_frame": slope, "pearson_r": r,
               "sweep": "increasing-magnification" if slope > 0 else
                        "decreasing-magnification"}
        out.append(rec)
        print(f"{rec['stack']:>16s}  |a| {m[0]:.6f} -> {m[-1]:.6f}  "
              f"slope {slope:+.3e}/frame  r={r:+.4f}  {rec['sweep']}")
    dump("e5_sweep_direction", out)

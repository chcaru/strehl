"""Why do isolated election outliers appear on a RIGID subject?

motion_hunt.py's own control refuted it as a motion detector: tweezers-cpl is a
rigid steel tool that cannot move between exposures, yet 2.076% of its output
pixels elect a frame >= 8 frames from their neighbourhood median in an isolated
speckle, while foam -- the subject M89 measured at 4.78% >8 sigma -- reads the
LOWEST of the three at 0.305%.

Competing explanation tested here: the election is INDETERMINATE where there is
no detail. Pass one takes a per-pixel argmax of a focus response. In a
featureless region that response is nearly flat across the whole sweep, so the
argmax is decided by noise and lands anywhere -- including frame 99 when the
neighbours picked frame 0. That is not motion. It is an argmax with nothing to
choose between.

Prediction, stated before the numbers below are read: if this is right, the
isolated outliers must concentrate in LOW-structure pixels. Quantified as the
median local structure at outlier pixels against the median over the whole
frame. A ratio well below 1 supports indeterminacy; a ratio near or above 1
refutes it and sends the explanation back to motion or to a defect.

This does not prove motion is absent. It tests one alternative that the control
made unavoidable.
"""

import json
import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

ROOT = Path(r"C:\dev\strehl-out\M116")
MAPS = ROOT / "maps"
MEASURE = ROOT / "measure"
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
MED, JUMP, MAX_BLOB = 9, 8, 64


def green(p: Path) -> np.ndarray:
    a = tifffile.imread(p)
    g = a[..., 1] if a.ndim == 3 else a
    assert g.ndim == 2, g.shape
    return g.astype(np.float32)


def structure(g: np.ndarray) -> np.ndarray:
    small = g[::4, ::4]
    m = ndimage.uniform_filter(small, 33)
    v = ndimage.uniform_filter(small * small, 33) - m * m
    sd = np.sqrt(np.maximum(v, 0.0))
    return np.repeat(np.repeat(sd, 4, 0), 4, 1)[:g.shape[0], :g.shape[1]]


def main() -> int:
    out = {}
    for s in SUBJECTS:
        idx = tifffile.imread(MAPS / f"{s}__A0-index.tif").astype(np.float32)
        if idx.ndim == 3:
            idx = idx[..., 0]
        resid = np.abs(idx - ndimage.median_filter(idx, size=MED))
        far = resid >= JUMP
        lab, n = ndimage.label(far)
        sizes = np.bincount(lab.ravel())
        sizes[0] = 0
        lut = np.zeros(sizes.size, dtype=bool)
        lut[np.flatnonzero((sizes > 0) & (sizes <= MAX_BLOB))] = True
        iso = lut[lab]

        st = structure(green(MEASURE / f"{s}__M0.tif"))
        st = st[:iso.shape[0], :iso.shape[1]]
        iso = iso[:st.shape[0], :st.shape[1]]

        med_all = float(np.median(st))
        med_iso = float(np.median(st[iso])) if iso.any() else float("nan")
        # what fraction of outliers sit in the flattest quintile of the frame?
        q20 = float(np.quantile(st, 0.20))
        frac_flat = float((st[iso] <= q20).mean()) if iso.any() else float("nan")

        print(f"\n== {s} ==")
        print(f"  isolated outlier pixels        : {int(iso.sum()):,}")
        print(f"  median structure, whole frame  : {med_all:9.2f}")
        print(f"  median structure, at outliers  : {med_iso:9.2f}")
        print(f"  ratio outlier/frame            : {med_iso / med_all:9.3f}")
        print(f"  outliers in flattest 20% of px : {100 * frac_flat:8.1f}%"
              f"   (chance = 20.0%)")
        out[s] = {"median_structure_all": med_all,
                  "median_structure_outliers": med_iso,
                  "ratio": med_iso / med_all,
                  "frac_in_flattest_quintile": frac_flat,
                  "n_isolated_px": int(iso.sum())}

    (ROOT / "election-indeterminacy.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {ROOT / 'election-indeterminacy.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

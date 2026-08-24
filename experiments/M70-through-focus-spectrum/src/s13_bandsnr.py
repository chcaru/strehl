"""M70 s13 - the charter's third question, as far as this data can take it.

The brief asks: "Fact 27 measured a *cutoff*, not a rolloff. Whether the
measured optical response below the cutoff is attenuated-but-present or
effectively absent is a different question from where the cutoff sits."

What is measurable here, and what is not:

  MEASURABLE. Whether a band carries signal at all, and by how much it stands
  above the calibrated noise floor, in the sharpest frame available. That is
  S_b / sigma^2 at the peak frame - a pure signal-to-noise ratio, needing no
  knowledge of the latent.

  NOT MEASURABLE from this corpus. The optical MTF itself. Measured band power
  is |H(f)|^2 |L(f)|^2. Natural scene spectra fall roughly as f^-alpha with
  alpha near 2, so a falling band-power curve is the product of a falling scene
  spectrum and a falling MTF and the two cannot be separated without a target
  of known spectrum. This script reports the product and says so.

The one thing this DOES settle is presence versus absence, because the noise
floor is externally calibrated (fact 29, and M70's own reproduction at
0.977-0.996x). A band whose peak-frame power sits at the floor contains no
signal in any frame, whatever the scene was.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
import s05_analyse as A5  # noqa: E402
import s07_unclipped as S7  # noqa: E402

OUT = A5.OUT
STACKS = S7.STACKS
APERTURE = S7.APERTURE
BAND_ORDER = [b[0] for b in M.BANDS]


def main() -> None:
    print("=" * 122)
    print("PEAK-FRAME BAND SNR  =  (best frame's band power - sigma^2) / sigma^2")
    print("  median over textured patches. This is |H|^2|L|^2 / sigma^2, NOT an MTF.")
    print("  A value near 0 means the band carries no signal in ANY frame of the stack.")
    print("=" * 122)
    hdr = f"{'stack':16s} {'K':>4s} {'F':>5s} " + " ".join(f"{b.split('_')[0]:>9s}" for b in BAND_ORDER)
    print(hdr)
    rows = []
    for st in STACKS:
        d = A5.load(st)
        s, nvar = A5.signal(d)
        tex, _ = A5.classify(d, s, nvar)
        idx = [p for p in range(s.shape[1]) if tex[p]]
        vals = []
        for j in range(s.shape[2]):
            v = [float(np.max(s[:, p, j]) / max(nvar[int(np.argmax(s[:, p, j])), p], 1e-30))
                 for p in idx]
            vals.append(A5.med(v))
        rows.append({"stack": st, "F": APERTURE[st], "K": int(s.shape[0]),
                     "snr": {BAND_ORDER[j]: vals[j] for j in range(len(vals))}})
        print(f"{st:16s} {s.shape[0]:4d} {APERTURE[st]:5.1f} "
              + " ".join(f"{v:9.2f}" for v in vals))

    print()
    print("=" * 122)
    print("THE SAME, GROUPED BY MARKED APERTURE (median of stack medians)")
    print("  fact 27 puts the f/11 cutoff at 0.2762 cyc/px, which is the b5/b6 boundary.")
    print("=" * 122)
    print(f"{'aperture':10s} {'n':>3s} " + " ".join(f"{b.split('_')[0]:>9s}" for b in BAND_ORDER)
          + "   b6/b5")
    ap_out = {}
    for ap in (5.6, 8.0, 11.0):
        g = [r for r in rows if r["F"] == ap]
        v = [float(np.median([r["snr"][b] for r in g])) for b in BAND_ORDER]
        ap_out[str(ap)] = {BAND_ORDER[j]: v[j] for j in range(len(v))}
        print(f"f/{ap:<9.1f} {len(g):3d} " + " ".join(f"{x:9.2f}" for x in v)
              + f"   {v[-1] / max(v[-2], 1e-9):6.3f}")

    print()
    print("  The b6/b5 ratio is the one number here that is close to MTF-like, because")
    print("  the two bands are adjacent and the scene spectrum changes little across them.")
    print("  It compares the band just above the f/11 cutoff with the band just below it.")

    print()
    print("=" * 122)
    print("FALL FROM b3_mid TO b5_mid - the product of scene spectrum and MTF, not the MTF")
    print("=" * 122)
    for r in rows:
        a, b = r["snr"]["b3_mid"], r["snr"]["b5_mid"]
        print(f"{r['stack']:16s} f/{r['F']:<5.1f} b3 {a:9.2f} -> b5 {b:9.2f}   "
              f"ratio {b / max(a, 1e-9):7.4f}")

    with open(os.path.join(OUT, "s13_bandsnr.json"), "w", encoding="utf-8") as fh:
        json.dump({"per_stack": rows, "per_aperture": ap_out}, fh, indent=1)
    print("\nwrote out/s13_bandsnr.json")


if __name__ == "__main__":
    main()

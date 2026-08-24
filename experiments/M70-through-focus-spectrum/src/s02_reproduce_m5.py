"""M70 s02 - reproduce M5's published numbers before extending its harness.

Two published numbers are re-derived from the original data with M5's own
committed library:

  * fact 27 - the f/11 green-quincunx knee at f_sig = 0.2762 sensor cyc/px,
    on the centre ROI of `109MSDCF`.
  * fact 29 - the spectral floor above that knee is a structure-free sigma
    estimate agreeing with the photon-transfer model to 0.950-1.093x.

The second is re-derived against the SHIPPED profile constants, not against
m5_lib's own `noise_model_var`, which predates M25's ISO-50 gain fix and M48's
read-noise fix. `109MSDCF` is ISO 160, where the two agree exactly, so this
comparison is like-for-like with M5's published figure; the divergence is at
ISO 50 and >= ISO 400 and is exercised in s04.

AGENTS.md: "reproduce one published number from the original data before
extending anyone's experiment".
"""

from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m70lib as M  # noqa: E402
from m70lib import L  # noqa: E402

STACK = r"D:\personal\macro\109MSDCF"
ROI_SIZE = 512
TILE = 256
ISO = 160.0
MARKED_F = 11.0


def main() -> None:
    frames = sorted(f for f in os.listdir(STACK) if f.lower().endswith(".arw"))
    print(f"stack {STACK}  n={len(frames)}")

    # M5 kept the N_BEST=5 sharpest frames per ROI; here we simply scan all of
    # them and report the best knee, which is what M5's headline quotes.
    rc = int(round(0.50 * L.ACTIVE_H))
    cc = int(round(0.50 * L.ACTIVE_W))
    rc -= rc % 2
    cc -= cc % 2
    print(f"centre ROI at sensor (r,c)=({rc},{cc})  size={ROI_SIZE} GQ samples  tile={TILE}")

    best = None
    rows = []
    for name in frames:
        a = L.load_active(os.path.join(STACK, name))
        patch = L.crop_lattice(a, "GQ", rc, cc, ROI_SIZE)
        f, p, counts = L.spectrum(patch, "GQ", tile=TILE, window="hann", sector="iso")
        kn = L.knee(f, p, counts, TILE, ROI_SIZE, "GQ", window="hann", sector="iso")
        sig = M.w2_weighted_mean(patch, TILE, "hann")
        model_var = float(M.noise_var_dn2(sig, ISO))
        # floor: mean power strictly above the detected knee (or above the
        # f/11 cutoff if no knee), i.e. M5's structure-free sigma estimate.
        fc = kn.get("f_c") or M.f_cutoff_sensor(MARKED_F)
        m_hi = f > (fc if np.isfinite(fc) else M.f_cutoff_sensor(MARKED_F))
        floor = float((p[m_hi] * counts[m_hi]).sum() / counts[m_hi].sum())
        rows.append((name, kn.get("f_c"), sig, floor, model_var))
        if kn.get("f_c") is not None and (best is None or kn["f_c"] > best[1]):
            best = (name, kn["f_c"], sig, floor, model_var)
        del a

    print()
    print(f"{'frame':16s} {'f_sig':>8s} {'mean DN':>9s} {'floor sd':>9s} {'model sd':>9s} {'ratio':>7s}")
    for name, fs, sig, floor, mv in rows:
        fs_s = f"{fs:.4f}" if fs else "   --  "
        print(
            f"{name:16s} {fs_s:>8s} {sig:9.1f} {np.sqrt(floor):9.2f} "
            f"{np.sqrt(mv):9.2f} {np.sqrt(floor/mv):7.3f}"
        )

    print()
    print("PUBLISHED (fact 27): best f_sig on the f/11 GQ centre ROI = 0.2762 sensor cyc/px")
    print(f"REPRODUCED         : best f_sig = {best[1]:.4f}  (frame {best[0]})")
    print("PUBLISHED (fact 29): floor / photon-transfer model = 0.950-1.093x over 15 f/11 cases")
    r = np.array([np.sqrt(fl / mv) for _, fs, _, fl, mv in rows if fs is not None])
    print(
        f"REPRODUCED         : floor/model = {r.min():.3f}-{r.max():.3f}x "
        f"(median {np.median(r):.3f}x) over {r.size} frames with a detected knee"
    )
    print()
    print("DERIVED cross-check of the a-priori optics gate (rule 21):")
    for mf in (5.6, 8.0, 11.0):
        print(
            f"  marked f/{mf:<4}  N_eff = {M.n_eff(mf):5.1f}  "
            f"f_c(B=3) = {M.f_cutoff_sensor(mf):.4f} cyc/px   "
            f"GQ reach = {L.lattice_nyquist_sensor('GQ'):.4f}"
        )


if __name__ == "__main__":
    main()


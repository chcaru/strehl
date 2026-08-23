"""01 -- prove the Python port reproduces `m9-support`'s committed numbers.

Discipline 15/34: reproduce a published number from the original data before
extending anyone's experiment.  This milestone's entire Gate 1a rests on a
Python transliteration of a Rust harness; if the port is wrong, every
simulated result downstream is wrong in a way that looks like physics.

Target: `experiments/m9-support/data/analysis-109MSDCF-coupled.txt` S8 and
`experiments/m9-support/data/sensitivity-109MSDCF.csv`, both measured on
`C:\\dev\\macro\\test\\109MSDCF` (22 frames, ISO 160) at the flat ROI
`2272,1344,256,256`.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/01-port-check.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402

STACK = r"C:\dev\macro\test\109MSDCF"
# S8's c(1)/floor are the mean over the FOUR flat ROIs of
# `data/rois-109MSDCF.txt` -- confirmed against `sweep-109MSDCF-coupled.csv`,
# which contains one row per (measure, width, roi).  phi, by contrast, comes
# from `sensitivity-109MSDCF.csv`, which is the single ROI 2272,1344.
# Mixing those two scopes up cost an hour; see the report's mistakes section.
FLAT_ROIS = [S.Roi(2272, 1344, 256, 256), S.Roi(2505, 441, 256, 256),
             S.Roi(2665, 1513, 256, 256), S.Roi(329, 1353, 256, 256)]
PHI_ROI = FLAT_ROIS[0]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "data", "port-check-109MSDCF.txt")

# The committed S8 table, verbatim, as the reproduction target.
S8 = {
    "ring-0-1":      (0.48469, 1.6917, 1.0525),
    "dsml-s12":      (0.46534, 1.8330, 1.0608),
    "dsml-s6":       (0.44773, 1.7924, 1.0609),
    "dsml-s3":       (0.43795, 1.7305, 1.0628),
    "dsml-s1":       (0.43568, 1.6180, 1.0294),
    "sml-w0":        (0.43568, 1.6180, 1.0294),
    "ring-1-3":      (0.05499, 1.2945, 1.0646),
    "sml-w2":        (0.03567, 1.0954, 1.0353),
    "tenengrad-w2":  (0.03456, 1.2150, 1.0597),
    "ring-2-6":      (0.01920, 1.2514, 1.0600),
    "sml-w5":        (0.00787, 1.0395, 1.0395),
    "tenengrad-w5":  (0.00652, 1.1142, 1.0596),
    "ring-4-12":     (0.00540, 1.1645, 1.0497),
    "sml-w11":       (0.00374, 1.0386, 1.0386),
    "tenengrad-w11": (0.00314, 1.0911, 1.0601),
    "tenengrad-w0":  (0.00284, 0.9952, 0.9952),
}
COMMITTED_RHO_PHI = 0.917
COMMITTED_RHO_SUP = -0.207
COMMITTED_SINGLE_SIGMA = 28.2007


def spearman(a, b):
    from scipy import stats
    r = stats.spearmanr(a, b)
    return float(r.statistic), float(r.pvalue)


def main():
    lines = []

    def say(s=""):
        print(s, flush=True)
        lines.append(s)

    t0 = time.time()
    say(f"loading {STACK}")
    raw = S.load_real(STACK)
    iso = S.iso_of(STACK)
    noise = F.NoiseModel.for_iso(iso)
    say(f"  {raw.shape[0]} frames, {raw.shape[2]}x{raw.shape[1]} raw, "
        f"ISO {iso:.0f}, g={noise.gain_dn_per_e:.5f} DN/e-, "
        f"RN={noise.read_noise_e:.2f} e-  [{time.time() - t0:.1f}s]")

    treatments = F.design(False)
    ms_all = F.design(True)
    sweep_margin = max((w - 1) // 2 for w in F.DEFAULT_WIDTHS) \
        + F.max_support(ms_all)
    reach = F.max_support(ms_all)
    phi_margin = 4 * reach + 2
    margin = max(sweep_margin, phi_margin)

    luma_all, val_all = {}, {}
    for r in FLAT_ROIS:
        luma_all[str(r)], val_all[str(r)] = S.tiles(raw, r, margin)

    def tile_at(l, m):
        o = margin - m
        return l[:, o:l.shape[1] - o, o:l.shape[2] - o]

    phi_luma = tile_at(luma_all[str(PHI_ROI)], phi_margin)
    single_sigma = F.mean_and_sigma(
        val_all[str(PHI_ROI)][raw.shape[0] // 2])[1]
    say(f"  sweep tile {256 + 2 * sweep_margin}x{256 + 2 * sweep_margin} "
        f"(margin {sweep_margin}); phi tile {phi_luma.shape[2]}x"
        f"{phi_luma.shape[1]} (margin {phi_margin}, reach {reach})")
    say(f"  {len(FLAT_ROIS)} flat ROIs pooled for c(1)/floor; "
        f"phi on {PHI_ROI} only")
    say(f"  single_sigma[{PHI_ROI}] = {single_sigma:.4f}  "
        f"(m9 committed {COMMITTED_SINGLE_SIGMA:.4f})")

    say()
    say(f"{'measure':<14} {'phi':>9} {'phi*':>9} {'c(1)':>8} {'c(1)*':>8} "
        f"{'floor':>8} {'floor*':>8} {'excess':>8}")
    got = {}
    for m in treatments:
        c, tot, phi, taps = F.phi_for(m, phi_luma, noise, reach)
        pooled = None
        for r in FLAT_ROIS:
            lu = tile_at(luma_all[str(r)], sweep_margin)
            va = val_all[str(r)]
            rows = F.sweep_measure(m, lu, va, va[raw.shape[0] // 2], noise,
                                   sweep_margin)
            rr = np.array([x["ratio"] for x in rows])
            pooled = rr if pooled is None else pooled + rr
        pooled = pooled / len(FLAT_ROIS)
        c1 = float(pooled[0])
        floor = float(pooled.min())
        got[m.name] = (phi, c1, floor, c1 - floor, taps)
        ephi, ec1, efl = S8[m.name]
        say(f"{m.name:<14} {phi:>9.5f} {ephi:>9.5f} {c1:>8.4f} {ec1:>8.4f} "
            f"{floor:>8.4f} {efl:>8.4f} {c1 - floor:>8.4f}")

    names = list(S8)
    phis = [got[n][0] for n in names]
    exc = [got[n][3] for n in names]
    sup = [dict((m.name, m.support_radius) for m in treatments)[n]
           for n in names]
    r_phi, p_phi = spearman(phis, exc)
    r_sup, p_sup = spearman(sup, exc)
    say()
    say(f"Spearman rho(phi, excess)     = {r_phi:+.3f}, p = {p_phi:.4f}   "
        f"(m9 committed {COMMITTED_RHO_PHI:+.3f})")
    say(f"Spearman rho(support, excess) = {r_sup:+.3f}, p = {p_sup:.4f}   "
        f"(m9 committed {COMMITTED_RHO_SUP:+.3f})")

    dphi = max(abs(got[n][0] - S8[n][0]) for n in names)
    dc1 = max(abs(got[n][1] - S8[n][1]) for n in names)
    dfl = max(abs(got[n][2] - S8[n][2]) for n in names)
    say()
    say(f"max |dphi|   = {dphi:.6f}")
    say(f"max |dc(1)|  = {dc1:.6f}")
    say(f"max |dfloor| = {dfl:.6f}")
    ok = (dphi < 5e-4 and dc1 < 5e-3 and dfl < 5e-3
          and abs(single_sigma - COMMITTED_SINGLE_SIGMA) < 5e-3)
    say(f"PORT CHECK: {'PASS' if ok else 'FAIL'}   [{time.time() - t0:.1f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {os.path.normpath(OUT)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""O8 -- the owner's unit. What does one frame off peak cost, in amplitude?

Bar B5 requires the result in a unit the owner can feel, from the MEASURED
through-focus response of this capture and never from a theoretical defocus
model. o5 gave the elector-vs-oracle mosaic spectra; it did not give the
yardstick in the same unit, so the conversion from "N frames off peak" to
"X % amplitude" was unmeasured.

This rebuilds the emitted mosaic at forced offsets of 0, 1, 2 and 5 frames from
the oracle's choice, on the evaluation channel G2, and takes the same radial
power spectra o5 used. The gradient of amplitude against forced offset IS the
capture's own through-focus response, in the same bands as the headline.

No new bar is registered here. This is a unit conversion of numbers already
measured under bars registered at 66c0d3f.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "M95-merge-vs-frame", "src"))
import m95lib as L  # noqa: E402
import o2lib as O  # noqa: E402
from o3_commission import CUBE, OUTD  # noqa: E402
from o5_deficit import argmaxes, gather_pixels, PLANE_PITCH_UM  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

ROIS = ["ROI-LOWDRIFT", "ROI-MIDDRIFT", "ROI-HIGHDRIFT"]
BANDS = ((0.10, 0.20), (0.20, 0.30), (0.30, 0.40), (0.40, 0.50))
OFFS = [0, 1, 2, 5]
EXCESS_PP = {"ROI-LOWDRIFT": 0.8119, "ROI-MIDDRIFT": 2.3615, "ROI-HIGHDRIFT": 2.3793}
ONE_FRAME_PCT = {"ROI-LOWDRIFT": 11.7008, "ROI-MIDDRIFT": 12.3642,
                 "ROI-HIGHDRIFT": 11.4792}


def main() -> int:
    meta = json.load(open(os.path.join(CUBE, "cube_meta.json"), encoding="utf-8"))
    n, black = meta["n"], meta["black"]
    f1 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g1.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    f2 = np.asarray(np.load(os.path.join(CUBE, "ROI-FLAT.g2.npy"), mmap_mode="r")[::12],
                    dtype=np.float64)
    noise, _ = O.fit_noise(f1.reshape(-1, f1.shape[-1]), f2.reshape(-1, f2.shape[-1]), black)
    del f1, f2
    print(f"noise model: {noise}")
    k = 1 + O.BOX_R
    res = {}

    for nm in ROIS:
        print("\n" + "=" * 74)
        print(nm)
        g1 = np.load(os.path.join(CUBE, f"{nm}.g1.npy"), mmap_mode="r")
        g2 = np.load(os.path.join(CUBE, f"{nm}.g2.npy"), mmap_mode="r")
        _, ao = argmaxes(g1, noise, n)
        picks = {f"off{o}": np.clip(ao + o, 0, n - 1) for o in OFFS}
        px = gather_pixels(g2, n, picks, k)
        c = 512
        y0 = (px["off0"].shape[0] - c) // 2
        x0 = (px["off0"].shape[1] - c) // 2
        ref = px["off0"][y0:y0 + c, x0:x0 + c]
        fr, pref, _ = L.radial_psd(ref)
        rows = []
        for o in OFFS:
            m = px[f"off{o}"][y0:y0 + c, x0:x0 + c]
            _, p, _ = L.radial_psd(m)
            e = {}
            for lo, hi in BANDS:
                b0 = L.band_power(fr, pref, lo, hi)
                b1 = L.band_power(fr, p, lo, hi)
                cy = 0.5 * (lo + hi) / (PLANE_PITCH_UM * 1e-3)
                e[f"{lo:.2f}-{hi:.2f}"] = dict(
                    cy_per_mm=cy, amp_pct=100.0 * (np.sqrt(b1 / b0) - 1.0))
            rows.append(dict(offset=o, bands=e))
            s = "  ".join(f"{v['cy_per_mm']:5.1f}cy/mm {v['amp_pct']:+7.3f}%"
                         for v in e.values())
            print(f"  forced +{o} frames: {s}")

        one = rows[1]["bands"]
        frames = EXCESS_PP[nm] / ONE_FRAME_PCT[nm]
        print(f"  measured election error = {EXCESS_PP[nm]:.4f} pp / "
              f"{ONE_FRAME_PCT[nm]:.4f} pp per frame = {frames:.4f} frames off peak")
        cost = {}
        for kk, v in one.items():
            c_pct = frames * v["amp_pct"]
            cost[kk] = dict(cy_per_mm=v["cy_per_mm"], one_frame_amp_pct=v["amp_pct"],
                            election_amp_pct=c_pct)
            print(f"    at {v['cy_per_mm']:5.1f} cy/mm: one frame costs "
                  f"{v['amp_pct']:+7.3f} % amplitude -> election costs "
                  f"{c_pct:+7.3f} %")
        res[nm] = dict(frames_off_peak=frames, rows=rows, cost=cost)
        del g1, g2, px

    print("\n" + "=" * 74)
    worst = min(min(v["election_amp_pct"] for v in r["cost"].values())
                for r in res.values())
    print(f"OWNER-FACING: the worst measured amplitude cost of the election, over "
          f"three ROIs and four bands, is {worst:+.3f} %.")
    with open(os.path.join(OUTD, "o8_owner.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=float)
    print(f"wrote {os.path.join(OUTD, 'o8_owner.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""crosspop -- the same two instruments, the same real pair, both populations.

`ladder.py` established that BOTH instruments recover a planted detail ratio to
within 0.3% on BOTH tile populations, including a rung where the companion is
SHARPER.  Neither is broken.  So the 1.7x field disagreement on `119MSDCF`
against `enfuse` cannot be an instrument error -- it has to come from what each
instrument was given.

The live hypothesis is the tile population.  `cohfree.py` reads C on
`rois.census(...)` DETAIL tiles; the V-NOISE2 scene term reads FLAT tiles --
tiles selected for the BOTTOM quartile of high-pass energy, i.e. chosen for
having no detail in them.  Those are different questions about the same image.

This script runs both statistics on the same real strehl/enfuse pair over both
populations, so the 2x2 either localises the disagreement to the population or
refutes that explanation.

    C is a cross-power within one arm's own A/B pair, so no cross-arm
    registration enters the FFT -- only crop PLACEMENT is registered, via the
    measured content scale.  Same for the scene term.  This is the property
    that lets both arms be read on their own native pixels.

Reported on one footing: "the comparator's detail amplitude relative to
strehl's", so >1 means enfuse holds more detail than strehl.

    python crosspop.py [nroi=40]
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import uniform_filter

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
sys.path.insert(0, os.path.join(_HERE, "..", "V-NOISE"))
import h2                                                        # noqa: E402
from h2h2b import Comp, cross_bands, T                           # noqa: E402
from noisefree import EDGE, HP                                   # noqa: E402

import hd2                                                       # noqa: E402
from ladder import scene_term                                    # noqa: E402

BAND = (0.2, 0.25)
W = (0.2126, 0.7152, 0.0722)


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "119"
    nroi = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    census, spec = hd2.paths_for(key)
    sc = hd2.scales_for(key)
    bi = list(h2.BANDS).index(BAND)

    z = np.load(census)
    cells, emax = z["cells"], z["emax"]
    flat_idx = list(z["flat"])
    order = np.argsort(emax)
    detail_idx = [int(i) for i in order[-len(flat_idx):]]
    rng = np.random.default_rng(11)

    def pick(idx):
        return [tuple(cells[idx[i]])
                for i in rng.permutation(len(idx))[:nroi]]

    pops = {"DETAIL": pick(detail_idx), "FLAT": pick(flat_idx)}

    arms = {}
    for k in ("strehl", "enfuse"):
        pa, pb, lab = spec[k]
        arms[k] = (Comp(dict(path=pa, weights=W)),
                   Comp(dict(path=pb, weights=W)),
                   float(sc.get(k, 1.0)), lab)

    print("=" * 96)
    print(f"CROSSPOP -- both instruments, real strehl vs enfuse, both "
          f"populations, {key}")
    print("=" * 96)
    for k, (_, _, s, lab) in arms.items():
        print(f"  {k:8s} content scale {s:.4f}   {lab}")
    print(f"  band {BAND[0]}-{BAND[1]} cyc/px, {nroi} tiles per population")
    print(f"\n  Reported as the COMPARATOR's detail amplitude relative to "
          f"strehl's: >1 means")
    print(f"  enfuse holds more detail.  Field readings to reproduce: "
          f"C 1.012, scene term 1.733.")

    out = {}
    print(f"\n  {'population':12s} {'C (enfuse/strehl)':>20s} "
          f"{'scene (enfuse/strehl)':>24s} {'disagreement':>14s}")
    for pname, cellset in pops.items():
        per = {}
        for k, (A, B, s, _) in arms.items():
            cs, ss = [], []
            tc = int(round(T / s))
            for (y, x) in cellset:
                y0, x0 = int(round(y / s)), int(round(x / s))
                ca, na = A.crop(y0, x0, tc)
                cb, nb = B.crop(y0, x0, tc)
                if ca is None or cb is None or na or nb:
                    continue
                C = cross_bands(ca, cb)
                S = scene_term(ca, cb)
                if C is not None and C[bi] > 0 and S and S > 0:
                    cs.append(float(C[bi]))
                    ss.append(S)
            per[k] = (float(np.median(cs)), float(np.median(ss)), len(cs))
        cr = np.sqrt(per["enfuse"][0] / per["strehl"][0])
        sr = per["enfuse"][1] / per["strehl"][1]
        out[pname] = {"C_ratio_amplitude": cr, "scene_ratio": sr,
                      "n": per["strehl"][2],
                      "raw": {k: v[:2] for k, v in per.items()}}
        print(f"  {pname:12s} {cr:20.3f} {sr:24.3f} {sr / cr:13.2f}x")

    print()
    print("=" * 96)
    print("READING")
    print("=" * 96)
    d, f = out["DETAIL"], out["FLAT"]
    print(f"  On DETAIL tiles the two instruments agree to "
          f"{max(d['scene_ratio'], d['C_ratio_amplitude']) / min(d['scene_ratio'], d['C_ratio_amplitude']):.2f}x; "
          f"on FLAT tiles, to "
          f"{max(f['scene_ratio'], f['C_ratio_amplitude']) / min(f['scene_ratio'], f['C_ratio_amplitude']):.2f}x.")
    print(f"  C moves {f['C_ratio_amplitude'] / d['C_ratio_amplitude']:.2f}x "
          f"between populations; the scene term moves "
          f"{f['scene_ratio'] / d['scene_ratio']:.2f}x.")
    dst = os.path.join(hd2.ROOT, f"crosspop-{key}.json")
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {dst}")


if __name__ == "__main__":
    main()

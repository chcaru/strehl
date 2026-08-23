r"""M48c script 02 -- ISO-resolved stability and cluster structure.

Script 01 stored only a COUNT of how many of the 11 ISO groups flagged each
pixel, which cannot answer the brief's second question: "a defect that appears
at ISO 2000 and not at ISO 50 needs a different remedy from one that is fixed
forever". A count of 6 is consistent with the six LOWEST ISOs and with the six
HIGHEST, and those are different objects. This pass stores an 11-bit MASK, one
bit per ISO group in ascending ISO order, so the question is answerable.

It also labels connected components, because the brief asks which POPULATIONS
exist and "hot pixels, stuck pixels, cold pixels and clusters are different
populations with different fixes". An isolated single pixel and a 40-pixel blob
are not the same defect and do not have the same remedy.

Criterion is identical to script 01's criterion B, unchanged:
    flag if |e - med(e)| > K * 1.4826*MAD(e),  K = 6
so the two runs are directly comparable and this is not a re-tune.

DISCLOSURE, found in script 01's output and not anticipated in its
pre-registration: sigma_obs is QUANTISED. Raw samples are integers, so a mean
over T=20 frames is a multiple of 1/20 DN, and the MAD of such a quantity can
only take values k/20 * 1.4826. Script 01's eleven sigma_obs values are exactly
6,6,6,7,7,9,9,10,14,17 twentieths. One quantum is 0.0741 DN, which against
sigma_obs = 0.4448 DN at ISO 50 is a +-5.6% systematic on any ratio built from
it. That is reported here per ISO rather than buried.

D:\macro-dark-frames is read-only source data. This script only reads it.
"""

import json
import os

import numpy as np
import rawpy
from scipy.ndimage import label, median_filter

ROOT = r"D:\macro-dark-frames"
DROP_STABILISATION = 2
PLANES = (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1))
K = 6.0
RECUR_MIN = 6

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "defect-stability.json")
MAPDIR = os.path.join(HERE, "data")


def iso_of(path):
    import exifread

    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return int(str(t.get("EXIF ISOSpeedRatings", "0")))


def load_mean(files):
    acc = None
    for f in files:
        with rawpy.imread(f) as rr:
            raw = rr.raw_image_visible
            if acc is None:
                acc = {
                    n: np.zeros(raw[dy::2, dx::2].shape, np.float64)
                    for n, dy, dx in PLANES
                }
            for n, dy, dx in PLANES:
                acc[n] += raw[dy::2, dx::2].astype(np.float64)
            del raw
    for n in acc:
        acc[n] /= len(files)
    return acc


def excess(m):
    fp = np.ones((3, 3), bool)
    fp[1, 1] = False
    return m - median_filter(m, footprint=fp, mode="nearest")


def main():
    dirs = sorted(
        os.path.join(ROOT, d)
        for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d))
    )
    # Bit position is ascending ISO, so bit 0 is ISO 50 and bit 10 is ISO 2000.
    def first_arw(d):
        return os.path.join(
            d, sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))[0]
        )

    order = sorted((iso_of(first_arw(d)), d) for d in dirs)
    isos = [i for i, _ in order]
    print("bit order (ascending ISO):", isos)

    hot_mask = None
    cold_mask = None
    per_iso = []

    for bit, (iso, d) in enumerate(order):
        files = sorted(
            os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".arw")
        )[DROP_STABILISATION:]
        t_n = len(files)
        means = load_mean(files)
        if hot_mask is None:
            shp = means["R"].shape
            hot_mask = {n: np.zeros(shp, np.uint16) for n, _, _ in PLANES}
            cold_mask = {n: np.zeros(shp, np.uint16) for n, _, _ in PLANES}

        rec = {"iso": iso, "frames": t_n, "planes": {}}
        for n, _, _ in PLANES:
            e = excess(means[n])
            med = float(np.median(e))
            mad_raw = float(np.median(np.abs(e - med)))
            s_obs = mad_raw * 1.4826
            quantum = 1.4826 / t_n
            d_e = e - med
            hb = d_e > K * s_obs
            cb = d_e < -K * s_obs
            hot_mask[n] |= hb.astype(np.uint16) << bit
            cold_mask[n] |= cb.astype(np.uint16) << bit
            rec["planes"][n] = {
                "sigma_obs_dn": s_obs,
                "quantum_dn": quantum,
                "quantum_rel_pct": 100.0 * (quantum / 2.0) / s_obs,
                "sigma_obs_in_quanta": s_obs / quantum,
                "hot": int(hb.sum()),
                "cold": int(cb.sum()),
            }
            del e, d_e, hb, cb
        g1 = rec["planes"]["G1"]
        print(
            f"bit {bit:2d}  ISO {iso:5d}  s_obs {g1['sigma_obs_dn']:6.4f} "
            f"= {g1['sigma_obs_in_quanta']:5.2f} quanta (+-{g1['quantum_rel_pct']:.2f}%)  "
            f"hot {g1['hot']:7d}  cold {g1['cold']:7d}"
        )
        per_iso.append(rec)
        del means

    n_iso = len(order)
    popcount = np.array([bin(v).count("1") for v in range(1 << n_iso)], np.uint8)

    out = {"bit_order_iso": isos, "per_iso": per_iso, "planes": {}}
    for n, _, _ in PLANES:
        hm, cm = hot_mask[n], cold_mask[n]
        hk = popcount[hm]
        ck = popcount[cm]
        defect = hk >= RECUR_MIN
        colddef = ck >= RECUR_MIN

        # Which ISOs does each recurring defect fire at? Per-bit hit rate
        # among defects tells low-ISO-only from high-ISO-only.
        dm = hm[defect]
        per_bit = [int(np.count_nonzero(dm & (1 << b))) for b in range(n_iso)]
        cdm = cm[colddef]
        per_bit_cold = [int(np.count_nonzero(cdm & (1 << b))) for b in range(n_iso)]

        lab, ncomp = label(defect, structure=np.ones((3, 3), int))
        sizes = np.bincount(lab.ravel())[1:] if ncomp else np.array([], int)
        shist = np.bincount(sizes, minlength=12)[:12] if sizes.size else [0] * 12

        out["planes"][n] = {
            "hot_defects": int(defect.sum()),
            "cold_defects": int(colddef.sum()),
            "hot_defect_hits_per_iso": per_bit,
            "cold_defect_hits_per_iso": per_bit_cold,
            "hot_all11": int((hk == n_iso).sum()),
            "components": int(ncomp),
            "component_size_hist": [int(v) for v in shist],
            "largest_component": int(sizes.max()) if sizes.size else 0,
            "isolated_singletons": int(shist[1]) if len(shist) > 1 else 0,
        }
        np.save(os.path.join(MAPDIR, f"hotmask-{n}.npy"), hm)
        np.save(os.path.join(MAPDIR, f"coldmask-{n}.npy"), cm)

    tot = sum(out["planes"][n]["hot_defects"] for n, _, _ in PLANES)
    hits = np.sum(
        [out["planes"][n]["hot_defect_hits_per_iso"] for n, _, _ in PLANES], axis=0
    )
    print(f"\nhot defects {tot}; hits per ISO among them:")
    for iso, h in zip(isos, hits):
        print(f"   ISO {iso:5d}: {h:7d}  ({100.0*h/tot:5.1f}% of defects)")
    comp = sum(out["planes"][n]["components"] for n, _, _ in PLANES)
    single = sum(out["planes"][n]["isolated_singletons"] for n, _, _ in PLANES)
    print(
        f"\ncomponents {comp}, isolated singletons {single} "
        f"({100.0*single/comp:.1f}%), largest "
        f"{max(out['planes'][n]['largest_component'] for n, _, _ in PLANES)}"
    )

    out["_meta"] = {
        "script": "02-stability-and-clusters.py",
        "criterion": "identical to 01 criterion B, K=6 robust MAD",
        "bit_semantics": "bit b set = flagged in the ISO group at bit_order_iso[b]",
        "quantisation_disclosure": "mean of T=20 integer frames is quantised at "
        "1/20 DN, so MAD takes only values k*1.4826/20; the per-ISO "
        "quantum_rel_pct is the resulting systematic on any ratio",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

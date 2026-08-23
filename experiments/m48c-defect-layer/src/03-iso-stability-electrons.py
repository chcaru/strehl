r"""M48c script 03 -- is the defect population ISO-stable at CONSTANT sensitivity?

Script 02 found the detection rate among defects rising from 26.1% at ISO 50 to
81.7% at ISO 2000 and read as "the population grows with ISO". That reading is
WRONG, and this script exists to say why and to replace it.

The threshold in script 02 is 6*sigma_obs in DN. Converting it to ELECTRONS by
dividing by g = max(ISO,100)/436.8 shows the instrument is not the same
instrument at each ISO:

    ISO   50: 6*0.4448/0.2289 = 11.66 e-      <-- least sensitive
    ISO 2000: 6*1.2602/4.5788 =  1.65 e-      <-- 7.1x more sensitive

So a DN-domain threshold asks a harder question at low ISO than at high ISO, and
a rising count is exactly what a fixed population would produce. Discipline 331
in a new costume: a precision that varies across the conditions being compared
cannot be used to compare them.

THE FIX. Threshold in ELECTRONS, which is the physical domain the defect lives
in. Dark current is a property of the silicon and of exposure time; every dark
here is 1/100 s, so a defect's excess in electrons must be the SAME at every
ISO if the population is fixed. Analogue gain changes how well we SEE it, not
how big it is.

PRE-REGISTERED EXPECTATION: at a fixed electron threshold the count is
ISO-INDEPENDENT. Residual variation should track the per-ISO noise floor in
electrons (1.94 e- at ISO 50 down to 0.28 e- at ISO 2000), i.e. the low ISOs
should still lose the very weakest defects to their own noise, but the strong
ones must appear at every ISO. If the count still rises 3x at fixed electron
threshold, the population genuinely is gain-dependent and my reading is wrong.

E_THRESH is swept rather than fixed at one value, because a single threshold
cannot distinguish "population is flat" from "threshold happens to sit in a
flat part of the amplitude distribution".

D:\macro-dark-frames is read-only source data. This script only reads it.
"""

import json
import os

import numpy as np
import rawpy
from scipy.ndimage import median_filter

ROOT = r"D:\macro-dark-frames"
DROP_STABILISATION = 2
PLANES = (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1))
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
# Sweep: 12 e- is just above the worst ISO's 6-sigma bar (11.66 e-), so every
# ISO can see it. 24 and 48 probe the strong tail; 6 deliberately sits BELOW
# the low-ISO bar so the low ISOs must fail there -- a built-in negative control.
E_THRESHOLDS = (6.0, 12.0, 24.0, 48.0)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "iso-stability-electrons.json")


def gain(iso):
    return max(iso, BASE_ISO) / GAIN_DIVISOR


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
    def first_arw(d):
        return os.path.join(
            d, sorted(f for f in os.listdir(d) if f.lower().endswith(".arw"))[0]
        )

    dirs = [
        os.path.join(ROOT, d)
        for d in os.listdir(ROOT)
        if os.path.isdir(os.path.join(ROOT, d))
    ]
    order = sorted((iso_of(first_arw(d)), d) for d in dirs)

    print("thresholds in electrons:", E_THRESHOLDS)
    print(
        f"{'ISO':>5} {'g':>7} {'noise_e':>8} "
        + " ".join(f"{t:>8.0f}e-" for t in E_THRESHOLDS)
    )

    rows = []
    for iso, d in order:
        files = sorted(
            os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith(".arw")
        )[DROP_STABILISATION:]
        means = load_mean(files)
        g = gain(iso)
        counts = {t: 0 for t in E_THRESHOLDS}
        noise_e = []
        amps = []
        for n, _, _ in PLANES:
            e = excess(means[n])
            med = float(np.median(e))
            s_obs = float(np.median(np.abs(e - med)) * 1.4826)
            e_el = (e - med) / g  # excess in electrons
            noise_e.append(s_obs / g)
            for t in E_THRESHOLDS:
                counts[t] += int(np.count_nonzero(e_el > t))
            sel = e_el[e_el > 12.0]
            if sel.size:
                amps.append(sel.astype(np.float32))
            del e, e_el
        allamp = np.concatenate(amps) if amps else np.zeros(0, np.float32)
        row = {
            "iso": iso,
            "gain_dn_per_e": g,
            "noise_floor_e": float(np.mean(noise_e)),
            "counts": {str(t): counts[t] for t in E_THRESHOLDS},
            "amp_e_median": float(np.median(allamp)) if allamp.size else None,
            "amp_e_p99": float(np.percentile(allamp, 99)) if allamp.size else None,
            "amp_e_max": float(allamp.max()) if allamp.size else None,
        }
        rows.append(row)
        print(
            f"{iso:5d} {g:7.4f} {row['noise_floor_e']:8.3f} "
            + " ".join(f"{counts[t]:10d}" for t in E_THRESHOLDS)
        )
        del means

    print("\nspread across ISO at each threshold (max/min):")
    summary = {}
    for t in E_THRESHOLDS:
        v = np.array([r["counts"][str(t)] for r in rows], float)
        # ISO 50/100 share a gain and are the least sensitive; report both the
        # full spread and the spread over the 9 ISOs at or above 200.
        hi = v[2:]
        summary[str(t)] = {
            "min": int(v.min()),
            "max": int(v.max()),
            "ratio_all": float(v.max() / v.min()) if v.min() else None,
            "ratio_iso200plus": float(hi.max() / hi.min()) if hi.min() else None,
            "cv_iso200plus": float(hi.std(ddof=1) / hi.mean()),
        }
        print(
            f"  {t:5.0f} e-: all {v.min():.0f}-{v.max():.0f} "
            f"({summary[str(t)]['ratio_all']:.2f}x)   "
            f"ISO>=200 {hi.min():.0f}-{hi.max():.0f} "
            f"({summary[str(t)]['ratio_iso200plus']:.2f}x, "
            f"CV {summary[str(t)]['cv_iso200plus']*100:.1f}%)"
        )

    payload = {
        "_meta": {
            "script": "03-iso-stability-electrons.py",
            "why": "script 02's DN-domain threshold varies 7.1x in electrons "
            "across ISO, so its rising count measures sensitivity not "
            "population",
            "thresholds_e": list(E_THRESHOLDS),
            "expectation_preregistered": "count is ISO-independent at fixed "
            "electron threshold; 6 e- is a deliberate negative control "
            "below the ISO-50 6-sigma bar of 11.66 e-",
            "exposure": "all groups 1/100 s, so electron excess is comparable",
        },
        "per_iso": rows,
        "spread": summary,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()

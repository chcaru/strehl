"""M48c script 06 -- which domain is the defect amplitude constant in?

Scripts 01-03 left Q2 ("are the defects stable across ISO?") genuinely
unanswered, and the reason is worth stating because it is discipline 331 in a
third costume: BOTH of my thresholds moved with ISO.

  - Script 01/02 thresholded at K * sigma_obs, and sigma_obs rises with ISO
    (0.4448 -> 1.2602 DN). Counts rose 20x with ISO.
  - Script 03 thresholded at a fixed electron excess, which in DN is e * g and
    also rises with ISO. Counts FELL, by 350x across the ISO-400 boundary.

Counts rising under one moving bar and falling under another tell you almost
nothing about the population. Neither experiment can distinguish "more defects
at high ISO" from "the same defects, seen through a different instrument".

This script removes the threshold entirely. It takes the SAME fixed pixel set at
every ISO -- the recurrent hot defects already identified by script 02 -- and
simply reports how large their excess is, in both candidate domains:

  DN domain        : excess in DN. Flat here => the amplitude is fixed in DN,
                     i.e. it arises AFTER the analog gain (readout / ADC).
  electron domain  : excess / g. Flat here => the amplitude is fixed in
                     electrons, i.e. it arises BEFORE the gain (dark current).

These are mutually exclusive and the sensor must pick one. A dark-current defect
is a rate of thermally generated electrons: it cannot depend on the ISO dial,
which is set after the photodiode. A readout-domain offset cannot depend on
exposure time. So this single table separates the two mechanisms with no fit,
no threshold, and no model.

Secondary test, same table, no extra cost: split the defect set by SENSOR ROW
PARITY. Script 01's per-plane counts show odd rows (G2, B) carrying 2.1-4.7x
more hot flags than even rows (R, G1) at every one of the 11 ISOs. Thermally
generated charge has no mechanism to prefer odd rows. An interleaved readout
does. If the parity asymmetry lives in the DN-flat component and not the
electron-flat one, that is a second, independent line of evidence for the same
conclusion.

I am not predicting the outcome. My last two pre-registered predictions in this
milestone were both refuted and I would rather record the mechanism I am testing
than a guess about which way it goes.

Reads only D:\\macro-dark-frames (READ-ONLY) and this milestone's own maps.

NOTE ON THE MAPS, because it cost me a wrong defect set in scripts 04 and 05:
`hotmask-*.npy` is a uint16 ELEVEN-BIT ISO BITMASK (bit 0 = ISO 50 ... bit 10 =
ISO 2000, max 2047), NOT a boolean mask. Writing `hotmask & (hp > 0)` silently
bitwise-ANDs it with 1 and selects "detected at ISO 50", not "recurrent". The
recurrent set is `hotcount-*.npy >= RECURRENCE_MIN`. Script 07 re-runs the
merge control against the correct set.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import rawpy

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
DARKS = pathlib.Path(r"D:\macro-dark-frames")

# Mirrors crates/strehl-core/src/profile.rs. See M48 for the derivation of
# read_noise_e_high = 1.2392; gain_divisor is fact 585.
GAIN_DIVISOR = 436.8
BASE_ISO = 100
SETTLING_FRAMES = 2  # owner's instruction: first two of each set are settling
RECURRENCE_MIN = 6  # script 01's pre-registered criterion: flagged at >= 6 of 11 ISOs

QUAD = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}
# Sensor row parity of each plane's rows: R/G1 are even rows, G2/B odd.
PARITY = {"R": "even", "G1": "even", "G2": "odd", "B": "odd"}


def gain(iso: int) -> float:
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def highpass(a: np.ndarray) -> np.ndarray:
    up, dn = a[:-2, 1:-1], a[2:, 1:-1]
    lf, rt = a[1:-1, :-2], a[1:-1, 2:]
    return a[1:-1, 1:-1] - np.median(np.stack([up, dn, lf, rt]), axis=0)


def iso_dirs() -> list[tuple[int, pathlib.Path]]:
    out = []
    for d in sorted(DARKS.iterdir()):
        if not d.is_dir():
            continue
        arws = sorted(d.glob("*.ARW"))
        if not arws:
            continue
        with rawpy.imread(str(arws[0])) as r:
            _ = r.sizes
        import exifread

        with open(arws[0], "rb") as fh:
            tags = exifread.process_file(fh, stop_tag="ISOSpeedRatings")
        iso = int(str(tags["EXIF ISOSpeedRatings"]))
        out.append((iso, d))
    return sorted(out)


def plane_mean(arws: list[pathlib.Path]) -> tuple[dict[str, np.ndarray], float]:
    acc: dict[str, np.ndarray] = {}
    blk = 0.0
    for p in arws:
        with rawpy.imread(str(p)) as r:
            v = r.raw_image_visible.astype(np.float64)
            blk = float(np.mean(r.black_level_per_channel))
            v = v - blk
            for name, (ro, co) in QUAD.items():
                pl = v[ro::2, co::2]
                acc[name] = pl if name not in acc else acc[name] + pl
    return {k: v / len(arws) for k, v in acc.items()}, blk


def main() -> None:
    masks = {
        n: (np.load(DATA / f"hotcount-{n}.npy") >= RECURRENCE_MIN)[1:-1, 1:-1]
        for n in QUAD
    }
    npx = {n: int(masks[n].sum()) for n in QUAD}
    print("recurrent hot defects per plane:", npx, "total", sum(npx.values()))

    rows = []
    for iso, d in iso_dirs():
        arws = sorted(d.glob("*.ARW"))[SETTLING_FRAMES:]
        means, blk = plane_mean(arws)
        g = gain(iso)
        rec: dict[str, object] = {
            "iso": iso,
            "dir": d.name,
            "frames": len(arws),
            "gain": g,
            "black_level": blk,
            "planes": {},
        }
        for name in QUAD:
            hp = highpass(means[name])
            v = hp[masks[name]]
            med_dn = float(np.median(v))
            rec["planes"][name] = {
                "median_excess_dn": med_dn,
                "median_excess_e": med_dn / g,
                "p90_excess_dn": float(np.percentile(v, 90)),
            }
        ev = np.array(
            [rec["planes"][n]["median_excess_dn"] for n in QUAD if PARITY[n] == "even"]
        )
        od = np.array(
            [rec["planes"][n]["median_excess_dn"] for n in QUAD if PARITY[n] == "odd"]
        )
        rec["even_dn"] = float(ev.mean())
        rec["odd_dn"] = float(od.mean())
        rows.append(rec)
        print(f"  ISO {iso:>4} done (g={g:.4f})")

    print(f"\n{'ISO':>5} {'g':>7} | {'DN':>8} {'e-':>8} | {'even DN':>8} {'odd DN':>8}")
    print("-" * 60)
    for r in rows:
        dn = float(np.mean([r["planes"][n]["median_excess_dn"] for n in QUAD]))
        e = float(np.mean([r["planes"][n]["median_excess_e"] for n in QUAD]))
        print(
            f"{r['iso']:>5} {r['gain']:>7.4f} | {dn:>8.4f} {e:>8.4f} | "
            f"{r['even_dn']:>8.4f} {r['odd_dn']:>8.4f}"
        )

    dn_all = np.array(
        [np.mean([r["planes"][n]["median_excess_dn"] for n in QUAD]) for r in rows]
    )
    e_all = np.array(
        [np.mean([r["planes"][n]["median_excess_e"] for n in QUAD]) for r in rows]
    )
    cv_dn = float(dn_all.std(ddof=1) / dn_all.mean())
    cv_e = float(e_all.std(ddof=1) / e_all.mean())
    print(
        f"\nacross all 11 ISOs:  CV(DN) = {cv_dn * 100:.1f}%   "
        f"CV(e-) = {cv_e * 100:.1f}%   spread DN {dn_all.max() / dn_all.min():.2f}x "
        f"vs e- {e_all.max() / e_all.min():.2f}x"
    )
    verdict = (
        "amplitude is fixed in DN -> POST-gain (readout/ADC), not dark current"
        if cv_dn < cv_e
        else "amplitude is fixed in electrons -> PRE-gain (dark current)"
    )
    print(f"VERDICT: {verdict}")

    out = {
        "_meta": {
            "purpose": "threshold-free amplitude scaling of a FIXED defect set",
            "gain_divisor": GAIN_DIVISOR,
            "base_iso": BASE_ISO,
            "settling_frames_dropped": SETTLING_FRAMES,
            "n_defects_per_plane": npx,
        },
        "per_iso": rows,
        "cv_dn": cv_dn,
        "cv_e": cv_e,
        "verdict": verdict,
    }
    p = DATA / "amplitude-domain.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"wrote {p}")


if __name__ == "__main__":
    main()

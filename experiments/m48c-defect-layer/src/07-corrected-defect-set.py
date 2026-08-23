"""M48c script 07 -- scripts 04 and 05 re-run against the CORRECT defect set.

WHY THIS EXISTS. Scripts 04 and 05 selected their defect pixels with

    mask = np.load(f"hotmask-{name}.npy")
    m = mask[1:-1, 1:-1] & (hp_in > 0)

and `hotmask-*.npy` is a uint16 ELEVEN-BIT ISO BITMASK (bit 0 = ISO 50 ...
bit 10 = ISO 2000, max value 2047), not a boolean map. numpy promotes the bool
operand to 0/1, so `bitmask & 1` extracts BIT ZERO. Scripts 04 and 05 therefore
measured "pixels flagged at ISO 50 with positive highpass", not "recurrent
defects". No exception was raised and the counts (R=101, B=1546-5686) were
plausible, so nothing surfaced it; it was found only when script 06 tried to use
the same array as a boolean index and blew up on a 215 GiB allocation.

That is a silent-wrong-answer bug of exactly the class this project keeps
finding, and the ISO-50 subset is arguably the WORST possible accidental choice:
ISO 50 is a pull ISO that reads out at base gain, it is the least sensitive of
the 11 (6 sigma_obs = 11.66 e- against 1.65 e- at ISO 2000), and script 02 found
only 26.1% of defects are detected there.

WHAT THIS SCRIPT DOES. It reruns both measurements against the pre-registered
recurrent set (hotcount >= 6 of 11 ISOs) AND against the accidental ISO-50-only
set, in the same run, on the same frames, through the same code path -- so the
size of my error is reported as a number rather than described in prose.

The statistic that matters remains D_defect / D_matched_control, which is
independent of the fitted TIFF/DN scale because that scale multiplies both.

Reads only the merged TIFF, the read-only corpus, and this milestone's maps.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import rawpy
import tifffile

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
STACK = pathlib.Path(r"D:\personal\macro\coffee-bubbles")

QUAD = {"R": (0, 0, 0), "G1": (0, 1, 1), "G2": (1, 0, 1), "B": (1, 1, 2)}
RECURRENCE_MIN = 6
RNG = np.random.default_rng(48)


def highpass(a: np.ndarray) -> np.ndarray:
    up, dn = a[:-2, 1:-1], a[2:, 1:-1]
    lf, rt = a[1:-1, :-2], a[1:-1, 2:]
    return a[1:-1, 1:-1] - np.median(np.stack([up, dn, lf, rt]), axis=0)


def unaligned_means(paths: list[pathlib.Path]) -> dict[str, np.ndarray]:
    acc: dict[str, np.ndarray] = {}
    for p in paths:
        with rawpy.imread(str(p)) as r:
            v = r.raw_image_visible.astype(np.float64)
            v = v - float(np.mean(r.black_level_per_channel))
            for name, (ro, co, _) in QUAD.items():
                pl = v[ro::2, co::2]
                acc[name] = pl if name not in acc else acc[name] + pl
    return {k: v / len(paths) for k, v in acc.items()}


def matched_controls(
    hp: np.ndarray, rows: np.ndarray, cols: np.ndarray, n_per: int = 4, tol: float = 0.10
) -> tuple[np.ndarray, np.ndarray]:
    h, w = hp.shape
    bad = np.zeros(hp.shape, dtype=bool)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            bad[np.clip(rows + dy, 0, h - 1), np.clip(cols + dx, 0, w - 1)] = True
    flat = hp.ravel()
    order = np.argsort(flat)
    sv = flat[order]
    bad_sorted = bad.ravel()[order]
    cr, cc = [], []
    for t in hp[rows, cols]:
        lo = np.searchsorted(sv, t * 0.90)
        hi = np.searchsorted(sv, t * 1.10)
        if hi <= lo:
            continue
        cand = order[lo:hi][~bad_sorted[lo:hi]]
        if cand.size == 0:
            continue
        pick = RNG.choice(cand, size=min(n_per, cand.size), replace=False)
        cr.append(pick // w)
        cc.append(pick % w)
    if not cr:
        return np.array([], dtype=int), np.array([], dtype=int)
    return np.concatenate(cr), np.concatenate(cc)


def measure(
    hp_in: np.ndarray, hp_out: np.ndarray, ag: float, sel: np.ndarray, best: int
) -> dict[str, float]:
    h, w = hp_in.shape
    rows, cols = np.nonzero(sel & (hp_in > 0))
    keep = (cols >= 4) & (cols < w - 5)
    rows, cols = rows[keep], cols[keep]
    d_in = float(np.median(hp_in[rows, cols]))
    d_out = float(np.median(hp_out[rows, cols + best] / ag))
    crow, ccol = matched_controls(hp_in, rows, cols)
    c_in = float(np.median(hp_in[crow, ccol]))
    c_out = float(np.median(hp_out[crow, ccol + best] / ag))
    return {
        "n_defects": int(rows.size),
        "n_controls": int(crow.size),
        "D_defect": d_out / d_in,
        "D_matched_control": c_out / c_in,
        "D_defect_over_D_control": (d_out / d_in) / (c_out / c_in),
        "defect_in_dn": d_in,
        "defect_out_dn": d_out,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: 07-corrected-defect-set.py <merged.tiff>")
    img = tifffile.imread(sys.argv[1]).astype(np.float64)
    best = int(json.loads((DATA / "merge-dilution.json").read_text())["column_offset_measured"])
    paths = sorted(STACK.glob("*.ARW"))
    print(f"merged {img.shape}; {len(paths)} frames; offset {best:+d}")
    means = unaligned_means(paths)

    out: dict[str, object] = {
        "_meta": {
            "purpose": "scripts 04/05 rerun against the correct recurrent defect set",
            "bug": "hotmask-*.npy is a uint16 ISO bitmask; `& (hp>0)` selected bit 0 (ISO 50)",
            "recurrence_min": RECURRENCE_MIN,
            "merged_tiff": sys.argv[1],
        },
        "planes": {},
    }

    for name in ("R", "B"):
        chan = QUAD[name][2]
        hp_in = highpass(means[name])
        h, w = hp_in.shape
        hp_out = highpass(img[:, :, chan])
        ry = RNG.integers(1, h - 1, 200_000)
        rx = RNG.integers(4, w - 5, 200_000)
        ag = float(np.polyfit(means[name][ry, rx], img[ry, rx + best, chan], 1)[0])

        recurrent = (np.load(DATA / f"hotcount-{name}.npy") >= RECURRENCE_MIN)[1:-1, 1:-1]
        iso50 = (np.load(DATA / f"hotmask-{name}.npy") & 1).astype(bool)[1:-1, 1:-1]

        res = {
            "recurrent": measure(hp_in, hp_out, ag, recurrent, best),
            "iso50_only_as_run_in_04_05": measure(hp_in, hp_out, ag, iso50, best),
        }
        out["planes"][name] = res
        print(f"\nplane {name}   (TIFF/DN scale a = {ag:.4f})")
        for label, r in res.items():
            print(
                f"  {label:>26}: n={r['n_defects']:>6}  "
                f"D_defect={r['D_defect']:.4f}  D_ctrl={r['D_matched_control']:.4f}  "
                f"ratio={r['D_defect_over_D_control']:.4f}"
            )

    p = DATA / "corrected-defect-set.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()

"""M48c script 05 -- the control that script 04 was missing.

Script 04 measured D = (merged defect excess in DN) / (unaligned-mean defect
excess in DN) and got D(median) = 1.2153 (R) and 1.1221 (B).  D > 1 says the
shipped merge *concentrates* a static sensor defect rather than diluting it.

That result has a confound big enough to produce it on its own, and this script
exists to kill it or confirm it.

THE CONFOUND.  Script 04 converts merged TIFF units to DN with a single global
slope `a`, fitted by regressing merged value on unaligned-mean DN over 200k
RANDOM pixels.  Random pixels are overwhelmingly low-local-contrast.  But the
merge is a sharpness SELECTOR: per output pixel it keeps the frames with the
best focus response.  If that selection systematically lifts high-local-contrast
pixels relative to a plain mean -- which is precisely what a sharpness selector
is *for* -- then a slope fitted on flat pixels under-corrects at every sharp
pixel, and D > 1 falls out for defects and for genuine detail alike.  In that
case D > 1 would be a property of my estimator of `a`, not of the merge's
treatment of defects.

PRE-REGISTERED CRITERION.  For every defect pixel, draw control pixels that are
NOT defects but have a matched unaligned-mean highpass amplitude (same sign,
within +/-10%).  Compute D by the identical code path for both populations.

  - If D_defect ~= D_matched  ->  the merge has NO defect-specific behaviour.
    It amplifies a hot pixel exactly as much as it amplifies real subject
    detail of the same contrast.  Script 04's D > 1 is then a statement about
    contrast handling in general, and the defect-specific claim is REFUTED.
  - If D_defect >  D_matched  ->  defects are concentrated over and above the
    general contrast lift, and the defect-specific claim SURVIVES.

Either outcome is reportable.  I am recording the criterion here before running
because the first result inverted my expectation once already in this milestone
and I do not intend to choose the test after seeing the answer.

A matched control also makes the measurement scale-free in the way that matters:
`a` multiplies D_defect and D_matched identically, so their RATIO is independent
of `a` entirely.  That ratio, not D itself, is the defensible statistic.

Reads only:  the merged TIFF passed as argv[1], the read-only corpus frames, and
this milestone's own defect maps.  Writes only into experiments/m48c-defect-layer/data.
"""

from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
import rawpy
import tifffile

ROOT = pathlib.Path(__file__).resolve().parents[3]
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
STACK = pathlib.Path(r"D:\personal\macro\coffee-bubbles")

# RGGB quad -> (row parity, col parity) and merged-TIFF channel.
QUAD = {"R": (0, 0, 0), "G1": (0, 1, 1), "G2": (1, 0, 1), "B": (1, 1, 2)}
RNG = np.random.default_rng(48)


def highpass(a: np.ndarray) -> np.ndarray:
    """Excess of a pixel over the median of its 4 same-plane neighbours."""
    up, dn = a[:-2, 1:-1], a[2:, 1:-1]
    lf, rt = a[1:-1, :-2], a[1:-1, 2:]
    return a[1:-1, 1:-1] - np.median(np.stack([up, dn, lf, rt]), axis=0)


def unaligned_means(paths: list[pathlib.Path]) -> dict[str, np.ndarray]:
    """Per-plane mean over all frames, in DN, black level removed."""
    acc: dict[str, np.ndarray] = {}
    for p in paths:
        with rawpy.imread(str(p)) as r:
            v = r.raw_image_visible.astype(np.float64)
            blk = float(np.mean(r.black_level_per_channel))
            v = v - blk
            for name, (ro, co, _) in QUAD.items():
                pl = v[ro::2, co::2]
                acc[name] = pl if name not in acc else acc[name] + pl
    return {k: v / len(paths) for k, v in acc.items()}


def matched_controls(
    hp: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    n_per: int = 4,
    tol: float = 0.10,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """For each (row, col) defect, find non-defect pixels of matched highpass.

    Returns (ctrl_rows, ctrl_cols, defect_index) so each control can be paired
    back to the defect whose amplitude it matches.
    """
    h, w = hp.shape
    is_defect = np.zeros(hp.shape, dtype=bool)
    is_defect[rows, cols] = True
    # Exclude the defect's immediate neighbourhood too: a control must not be
    # contaminated by the defect it is matched against.
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            rr = np.clip(rows + dy, 0, h - 1)
            cc = np.clip(cols + dx, 0, w - 1)
            is_defect[rr, cc] = True

    flat = hp.ravel()
    order = np.argsort(flat)
    sorted_vals = flat[order]
    bad_sorted = is_defect.ravel()[order]

    cr, cc, di = [], [], []
    targets = hp[rows, cols]
    for i, t in enumerate(targets):
        lo = np.searchsorted(sorted_vals, t * (1.0 - tol) if t > 0 else t * (1.0 + tol))
        hi = np.searchsorted(sorted_vals, t * (1.0 + tol) if t > 0 else t * (1.0 - tol))
        if hi <= lo:
            continue
        cand = order[lo:hi][~bad_sorted[lo:hi]]
        if cand.size == 0:
            continue
        pick = RNG.choice(cand, size=min(n_per, cand.size), replace=False)
        cr.append(pick // w)
        cc.append(pick % w)
        di.append(np.full(pick.size, i))
    if not cr:
        return np.array([]), np.array([]), np.array([])
    return np.concatenate(cr), np.concatenate(cc), np.concatenate(di)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: 05-contrast-matched-control.py <merged.tiff>")
    img = tifffile.imread(sys.argv[1]).astype(np.float64)
    prev = json.loads((DATA / "merge-dilution.json").read_text())
    best = int(prev["column_offset_measured"])

    paths = sorted(STACK.glob("*.ARW"))
    print(f"merged TIFF {img.shape}; {len(paths)} frames; column offset {best:+d}")
    means = unaligned_means(paths)

    out: dict[str, object] = {
        "_meta": {
            "purpose": "contrast-matched control for script 04's D > 1",
            "merged_tiff": sys.argv[1],
            "n_frames": len(paths),
            "column_offset": best,
            "match_tolerance": 0.10,
        },
        "planes": {},
    }

    for name in ("R", "B"):
        chan = QUAD[name][2]
        mask = np.load(DATA / f"hotmask-{name}.npy")
        hp_in = highpass(means[name])
        h, w = hp_in.shape
        m = mask[1:-1, 1:-1] & (hp_in > 0)
        rows, cols = np.nonzero(m)
        keep = (cols >= 4) & (cols < w - 5)
        rows, cols = rows[keep], cols[keep]

        hp_out = highpass(img[:, :, chan])
        ag, _ = np.polyfit(
            means[name][
                (ry := RNG.integers(1, h - 1, 200_000)),
                (rx := RNG.integers(4, w - 5, 200_000)),
            ],
            img[ry, rx + best, chan],
            1,
        )

        d_in = hp_in[rows, cols]
        d_out = hp_out[rows, cols + best] / ag
        d_ratio = float(np.median(d_out) / np.median(d_in))

        crow, ccol, didx = matched_controls(hp_in, rows, cols)
        c_in = hp_in[crow, ccol]
        c_out = hp_out[crow, ccol + best] / ag
        c_ratio = float(np.median(c_out) / np.median(c_in))

        rel = d_ratio / c_ratio
        out["planes"][name] = {
            "n_defects": int(rows.size),
            "n_controls": int(crow.size),
            "defect_in_dn": float(np.median(d_in)),
            "defect_out_dn": float(np.median(d_out)),
            "D_defect": d_ratio,
            "control_in_dn": float(np.median(c_in)),
            "control_out_dn": float(np.median(c_out)),
            "D_matched_control": c_ratio,
            "D_defect_over_D_control": rel,
        }
        print(
            f"\nplane {name}: {rows.size} defects, {crow.size} matched controls\n"
            f"  defect  : in {np.median(d_in):8.3f} DN -> out {np.median(d_out):8.3f} DN"
            f"   D = {d_ratio:.4f}\n"
            f"  matched : in {np.median(c_in):8.3f} DN -> out {np.median(c_out):8.3f} DN"
            f"   D = {c_ratio:.4f}\n"
            f"  D_defect / D_control = {rel:.4f}   "
            f"({'defect-specific' if abs(rel - 1) > 0.10 else 'NOT defect-specific'})"
        )

    p = DATA / "contrast-matched-control.json"
    p.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()

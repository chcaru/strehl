"""Default pyramid ladder vs flat exponent 1, scored per subject.

THE QUESTION
------------
The shipping merge runs a per-octave exponent ramp. Read from the run's own
banner rather than from any document:

    bands        : 7 Laplacian levels + 1 base, coarsest 28 x 19
    exponent     : 2.00
    per-band exp : 2 3 4 5 8 8 8   (coarsest -> finest)

The candidate arm is `--pyramid-exponent 1.0 --pyramid-sharpen 1.0`, which the
binary's own help says "disables the ramp and restores a single global
exponent", and which its banner confirms as `exponent : 1.00` /
`sharpness ramps 1.0x per octave`. So the arms are ladder 2-3-4-5-8-8-8 against
flat 1-1-1-1-1-1-1, and nothing else: one binary (sha16 A058F737DFE695F7), one
input set, one alignment, one tone path, one output format.

WHAT IS MEASURED, AND WHY BOTH HALVES ARE MANDATORY
---------------------------------------------------
Every noise number is paired with a sharpness number ON THE SAME PIXELS, in
named bands. That is not decoration. A lower exponent blends more frames and
therefore averages more; averaging always reduces a noise statistic, and the
degenerate limit of this arm -- exponent 0 -- is the plain mean, which this
project has already measured winning on blotch while destroying 78% of the
sharpness. A blotch number quoted alone cannot tell those apart. Two lanes have
independently walked into that trap on this corpus.

So the verdict for each cell is formed by `recertlib.classify`, whose
discriminator is not "did noise fall" but `paid = d_peak / d_floor`: what share
of the noise win was bought out of structure. A true denoise pays near 0; a blur
pays near 1.

SITES ARE CHOSEN BY CONTENT, ON THE BASE ARM ONLY
-------------------------------------------------
Not by geometry. This corpus contains subjects shot on a black backdrop, where a
fixed grid of crop coordinates lands on constant black; `band_stats` then reports
a degenerate floor and every cell REFUSES. Choosing by local variance puts the
crops on the subject. Selection reads the BASE arm only, so the candidate cannot
influence where it is judged -- picking sites on the candidate would let a blur
choose the flattest places to be measured.

REFUSALS ARE COUNTED, NEVER MERGED INTO PASSES
----------------------------------------------
A cell that could not be measured is reported as REFUSED and is visible in a
partition that sums to the number of cells attempted. A count that does not move
reads the same whether nothing was wrong or nothing was examined.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import tifffile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import recertlib as R  # noqa: E402

DEF_DIR = Path(r"C:\dev\strehl-out\BUILD-RECERT\arms\DEF-2f858c62")
FLAT_DIR = Path(r"C:\dev\strehl-out\BUILD-RECERT\arms\FLAT1-2f858c62")
OUT = Path(r"C:\dev\strehl-out\BUILD-RECERT\logs")

CROP = R.CROP
N_SITES = 5
# Candidate site centres on a coarse grid; the top N by content score are kept.
GRID_STEP = 600
MARGIN = 300

# A site must have at least this fraction of non-constant samples to be offered
# to the measurement at all. Purely a screen against black backdrop; the real
# refusal still happens inside `band_stats`, which is the authority.
MIN_NONCONST = 0.90

# `display_crop` multiplies by a per-channel gain vector and adds a per-channel
# offset vector; scalars raise. Both arms share one binary and one tone path, so
# these are identity.
UNIT_GAIN = [1.0, 1.0, 1.0]
ZERO_OFF = [0.0, 0.0, 0.0]


def content_sites(arr, n=N_SITES):
    """Pick the n highest-variance non-overlapping crops. Deterministic."""
    h, w = arr.shape[:2]
    cand = []
    for y in range(MARGIN, h - CROP - MARGIN, GRID_STEP):
        for x in range(MARGIN, w - CROP - MARGIN, GRID_STEP):
            # Score on a cheap decimated view; full-res variance over the whole
            # image would cost more than the measurement it is choosing for.
            v = arr[y:y + CROP:8, x:x + CROP:8, :3].astype(np.float32)
            nonconst = float(np.mean(v != np.median(v)))
            if nonconst < MIN_NONCONST:
                continue
            cand.append((float(v.std()), y, x, nonconst))
    cand.sort(key=lambda t: -t[0])
    picked = []
    for score, y, x, nc in cand:
        if all(abs(y - py) >= CROP or abs(x - px) >= CROP for _, py, px, _ in picked):
            picked.append((score, y, x, nc))
        if len(picked) >= n:
            break
    return [(y, x) for _, y, x, _ in picked]


def registration_shift(a, b, y, x, radius=4):
    """Integer shift that best aligns b to a at one site, by SSD.

    The two arms come from one binary, one input set and one alignment solve, so
    the honest expectation is exactly (0, 0) and anything else means the arms are
    not on a common grid and no per-pixel comparison between them is admissible.
    This CHECKS that rather than assuming it -- a structural claim about a render
    is a claim about pixels.
    """
    pa = a[y:y + CROP, x:x + CROP, 1].astype(np.float32)
    best, bshift = None, (0, 0)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            pb = b[y + dy:y + dy + CROP, x + dx:x + dx + CROP, 1].astype(np.float32)
            if pb.shape != pa.shape:
                continue
            s = float(np.mean((pa - pb) ** 2))
            if best is None or s < best:
                best, bshift = s, (dy, dx)
    return bshift


def score_subject(name, verbose=False, paths=None):
    dp, fp = paths if paths else (DEF_DIR / f"{name}--DEF-2f858c62.tiff",
                                  FLAT_DIR / f"{name}--FLAT1-2f858c62.tiff")
    dp, fp = Path(dp), Path(fp)
    if not dp.exists() or not fp.exists():
        return {"subject": name, "state": "MISSING",
                "missing": [str(p) for p in (dp, fp) if not p.exists()]}
    a = tifffile.imread(dp)
    b = tifffile.imread(fp)
    if a.shape != b.shape:
        return {"subject": name, "state": "SHAPE-MISMATCH",
                "shapes": [list(a.shape), list(b.shape)]}

    sites = content_sites(a)
    if not sites:
        return {"subject": name, "state": "NO-SITES"}

    shift = registration_shift(a, b, *sites[0])
    if shift != (0, 0):
        return {"subject": name, "state": "UNREGISTERED", "shift": list(shift)}

    cells = []
    for (y, x) in sites:
        # Unit gain, zero offset, unit exposure: the two arms come from one
        # binary and one tone path, so there is nothing to photometrically match
        # and inventing a per-arm gain would let a brightness change masquerade
        # as a noise change. `exposure` is MULTIPLICATIVE in `display_crop`;
        # passing 0.0 zeroes every crop and refuses every cell, which cost this
        # lane a full measurement round earlier tonight.
        da = R.display_crop(a, y, x, (0, 0), UNIT_GAIN, ZERO_OFF, 1.0, already_srgb=True)
        db = R.display_crop(b, y, x, (0, 0), UNIT_GAIN, ZERO_OFF, 1.0, already_srgb=True)
        ma, mb = R.measure_crop(da), R.measure_crop(db)
        for band in R.BANDS:
            c = R.classify(ma[band], mb[band])
            # A cell has TWO independent claims and they refuse independently.
            # `classify` returns a partial refusal when a band holds no structure
            # above its own noise floor: no sharpness claim may be formed, but
            # `d_floor` is still returned and is still valid, because measuring
            # how loud a band is does not require it to contain detail. A first
            # version of this scorer discarded the floor whenever the sharpness
            # half refused, and every commissioning arm read REFUSED -- the
            # instrument was throwing away the measurement it exists to make.
            floor_ok = not (ma[band]["degenerate"] or mb[band]["degenerate"])
            struct_ok = c["d_peak"] is not None
            cells.append({
                "site": [y, x], "band": band,
                "base_floor": ma[band]["floor"], "cand_floor": mb[band]["floor"],
                "base_struct": ma[band]["structure"], "cand_struct": mb[band]["structure"],
                "d_floor": c["d_floor"], "d_peak": c["d_peak"], "paid": c["paid"],
                "floor_ok": bool(floor_ok), "struct_ok": bool(struct_ok),
                "refused": bool(c.get("refused")), "verdict": c["verdict"],
            })
    return {"subject": name, "state": "SCORED", "sites": sites, "cells": cells}


def ratios(rows, band, key):
    """Median ratio cand/base over usable cells of one band, or None.

    Usability is per-claim, not per-cell: `floor` needs only a non-degenerate
    noise floor, while `struct` additionally needs structure detectable above
    that floor in BOTH arms. Conflating them discards valid blotch measurements
    on every flat crop in the corpus.

    NaN and non-finite values are dropped explicitly rather than compared away:
    `NaN > x` is False, so a non-finite value reaching a threshold test reads as
    a pass. One reached `cert.json` on this project tonight.
    """
    gate = "floor_ok" if key == "floor" else "struct_ok"
    vals = []
    for c in rows:
        if c["band"] != band or not c.get(gate):
            continue
        base, cand = c[f"base_{key}"], c[f"cand_{key}"]
        if base is None or cand is None or base <= 1e-12:
            continue
        r = cand / base
        if np.isfinite(r):
            vals.append(r)
    return (float(np.median(vals)), len(vals)) if vals else (None, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--pair", nargs=3, metavar=("NAME", "DEFAULT_TIFF", "FLAT_TIFF"),
                    help="score one explicit pair instead of the two arm directories")
    ap.add_argument("--out", default=str(OUT / "flatexp.json"))
    args = ap.parse_args()

    if args.pair:
        name, dpath, fpath = args.pair
        jobs = [(name, (Path(dpath), Path(fpath)))]
        print(f"explicit pair: {dpath}\n               {fpath}\n")
    else:
        subs = sorted({p.name.split("--")[0] for p in DEF_DIR.glob("*.tiff")})
        if args.only:
            subs = [s for s in subs if s in args.only]
        if not subs:
            raise SystemExit(f"no subjects found under {DEF_DIR}")
        jobs = [(s, None) for s in subs]
        print(f"default arm : {DEF_DIR}")
        print(f"flat-1 arm  : {FLAT_DIR}")
        print(f"subjects    : {len(subs)}\n")

    hdr = (f"{'subject':<28} {'blotch':>8} {'sharp':>8} {'grain':>8} "
           f"{'nB':>3} {'nS':>3} {'noS':>4}  verdict")
    print(hdr)
    print("-" * len(hdr))

    out, tally = [], {}
    for s, paths in jobs:
        r = score_subject(s, paths=paths)
        if r["state"] != "SCORED":
            print(f"{s:<28} {r['state']}")
            tally[r["state"]] = tally.get(r["state"], 0) + 1
            out.append(r)
            continue
        cells = r["cells"]
        blotch, nb = ratios(cells, "mottle", "floor")
        sharp, ns = ratios(cells, "struct", "struct")
        grain, ng = ratios(cells, "grain", "floor")
        # Cells where a sharpness claim could NOT be formed are counted and
        # printed separately. A number that does not move must not read the same
        # whether nothing was wrong or nothing was examined.
        n_struct_cells = sum(1 for c in cells if c["band"] == "struct")
        no_struct = n_struct_cells - ns

        # Two-sided on BOTH axes, and explicitly finite-guarded.
        #
        # An earlier version keyed the verdict on `blotch` alone and reported
        # NEUTRAL whenever blotch sat within +/-2%. Run against the real
        # coffee-bubbles pair it returned "NEUTRAL" on blotch 1.0065 while
        # sharpness had fallen to 0.8587 -- it hid a 14.1% loss of detail behind
        # a noise number that had not moved. That is the exact failure ORCH named:
        # a candidate that trades resolution must be VISIBLE as such, not averaged
        # away. Sharpness is now a first-class axis and can convict on its own.
        def fin(v):
            return v is not None and np.isfinite(v)

        if not (fin(blotch) and fin(sharp)):
            v = "REFUSED -- no admissible blotch/sharpness pair"
        else:
            quieter, noisier = blotch < 0.98, blotch > 1.02
            softer, sharper = sharp < 0.98, sharp > 1.02
            if quieter and not softer:
                v = "FLAT WINS -- quieter, sharpness held"
            elif quieter and softer:
                v = f"TRADE -- quieter, {(1 - sharp) * 100:.1f}% softer"
            elif softer:
                # Softer WITHOUT a blotch win is not a trade, it is a loss:
                # detail was spent and nothing was bought with it.
                v = f"FLAT LOSES -- {(1 - sharp) * 100:.1f}% softer, blotch not improved"
            elif noisier:
                v = "FLAT LOSES -- noisier"
            elif sharper:
                v = "FLAT WINS -- sharper, blotch held"
            else:
                v = "NEUTRAL -- both axes within tolerance"
        tally[v.split(" --")[0]] = tally.get(v.split(" --")[0], 0) + 1
        r["blotch"], r["sharp"], r["grain"], r["verdict"] = blotch, sharp, grain, v
        r["n_blotch"], r["n_sharp"], r["n_no_sharp"] = nb, ns, no_struct
        out.append(r)

        def f(v):
            return f"{v:>8.4f}" if fin(v) else f"{'--':>8}"
        print(f"{s:<28} {f(blotch)} {f(sharp)} {f(grain)} "
              f"{nb:>3} {ns:>3} {no_struct:>4}  {v}")

    print()
    total = sum(tally.values())
    print(f"partition ({total} subjects): " +
          ", ".join(f"{k}={v}" for k, v in sorted(tally.items())))
    assert total == len(jobs), f"partition {total} != {len(jobs)} subjects"

    # Corpus roll-up, medians of the per-subject medians.
    for label, key in (("blotch (mottle 21-61px floor)", "blotch"),
                       ("sharpness (struct 5-13px)", "sharp"),
                       ("grain (<=3px floor)", "grain")):
        vals = [r[key] for r in out if r.get(key) is not None and np.isfinite(r[key])]
        if vals:
            print(f"  corpus median {label:<32} flat/default = {np.median(vals):.4f}  "
                  f"(n={len(vals)})")

    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

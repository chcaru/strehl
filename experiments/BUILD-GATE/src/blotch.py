"""Blotch and sharpness across the admission sweep, on artifacts already on disk.

ORCH's ask: for every `--pyramid-gate k`, blotch at 20-60px AND sharpness on the
SAME pixels, band stated. A row with only the blotch column is inadmissible,
because a focus stacker can win every noise number by blurring and a shipping
competitor already has.

THE STATISTIC IS ORCH'S, IMPORTED NOT REWRITTEN. `orch_eye_check.sigma_mid` is
`std(boxblur(p,10) - boxblur(p,30))`: a difference of box means of width 21 and
61 px, i.e. exactly the 20-60px band the convictions live in. `boxblur` and
`srgb` are imported from that module so this is the same instrument that formed
the verdict, not a third implementation of it.

WHY MEASURING MOTTLE ON TEXTURED SITES IS NOT THE TRAP IT LOOKS LIKE. A mid-band
statistic charges for subject structure -- ORCH's own was refuted for lighting up
on a leaf's vein network. The defence is the matched arm, and this design has the
strongest possible one: every arm is the SAME SUBJECT, SAME FRAMES, SAME
REGISTRATION, rendered by ONE PINNED BINARY, differing only in the value of k.
Subject structure is therefore numerically identical across arms and cancels
EXACTLY in an arm-to-arm ratio. The absolute sigma_mid is not interpretable as
blotch; the ratio between two arms is. Only ratios are reported.

Blotch is additionally reported on a FLAT population -- the tiles in the lowest
quartile of fine-band energy -- because that is where mottle is diagnosed and
where subject structure contributes least even before the ratio cancels it.

DISPLAY STATE. The sweep masters were rendered `--srgb`, so they are already
display-referred; `srgb()` is NOT re-applied, which would double-encode. Values
are scaled 16-bit -> 8-bit codes so the numbers are comparable to
`orch_eye_check`'s. Every arm gets identical treatment, which is what the ratio
requires.
"""
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "ORCH-drift-check"))

from orch_eye_check import boxblur                                # noqa: E402
from orch_sharp1to1 import CROP, PATCH, luma                      # noqa: E402
from ceiling import NTILE, pick_sites                             # noqa: E402
import bandceiling as bc                                          # noqa: E402

SWEEP = r"C:\dev\strehl-out\BUILD-GATE\sweep"
ARMS = ["WHITE200", "G100", "G140", "G170", "G200", "G300", "G400"]
KS = {"WHITE200": None, "G100": 1.0, "G140": 1.4, "G170": 1.7,
      "G200": 2.0, "G300": 3.0, "G400": 4.0}
NFRAMES = {"bee-1-cpl": 299, "flower-bud-alone-cpl": 205, "119MSDCF": 33,
           "109MSDCF": 22, "coffee-bubbles": 19}


def sigma_mid(p):
    """ORCH's mottle statistic, 20-60px, on 8-bit display codes."""
    return float(np.std(boxblur(p, 10) - boxblur(p, 30)))


def sigma_hp(p):
    """ORCH's grain statistic, high-frequency residual."""
    return float(np.std(p - boxblur(p, 1)))


def codes(path, y, x):
    """The CROP at (y,x) as 8-bit display codes, per channel."""
    a = tifffile.imread(path)[..., :3].astype(np.float64)
    return a[y:y + CROP, x:x + CROP, :] / 65535.0 * 255.0


def tile_flatness(cy):
    """Per-tile fine-band energy, used only to CHOOSE the flat population."""
    return bc.tile_bands(cy)[..., 1]


def measure(path, sites, flat_masks=None):
    """Blotch (20-60px) and grain, on textured sites and on the flat population."""
    mid, hp, midflat = [], [], []
    for si, (y, x) in enumerate(sites):
        c = codes(path, y, x)
        mid.append(np.mean([sigma_mid(c[..., ch]) for ch in range(3)]))
        hp.append(np.mean([sigma_hp(c[..., ch]) for ch in range(3)]))
        if flat_masks is not None:
            m = flat_masks[si]
            vals = []
            for py in range(NTILE):
                for px in range(NTILE):
                    if not m[py, px]:
                        continue
                    t = c[py * PATCH:(py + 1) * PATCH, px * PATCH:(px + 1) * PATCH, :]
                    vals.append(np.mean([sigma_mid(t[..., ch]) for ch in range(3)]))
            if vals:
                midflat.append(float(np.mean(vals)))
    return (float(np.mean(mid)), float(np.mean(hp)),
            float(np.mean(midflat)) if midflat else float("nan"))


def flat_population(ref_path, sites):
    """Lowest-quartile fine-band tiles, chosen ONCE on the reference arm.

    Chosen once and reused for every arm, so all arms are scored on identical
    pixels. Re-choosing per arm would let each arm pick its own flattest tiles
    and would compare different populations.
    """
    out = []
    for (y, x) in sites:
        c = codes(ref_path, y, x)
        e = tile_flatness(luma(c * 257.0))
        out.append(e <= np.quantile(e, 0.25))
    return out


def pick_flat_sites(ref_path, n=3, step=280, margin=64):
    """FLAT 560px sites, which is where mottle is diagnosed.

    `orch_sharp1to1.pick_sites` picks the most TEXTURED sites, which is right for
    a sharpness ceiling and wrong here: commissioning measured sigma_mid = 25.34
    codes on a textured site, so a planted blotch of 2.0 codes is a 0.3% change
    and is unresolvable. On a textured crop the 20-60px band is almost entirely
    subject structure. Mottle has to be read where the subject is quiet.

    Sites are rejected if they clip, if they are near-black (a ratio of two
    near-zero sigmas is not a ratio of mottle), or if they overlap an already
    accepted site. The rejected count is reported and never folded into the
    accepted one.
    """
    a = tifffile.imread(ref_path)[..., :3].astype(np.float64)
    y8 = luma(a)
    h, w = y8.shape
    cand, rej = [], {"clip": 0, "dark": 0, "edge": 0}
    for y in range(margin, h - CROP - margin, step):
        for x in range(margin, w - CROP - margin, step):
            c = a[y:y + CROP, x:x + CROP, :]
            cy = y8[y:y + CROP, x:x + CROP]
            if (c >= 65000).mean() > 0.001:
                rej["clip"] += 1
                continue
            if np.median(cy) < 0.02 * 65535:
                rej["dark"] += 1
                continue
            cand.append((float(np.mean(bc.tile_bands(cy)[..., 1])), y, x))
    cand.sort()
    out = []
    for _, y, x in cand:
        if any(abs(y - yy) < CROP and abs(x - xx) < CROP for yy, xx in out):
            rej["edge"] += 1
            continue
        out.append((y, x))
        if len(out) == n:
            break
    return out, rej, len(cand)

"""Step 1: the band census, run BEFORE any arm is scored (AGENTS rule 9, and
the reopening bar in `docs/research/ORCH-kernel-decision.md` §9).

M85 retracted the project's standing sharpness band (0.30-0.48 cyc/px) after
measuring it at **12.8 % subject detail / 87.2 % noise**, with a dark frame
reading the same gain. Every kernel and merge comparison scored in that band is
therefore uninterpretable. Before BUILD-SHARP scores anything it establishes,
per frequency bin, how much of the power is subject and how much is noise --
on the owner's own subject, through the shipped binary.

The discriminator is a **defocused control**: tiles of the same render, in the
same frame, at the same radius band, containing no resolved subject detail
because nothing in the stack is in focus there. Whatever power they carry at
frequency f is noise plus whatever the pipeline manufactures. A band in which
detail tiles and defocus tiles read the same power carries no subject.

The tiles are chosen ONCE, on an arm that is not compared to anything
(`g0-nn`), so no arm can be flattered by the selection.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import bslib as B

TILE = 256


def gradient_energy(g: np.ndarray) -> np.ndarray:
    gy = np.abs(np.diff(g, axis=0))[:, :-1]
    gx = np.abs(np.diff(g, axis=1))[:-1, :]
    return gy + gx


def pick_tiles(g: np.ndarray, n: int, largest: bool, margin: int, exclude=None):
    """Non-overlapping TILE-px tiles, ranked by mean gradient energy."""
    h, w = g.shape
    e = gradient_energy(g)
    ny = (h - 2 * margin) // TILE
    nx = (w - 2 * margin) // TILE
    scores = []
    for iy in range(ny):
        for ix in range(nx):
            y = margin + iy * TILE
            x = margin + ix * TILE
            blk = e[y : y + TILE, x : x + TILE]
            scores.append((float(blk.mean()), y, x))
    scores.sort(reverse=largest)
    taken = []
    used = set()
    for s, y, x in scores:
        key = (y // TILE, x // TILE)
        if key in used:
            continue
        if exclude and any(abs(y - ey) < TILE and abs(x - ex) < TILE for ey, ex in exclude):
            continue
        used.add(key)
        taken.append((y, x, s))
        if len(taken) >= n:
            break
    return taken


def spectra(g: np.ndarray, tiles, nbins=64):
    acc = None
    cnt = None
    for y, x, _ in tiles:
        f, p, c = B.radial_power(g[y : y + TILE, x : x + TILE], nbins)
        acc = p if acc is None else acc + p
        cnt = c
    return f, acc / len(tiles), cnt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--select-on", default="g0-nn")
    ap.add_argument("--score-on", default="base-g4-cr")
    ap.add_argument("--ntiles", type=int, default=40)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    sel = B.read_green(B.arm(a.subject, a.select_on))
    print(f"tile selection on : {a.select_on}  {sel.shape}")

    margin = 600  # inside every frame's coverage on the deep stacks
    detail = pick_tiles(sel, a.ntiles, True, margin)
    flat = pick_tiles(sel, a.ntiles, False, margin, exclude=[(y, x) for y, x, _ in detail])
    print(f"detail tiles      : {len(detail)}  grad {detail[0][2]:.5f} .. {detail[-1][2]:.5f}")
    print(f"defocus tiles     : {len(flat)}  grad {flat[0][2]:.5f} .. {flat[-1][2]:.5f}")

    g = B.read_green(B.arm(a.subject, a.score_on))
    f, pd, c = spectra(g, detail)
    _, pf, _ = spectra(g, flat)

    rows = []
    print()
    print(f"band census on {a.score_on}: power in DETAIL tiles vs DEFOCUS tiles")
    print(f"{'f cyc/px':>9} {'detail':>12} {'defocus':>12} {'ratio':>8} {'subject%':>9}")
    for i in range(len(f)):
        if c[i] == 0:
            continue
        r = pd[i] / pf[i] if pf[i] > 0 else np.inf
        subj = 100.0 * max(0.0, 1.0 - 1.0 / r) if np.isfinite(r) and r > 0 else 0.0
        rows.append(dict(f=float(f[i]), detail=float(pd[i]), defocus=float(pf[i]),
                         ratio=float(r), subject_pct=float(subj)))
        if i % 2 == 0:
            print(f"{f[i]:9.4f} {pd[i]:12.4e} {pf[i]:12.4e} {r:8.2f} {subj:8.1f}%")

    out = Path(a.out) if a.out else (Path(__file__).resolve().parents[1] / "out" /
                                     f"bands-{a.subject}-{a.score_on}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dict(
        subject=a.subject, select_on=a.select_on, score_on=a.score_on,
        tile=TILE, margin=margin,
        detail_tiles=[[y, x] for y, x, _ in detail],
        flat_tiles=[[y, x] for y, x, _ in flat],
        bins=rows), indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

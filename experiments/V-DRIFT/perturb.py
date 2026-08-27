#!/usr/bin/env python3
"""Plant a KNOWN misregistration into a warp sidecar, in two shapes.

WHY TWO SHAPES, AND WHY THIS IS THE DECISIVE EXPERIMENT
-------------------------------------------------------
The hypothesis under test is that registration error ACCUMULATES along a deep
stack and that the accumulation is what destroys detail.  That hypothesis
conflates two quantities which this script deliberately separates:

  ABSOLUTE placement error   how far frame i sits from where it belongs,
                             measured against the reference.  This is what
                             "drift" and "total corner drift" report, and it
                             is what accumulates.

  LOCAL RELATIVE error       how far frame i sits from frame i+1, i+2, ...
                             This is what a merge is actually exposed to,
                             because at any output pixel a merge combines only
                             the frames where that pixel is in focus, and those
                             are a contiguous run of neighbouring indices.

A slowly accumulating error moves neighbouring frames TOGETHER.  It is a smooth
low-frequency warp of the output: it displaces, it does not blur.  Only local
relative error can blur.  That is an argument, so this script measures it.

  walk   a random walk in translation, centred on the reference frame.  Large
         ABSOLUTE excursion, tiny LOCAL relative error.  This is what pure
         accumulation looks like.
  iid    independent per-frame translation.  The SAME absolute envelope, so the
         same field-of-view crop, but large LOCAL relative error.

The two arms are scaled to the same max |displacement| so the merge's coverage
crop -- and therefore the band-frequency scale factor `k` that BUILD-TRIAGE
warns about -- is matched between them.  If `walk` costs little detail and
`iid` costs a lot at equal envelope, accumulation is not the mechanism.

WHY TRANSLATION ONLY.  A pure translation has da = 0, so
`corner_err = max_c |da.c + db| = |db|` EXACTLY.  The dose is then a plain
number of plane pixels with no dependence on where the corner is.  Perturbing
`a` would be more physical but the dose would no longer be one number.

BOTH-WAYS COMMISSIONING.  A dose ladder is monotone in both directions by
construction: going up the ladder must lose detail and coming down it must
regain detail.  A statistic that only ever falls under damage passes a
degradation-only test trivially, so the ladder is run as a ladder and the
detail metric must track it in BOTH directions.  See dose.py.
"""
from __future__ import annotations

import argparse
import math
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wm import WarpMap  # noqa: E402


def _f64_hex(x: float) -> str:
    """f64 -> the 16-char big-endian bit pattern the sidecar stores."""
    return struct.pack(">d", x).hex()


def perturb(src: Path, dst: Path, shape: str, amp: float, seed: int) -> dict:
    """Rewrite `src` to `dst` with a planted translation of shape `shape`.

    `amp` is the maximum |displacement| in plane pixels, identical between
    shapes so the coverage crop is matched.  Returns the realised statistics --
    never the requested ones, because what was asked for and what landed are
    different claims.
    """
    wm = WarpMap(src)
    idx = wm.placed()
    n = len(idx)
    rng = np.random.default_rng(seed)

    if shape == "none":
        d = np.zeros((n, 2))
    elif shape == "iid":
        d = rng.normal(size=(n, 2))
    elif shape == "walk":
        d = np.cumsum(rng.normal(size=(n, 2)), axis=0)
    else:
        raise SystemExit(f"unknown shape {shape!r}")

    # Reference the plant to the sidecar's own reference frame, so the
    # reference stays exactly where the solve put it and the plant is a
    # perturbation OF that solve rather than a different solve.
    if wm.reference in wm.a and shape != "none":
        d = d - d[idx.index(wm.reference)]

    mag = np.hypot(d[:, 0], d[:, 1])
    if shape != "none" and mag.max() > 0:
        d = d * (amp / mag.max())
    mag = np.hypot(d[:, 0], d[:, 1])

    # Realised local relative error, at the separations a merge combines over.
    local = {}
    for sep in (1, 2, 4, 8):
        if n > sep:
            step = d[sep:] - d[:-sep]
            local[sep] = float(np.median(np.hypot(step[:, 0], step[:, 1])))

    out_lines = []
    for line in src.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        parts = s.split()
        if not s or s.startswith("#") or len(parts) < 6 or parts[1] != "placed":
            if s.startswith("note "):
                line = line + f" | V-DRIFT plant shape={shape} amp={amp:g}px seed={seed}"
            out_lines.append(line)
            continue
        i = int(parts[0])
        dx, dy = d[idx.index(i)]
        g = wm.b[i]
        b_re, b_im = g.real + float(dx), g.imag + float(dy)
        tail = line.split("#", 1)
        cmt = ("#" + tail[1]) if len(tail) > 1 else ""
        out_lines.append(
            f"{i} placed {parts[2]} {parts[3]} {_f64_hex(b_re)} {_f64_hex(b_im)} {cmt}".rstrip()
        )
    dst.write_text("\n".join(out_lines) + "\n", encoding="utf-8")

    return {
        "shape": shape,
        "amp_px": amp,
        "seed": seed,
        "frames": n,
        "abs_max_px": float(mag.max()),
        "abs_median_px": float(np.median(mag)),
        "local_rel_px": local,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path)
    ap.add_argument("dst", type=Path)
    ap.add_argument("--shape", required=True, choices=["none", "iid", "walk"])
    ap.add_argument("--amp", type=float, required=True)
    ap.add_argument("--seed", type=int, default=20260824)
    a = ap.parse_args()
    st = perturb(a.src, a.dst, a.shape, a.amp, a.seed)
    print(
        f"{st['shape']:5s} amp={st['amp_px']:7.3f}px  abs: max {st['abs_max_px']:7.3f} "
        f"median {st['abs_median_px']:7.3f}  local rel: "
        + "  ".join(f"sep{k} {v:6.3f}" for k, v in st["local_rel_px"].items())
    )


if __name__ == "__main__":
    main()

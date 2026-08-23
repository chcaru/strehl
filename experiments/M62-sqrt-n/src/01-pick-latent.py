"""Arm A step 1 -- choose the latent frame and the crop.

Reads ONE frame from `109MSDCF` (ISO 160, 17 May 2026 -- before the circular
polariser was fitted on 25 May, fact 845) and searches for a crop that is
mid-tone, unclipped and textured. Writes the crop to `data/latent.npy` plus a
provenance record.

Corpus is READ-ONLY. Nothing here writes to `D:\\`.

rule 32: `raw_image_visible` is a view into LibRaw's buffer. It is copied with
`.astype` on the same line, inside the `with`.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import rawpy

STACK = pathlib.Path(r"D:\personal\macro\109MSDCF")
EXPECTED_FRAMES = 22  # AGENTS.md corpus table. Discipline 388: assert, never glob and hope.
OUT = pathlib.Path(__file__).resolve().parents[1] / "data"
EVID = pathlib.Path(__file__).resolve().parents[1] / "out"

CROP = 2048  # sensor px, so 1024 x 1024 plane px
BLACK = 512.0


def hp_sd(a, side=9):
    """Box high-pass residual sd on the valid interior -- the shipped kernel."""
    from scipy.ndimage import uniform_filter

    r = a - uniform_filter(a, side, mode="nearest")
    k = side // 2
    return float(r[k:-k, k:-k].std())


def main():
    paths = sorted(STACK.glob("*.ARW"))
    assert len(paths) == EXPECTED_FRAMES, f"{STACK}: {len(paths)} frames, expected {EXPECTED_FRAMES}"

    src = paths[len(paths) // 2]
    with rawpy.imread(str(src)) as raw:
        cfa = raw.raw_image_visible.astype(np.float64)  # copy inside the `with`
        colors = raw.raw_colors_visible.astype(np.uint8).copy()
        pattern = raw.raw_pattern.tolist()
        black_libraw = float(np.mean(raw.black_level_per_channel))
        white_libraw = int(raw.white_level)
    h, w = cfa.shape

    # Find the phase offset at which the 2x2 reads RGGB. LibRaw colour codes are
    # 0=R 1=G 2=B 3=G2.
    phase = None
    for dy in (0, 1):
        for dx in (0, 1):
            q = colors[dy : dy + 2, dx : dx + 2]
            if q[0, 0] == 0 and q[0, 1] in (1, 3) and q[1, 0] in (1, 3) and q[1, 1] == 2:
                phase = (dy, dx)
    assert phase is not None, f"no RGGB phase found; pattern={pattern}"

    # Candidate crops on a coarse grid, phase-aligned.
    best = None
    step = 512
    for y0 in range(phase[0], h - CROP, step):
        for x0 in range(phase[1], w - CROP, step):
            if (y0 - phase[0]) % 2 or (x0 - phase[1]) % 2:
                continue
            sub = cfa[y0 : y0 + CROP, x0 : x0 + CROP]
            g1 = sub[0::2, 1::2]
            g2 = sub[1::2, 0::2]
            green = 0.5 * (g1 + g2) - BLACK
            p999 = float(np.percentile(sub, 99.9))
            mean = float(green.mean())
            if p999 > 12000 or not (1200.0 < mean < 7000.0):
                continue
            tex = hp_sd(green[::4, ::4])
            cand = dict(y0=int(y0), x0=int(x0), mean_green_dn=mean, p999=p999, texture=tex)
            if best is None or tex > best["texture"]:
                best = cand
    assert best is not None, "no crop met the mid-tone / unclipped criteria"

    y0, x0 = best["y0"], best["x0"]
    latent = cfa[y0 : y0 + CROP, x0 : x0 + CROP]

    OUT.mkdir(parents=True, exist_ok=True)
    EVID.mkdir(parents=True, exist_ok=True)
    np.save(OUT / "latent.npy", latent.astype(np.float64))

    planes = {
        "R": latent[0::2, 0::2],
        "G1": latent[0::2, 1::2],
        "G2": latent[1::2, 0::2],
        "B": latent[1::2, 1::2],
    }
    rec = {
        "source_file": str(src),
        "stack": "109MSDCF",
        "stack_frames": len(paths),
        "frame_index_in_stack": len(paths) // 2,
        "sensor_shape_visible": [h, w],
        "libraw_black_mean": black_libraw,
        "libraw_white": white_libraw,
        "rggb_phase_dy_dx": list(phase),
        "raw_pattern": pattern,
        "crop": {"y0": y0, "x0": x0, "size": CROP},
        "crop_stats": {
            "min": float(latent.min()),
            "max": float(latent.max()),
            "p999": best["p999"],
            "mean_green_signal_dn": best["mean_green_dn"],
            "texture_hp_sd_dn": best["texture"],
        },
        "plane_means_dn": {k: float(v.mean()) for k, v in planes.items()},
        "plane_signal_dn": {k: float(v.mean() - BLACK) for k, v in planes.items()},
        "saturated_px_at_15360": int((latent >= 15360).sum()),
    }
    (EVID / "01-latent-provenance.json").write_text(json.dumps(rec, indent=2))
    print(json.dumps(rec, indent=2))


if __name__ == "__main__":
    main()

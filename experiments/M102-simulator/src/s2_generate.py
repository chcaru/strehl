"""M102 S2 -- generate a synthetic focus stack as DNG files.

Requirement 5 says the ISO must be read through my own `sensor_for()` rather
than hard-coded. That is done literally: the generator names a REAL reference
stack, asks the M92b guard for that stack's EXIF triple, uses the returned
gain and read noise for the noise model, and writes the returned ISO into the
DNG. The number is never typed into this file. `s3_roundtrip.py` then reads
the ISO back out of the written file with the shipped decoder and asserts it
matches -- which closes the exact loop M92's defect broke, where a module
constant `ISO = 500` was applied to an ISO-160 stack.

Usage:
  python src/s2_generate.py <outdir> [--plant index1|warp] [--seed N] [--tag]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))),
    "M92-null-averaging", "src"))

import m102lib as M          # noqa: E402
import m102scene as S        # noqa: E402
import s13_sensor_guard as G  # noqa: E402

REFERENCE_STACK = "bee-3-cpl"


def generate(outdir, spec, plant=None, extra_tag=False, ref=REFERENCE_STACK,
             breathing=True, warp_pct=None):
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.lower().endswith((".arw", ".npz", ".json")):
            os.remove(os.path.join(outdir, f))

    iso, g, rn_e = G.sensor_for(ref)
    spec.iso = int(iso)

    layers, truth, masks = S.build_scene(spec)
    scale = M.scale_track(spec.frames)
    photo = M.photometric_track(scale)
    if not breathing:
        # Geometry held fixed so the output grid is the latent grid exactly.
        # This isolates "does the shipped focus measure recover the planted
        # depth" from "does the aligner solve the breathing", which are two
        # different questions and are scored separately. Photometry is left
        # ON: it is not a geometric term and fact 1259 makes it a real
        # confound for the focus response, so removing it would be removing
        # part of the physics under test.
        scale = np.ones_like(scale)
    neff = M.n_eff()
    rng = np.random.default_rng(spec.seed + 1000)

    span = M.WHITE - M.BLACK
    for k in range(spec.frames):
        # D1 (index offset): render the schedule one frame late while
        # recording the unshifted index as truth. Discipline 615 -- this
        # perturbs the CORRESPONDENCE only. Every frame remains a physically
        # valid frame of the same stack: same noise, same texture, same
        # defocus statistics. Only which frame is sharp where moves.
        k_render = k + 1.0 if plant == "index1" else float(k)
        # D2 (unmodelled warp): an extra global scale on the second half,
        # on top of the modelled breathing track. Defocus and noise untouched.
        ex = 1.0
        if plant == "warp" and k >= spec.frames // 2:
            # Magnitude in PERCENT OF SCALE, swept by s5. The registered
            # value was 0.5% of the half-diagonal, which on a 512 px frame
            # is 4.127% of scale -- and it did not redden the round-trip.
            # The sweep exists because that failure is a measurement, not a
            # thing to quietly re-tune.
            pct = 4.127 if warp_pct is None else float(warp_pct)
            ex = 1.0 + pct / 100.0

        rgb = S.render_frame(layers, spec, k_render, scale[k], neff,
                             extra_scale=ex)
        rgb = np.clip(rgb, 0.0, None) * photo[k]
        cfa = S.mosaic(rgb) * (spec.level * span)
        cfa = S.add_noise(cfa, g, rn_e, rng) + M.BLACK
        cfa = np.clip(np.rint(cfa), 0, M.WHITE).astype(np.uint16)
        M.write_dng(os.path.join(outdir, f"DSC{k + 1:05d}.ARW"), cfa,
                    iso=spec.iso,
                    description="M102 synthetic" if extra_tag else None)

    meta = {
        "frames": spec.frames, "h": spec.h, "w": spec.w,
        "blur_px_per_frame": spec.blur_px_per_frame,
        "iso": spec.iso, "gain_dn_per_e": g, "read_noise_e": rn_e,
        "reference_stack": ref, "plant": plant, "seed": spec.seed,
        "extra_tag": bool(extra_tag), "breathing": bool(breathing),
        "warp_pct": warp_pct,
        "n_eff": neff, "level": spec.level,
        "scale_first_last": [float(scale[0]), float(scale[-1])],
        "photo_first_last": [float(photo[0]), float(photo[-1])],
    }
    np.savez_compressed(os.path.join(outdir, "truth.npz"), truth=truth,
                        scale=scale, photo=photo,
                        **{f"mask_{k}": v for k, v in masks.items()})
    with open(os.path.join(outdir, "truth.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    return meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--plant", choices=["index1", "warp"], default=None)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--tag", action="store_true")
    ap.add_argument("--frames", type=int, default=32)
    ap.add_argument("--no-breathing", action="store_true")
    ap.add_argument("--warp-pct", type=float, default=None)
    ap.add_argument("--size", type=int, default=512)
    a = ap.parse_args()
    spec = S.SimSpec(h=a.size, w=a.size, frames=a.frames, seed=a.seed)
    m = generate(a.outdir, spec, plant=a.plant, extra_tag=a.tag,
                 breathing=not a.no_breathing)
    print(json.dumps(m, indent=2))


if __name__ == "__main__":
    main()

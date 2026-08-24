"""M101 probe: geometry, EXIF and the noise-model sigmas the bars are stated in.

Reads metadata and ONE frame of each kind. No hypothesis is tested here; this
exists so the pre-registration can quote real numbers rather than guesses.

Read-only against D:\\macro-dark-frames and D:\\personal\\macro.
"""

import glob
import json
import os

import exifread
import numpy as np
import rawpy

DARKS = r"D:\macro-dark-frames"
MACRO = r"D:\personal\macro"
OUT = r"C:\dev\strehl-out\M101"

# profile.rs A7C2, read at 6a8ac30.
GAIN_DIVISOR = 436.8
BASE_ISO = 100.0
RN_LOW = 4.20
RN_HIGH = 1.2392
SECOND_BASE_ISO = 400.0
BLACK = 512.0


def gain(iso):
    return max(iso, BASE_ISO) / GAIN_DIVISOR


def read_noise_e(iso):
    return RN_HIGH if iso >= SECOND_BASE_ISO else RN_LOW


def sigma_dn(iso, signal_dn):
    g = gain(iso)
    return float(np.sqrt(g * signal_dn + (read_noise_e(iso) * g) ** 2))


def exif(path):
    with open(path, "rb") as fh:
        t = exifread.process_file(fh, details=False)
    return {
        "iso": str(t.get("EXIF ISOSpeedRatings", "?")),
        "exposure": str(t.get("EXIF ExposureTime", "?")),
        "fnumber": str(t.get("EXIF FNumber", "?")),
        "datetime": str(t.get("EXIF DateTimeOriginal", "?")),
    }


def main():
    rep = {}

    groups = []
    for d in sorted(glob.glob(os.path.join(DARKS, "*MSDCF"))):
        fs = sorted(glob.glob(os.path.join(d, "*.ARW")))
        e_first = exif(fs[0])
        e_third = exif(fs[2])
        iso = float(e_first["iso"])
        groups.append(
            {
                "dir": os.path.basename(d),
                "n": len(fs),
                "iso": iso,
                "exposure": e_first["exposure"],
                "datetime_first": e_first["datetime"],
                "datetime_third": e_third["datetime"],
                "same_iso_first_vs_third": e_first["iso"] == e_third["iso"],
                "gain_dn_per_e": gain(iso),
                "read_noise_e": read_noise_e(iso),
                "sigma_dn_at_zero": sigma_dn(iso, 0.0),
            }
        )
    rep["dark_groups"] = groups

    with rawpy.imread(sorted(glob.glob(os.path.join(DARKS, "118MSDCF", "*.ARW")))[0]) as rr:
        vis = rr.raw_image_visible.astype(np.uint16)
        full = rr.raw_image.astype(np.uint16)
        pat = rr.raw_pattern.tolist()
        rep["dark_frame"] = {
            "raw_image_visible_shape": list(vis.shape),
            "raw_image_shape": list(full.shape),
            "raw_pattern": pat,
            "black_level_per_channel": [int(v) for v in rr.black_level_per_channel],
            "white_level": int(rr.white_level),
            "camera_whitebalance": [float(v) for v in rr.camera_whitebalance],
            "colour_desc": rr.color_desc.decode(),
            "plane_shape": [vis.shape[0] // 2, vis.shape[1] // 2],
            "mean_dn": float(vis.mean()),
            "p99_dn": float(np.percentile(vis, 99)),
        }

    stacks = {}
    for name in ("bee-3-cpl", "bee-2-cpl", "coffee-bubbles", "109MSDCF", "foam"):
        fs = sorted(glob.glob(os.path.join(MACRO, name, "*.ARW")))
        if not fs:
            continue
        e = exif(fs[0])
        iso = float(e["iso"])
        stacks[name] = {
            "frames": len(fs),
            **e,
            "gain_dn_per_e": gain(iso),
            "read_noise_e": read_noise_e(iso),
            "sigma_dn_at_zero": sigma_dn(iso, 0.0),
            "sigma_dn_at_1000": sigma_dn(iso, 1000.0),
        }
    with rawpy.imread(sorted(glob.glob(os.path.join(MACRO, "bee-3-cpl", "*.ARW")))[0]) as rr:
        vis = rr.raw_image_visible.astype(np.float32)
        stacks["bee-3-cpl"]["raw_image_visible_shape"] = list(vis.shape)
        stacks["bee-3-cpl"]["plane_shape"] = [vis.shape[0] // 2, vis.shape[1] // 2]
        stacks["bee-3-cpl"]["mean_dn"] = float(vis.mean())
        stacks["bee-3-cpl"]["p999_dn"] = float(np.percentile(vis, 99.9))
        stacks["bee-3-cpl"]["black_level_per_channel"] = [
            int(v) for v in rr.black_level_per_channel
        ]
        stacks["bee-3-cpl"]["white_level"] = int(rr.white_level)
    rep["stacks"] = stacks

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "00-probe.json"), "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1)

    print("=== dark groups ===")
    for g in groups:
        print(
            f"  {g['dir']}  ISO {g['iso']:>6.0f}  exp {g['exposure']:>7}  n={g['n']}  "
            f"g={g['gain_dn_per_e']:.4f} DN/e-  RN={g['read_noise_e']:.4f} e-  "
            f"sigma(0)={g['sigma_dn_at_zero']:.4f} DN  t0={g['datetime_first']}"
        )
    print("\n=== dark frame geometry ===")
    for k, v in rep["dark_frame"].items():
        print(f"  {k}: {v}")
    print("\n=== stacks ===")
    for k, v in stacks.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()

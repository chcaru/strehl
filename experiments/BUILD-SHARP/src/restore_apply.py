"""Drive strehl-core's restore-plane example over a rendered arm.

Why a sweep rather than a value
-------------------------------
The Wiener denominator carries `sigma^2 / S(f)`, which is a knob, and ORCH's
brief says plainly: if you find yourself choosing that parameter to make a
number land, stop. So this does not choose one. It runs a range spanning every
sigma the project has a defensible claim to and reports the ESF delta and the
cost columns at each, so the reader sees the whole response curve including the
settings that do not help.

Two facts make that safe to do here, and neither held in section 13:

  * `H` is our own Catmull-Rom gather kernel, not a lens OTF, and it never
    falls below 0.6251 across the band. A FULL inverse is therefore bounded at
    1.60x gain. There is no sigma at which this runs away.
  * The filter is zero-phase by construction, so no sigma can move an edge.

Consistency of the two power estimates
--------------------------------------
Section 16 caught a trap: flat-window noise combined with whole-frame signal
reports under 1% noise at Nyquist and licenses near-total inverse filtering.
`power_at` inside restore.rs estimates `S(f)` from the whole plane, so a sigma
taken from a dark flat backdrop would be the same mismatch. The sweep is
reported against the image's own median-level noise scale rather than its
backdrop, and the endpoints are chosen to bracket that rather than to flatter
it.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import subprocess
import sys

import numpy as np
import tifffile

ROOT = r"C:\dev\blog\death-of-software\projects\strehl"
EXE = os.path.join(ROOT, "target", "release", "examples", "restore-plane.exe")


def write_raw(path: str, plane: np.ndarray) -> None:
    h, w = plane.shape
    with open(path, "wb") as fh:
        fh.write(struct.pack("<II", w, h))
        fh.write(np.ascontiguousarray(plane, dtype="<f4").tobytes())


def read_raw(path: str) -> np.ndarray:
    with open(path, "rb") as fh:
        w, h = struct.unpack("<II", fh.read(8))
        data = np.frombuffer(fh.read(), dtype="<f4")
    assert data.size == w * h, f"{path}: expected {w * h} floats, got {data.size}"
    return data.reshape(h, w).astype(np.float64)


def restore_image(img: np.ndarray, grid: float, sigma2: float, cap: float, tmp: str):
    """Apply the Rust filter to each channel. Returns (image, per-channel reports)."""
    out = np.empty_like(img, dtype=np.float64)
    reports = []
    for c in range(img.shape[2]):
        rin = os.path.join(tmp, f"in{c}.raw")
        rout = os.path.join(tmp, f"out{c}.raw")
        write_raw(rin, img[:, :, c])
        proc = subprocess.run(
            [EXE, rin, rout, str(grid), str(sigma2), str(cap)],
            capture_output=True,
        )
        if proc.returncode != 0:
            raise SystemExit(
                f"restore-plane failed on channel {c}: {proc.stderr.decode('utf-8', 'replace')}"
            )
        reports.append(json.loads(proc.stdout.decode("utf-8")))
        out[:, :, c] = read_raw(rout)
        os.remove(rin)
        os.remove(rout)
    return out, reports


def noise_scale(img: np.ndarray) -> dict:
    """Direct measurements of the image's own noise scale, for context only.

    Reported so the sweep endpoints can be read against something, NOT used to
    pick a value. The MAD of the Laplacian is a high-pass estimate and is
    contaminated by real detail on a textured subject; that contamination is
    the point of section 16 and is why this is context rather than a choice.
    """
    g = img[:, :, 1] if img.shape[2] > 1 else img[:, :, 0]
    lap = g[1:-1, 1:-1] * 4.0 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    mad = float(np.median(np.abs(lap - np.median(lap))))
    sigma_hp = mad / 0.6745 / np.sqrt(20.0)
    return {
        "median_level_dn": float(np.median(g)),
        "laplacian_mad_sigma_dn": sigma_hp,
        "laplacian_mad_sigma2": sigma_hp**2,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="reference linear TIFF (the unrestored arm)")
    ap.add_argument("--out", required=True, help="output directory; one subdir per arm")
    ap.add_argument("--tifname", default="linear-srgb.tif", help="filename written inside each arm dir")
    ap.add_argument("--no-ref-copy", action="store_true", help="do not re-write the reference arm")
    ap.add_argument("--grid", type=float, default=2.0)
    ap.add_argument("--cap", type=float, default=1.7)
    ap.add_argument(
        "--sigma2",
        type=float,
        nargs="+",
        default=[100.0, 691.6, 2000.0, 4983.0, 20000.0],
        help="the sweep. 691.6 and 4983.0 are restore.rs's own recorded calibrations.",
    )
    args = ap.parse_args()

    img = tifffile.imread(args.ref).astype(np.float64)
    if img.ndim == 2:
        img = img[:, :, None]
    if img.ndim != 3:
        raise SystemExit(f"expected a 2-D or RGB TIFF, got shape {img.shape}")
    raw_dtype = tifffile.imread(args.ref).dtype
    print(f"reference {args.ref}  shape {img.shape}  dtype in file {raw_dtype}")
    ctx = noise_scale(img)
    print("noise context (NOT used to choose sigma^2):")
    for k, v in ctx.items():
        print(f"  {k:28s} {v:14.4f}")

    os.makedirs(args.out, exist_ok=True)
    tmp = os.path.join(args.out, "_tmp")
    os.makedirs(tmp, exist_ok=True)

    ref_dir = os.path.join(args.out, "ref")
    if not args.no_ref_copy:
        os.makedirs(ref_dir, exist_ok=True)
        tifffile.imwrite(
            os.path.join(ref_dir, args.tifname), np.clip(img, 0, 65535).astype(np.uint16).squeeze()
        )

    rows = []
    for s2 in args.sigma2:
        out, reports = restore_image(img, args.grid, s2, args.cap, tmp)
        name = f"s2-{s2:g}"
        d = os.path.join(args.out, name)
        os.makedirs(d, exist_ok=True)
        clipped = float(np.mean(out >= 65535.0))
        tifffile.imwrite(
            os.path.join(d, args.tifname), np.clip(out, 0, 65535).astype(np.uint16).squeeze()
        )
        r = reports[1] if len(reports) > 1 else reports[0]
        rows.append(
            {
                "arm": name,
                "sigma2": s2,
                "dc_gain": r["dc_gain"],
                "max_gain": r["max_gain"],
                "gain_at_nyquist": r["gain_at_nyquist"],
                "recovered_fraction": r["recovered_fraction"],
                "clipped_frac": clipped,
                "mean_delta_dn": float(np.mean(out - img)),
                "taps": r["taps"],
            }
        )
        print(
            f"  {name:12s} dc {r['dc_gain']:.12f}  max {r['max_gain']:.4f}  "
            f"nyq {r['gain_at_nyquist']:.4f}  recovered {r['recovered_fraction']:.4f}  "
            f"mean delta {rows[-1]['mean_delta_dn']:+.3f} DN  clipped {clipped * 100:.4f}%"
        )

    os.rmdir(tmp)
    with open(os.path.join(args.out, "restore-sweep.json"), "w", encoding="utf-8") as fh:
        json.dump({"ref": args.ref, "context": ctx, "arms": rows}, fh, indent=2)

    # The structural guard, checked on the real image rather than only in the
    # unit tests: DC gain is 1 to machine precision, so none of these arms can
    # be an exposure change dressed up as a sharpening.
    worst = max(abs(r["dc_gain"] - 1.0) for r in rows)
    print(f"\nworst |dc_gain - 1| across the sweep: {worst:.3e}")
    if worst > 1e-9:
        print("  FAIL: the filter is not DC neutral on real data")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

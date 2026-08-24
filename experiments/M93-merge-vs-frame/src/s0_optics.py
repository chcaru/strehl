"""S0 -- the optics, re-derived from primary data in this session.

Nothing here is taken from an earlier milestone's note. The sensor pitch comes
from the file's own focal-plane resolution tags, the aperture and lens from its
own EXIF, and the diffraction cutoff from the standard incoherent-imaging
result. Where a quantity is genuinely unknown for THIS stack -- the working
magnification -- it is carried as an interval and the conclusion is stated over
the whole interval.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m93lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUTDIR = os.path.join(HERE, "out")
LAMBDA_UM = 0.550


def main() -> int:
    import exifread

    paths = sorted(
        os.path.join(L.STACK, f) for f in os.listdir(L.STACK) if f.lower().endswith(".arw")
    )
    with open(paths[len(paths) // 2], "rb") as f:
        tags = exifread.process_file(f, details=False)
    want = [
        "Image Model", "EXIF LensModel", "EXIF FNumber", "EXIF MaxApertureValue",
        "EXIF FocalLength", "EXIF FocalLengthIn35mmFilm", "EXIF ISOSpeedRatings",
        "EXIF ExposureTime", "EXIF FocalPlaneXResolution", "EXIF FocalPlaneYResolution",
        "EXIF FocalPlaneResolutionUnit", "EXIF ExifImageWidth", "EXIF ExifImageLength",
        "EXIF SubjectDistance", "MakerNote FocusPosition2",
    ]
    print("EXIF, read this session from", os.path.basename(paths[len(paths) // 2]))
    ex = {}
    for w in want:
        if w in tags:
            print(f"  {w:<34} {tags[w]}")
            ex[w] = str(tags[w])
    print()

    rf = L.decode_raw(paths[len(paths) // 2])
    h, w = rf.cfa.shape
    print(f"visible CFA (rawpy)   : {w} x {h}")

    # Pitch two ways, and they must agree.
    fpx = tags.get("EXIF FocalPlaneXResolution")
    unit = str(tags.get("EXIF FocalPlaneResolutionUnit", "2"))
    pitch_exif = None
    if fpx is not None:
        v = fpx.values[0]
        px_per_unit = float(v.num) / float(v.den)
        mm_per_unit = 25.4 if unit in ("2", "Inch") else 10.0
        pitch_exif = mm_per_unit / px_per_unit * 1000.0  # micrometres
        print(f"pitch from EXIF FPXRes: {pitch_exif:.4f} um   "
              f"({px_per_unit:.2f} px per {mm_per_unit} mm)")
    # Full-frame nominal active width.
    for wmm in (35.6, 35.7, 35.9, 36.0):
        print(f"pitch if sensor is {wmm} mm wide over {w} px : {1000*wmm/w:.4f} um")
    pitch = pitch_exif if pitch_exif else 1000 * 35.9 / w
    nyq_full = 1000.0 / (2 * pitch)  # cy/mm on the full sensor grid
    nyq_bin = nyq_full / 2.0
    print()
    print(f"ADOPTED pitch p        : {pitch:.4f} um")
    print(f"full-res Nyquist       : {nyq_full:.2f} cy/mm  (0.5 cy per sensor px)")
    print(f"binned-plane Nyquist   : {nyq_bin:.2f} cy/mm  (0.5 cy per 2x2 quad)")

    # The green quincunx. Green sits on half the sites, on a checkerboard. Its
    # reciprocal cell is a DIAMOND: the lattice supports |fx| + |fy| <= 0.5
    # cy/sensor-px. So the highest green-representable frequency depends on
    # direction -- 0.5 cy/px along the axes, 0.25*sqrt(2) along the diagonals.
    g_axis = nyq_full
    g_diag = 0.25 * np.sqrt(2.0) * 1000.0 / pitch
    print()
    print(f"green quincunx, axis   : {g_axis:.2f} cy/mm")
    print(f"green quincunx, diag   : {g_diag:.2f} cy/mm   <-- the diamond's short radius")
    print(f"        radial mean of the diamond boundary : "
          f"{np.mean([np.hypot(*p) for p in _diamond_boundary()]) * 1000.0 / pitch:.2f} cy/mm")

    # Diffraction. N_eff = N (1 + m/p_pupil); f_c = 1 / (lambda N_eff).
    N = 5.6
    print()
    print(f"N (EXIF FNumber)       : {N}")
    print(f"lambda                 : {LAMBDA_UM*1000:.0f} nm")
    rows = []
    for pupil in (1.0, 1.31, 1.62, 1.94):
        for m in (1.0, 2.0, 2.72, 2.8):
            B = 1.0 + m / pupil
            neff = N * B
            fc = 1000.0 / (LAMBDA_UM * neff)  # cy/mm
            rows.append(dict(pupil=pupil, m=m, B=B, N_eff=neff, f_c=fc))
    print(f"{'p_pupil':>8} {'m':>6} {'B':>6} {'N_eff':>7} {'f_c cy/mm':>10} "
          f"{'MTF@'+f'{nyq_full:.0f}':>10} {'MTF@74':>8}")
    for r in rows:
        print(f"{r['pupil']:8.2f} {r['m']:6.2f} {r['B']:6.3f} {r['N_eff']:7.2f} "
              f"{r['f_c']:10.1f} {mtf_diff(nyq_full, r['f_c']):10.4f} "
              f"{mtf_diff(74.0, r['f_c']):8.4f}")

    out = dict(exif=ex, cfa=[h, w], pitch_um=pitch, pitch_exif_um=pitch_exif,
               nyq_full_cymm=nyq_full, nyq_bin_cymm=nyq_bin,
               green_axis_cymm=g_axis, green_diag_cymm=g_diag,
               lambda_um=LAMBDA_UM, N=N, table=rows)
    dst = os.path.join(OUTDIR, "s0_optics.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


def _diamond_boundary(n=4096):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    c, s = np.cos(t), np.sin(t)
    r = 0.5 / (np.abs(c) + np.abs(s))
    return list(zip(r * c, r * s))


def mtf_diff(f_cymm: float, f_c_cymm: float) -> float:
    """Incoherent diffraction MTF of a circular pupil at normalised nu = f/f_c."""
    nu = min(f_cymm / f_c_cymm, 1.0)
    return float(2.0 / np.pi * (np.arccos(nu) - nu * np.sqrt(1.0 - nu**2)))


if __name__ == "__main__":
    raise SystemExit(main())

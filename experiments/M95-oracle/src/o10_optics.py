"""O10 -- the second arm: what is at 74 cy/mm, and where does it live?

M85 section 7 named an artefact floor at 74 cy/mm where the optics still deliver
19-34 % MTF, and my brief asks whether that floor is in the optics, the
demosaic, the resample or the merge. This computes the band structure from
primary constants and the measured geometry of this capture, so the answer is
arithmetic rather than recollection.

EXIF, verified by the orchestrator: FE 100mm F2.8 Macro GM OSS + 2X
Teleconverter, FNumber 5.6, MaxApertureValue 5.6 -- f/5.6 is WIDE OPEN with the
teleconverter fitted, so there is no aperture headroom at all. The working
aperture at magnification m is N_eff = N (1 + m/p), and with p = 1 the
diffraction cutoff is 1 / (lambda N_eff).

The shooting magnification is not in EXIF, so it is BOUNDED rather than assumed:
the bare lens is a 1.4:1 macro and the 2X teleconverter takes it to 2.8:1, so
m lies in [0.5, 2.8] for any plausible frame-filling macro of a bee. Every
number below is printed for the whole range, and the conclusion is checked to
hold across all of it.
"""

from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from o3_commission import CUBE, OUTD  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")

SENSOR_W_MM = 35.9
N_F = 5.6
LAMBDA_MM = 550e-6
MAGS = [0.5, 1.0, 1.4, 2.0, 2.8]
M85_FLOOR = 74.0


def mtf_diff(f, fc):
    s = np.clip(f / fc, 0.0, 1.0)
    phi = np.arccos(s)
    return (2.0 / np.pi) * (phi - np.cos(phi) * np.sin(phi))


def main() -> int:
    meta = json.load(open(os.path.join(CUBE, "cube_meta.json"), encoding="utf-8"))
    ph, pw = meta["plane_shape"]
    cfa_h, cfa_w = ph * 2, pw * 2
    g = np.load(os.path.join(CUBE, "ROI-FLAT.g1.npy"), mmap_mode="r")
    print(f"green plane emitted by the product: {ph} x {pw}")
    print(f"CFA it came from: {cfa_h} x {cfa_w}  = {cfa_h*cfa_w/1e6:.1f} MP")
    print(f"green-plane crop dtype {g.dtype}, {g.shape[0]} frames")
    del g

    pitch_sensor = SENSOR_W_MM / cfa_w
    pitch_plane = 2.0 * pitch_sensor
    nyq_sensor = 0.5 / pitch_sensor
    nyq_plane = 0.5 / pitch_plane
    print(f"\nsensor pitch      {pitch_sensor*1000:.4f} um   "
          f"Nyquist {nyq_sensor:.2f} cy/mm")
    print(f"emitted plane pitch {pitch_plane*1000:.4f} um   "
          f"Nyquist {nyq_plane:.2f} cy/mm")
    print(f"emitted pixels    {ph*pw/1e6:.1f} MP from a "
          f"{cfa_h*cfa_w/1e6:.1f} MP capture = "
          f"{100.0*ph*pw/(cfa_h*cfa_w):.1f} %")

    print(f"\nM85's floor at {M85_FLOOR:.0f} cy/mm sits at "
          f"{M85_FLOOR/nyq_plane:.3f} x the EMITTED Nyquist and "
          f"{M85_FLOOR/nyq_sensor:.3f} x the SENSOR Nyquist.")
    print("  -> representable by the sensor, NOT representable by what the "
          "product emits.")

    print("\ndiffraction, f/5.6 wide open with the 2X TC, lambda = 550 nm:")
    rows = []
    for m in MAGS:
        neff = N_F * (1.0 + m)
        fc = 1.0 / (LAMBDA_MM * neff)
        r = dict(m=m, n_eff=neff, cutoff=fc,
                 mtf_at_plane_nyq=float(mtf_diff(nyq_plane, fc)),
                 mtf_at_74=float(mtf_diff(M85_FLOOR, fc)),
                 mtf_at_sensor_nyq=float(mtf_diff(nyq_sensor, fc)))
        rows.append(r)
        print(f"  m={m:4.1f}  N_eff={neff:5.2f}  cutoff={fc:7.1f} cy/mm   "
              f"MTF at emitted Nyq {nyq_plane:.1f} = {r['mtf_at_plane_nyq']*100:5.1f} %"
              f"   at 74 = {r['mtf_at_74']*100:5.1f} %"
              f"   at sensor Nyq {nyq_sensor:.1f} = "
              f"{r['mtf_at_sensor_nyq']*100:5.1f} %")

    lo = min(r["mtf_at_plane_nyq"] for r in rows)
    hi = max(r["mtf_at_plane_nyq"] for r in rows)
    l74 = min(r["mtf_at_74"] for r in rows)
    h74 = max(r["mtf_at_74"] for r in rows)
    print(f"\nover the whole plausible magnification range m = "
          f"{MAGS[0]} to {MAGS[-1]}:")
    print(f"  diffraction MTF at the EMITTED Nyquist: "
          f"{lo*100:.1f} % to {hi*100:.1f} %")
    print(f"  diffraction MTF at 74 cy/mm           : "
          f"{l74*100:.1f} % to {h74*100:.1f} %")
    print(f"  M85 section 7 reported 19-34 % at 74 cy/mm; this range "
          f"{'CONTAINS' if l74 <= 0.34 and h74 >= 0.19 else 'DOES NOT CONTAIN'} it.")

    print("\nANSWER TO THE SECOND ARM:")
    print("  The 74 cy/mm floor is not in the demosaic, the resample or the "
          "merge, because")
    print(f"  74 cy/mm is {M85_FLOOR/nyq_plane:.2f} x the Nyquist frequency of "
          "the plane those")
    print("  stages operate on. No stage downstream of the mosaic can represent "
          "it, so")
    print("  none of them can be the floor. It is lost at the point the product "
          "chooses")
    print("  to emit one pixel per 2x2 Bayer cell, and the optics still deliver "
          f"{lo*100:.0f}-{hi*100:.0f} %")
    print("  MTF at the very edge of what is emitted.")

    out = dict(cfa_shape=[cfa_h, cfa_w], pitch_sensor_um=pitch_sensor * 1000,
               pitch_plane_um=pitch_plane * 1000, nyq_sensor=nyq_sensor,
               nyq_plane=nyq_plane, rows=rows)
    with open(os.path.join(OUTD, "o10_optics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, default=float)
    print(f"\nwrote {os.path.join(OUTD, 'o10_optics.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

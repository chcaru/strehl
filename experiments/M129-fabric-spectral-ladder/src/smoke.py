"""Smoke test: does M5's decoder accept the fabric captures, and what is in them?

This is instrument validation, not measurement. It answers three questions that
must be settled before any reduction is designed:

  1. Do M5's hard assertions about this sensor still hold? `load_active` asserts
     the black level, the white level, the CFA pattern and zero margins. If the
     ILCE-7CM2 in this capture differs from whatever M5 was built against, every
     downstream number would be wrong, and it should fail loudly here.
  2. What are the signal levels, and is anything clipped? The registered clipping
     gate (T5) needs to know whether it will ever fire.
  3. Does a GQ spectrum come out with a sane shape?

Read-only with respect to D:\\personal\\macro. Writes nothing.
"""

import os
import sys
import glob

import numpy as np

M5 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "m5-diffraction")
sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

ROOT = r"D:\personal\macro\requests\7-aperture-pairs"
APERTURES = [("f5.6", 5.6), ("f8", 8.0), ("f11", 11.0), ("f14", 14.0), ("f18", 18.0)]


def folder(tag):
    return os.path.join(ROOT, f"fabric-weave-{tag}-sw5-cpl")


def main():
    print(f"M5 constants: black {L.BLACK_LEVEL}, white {L.WHITE_LEVEL}, "
          f"active {L.ACTIVE_W}x{L.ACTIVE_H}, pitch {L.PITCH_UM} um")
    print(f"GQ reach {L.sensor_cyc_px_to_cyc_mm(L.lattice_nyquist_sensor('GQ')):.2f} "
          f"cy/mm, G1 reach "
          f"{L.sensor_cyc_px_to_cyc_mm(L.lattice_nyquist_sensor('G1')):.2f} cy/mm\n")

    for tag, n in APERTURES:
        d = folder(tag)
        files = sorted(glob.glob(os.path.join(d, "*.ARW")))
        if not files:
            print(f"{tag:>6}: NO FILES at {d}")
            continue
        mid = files[len(files) // 2]
        try:
            a = L.load_active(mid)
        except AssertionError as e:
            print(f"{tag:>6}: DECODER ASSERTION FAILED on {os.path.basename(mid)}: {e}")
            continue
        except Exception as e:
            print(f"{tag:>6}: DECODE ERROR {type(e).__name__}: {e}")
            continue

        af = a.astype(np.float64)
        pct = np.percentile(af, [0.1, 50, 99.9, 100])
        clipped = float(np.mean(af >= L.WHITE_LEVEL) * 100.0)
        # centre GQ patch
        try:
            patch = L.crop_lattice(a, "GQ", L.ACTIVE_H // 2, L.ACTIVE_W // 2, 512)
            f, p, counts = L.spectrum(patch, "GQ", tile=256, window="hann")
            k = L.knee(f, p, counts, 256, 512, "GQ")
            mf = L.knee_model_fit(f, p, counts)
            fc_cy = (L.sensor_cyc_px_to_cyc_mm(k["f_c"])
                     if k["f_c"] is not None else float("nan"))
            mfc_cy = (L.sensor_cyc_px_to_cyc_mm(mf["f_c"])
                      if mf.get("f_c") is not None else float("nan"))
            print(f"{tag:>6} N={n:<5} {os.path.basename(mid)}  {len(files)} frames")
            print(f"        DN p0.1/med/p99.9/max = {pct[0]:.0f}/{pct[1]:.0f}/"
                  f"{pct[2]:.0f}/{pct[3]:.0f}   clipped {clipped:.4f}%")
            print(f"        patch mean {patch.mean():.0f} DN   dyn "
                  f"{k['dynamic_range']:.1f}  has_signal {k['has_signal']}  "
                  f"saturated {k['saturated']}")
            print(f"        knee f_c {fc_cy:8.2f} cy/mm    model f_c {mfc_cy:8.2f} "
                  f"cy/mm  above_reach {mf.get('above_reach')}  "
                  f"resid {mf.get('resid_rms', float('nan')):.4f}")
        except Exception as e:
            print(f"{tag:>6}: SPECTRUM ERROR {type(e).__name__}: {e}")


if __name__ == "__main__":
    main()

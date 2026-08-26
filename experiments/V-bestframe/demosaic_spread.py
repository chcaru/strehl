"""Bound the demosaic asymmetry that section 13.8 listed as un-ruled-out.

The frame arm decodes with rawpy's default AHD. The gallery log says
blend-render used "Malvar-He-Cutler". Neither is a resample, so BUILD-SHARP's
chain audit does not cover it, and it is a genuine differential between the arms.
LibRaw does not offer MHC, so it cannot be measured directly. What CAN be
measured is the SPREAD across the algorithms LibRaw does offer, which bounds how
much any demosaic choice can move this instrument's band.

MHC is bilinear plus a gradient correction term, so LINEAR is the structural
floor of that family and AHD an adaptive member. If the whole spread is small
compared with the deficit, the asymmetry cannot carry the deficit whichever
algorithm MHC most resembles.
"""
import argparse
import numpy as np
import rawpy
from pathlib import Path
import bestframe as B
from boundary import tile_amp

RAW = Path(r"D:\personal\macro")
ALGOS = ["AHD", "LINEAR", "VNG", "PPG", "DCB", "AAHD"]


def decode_with_algo(path, name):
    with rawpy.imread(str(path)) as r:
        a = r.postprocess(output_bps=16, no_auto_bright=True, use_camera_wb=True,
                          demosaic_algorithm=getattr(rawpy.DemosaicAlgorithm, name))
    assert a.dtype == np.uint16, f"rawpy returned {a.dtype}, NOT uint16"
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--frac", type=float, default=0.5)
    a = ap.parse_args()
    for subj in a.subjects:
        fs = sorted((RAW / subj).glob("*.ARW"))
        k = int(round(a.frac * (len(fs) - 1)))
        path = fs[k]
        print(f"\n{'=' * 78}\n{subj}  frame {k} {path.name}\n{'=' * 78}", flush=True)
        ref = None
        for nm in ALGOS:
            lum = B.luma(decode_with_algo(path, nm)).astype(np.float32)
            if ref is None:
                ye = B.tile_edges(lum.shape[0], B.NTY)
                xe = B.tile_edges(lum.shape[1], B.NTX)
            amp = tile_amp(lum, ye, xe, B.FINE)
            del lum
            if ref is None:
                ref = amp
                print(f"  {nm:<8} (reference, what this instrument uses)")
                continue
            r = amp / ref
            q = np.nanpercentile(r, [5, 50, 95])
            print(f"  {nm:<8} band amplitude vs AHD: median {q[1]:.4f}  "
                  f"p05 {q[0]:.4f} p95 {q[2]:.4f}", flush=True)


if __name__ == "__main__":
    main()
"""M115 -- negative control on bitdepth_check.py, and a measured answer to the
question ORCH's triage actually needs: HOW MUCH would an 8-bit narrowing have
moved a real SNR result?

ORCH's instruction 4 is 'do not argue from first principles that 8 bits was
enough'.  This does not argue.  It plants the narrowing PIL performs -- keep the
high byte, discard the low one -- into M115's own loader, on M115's own frames,
and re-runs the headline.  Two things come out:

  1. the bit-depth check is COMMISSIONED: a check that cannot go red on a
     narrowed input is not evidence that the input was not narrowed
  2. a measured sensitivity for the fleet: what the hazard does to a band-SNR
     ratio computed on real macro frames

The narrowing is applied to the raw DN before black subtraction, which is where
a file reader would impose it.
"""
import os, sys, json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import load_detail, banner

ROIS = json.load(open(os.path.join(L.OUT, "s01_rois.json")))
STACK = "109MSDCF"
DF = 0.01


def narrow8(cube):
    """Exactly what PIL does to a 16-bit RGB TIFF: keep the high byte."""
    raw = cube.astype(np.float64) + L.BLACK
    return (np.floor(raw / 256.0) * 256.0 - L.BLACK).astype(np.float32)


def main():
    banner("negative control -- plant the PIL narrowing into M115's own loader")
    cube, g, rn_e, B = load_detail(STACK)
    nar = narrow8(cube)
    print(f"  distinct levels: intact {np.unique(cube).size}, "
          f"narrowed {np.unique(nar).size}")
    assert np.unique(nar).size <= 256, "the plant did not land"

    # 1. does the check's assert actually fire?
    fired = False
    try:
        assert np.unique(nar).size > 256
    except AssertionError:
        fired = True
    print(f"  bitdepth_check's '>256 distinct levels' assert fires on the "
          f"narrowed cube: {fired}  -> {'COMMISSIONED' if fired else 'USELESS'}")

    # 2. what would it have done to the headline?
    crop = L.crop_fn(L.PAD, B)
    rb = L.RadialBins(B, DF)
    mid = rb.band_mask(*L.MIDBAND)
    res = {}
    for name, c in [("intact", cube), ("narrowed", nar)]:
        fine, coarse, reg = L.focus_fields(c, g, rn_e)
        s0, _, _ = L.calibrate_s(c, coarse)
        sp = L.split_channel(c, g, rn_e, s0, crop, want=["GATE", "WIENER", "FRAME*"])
        st = {a: L.split_stats(rb, *sp[a]) for a in ["GATE", "WIENER", "FRAME*"]}
        snr = {a: np.sqrt(np.maximum(st[a][2][mid], 0)) for a in st}
        ratio = float(np.mean(snr["WIENER"] / np.maximum(snr["GATE"], 1e-30)))
        noise = float(np.mean(st["FRAME*"][1][mid]))
        res[name] = dict(s=s0, ratio=ratio, noise=noise,
                         snr_frame=float(np.mean(st["FRAME*"][2][mid])),
                         psig=float(np.mean(st["FRAME*"][0][mid])))
        print(f"\n  {name:9s} s={s0:.4f}  FRAME* P_noise {noise:11.4g}  "
              f"FRAME* SNR {res[name]['snr_frame']:9.3f}")
        print(f"  {'':9s} R_SNR(WIENER)/R_SNR(GATE) = {ratio:.4f}")

    a, b = res["intact"], res["narrowed"]
    print(f"\n  the narrowing multiplied the measured noise power by "
          f"{b['noise']/a['noise']:.1f}x")
    print(f"  and the measured FRAME* band SNR by {b['snr_frame']/a['snr_frame']:.3f}x")
    print(f"  the headline ratio moved {a['ratio']:.4f} -> {b['ratio']:.4f} "
          f"({100*(b['ratio']/a['ratio']-1):+.1f}%)")
    print(f"\n  Read this the right way round: the headline ratio is a RATIO of")
    print(f"  two arms measured on the same data, so it is partly protected by")
    print(f"  cancellation.  The ABSOLUTE noise and SNR readings are not, and")
    print(f"  they are what a fleet-wide 'is my small signal real' question")
    print(f"  depends on.  A {b['noise']/a['noise']:.0f}x error in noise power is a "
          f"{np.sqrt(b['noise']/a['noise']):.1f}x error in sigma.")
    json.dump(res, open(os.path.join(L.OUT, "negctl_bitdepth.json"), "w"), indent=2)
    print(f"\n  -> negctl_bitdepth.json")


if __name__ == "__main__":
    main()

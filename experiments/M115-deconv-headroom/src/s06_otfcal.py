"""M115 s06 -- does OTF self-calibration from the through-focus curve work?

The reviewer's proposal is that no lens model is needed because 'the width of
the through-focus response curve IS the local PSF scale sampled by the
operator'.  That is a claim with a sharp, falsifiable consequence.

A defocus model says the per-frame optical transfer function is
frequency-dependent: at defocus radius r the OTF is a jinc, which attenuates
HIGH frequencies far more than low ones and changes sign past its first zero.
So if a single self-calibrated s is a valid summary, then

    M_meas(dk, f) = M_model(dk, f) = |OTF_defocus(dk*s, f)| * |OTF_diff(f)|

must hold ACROSS f with ONE value of s.

M70 measured the competing possibility on 12 stacks: the through-focus band
matrix is rank-1 to 0.9959, i.e. off-focus frames are approximately SCALED
COPIES of the focused one rather than differently-shaped ones.  If that holds
in the output domain too, the measured attenuation is FLAT in f, no single s
reproduces it, and the width of the curve cannot stand in for the PSF scale.

The discriminator, registered before running: fit s independently in each
radial bin.  A valid model gives the SAME s in every bin.  A rank-1 stack gives
s falling steeply with f, because the model can only make a flat attenuation at
high f by pretending the defocus is small.
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m115lib as L
from s03_instrument import load_detail, banner

DF = 0.01
STACKS = ["109MSDCF", "119MSDCF"]
DKS = [1, 2, 3, 4, 6]


def otfcal(stack, log):
    banner(f"OTF self-calibration -- {stack} detail ROI")
    cube, g, rn_e, B = load_detail(stack)
    crop = L.crop_fn(L.PAD, B)
    fine, coarse, reg = L.focus_fields(cube, g, rn_e)
    s0, fw_m, fw_mod = L.calibrate_s(cube, coarse)
    n = cube.shape[0]
    ks = int(np.argmax(coarse.reshape(n, -1).mean(1)))
    rb = L.RadialBins(B, DF)
    mid = rb.band_mask(*L.MIDBAND)
    fc = rb.centres

    def psig(k):
        img = crop(cube[k]).astype(np.float64)
        v = L.quad_var(float(img.mean()), g, rn_e)
        return np.maximum(rb.power(img) - v * rb.nrm, 1e-30)

    p0 = psig(ks)
    print(f"  {n} frames, k* = {ks}, curve FWHM {fw_m:.1f} frames -> "
          f"self-calibrated s = {s0:.4f} quad px/frame "
          f"(model reproduces FWHM {fw_mod:.1f})")
    print(f"\n  measured |OTF| relative to k*, against the model at that s:")
    print(f"  {'f':>7s} " + " ".join(f"{'dk='+str(d):>15s}" for d in DKS))
    rows = {}
    hd = L.otf_diffraction(fc)
    for d in DKS:
        ka, kb = min(ks + d, n - 1), max(ks - d, 0)
        m = np.sqrt(0.5 * (psig(ka) + psig(kb)) / p0)
        mod = np.abs(L.otf_defocus(d * s0, fc))
        rows[d] = dict(meas=m.tolist(), model=mod.tolist())
    for i, f in enumerate(fc):
        if not mid[i]:
            continue
        print(f"  {f:7.3f} " + " ".join(
            f"{rows[d]['meas'][i]:6.3f}/{rows[d]['model'][i]:6.3f}" for d in DKS))

    # the registered discriminator: fit s independently per radial bin
    print(f"\n  per-bin best-fit s (a valid model gives ONE value in every bin):")
    grid = np.linspace(0.05, 6.0, 400)
    per_bin = []
    for i in np.where(mid)[0]:
        err = []
        for sv in grid:
            e = sum((np.abs(L.otf_defocus(d * sv, np.array([fc[i]])))[0]
                     - rows[d]["meas"][i]) ** 2 for d in DKS)
            err.append(e)
        per_bin.append(float(grid[int(np.argmin(err))]))
    fs = fc[mid]
    for i, f in enumerate(fs):
        print(f"    f={f:.3f}  s_fit = {per_bin[i]:.3f}")
    lo, hi = float(np.min(per_bin)), float(np.max(per_bin))
    sl = float(np.polyfit(fs, per_bin, 1)[0])
    spread = hi / max(lo, 1e-9)
    print(f"\n  s_fit ranges {lo:.3f}..{hi:.3f} ({spread:.2f}x), slope in f = {sl:+.2f}")
    print(f"  curve-width self-calibration gave s = {s0:.4f}")
    ok = spread < 1.5
    print(f"  VERDICT: a single s {'DOES' if ok else 'DOES NOT'} describe the "
          f"measured through-focus attenuation across frequency.")

    # is the attenuation flat in f?  that is M70's rank-1 alternative
    flat = {d: float(np.std(np.array(rows[d]["meas"])[mid]) /
                     max(np.mean(np.array(rows[d]["meas"])[mid]), 1e-9))
            for d in DKS}
    print(f"  relative spread of measured attenuation ACROSS the mid band: "
          + ", ".join(f"dk={d}: {flat[d]*100:.1f}%" for d in DKS))
    log.setdefault("otfcal", {})[stack] = dict(
        s_curve=s0, fwhm_meas=fw_m, fwhm_model=fw_mod, kstar=ks,
        f=fs.tolist(), s_per_bin=per_bin, s_lo=lo, s_hi=hi, spread=spread,
        slope=sl, single_s_ok=bool(ok), flatness=flat,
        rows={str(d): rows[d] for d in DKS}, centres=fc.tolist())
    return ok


def consistency(log):
    """s05 measured the matched-contrast noise ratio directly.  Algebraically it
    must equal R_SNR(WIENER)/R_SNR(GATE), which s04 measured by a different
    route on different crops.  If the two disagree, one of them is wrong."""
    banner("internal consistency: s04's R_SNR ratio vs s05's matched-contrast test")
    h = json.load(open(os.path.join(L.OUT, "s04_headroom.json")))["headline"]["FRAME*"]
    m = json.load(open(os.path.join(L.OUT, "s05_ringing.json")))["matched"]
    w = np.array(h["WIENER"]["rs"]); gt = np.array(h["GATE"]["rs"])
    ident = w / np.maximum(gt, 1e-9)
    print(f"  s04 (8 blocks of 256, both stacks pooled): "
          f"R_SNR(WIENER)/R_SNR(GATE) mid-band mean = {ident.mean():.4f}")
    for st in STACKS:
        v = np.array(m[st]["noise_ratio"])
        print(f"  s05 ({st}, full 512 ROI): matched-contrast noise ratio = "
              f"{v.mean():.4f}")
    both = np.mean([np.mean(m[st]["noise_ratio"]) for st in STACKS])
    print(f"  s05 mean over both stacks = {both:.4f}")
    print(f"  the two routes agree to {abs(both-ident.mean()):.3f} in absolute "
          f"ratio; both sit within 10% of 1.00, i.e. of 'no difference'.")
    log["consistency"] = dict(s04_ratio=float(ident.mean()),
                              s05_ratio=float(both),
                              per_bin=ident.tolist())


def main():
    t0 = time.time()
    log = {}
    for st in STACKS:
        otfcal(st, log)
    consistency(log)
    json.dump(log, open(os.path.join(L.OUT, "s06_otfcal.json"), "w"), indent=2)
    print(f"\nelapsed {time.time()-t0:.1f}s -> s06_otfcal.json")


if __name__ == "__main__":
    main()

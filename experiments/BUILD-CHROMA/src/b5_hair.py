"""
b5_hair.py -- does the measured axial CA actually explain the rainbow speckle?

The brief asks for this quantitatively, not by assertion. So this does not ask
"is there chroma on the hairs" (there plainly is, you can see it). It asks
whether the chroma has the STATISTICS that the measured axial offset predicts.

Three arms, all measured with the identical estimator (b3_defects.hair_chroma):

  MERGE      the shipped stack output. The defect as observed.

  SINGLE     one raw frame, binned to the same composition, no stacking at all.
             This carries the full optical axial CA of the lens and none of the
             election behaviour of the stacker. If the speckle is optical, it is
             already here at full strength.

  FORWARD    the merge, with R and B replaced by blurred copies of themselves,
             blurred by exactly the amount the measured axial offset costs.
             This is what the stack WOULD look like if the only consequence of
             electing on green were that R and B arrive defocused.

The blur is not guessed. b2 measured the gradient-energy forfeit directly
(R 6.62%, B 5.19% on lavendar-cpl), so the blur radius is calibrated by
bisection until blur(R) loses exactly that much gradient energy. That makes
FORWARD a dose-matched null in the sense of rule 3: it matches the treatment in
the quantity that actually drives the effect, not merely in magnitude.

The discriminating statistic is the SIGN FLIP RATE along a structure.
A defocus difference is a low-pass operation. Low-pass filtering cannot create
structure at the pixel scale; the sign of (sharp green - blurred red) is set by
whether the sample sits on a ridge crest or in a flank, and so it reverses on
the scale of the PSF, not from one pixel to the next. Confetti -- alternating
colour every pixel or two -- has a correlation length far shorter than any blur
difference can produce. So:

  if FORWARD reproduces the merge's flip rate  -> axial CA explains the speckle
  if FORWARD is much smoother than the merge   -> something else makes it, and
                                                  the axial offset is at most a
                                                  modulator
"""
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

from common import OUT, dump
import b3_defects as b3

REND = os.path.join(OUT, "render")

# Measured on lavendar-cpl by b2_analyse: fraction of gradient energy the
# elected-on-green gather forfeits in each channel.
LOSS = {"R": 0.0662, "B": 0.0519}


def grad_energy_rgb(ch):
    gy, gx = np.gradient(ch.astype(np.float64))
    return float(np.mean(gy * gy + gx * gx))


def blur_for_loss(ch, target_loss, lo=0.01, hi=3.0, tol=1e-4):
    """Gaussian sigma whose gradient-energy loss equals `target_loss`.

    Bisection, because gradient energy falls monotonically with sigma. Returns
    the sigma and the loss actually achieved, so the caller can check it.
    """
    e0 = grad_energy_rgb(ch)
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        loss = 1.0 - grad_energy_rgb(gaussian_filter(ch, mid)) / e0
        if abs(loss - target_loss) < tol:
            break
        if loss < target_loss:
            lo = mid
        else:
            hi = mid
    return mid, loss


def forward_model(img):
    """Merge with R and B defocused by the measured axial forfeit.

    Returns float64, deliberately. Quantising back to uint16 would re-introduce
    the wraparound hazard documented in b3_defects.hair_chroma and would also
    add a rounding step that the treatment arm does not have.
    """
    out = img.astype(np.float64).copy()
    got = {}
    for idx, name in ((0, "R"), (2, "B")):
        sig, loss = blur_for_loss(out[:, :, idx], LOSS[name])
        out[:, :, idx] = gaussian_filter(out[:, :, idx], sig)
        got[name] = {"sigma_px": float(sig), "achieved_loss": float(loss),
                     "target_loss": LOSS[name]}
    return out, got


def run(stack="lavendar-cpl", k=None):
    res = {"stack": stack, "arms": {}}

    p = os.path.join(REND, f"{stack}-merge.tif")
    merge = b3.read16(p)
    print(f"-- merge {p} {merge.shape} uint16-verified")
    res["arms"]["merge"] = b3.hair_chroma(merge, "merge")

    fs = b3.frames(stack) if hasattr(b3, "frames") else None
    if k is None:
        from common import frames as _frames
        k = len(_frames(stack)) // 2
    print(f"-- single frame k={k}")
    single = b3.single_frame_binned(stack, k)
    res["arms"][f"single_k{k}"] = b3.hair_chroma(single, f"single k={k}")

    print("-- forward model (R,B blurred to the measured gradient forfeit)")
    fwd, cal = forward_model(merge)
    res["blur_calibration"] = cal
    for nm, c in cal.items():
        print(f"   {nm}: sigma {c['sigma_px']:.3f} px -> loss "
              f"{c['achieved_loss']*100:.2f}% (target {c['target_loss']*100:.2f}%)")
    res["arms"]["forward_axialCA"] = b3.hair_chroma(fwd, "forward axial CA")

    # a deliberately exaggerated dose, to prove the forward model CAN move the
    # statistic when the effect is large enough -- otherwise a null result here
    # would be uninterpretable (it might just mean the statistic is inert)
    print("-- forward model at 10x dose (does the statistic respond at all?)")
    big = merge.astype(np.float64).copy()
    for idx, name in ((0, "R"), (2, "B")):
        sig, loss = blur_for_loss(big[:, :, idx], min(0.6, 10 * LOSS[name]))
        big[:, :, idx] = gaussian_filter(big[:, :, idx], sig)
        print(f"   {name}: sigma {sig:.3f} px -> loss {loss*100:.2f}%")
    res["arms"]["forward_axialCA_10x"] = b3.hair_chroma(big, "forward 10x")

    return res


def show(o):
    print(f"\n===== rainbow speckle attribution: {o['stack']} =====")
    hdr = (f"{'arm':<22}{'n_struct':>9}{'rg_sd':>9}{'bg_sd':>9}"
           f"{'flip':>8}{'consist':>9}{'frac_rg+':>10}")
    print(hdr)
    for name, a in o["arms"].items():
        if "median_sign_flip_rate" not in a:
            print(f"{name:<22}  {a.get('verdict')}")
            continue
        print(f"{name:<22}{a['n_structures']:>9}"
              f"{a['rg_hp_sd']:>9.4f}{a['bg_hp_sd']:>9.4f}"
              f"{a['median_sign_flip_rate']:>8.3f}"
              f"{a['median_sign_consistency']:>9.3f}"
              f"{a['frac_rg_positive']:>10.3f}")


if __name__ == "__main__":
    stack = sys.argv[1] if len(sys.argv) > 1 else "lavendar-cpl"
    o = run(stack)
    show(o)
    dump(f"b5_hair_{stack}", o)

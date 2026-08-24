"""E8 -- the ORCH-kernel arms: does `nearest` reveal a pre-existing fringe, or create one?

Bars K1-K6 are registered in experiments/M107-chroma/PRE-REGISTRATION-2.md,
committed bf975e0 BEFORE this file read a pixel.

Physics the statistic rests on
------------------------------
For a DISPLACEMENT-type fringe, channel c is f(x - d_c), so to first order
    chroma = d_c * f'      luma_edge = f'
and a channel-independent linear filter h scales both identically:
    rho = rms(HP(chroma)) / rms(HP(luma))    is INVARIANT under h.
That invariance is the whole discriminator. If `nearest` merely removes a
lowpass, rho holds. If `nearest` synthesises colour by aliasing, the numerator
gains power the denominator does not and rho rises.

Two controls make rho mean something, and neither is optional:
  K3-CTRL  apply a synthetic channel-independent Gaussian blur to the
           catmull arm. rho MUST hold. If my own instrument cannot return
           "invariant" when the input is invariant by construction, a measured
           "invariant" on the real arms is worthless.
  K3-POWER shift ONLY the red channel of the catmull arm by a known subpixel
           amount. rho MUST rise. If it does not, rho is blind to exactly the
           thing it is being asked to detect and every number here is noise.

The free null throughout is LUMA. Changing the kernel decorrelates everything;
any claim that the chroma field decorrelated must be relative to how much the
luma field decorrelated on the same pixels.
"""
import json
import os
import sys
import hashlib

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter, shift as ndshift, sobel

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, dump  # noqa: E402

KDIR = r"C:\dev\strehl-out\ORCH-kernel"
GAL = r"C:\dev\strehl-out\ORCH-gallery3"
ARMS = ["catmull-rom", "nearest", "bilinear"]
REF = "catmull-rom"          # shipped default; the arm the gallery claim was made on
S = 1024                     # ROI side, px
SIGMA = 6.0                  # high-pass sigma, px -- stated on every figure
EDGE_PCT = 90.0              # edge mask = top 10% of |grad L| on the REF arm only


def srgb_to_linear(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest().upper()


def hp(x, sigma=SIGMA):
    return x - gaussian_filter(x, sigma)


def fields(rgb):
    """Linear-light luma and the two chroma differences."""
    R, G, B = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    L = 0.2126 * R + 0.7152 * G + 0.0722 * B
    return L, R - G, B - G


def pick_roi(img, rmax=None):
    """Tile maximising mean |HP(R-G)| + |HP(B-G)| on the REF arm.

    Explicit and self-contained rather than reusing figures._pick_roi, so the
    selection rule is auditable from this file alone. Searched on a 4x
    decimated copy for speed; the returned origin is snapped to even pixels so
    the ROI lands on a whole CFA quad in every arm.

    `rmax` restricts the search to tile centres within that radius of the
    frame centre. Unrestricted, this selector goes straight to the wing at
    r = 2713 px -- the highest-contrast fine edges in the frame, but NOT the
    bee hair the orchestrator's by-eye claim is about, and a radius at which
    lateral CA is near its maximum. Rendering the unrestricted choice
    (fig6-auto) is what revealed that; the restricted arm exists because of it.
    """
    d = img[::4, ::4].astype(np.float64) / 65535.0
    L, cr, cb = fields(srgb_to_linear(d))
    score = np.abs(hp(cr, SIGMA / 4)) + np.abs(hp(cb, SIGMA / 4))
    s4 = S // 4
    box = gaussian_filter(score, s4 / 3.0, mode="constant")
    m = s4 // 2 + 2
    box[:m, :] = box[-m:, :] = box[:, :m] = box[:, -m:] = -1.0
    if rmax is not None:
        h4, w4 = box.shape
        yy4, xx4 = np.mgrid[0:h4, 0:w4]
        rr = np.hypot(xx4 - w4 / 2.0, yy4 - h4 / 2.0) * 4.0
        box[rr > rmax] = -1.0
    yy, xx = np.unravel_index(int(np.argmax(box)), box.shape)
    y0 = int(np.clip((yy * 4) - S // 2, 0, img.shape[0] - S)) & ~1
    x0 = int(np.clip((xx * 4) - S // 2, 0, img.shape[1] - S)) & ~1
    return x0, y0


def load(arm, x0=None, y0=None, rmax=None):
    img = tifffile.imread(os.path.join(KDIR, f"bee-3-cpl-{arm}.tif"))
    shape, dtype = img.shape, str(img.dtype)
    if x0 is None:
        x0, y0 = pick_roi(img, rmax)
    c = srgb_to_linear(img[y0:y0 + S, x0:x0 + S].astype(np.float64) / 65535.0)
    del img
    return c, (x0, y0), shape, dtype


def stats(L, cr, cb, mask, sigma=SIGMA):
    Lh, crh, cbh = hp(L, sigma), hp(cr, sigma), hp(cb, sigma)
    r = lambda a: float(np.sqrt(np.mean(a[mask] ** 2)))
    return {
        "rms_L": r(Lh), "rms_cr": r(crh), "rms_cb": r(cbh),
        "rho_cr": r(crh) / r(Lh), "rho_cb": r(cbh) / r(Lh),
    }, (Lh, crh, cbh)


def corr_slope(a, b, mask):
    """corr and least-squares slope of a on b, over mask."""
    x, y = b[mask], a[mask]
    x = x - x.mean()
    y = y - y.mean()
    sx = float(np.sqrt(np.mean(x * x)))
    sy = float(np.sqrt(np.mean(y * y)))
    r = float(np.mean(x * y) / (sx * sy))
    return r, float(np.mean(x * y) / np.mean(x * x))


def spectrum_stats(res):
    """Fraction of power above 0.7*Nyquist, and axis anisotropy up there."""
    n = res.shape[0]
    w = np.hanning(n)
    P = np.abs(np.fft.fftshift(np.fft.fft2(res * w[:, None] * w[None, :]))) ** 2
    f = np.fft.fftshift(np.fft.fftfreq(n))
    fu, fv = np.meshgrid(f, f, indexing="xy")
    rad = np.hypot(fu, fv) / 0.5                       # 1.0 == Nyquist on axis
    hi = rad > 0.7
    tot = float(P.sum())
    frac = float(P[hi].sum() / tot) if tot > 0 else float("nan")
    th = np.degrees(np.arctan2(fv, fu))
    d = np.minimum(np.abs(((th + 90) % 180) - 90), np.abs(((th) % 180) - 90))
    axis = (np.minimum(np.abs(th % 180), np.abs(180 - (th % 180))) <= 15.0) | \
           (np.abs((np.abs(th) % 180) - 90) <= 15.0)
    a = float(P[hi & axis].mean()) if (hi & axis).any() else float("nan")
    b = float(P[hi & ~axis].mean()) if (hi & ~axis).any() else float("nan")
    del d
    return {"hf_fraction": frac, "axis_anisotropy": a / b if b else float("nan")}


def run(tag="auto", rmax=None):
    res = {"config": {"S": S, "sigma": SIGMA, "edge_pct": EDGE_PCT,
                      "ref_arm": REF, "arms": ARMS, "tag": tag, "rmax": rmax}}

    # -- K1 VALIDITY --------------------------------------------------------
    ref_rgb, (x0, y0), shape, dtype = load(REF, rmax=rmax)
    res["roi"] = {"x0": x0, "y0": y0, "S": S}
    res["shape"] = {REF: [list(shape), dtype]}
    r_roi = float(np.hypot(x0 + S / 2 - shape[1] / 2, y0 + S / 2 - shape[0] / 2))
    res["roi"]["r_from_centre_px"] = r_roi
    print(f"[{tag}] ROI x0={x0} y0={y0} S={S} r={r_roi:.0f}  from {shape} {dtype}",
          flush=True)

    h_arm = sha256(os.path.join(KDIR, f"bee-3-cpl-{REF}.tif"))
    h_gal = sha256(os.path.join(GAL, "bee-3-cpl.tif"))
    res["K1_hash"] = {"arm": h_arm, "gallery": h_gal, "identical": h_arm == h_gal}
    print(f"K1 catmull-rom vs gallery byte-identical: {h_arm == h_gal}", flush=True)

    Lr, crr, cbr = fields(ref_rgb)

    # edge mask from the REF arm ONLY -- identical pixels for every arm
    g = np.hypot(sobel(Lr, 0), sobel(Lr, 1))
    mask = g >= np.percentile(g, EDGE_PCT)
    res["mask_pixels"] = int(mask.sum())
    print(f"edge mask: {int(mask.sum())} px of {S*S}", flush=True)

    # -- per-arm fields -----------------------------------------------------
    arm_stats, H = {}, {}
    for a in ARMS:
        rgb = ref_rgb if a == REF else load(a, x0, y0)[0]
        if a != REF:
            res["shape"][a] = [list(tifffile.TiffFile(
                os.path.join(KDIR, f"bee-3-cpl-{a}.tif")).pages[0].shape), dtype]
        L, cr, cb = fields(rgb)
        st, h = stats(L, cr, cb, mask)
        arm_stats[a], H[a] = st, h
        print(f"  {a:12s} rms_L={st['rms_L']:.6f} rms_cr={st['rms_cr']:.6f} "
              f"rms_cb={st['rms_cb']:.6f} rho_cr={st['rho_cr']:.4f} "
              f"rho_cb={st['rho_cb']:.4f}", flush=True)
        del rgb, L, cr, cb
    res["arms"] = arm_stats

    N, C = "nearest", REF
    # -- K2 PREMISE ---------------------------------------------------------
    res["K2"] = {
        "cr_ratio": arm_stats[N]["rms_cr"] / arm_stats[C]["rms_cr"],
        "cb_ratio": arm_stats[N]["rms_cb"] / arm_stats[C]["rms_cb"],
        "luma_ratio": arm_stats[N]["rms_L"] / arm_stats[C]["rms_L"],
    }
    # -- K3 RATIO INVARIANCE ------------------------------------------------
    res["K3"] = {
        "rho_cr_ratio": arm_stats[N]["rho_cr"] / arm_stats[C]["rho_cr"],
        "rho_cb_ratio": arm_stats[N]["rho_cb"] / arm_stats[C]["rho_cb"],
    }
    # -- K4 STRUCTURE (luma is the null) ------------------------------------
    k4 = {}
    for lab, i in (("L", 0), ("cr", 1), ("cb", 2)):
        r, s = corr_slope(H[N][i], H[C][i], mask)
        k4[lab] = {"corr": r, "slope": s}
    k4["cr_rel"] = k4["cr"]["corr"] / k4["L"]["corr"]
    k4["cb_rel"] = k4["cb"]["corr"] / k4["L"]["corr"]
    res["K4"] = k4
    # -- K5 LATTICE ---------------------------------------------------------
    k5 = {}
    for lab, i in (("L", 0), ("cr", 1), ("cb", 2)):
        s = k4[lab]["slope"]
        k5[lab] = spectrum_stats(H[N][i] - s * H[C][i])
    res["K5"] = k5
    # -- K6 (b) vs (c) ------------------------------------------------------
    B = "bilinear"
    res["K6"] = {
        "rho_cr_bilinear_over_nearest": arm_stats[B]["rho_cr"] / arm_stats[N]["rho_cr"],
        "rho_cb_bilinear_over_nearest": arm_stats[B]["rho_cb"] / arm_stats[N]["rho_cb"],
        "slope_bilinear_on_catmull_cr": corr_slope(H[B][1], H[C][1], mask)[1],
        "slope_bilinear_on_catmull_cb": corr_slope(H[B][2], H[C][2], mask)[1],
        "slope_nearest_on_catmull_cr": k4["cr"]["slope"],
        "slope_nearest_on_catmull_cb": k4["cb"]["slope"],
    }

    # -- K3-CTRL: synthetic channel-INDEPENDENT blur; rho must HOLD ----------
    # Luma rms is reported at each point so the control can be CALIBRATED
    # against the real arm separation. Quoting a control at an arbitrary blur
    # that is 10x the effect under test is not a control.
    ctrl = {}
    for sg in (0.25, 0.5, 1.0, 2.0):
        blurred = gaussian_filter(ref_rgb, (sg, sg, 0))
        st, _ = stats(*fields(blurred), mask)
        ctrl[f"sigma_{sg}"] = {
            "rho_cr_ratio": st["rho_cr"] / arm_stats[C]["rho_cr"],
            "rho_cb_ratio": st["rho_cb"] / arm_stats[C]["rho_cb"],
            "rms_L_ratio": st["rms_L"] / arm_stats[C]["rms_L"]}
        del blurred
    res["K3_CTRL"] = ctrl

    # -- K3-POWER: shift RED ONLY; rho must RISE ----------------------------
    power = {}
    for dx in (0.3, 0.6):
        pert = ref_rgb.copy()
        pert[..., 0] = ndshift(pert[..., 0], (0.0, dx), order=3, mode="nearest")
        st, _ = stats(*fields(pert), mask)
        power[f"dx_{dx}"] = {
            "rho_cr_ratio": st["rho_cr"] / arm_stats[C]["rho_cr"],
            "rho_cb_ratio": st["rho_cb"] / arm_stats[C]["rho_cb"]}
        del pert
    res["K3_POWER"] = power

    # -- K7 MATCHED-LUMA SUBSTITUTION (bar in PRE-REGISTRATION-2-AMENDMENT,
    #    committed e96040d before this ran; POST-HOC relative to K1-K6) -------
    #
    # The orchestrator's reading literally asserts: `nearest` shows more fringe
    # ONLY because Catmull-Rom lowpasses it away. Then applying an equivalent
    # channel-INDEPENDENT lowpass to `nearest` must reproduce Catmull-Rom's
    # chroma. This is that substitution, done directly, instead of testing a
    # ratio's invariance.
    def match_blur(src_rgb, target_rms_L):
        """sigma of a channel-independent Gaussian matching target luma HP rms."""
        lo, hi = 0.0, 4.0
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            b = gaussian_filter(src_rgb, (mid, mid, 0)) if mid > 1e-6 else src_rgb
            v = float(np.sqrt(np.mean(hp(fields(b)[0])[mask] ** 2)))
            if v > target_rms_L:
                lo = mid
            else:
                hi = mid
        sg = 0.5 * (lo + hi)
        b = gaussian_filter(src_rgb, (sg, sg, 0))
        return sg, stats(*fields(b), mask)[0]

    k7 = {}
    for lab, src, tgt in (("nearest_to_catmull", N, C),      # the headline
                          ("catmull_to_bilinear", C, B)):    # the NULL
        src_rgb = ref_rgb if src == REF else load(src, x0, y0)[0]
        sg, st = match_blur(src_rgb, arm_stats[tgt]["rms_L"])
        k7[lab] = {
            "sigma_star": sg,
            "rms_L_after": st["rms_L"], "rms_L_target": arm_stats[tgt]["rms_L"],
            "rho7_cr": st["rms_cr"] / arm_stats[tgt]["rms_cr"],
            "rho7_cb": st["rms_cb"] / arm_stats[tgt]["rms_cb"]}
        print(f"  K7 {lab:22s} sigma*={sg:.4f} px  "
              f"rho7_cr={k7[lab]['rho7_cr']:.4f} rho7_cb={k7[lab]['rho7_cb']:.4f}",
              flush=True)
        del src_rgb
    res["K7"] = k7

    # -- robustness: the veil is low-frequency; sigma must not drive this ----
    rob = {}
    for sg in (3.0, 12.0):
        per = {}
        for a in ARMS:
            rgb = ref_rgb if a == REF else load(a, x0, y0)[0]
            per[a] = stats(*fields(rgb), mask, sigma=sg)[0]
            del rgb
        rob[f"sigma_{sg}"] = {
            "rho_cr_ratio": per[N]["rho_cr"] / per[C]["rho_cr"],
            "rho_cb_ratio": per[N]["rho_cb"] / per[C]["rho_cb"],
            "K2_cr_ratio": per[N]["rms_cr"] / per[C]["rms_cr"]}
        print(f"  robustness sigma={sg}: {rob[f'sigma_{sg}']}", flush=True)
    res["robustness"] = rob

    dump(f"e8_kernel_{tag}", res)
    print(json.dumps({k: res[k] for k in
                      ("K2", "K3", "K4", "K5", "K6", "K7", "K3_CTRL", "K3_POWER")},
                     indent=2))
    return res


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "auto"
    rmax = float(sys.argv[2]) if len(sys.argv) > 2 else None
    run(tag, rmax)

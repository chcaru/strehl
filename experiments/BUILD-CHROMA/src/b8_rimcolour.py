"""
b8_rimcolour.py -- what colour IS the rim, in words a person would use?

b7 walked the render ladder and found the rim is red-only at every rung,
including the shipped gallery JPEG (R/G +3.77%, B/G -0.04%). That is in tension
with the reported observation of a "pink-magenta" rim, because magenta is
red-and-blue against green and there is no blue here at all.

Rule 7 says the pictures are right. So this does not argue with the observation;
it goes and looks. It pulls the actual rim pixels out of the gallery JPEG,
reports the sRGB triplets a person is actually seeing, converts them to a hue
angle so the colour has a name rather than an adjective, and writes a
magnified crop to be viewed directly.

The hypothesis being tested is that "pink-magenta" and "red-only" are the same
observation described two ways: a red excess with no blue excess, sitting on a
slightly desaturated background, is PINK. Pink and magenta are adjacent words
but they make opposite predictions about blue, and blue is the channel that
discriminates the two mechanisms:

    lateral CA   eps_R = -704.5 ppm, eps_B = +68.4 ppm  (fact 1414)
                 -> red displaced ~10x more than blue -> red-only rim -> PINK
    axial CA     dB/dR = 0.60 on this stack             (measured here)
                 -> blue excess ~60% of red's           -> red+blue -> MAGENTA

So the blue channel at the rim is a clean, pre-registered discriminator between
the two, and it is worth stating the predictions before reading the number off.
"""
import os

import numpy as np

from common import OUT, dump
import b3_defects as b3
import b7_magenta as b7

GALLERY = r"C:\dev\strehl-out\gallery"
FIG = os.path.join(OUT, "fig")

# Measured here, on coffee-bean, by b2_analyse.
DR, DB = -0.8100, -0.4845


def hue_name(r, g, b):
    """Coarse hue name from an sRGB triplet, so the colour has a word."""
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn < 1e-6:
        return "neutral"
    if mx == r:
        h = 60.0 * (((g - b) / (mx - mn)) % 6)
    elif mx == g:
        h = 60.0 * ((b - r) / (mx - mn) + 2)
    else:
        h = 60.0 * ((r - g) / (mx - mn) + 4)
    sat = (mx - mn) / mx
    names = [(15, "red"), (45, "orange"), (75, "yellow"), (150, "green"),
             (195, "cyan"), (255, "blue"), (285, "violet"), (315, "magenta"),
             (345, "pink"), (360, "red")]
    nm = next(n for lim, n in names if h < lim)
    # pink is a desaturated / light red, magenta needs real blue
    if nm == "red" and sat < 0.45:
        nm = "pink"
    return f"{nm} (hue {h:.0f} deg, sat {sat:.2f})"


def run():
    import imageio.v3 as iio
    p = os.path.join(GALLERY, "coffee-bean.jpg")
    srgb8 = iio.imread(p)
    assert srgb8.dtype == np.uint8
    lin = b7.srgb_to_linear(srgb8[:, :, :3] / 255.0)
    h, w = lin.shape[:2]
    print(f"-- gallery {p} {srgb8.shape}")

    ys, xs, ny, nx = b3.silhouette_normals(lin, nsample=6000)
    d, prof = b3.normal_profiles(lin, ys, xs, ny, nx)   # (3, nd, npts)

    # Locate the rim by the same statistic b7 used -- the peak R/G excess
    # relative to the far background -- so that the colour is read at exactly
    # the offset the ladder measured, and not at some other feature.
    eps = 1e-9
    R, G, B = prof
    rg_p = R / np.maximum(G, eps)
    far = d >= 18
    rg_n = rg_p / np.maximum(rg_p[far].mean(0, keepdims=True), eps)
    curve = rg_n.mean(axis=1)
    kpk = int(np.argmax(np.where(d > 0, curve, -np.inf)))
    kbg = int(np.argmin(np.abs(d - 22.0)))
    print(f"   rim at normal offset {d[kpk]:+.1f} px "
          f"(R/G excess {(curve[kpk]-1)*100:+.2f}%), "
          f"background reference {d[kbg]:+.1f} px")

    def srgb_at(k):
        v = prof[:, k, :].mean(axis=1)            # linear light, per channel
        e = np.where(v <= 0.0031308, 12.92 * v,
                     1.055 * np.maximum(v, 0) ** (1 / 2.4) - 0.055)
        return v, np.clip(e * 255, 0, 255)

    v_rim, s_rim = srgb_at(kpk)
    v_bg, s_bg = srgb_at(kbg)

    # ---- measure where the defect is actually VISIBLE --------------------
    # The all-contour average above is honest but diluted: it pools every
    # boundary point, including the large fraction where the bean meets a dim
    # or cluttered surround and there is no visible fringe at all. The crop
    # shows the band is vivid only where the silhouette meets the bright white
    # background. That is not cherry-picking as long as the selection is made
    # on a variable that is not the colour being measured -- here, the
    # BRIGHTNESS of the far background, which is a contrast criterion and
    # carries no chroma information. Rule 7: the picture shows a saturated
    # pink band, so a statistic that reports saturation 0.05 is measuring the
    # wrong population, not refuting the picture.
    far_lum = prof[:, far, :].sum(axis=0).mean(axis=0)      # per boundary point
    hi = far_lum >= np.percentile(far_lum, 75)
    print(f"   high-contrast subset: {int(hi.sum())}/{hi.size} boundary points")

    def srgb_sub(k, sel):
        v = prof[:, k, sel].mean(axis=1)
        e = np.where(v <= 0.0031308, 12.92 * v,
                     1.055 * np.maximum(v, 0) ** (1 / 2.4) - 0.055)
        return v, np.clip(e * 255, 0, 255)

    rg_hi = (R[:, hi] / np.maximum(G[:, hi], eps))
    rg_hi = rg_hi / np.maximum(rg_hi[far].mean(0, keepdims=True), eps)
    k_hi = int(np.argmax(np.where(d > 0, rg_hi.mean(axis=1), -np.inf)))
    v_rh, s_rh = srgb_sub(k_hi, hi)
    v_bh, s_bh = srgb_sub(kbg, hi)
    rg_h = float(v_rh[0] / v_rh[1] / (v_bh[0] / v_bh[1]) - 1.0)
    bg_h = float(v_rh[2] / v_rh[1] / (v_bh[2] / v_bh[1]) - 1.0)
    print(f"   HIGH-CONTRAST rim at {d[k_hi]:+.1f} px: "
          f"sRGB8 R{s_rh[0]:6.1f} G{s_rh[1]:6.1f} B{s_rh[2]:6.1f} "
          f"-> {hue_name(*s_rh)}")
    print(f"   HIGH-CONTRAST  R/G {rg_h*100:+.2f}%   B/G {bg_h*100:+.2f}%")

    # ---- the alternative hypothesis, tested rather than assumed ----------
    # Before concluding "not axial CA, look elsewhere", the obvious competing
    # mechanism has to be excluded: the rim may not be a chromatic effect at
    # all. If signal from the SUBJECT leaks outward across the silhouette --
    # a contamination or halo mechanism, achromatic in itself -- then the rim
    # is simply background with a little bean mixed in, and it inherits the
    # bean's colour. The bean is brown: red-rich, blue-poor. That produces
    # R up, G down, B down further, which is what was just measured.
    #
    # The test is falsifiable. Fit  rim = (1-f)*background + f*subject
    # INDEPENDENTLY IN EACH CHANNEL, in linear light. A mixing mechanism is
    # achromatic in f, so the three channels must return the SAME f. A
    # chromatic mechanism has no reason to.
    k_in = int(np.argmin(np.abs(d - (-18.0))))          # well inside the subject
    v_sub, _ = srgb_sub(k_in, hi)
    f_ch = (v_rh - v_bh) / np.where(np.abs(v_sub - v_bh) > 1e-12,
                                    v_sub - v_bh, np.nan)
    print(f"   subject-mixing test: implied f per channel "
          f"R {f_ch[0]:.3f}  G {f_ch[1]:.3f}  B {f_ch[2]:.3f}"
          f"   spread {np.nanmax(f_ch)-np.nanmin(f_ch):.3f}")

    res = {
        "rim_offset_px": float(d[kpk]),
        "bg_offset_px": float(d[kbg]),
        "rim_srgb8": [float(x) for x in s_rim],
        "bg_srgb8": [float(x) for x in s_bg],
        "rim_hue": hue_name(*s_rim),
        "bg_hue": hue_name(*s_bg),
        "rim_minus_bg_srgb8": [float(a - b_) for a, b_ in zip(s_rim, s_bg)],
        "high_contrast": {
            "n_points": int(hi.sum()),
            "rim_offset_px": float(d[k_hi]),
            "rim_srgb8": [float(x) for x in s_rh],
            "bg_srgb8": [float(x) for x in s_bh],
            "rim_hue": hue_name(*s_rh),
            "rg_excess": rg_h,
            "bg_excess": bg_h,
            "axial_predicted_bg_excess": rg_h * (DB / DR),
            "lateral_predicted_bg_excess": rg_h * 68.4 / 704.5,
            "subject_mixing_f_per_channel": [float(x) for x in f_ch],
            "subject_mixing_f_spread": float(np.nanmax(f_ch) - np.nanmin(f_ch)),
            "subject_srgb8": [float(x) for x in srgb_sub(k_in, hi)[1]],
        },
    }
    print(f"   rim sRGB8  R{s_rim[0]:6.1f} G{s_rim[1]:6.1f} B{s_rim[2]:6.1f}"
          f"   -> {res['rim_hue']}")
    print(f"   bg  sRGB8  R{s_bg[0]:6.1f} G{s_bg[1]:6.1f} B{s_bg[2]:6.1f}"
          f"   -> {res['bg_hue']}")
    print(f"   rim - bg   R{res['rim_minus_bg_srgb8'][0]:+6.1f} "
          f"G{res['rim_minus_bg_srgb8'][1]:+6.1f} "
          f"B{res['rim_minus_bg_srgb8'][2]:+6.1f}")

    # ---- the pre-registered discriminator -------------------------------
    rg = float(v_rim[0] / v_rim[1] / (v_bg[0] / v_bg[1]) - 1.0)
    bg_ = float(v_rim[2] / v_rim[1] / (v_bg[2] / v_bg[1]) - 1.0)
    pred_axial_bg = rg * (DB / DR)
    res["discriminator"] = {
        "measured_rg_excess": rg,
        "measured_bg_excess": bg_,
        "axial_predicted_bg_excess": pred_axial_bg,
        "axial_prediction_ratio_dB_over_dR": DB / DR,
        "lateral_predicted_bg_over_rg": 68.4 / 704.5,
        "lateral_predicted_bg_excess": rg * 68.4 / 704.5,
    }
    print(f"\n   measured   R/G excess {rg*100:+.2f}%   B/G excess {bg_*100:+.2f}%")
    print(f"   axial CA predicts B/G {pred_axial_bg*100:+.2f}% "
          f"(= R/G x dB/dR = x{DB/DR:.2f})")
    print(f"   lateral CA predicts B/G {rg*68.4/704.5*100:+.2f}% "
          f"(= R/G x eps_B/eps_R = x{68.4/704.5:.3f})")

    # ---- go and look at it ----------------------------------------------
    # Centre the crop on an ACTUAL boundary point. An early version used the
    # median of the contour coordinates, which is the centroid of a closed
    # contour -- i.e. the middle of the subject, nowhere near the rim -- and
    # produced a crop of bean texture that showed nothing. Pick the boundary
    # sample whose outward normal is most horizontal, so the rim runs roughly
    # vertically through the crop and is easy to read.
    j = int(np.argmax(np.abs(nx)))
    yc, xc = int(ys[j]), int(xs[j])
    y0, x0 = max(0, yc - 60), max(0, xc - 100)
    crop = srgb8[y0:y0 + 120, x0:x0 + 200, :3]
    crop = np.repeat(np.repeat(crop, 4, axis=0), 4, axis=1)
    os.makedirs(FIG, exist_ok=True)
    outp = os.path.join(FIG, "coffee-bean-rim-4x.png")
    iio.imwrite(outp, crop)
    print(f"   -> {outp}  (4x, boundary point y={yc} x={xc})")
    res["crop"] = outp
    res["crop_centre"] = [yc, xc]
    return res


if __name__ == "__main__":
    o = run()
    dump("b8_rimcolour", o)

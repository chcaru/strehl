"""Shared library for the head-to-head.

TONE INVERSION.  strehl's shipped master is a VIEWING render:
    lin_sRGB -> tone gain g(luma) -> gamut_map -> srgb_encode -> s_curve(0.55) -> u16
(crates/strehl-cli/src/image_out.rs::develop_pixel).  Every stage is monotone
and invertible except gamut_map, which is the identity on in-gamut pixels.  We
invert the chain exactly so that microcontrast is compared in LINEAR light and
not in strehl's S-curve.

GEOMETRY.  Nothing is ever resampled.  We only MEASURE the similarity relating
the two rasters and use it to pick corresponding INTEGER pixel windows.
"""
import numpy as np, tifffile

PRIOR  = r"C:\dev\macro\out\coffee-bean\stack.tif"
STREHL = r"C:\dev\strehl-out\SHIP-V2\coffee-bean--SHIP-V2.tiff"

# from the render log / TIFF ImageDescription of coffee-bean--SHIP-V2.tiff
TONE_BLACK    = 0.017183
TONE_WHITE    = 0.998214
TONE_CONTRAST = 0.550
TONE_TOE      = 0.004

def s_curve(x, k=TONE_CONTRAST):
    s = x * x * (3.0 - 2.0 * x)
    return x + (s - x) * k

def inv_s_curve(y, k=TONE_CONTRAST):
    x = np.linspace(0.0, 1.0, 65536, dtype=np.float64)
    return np.interp(np.clip(y, 0, 1), s_curve(x, k), x)

def srgb_encode(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1 / 2.4) - 0.055)

def srgb_decode(v):
    v = np.clip(v, 0, 1)
    return np.where(v <= 0.04045, v / 12.92, np.power((v + 0.055) / 1.055, 2.4))

def tone_gain(L):
    """crates/strehl-cli/src/image_out.rs::Tone::gain, vectorised."""
    L = np.maximum(np.asarray(L, np.float64), 0.0)
    s = 1.0 / (TONE_WHITE - TONE_BLACK)
    y = (L - TONE_BLACK) * s
    soft = 0.5 * (y + np.sqrt(y * y + TONE_TOE * TONE_TOE))
    with np.errstate(divide="ignore", invalid="ignore"):
        g = np.where(L > 0, soft / np.where(L > 0, L, 1.0), 0.0)
    return np.minimum(g, s)

_LT = None
def inv_tone_luma(Lp):
    """Invert L' = L * gain(L).  Monotone, so a LUT + interp is exact enough."""
    global _LT
    if _LT is None:
        L = np.concatenate([np.linspace(0, 0.05, 200001), np.linspace(0.05, 4.0, 200001)[1:]])
        _LT = (L * tone_gain(L), L)
    return np.interp(np.clip(Lp, 0, None), _LT[0], _LT[1])

def luma709(rgb):
    return 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]

def strehl_to_linear(u16_rgb):
    """u16 sRGB viewing render -> linear sRGB (BT.709 primaries), tone removed."""
    d = np.asarray(u16_rgb, np.float64) / 65535.0
    d = inv_s_curve(d)                 # undo display-space S-curve
    v = srgb_decode(d)                 # undo sRGB transfer -> post-tone linear
    Lp = luma709(v)                    # post-tone luminance
    L  = inv_tone_luma(Lp)             # pre-tone luminance
    g  = np.where(L > 0, Lp / np.maximum(L, 1e-12), 1.0)
    g  = np.where(g > 1e-9, g, 1.0)
    return v / g[..., None]            # undo the single luminance-derived gain

# ---- geometry, measured by geom.py (MEASURED, not assumed) -------------------
SCALE = 1.035063
ROT   = np.radians(0.03148)
TX, TY = 14.78, 5.06
PC = (7008 / 2.0, 4672 / 2.0)      # prior centre (x, y)

def prior_to_strehl(x, y):
    dx = x - PC[0]; dy = y - PC[1]
    c, s = np.cos(ROT) * SCALE, np.sin(ROT) * SCALE
    return (c * dx - s * dy + PC[0] + TX, s * dx + c * dy + PC[1] + TY)

def open_arms():
    return tifffile.memmap(PRIOR, mode="r"), tifffile.memmap(STREHL, mode="r")

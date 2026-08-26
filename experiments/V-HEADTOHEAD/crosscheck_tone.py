"""RE-CHOOSE, DON'T RE-COMPUTE (rule 24).

The main comparison inverts strehl's tone rendering to reach linear light.  If
that inversion is wrong, every contrast number is wrong.  So do it the OTHER way
round as well: take the prior arm (already linear), put it on strehl's linear
scale with the single measured gain, then push it FORWARD through strehl's exact
tone chain (black/white placement -> sRGB transfer -> 0.55 S-curve) and compare
the two arms in strehl's DISPLAY space instead.

If the contrast ratio is the same both ways, it is a property of the images.  If
it flips, it is a property of my transform.
"""
import numpy as np, h2h, arms, spec, tifffile

GAIN = 1.4157   # prior_linear = GAIN * strehl_linear, fitted in verify_tone.py

def forward_tone_gray(lin):
    """strehl's develop_pixel restricted to a GREY approximation: the tone gain is
    derived from luminance, and on a grey ramp luminance == the channel value."""
    g = h2h.tone_gain(lin)
    v = np.clip(lin * g, 0, 1)
    return h2h.s_curve(h2h.srgb_encode(v))

def strehl_display_arm():
    a = tifffile.memmap(h2h.STREHL, mode="r")
    g = np.ascontiguousarray(a[:, :, 1]).astype(np.float32) / 65535.0
    clip = np.zeros(g.shape, bool)
    for y0 in range(0, a.shape[0], 256):
        y1 = min(y0+256, a.shape[0])
        clip[y0:y1] = np.asarray(a[y0:y1], np.uint16).max(axis=2) >= 65535
    del a
    return arms.Arm("strehl-display", g, h2h.prior_to_strehl, h2h.SCALE, clip)

def prior_pushed_arm():
    P = arms.prior_arm()
    g = forward_tone_gray(P.g.astype(np.float64) / GAIN).astype(np.float32)
    return arms.Arm("prior->strehl-display", g, lambda x, y: (x, y), 1.0, P.clip)

if __name__ == "__main__":
    A = prior_pushed_arm(); B = strehl_display_arm()
    spec.compare(A, B, spec.DETAIL_ROIS, 384,
        "CROSS-CHECK in strehl DISPLAY space: prior pushed forward vs strehl as shipped",
        "prior->disp", "strehl-disp")
    spec.compare(A, B, spec.FLAT_ROIS, 384,
        "CROSS-CHECK in strehl DISPLAY space, FLAT ROIs", "prior->disp", "strehl-disp")

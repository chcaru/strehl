# ============================================================================
# REJECTED INSTRUMENT - DO NOT USE ITS OUTPUT. Kept as the audit trail for
# BUILD-HIGHLIGHT.md 13.5, which reports the axial-CA hypothesis as UNTESTED.
#
# Two normalisations were tried and BOTH are confounded on specular-on-dark:
#   v1  gradient energy / channel MEAN      -> red -85% vs green.  Rejected:
#       conflates level with sharpness on a near-black subject, and disagrees
#       with M107's established 8.96-14.74% by an order of magnitude.
#   v2  gradient energy / channel VARIANCE  -> red +42% vs green.  Rejected:
#       scale-invariant and calibrated (below), but a high-frequency FRACTION
#       is inflated by noise, and red has the lowest SNR on this subject. It
#       cannot separate "red is sharper" from "red is noisier".
#
# The two answers have OPPOSITE SIGN. Reporting either would be choosing the
# one that suited the hypothesis. The discriminating experiment is a
# per-channel focus-index offset (M107 fact 1417), which is estimator work.
# ============================================================================
# CORRECTED. The previous version normalised gradient energy by the channel MEAN,
# which on a near-black subject conflates level with sharpness and returned -85%
# against M107's 8.96-14.74%. A ratio that disagrees with the established
# measurement by an order of magnitude is measuring something else.
#
# HF fraction = gradient energy / variance is scale-invariant: both numerator and
# denominator go as amplitude squared, so it reports WHAT FRACTION OF A CHANNEL'S
# OWN STRUCTURE sits at high frequency -- which is what "is red blurrier than
# green" actually asks. Calibrated below on a planted blur.
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter
def hf_frac(p):
    gy=np.diff(p,axis=0); gx=np.diff(p,axis=1)
    return float(((gy*gy).mean()+(gx*gx).mean())/max(float(p.var()),1e-12))

rng=np.random.default_rng(3); t=rng.normal(0,1,(700,700)).astype(np.float32)
base=hf_frac(t)
for s in (0.3,0.5,0.8):
    print("  CALIBRATION: sigma=%.1f blur -> HF fraction %.4f of unblurred (must be <1)"%(s, hf_frac(gaussian_filter(t,s))/base))
print()
for nm,path in [("coffee CA-ON ","C:/dev/strehl-out/BUILD-HIGHLIGHT/ladder/K3-stack-demo.tif"),
                ("coffee CA-OFF","C:/dev/strehl-out/BUILD-HIGHLIGHT/ladder/K5-stack-caoff.tif"),
                ("flowerbud ON ","C:/dev/strehl-out/BUILD-HIGHLIGHT/flowerbud/M1-caon-kneeoff.tif")]:
    img=tifffile.imread(path).astype(np.float32)/65535.0
    h=[hf_frac(img[...,c]) for c in range(3)]
    print("%s  HF fraction  R=%.4f G=%.4f B=%.4f   red vs green %+.2f%%   blue vs green %+.2f%%"
          %(nm,h[0],h[1],h[2],100*(h[0]/h[1]-1),100*(h[2]/h[1]-1)))
    del img


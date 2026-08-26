"""V-HULLCOST signal-vs-noise discriminator.

Two interleaved half-stacks (even-indexed frames, odd-indexed frames) of the
SAME subject. Each half spans the whole focus bracket, so the SCENE they
reconstruct is the same; only the NOISE realisation is independent.

For a high-pass field X:  corr(X_even, X_odd) ~ signal_power/(signal+noise).
  r ~ 1  -> scene-locked  = DETAIL
  r ~ 0  -> uncorrelated  = NOISE

r_img : correlation of the merged image's own high-pass content  (CONTROL:
        must be high, else the two renders are misregistered and the test
        is void)
r_D   : correlation of D = unclamped - clamped, the content the CLAMP REMOVES
"""
import sys, json
import numpy as np, tifffile
from scipy.ndimage import gaussian_filter

def g(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, "%s is %s" % (path, a.dtype)
    return a[:, :, 1].astype(np.float32)

def hp(x, s=1.0):
    return x - gaussian_filter(x, s, mode="reflect")

def r(a, b):
    a = a.ravel().astype(np.float64); b = b.ravel().astype(np.float64)
    a = a - a.mean(); b = b - b.mean()
    return float((a @ b) / np.sqrt((a @ a) * (b @ b)))

ce, ue, co, uo = (g(p) for p in sys.argv[1:5])
out = {}
out["r_img_control_hp"] = r(hp(ce), hp(co))
out["r_img_control_raw"] = r(ce, co)
De, Do = ue - ce, uo - co
out["De_rms_DN"] = float(np.sqrt((De.astype(np.float64)**2).mean()))
out["Do_rms_DN"] = float(np.sqrt((Do.astype(np.float64)**2).mean()))
out["r_D_removed_content"] = r(De, Do)
# restrict to where the clamp actually bit in BOTH halves
m = (np.abs(De) >= 8) & (np.abs(Do) >= 8)
out["both_bit_count"] = int(m.sum())
if m.sum() > 1000:
    out["r_D_where_both_bit"] = r(De[m], Do[m])
    out["r_img_hp_where_both_bit"] = r(hp(ce)[m], hp(co)[m])
# noise floor reference: the half-to-half difference of the clamped renders
N = ce - co
out["halfdiff_rms_DN"] = float(np.sqrt((N.astype(np.float64)**2).mean()))
out["hp_halfdiff_rms_DN"] = float(np.sqrt((hp(N).astype(np.float64)**2).mean()))
print(json.dumps(out, indent=1))

"""M34 step 1: build four candidate confidence channels on the same pixels.

Question 65 asks what a shippable confidence output should contain, and proposes
a small vector: predicted sigma of the merged estimate (a), the acceptance-set
width / n_eff (b), and the sub-frame peak offset (c).  M33 measured (c).  This
milestone asks the prior question that decides M18's output contract:

    are these channels finding DIFFERENT bad pixels, or the same ones?

If they rank pixels the same way, the vector is decoration and one number ships.
If they flag disjoint populations, each earns its place -- and the union is the
honest "do not trust this pixel" mask, which is larger than any single channel.

Everything is on the SAME pixels: M32's raw cube (53 frames, x2 sampling) and
M33's dense focus volume decimated x2 agree pixel-for-pixel -- identical crop
(CY,CX,H = 1172,1757,512), identical green sublattice, identical black level.
Script 01 asserts that rather than trusting it.

All four channels are oriented as BADNESS: larger = less trustworthy.

PRE-REGISTERED (written before any of this was run):

  P1  C1 (photon noise) vs C3 (sampling deficit) worst-5% Jaccard < 0.15.
      They measure orthogonal failure modes -- too few photons versus the focus
      peak falling between two frames -- so they should overlap near the 0.0256
      chance level for two independent 5% sets.
  P2  C2 (posterior perplexity) is DEGENERATE: within 1% of 1.0 for >95% of
      pixels.  This is a forward prediction from fact 261, on a statistic fact
      261 did not report.  If it fails, fact 261 is wrong on this crop and M32
      needs revisiting.
  P3  Reliability ceiling (self-overlap of a channel across two independent
      noise realisations) > 0.60 Jaccard for C1 and C3, so that the cross-channel
      numbers are being read against a real ceiling and not against estimator
      noise.
  P4  Union of the four worst-5% sets covers > 12% of pixels (20% if perfectly
      disjoint, 5% if identical).
  P5  C4 (clip/boundary flags) fires on < 5% of pixels.  M30 measured 0.075%
      clipping at gathered frames; the boundary term is the unknown.
"""
import numpy as np, os, json

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "..", "out")
CACHE = os.path.join(OUT, "cache")
M32 = os.path.join(HERE, "..", "..", "m32-posterior", "out", "cache", "raw.npy")
M33 = os.path.join(HERE, "..", "..", "m33-subframe-offset", "out", "cache", "dense_focus.npy")

ISO, G, RN_E = 50, 50 / 436.8, 4.20        # M4
WHITE = 15360 - 512                        # camera_white_level_per_channel, above black

raw = np.load(M32, mmap_mode="r")          # (53, 1024, 1024) signal in DN above black
dense = np.load(M33, mmap_mode="r")        # (105, 1024, 1024) focus response
foc = np.ascontiguousarray(dense[::2])     # the operational x2 focus volume
n, HH, WW = foc.shape
assert raw.shape == foc.shape, (raw.shape, foc.shape)
print(f"raw {raw.shape}  focus {foc.shape}")

# --- consistency check: the two caches must describe the same pixels ---------
# The focus response is a Sobel magnitude of the raw frame, so bright textured
# regions must be bright in both.  A rank correlation near zero would mean the
# crops are misaligned and everything downstream is meaningless.
from scipy.stats import spearmanr
sub = (slice(None, None, 8), slice(None, None, 8))
rho_align = spearmanr(np.asarray(raw[0])[sub].ravel(), foc[0][sub].ravel()).statistic
print(f"cache alignment check: spearman(raw[0], focus[0]) = {rho_align:.4f}")
assert rho_align > 0.3, "caches are not the same pixels"

# --- focus-response noise, model-free (M32's validated method) ---------------
# Second differences along k on the defocused tail are dominated by noise, not
# by curvature, because the tail is flat.  var(second difference) = 6 sigma^2.
tail = np.concatenate([foc[:6], foc[-6:]], 0)
d2 = tail[2:] - 2 * tail[1:-1] + tail[:-2]
sigma_f = np.sqrt(np.maximum(d2.var(0), 1e-12) / 6.0).astype(np.float32)
print(f"sigma_f  median {np.median(sigma_f):.4f}  p01 {np.percentile(sigma_f,1):.4f}"
      f"  p99 {np.percentile(sigma_f,99):.4f}")

kmax = foc.argmax(0)
fmax = foc.max(0)
yy, xx = np.mgrid[0:HH, 0:WW]

# --- C2: posterior perplexity ------------------------------------------------
# Gaussian likelihood in focus-response space: a frame is a plausible peak in
# proportion to exp(-(fmax - f_k)^2 / 2 sigma_f^2).
d = (fmax[None] - foc) / np.maximum(sigma_f, 1e-6)[None]
logp = -0.5 * d.astype(np.float64) ** 2
logp -= logp.max(0)
p = np.exp(logp)
p /= p.sum(0)
perplexity = np.exp(-(p * np.log(np.maximum(p, 1e-300))).sum(0)).astype(np.float32)
del d, logp
print(f"C2 perplexity  median {np.median(perplexity):.6f}"
      f"  p99 {np.percentile(perplexity,99):.6f}  max {perplexity.max():.4f}")
frac_deg = float((perplexity < 1.01).mean())
print(f"   P2 check: fraction within 1% of 1.0 = {frac_deg:.4%}")

# --- C1: predicted sigma of the merged estimate ------------------------------
# Acceptance set = frames within 1 sigma_f of the peak.  The merge averages them,
# so its variance is sum(sigma_k^2)/|A|^2 with sigma_k from the M4 model at that
# frame's own signal level.  Reported as inverse output SNR: badness = sigma/S.
acc = (fmax[None] - foc) <= sigma_f[None]
nacc = acc.sum(0).astype(np.float32)
sig_k = np.asarray(raw, np.float32)
var_k = G * np.clip(sig_k, 0, None) + (RN_E * G) ** 2
var_merge = (var_k * acc).sum(0) / np.maximum(nacc, 1) ** 2
S_merge = (sig_k * acc).sum(0) / np.maximum(nacc, 1)
C1 = np.sqrt(var_merge) / np.maximum(S_merge, 1e-3)
print(f"C1 = sigma/S   median {np.median(C1):.5f}  p95 {np.percentile(C1,95):.5f}")
print(f"   acceptance set size: median {np.median(nacc):.1f}  p99 {np.percentile(nacc,99):.1f}")

# --- C3: sub-frame deficit, M33's log-baseline fit ---------------------------
# Baseline = the defocused floor (min along k); log is not shift-invariant, so
# it has to come off before the fit.  Fact 272.
base = foc.min(0)
km = np.clip(kmax, 1, n - 2)
a0 = np.log(np.maximum(foc[km, yy, xx] - base, 1e-6))
am_ = np.log(np.maximum(foc[km - 1, yy, xx] - base, 1e-6))
ap = np.log(np.maximum(foc[km + 1, yy, xx] - base, 1e-6))
denom = am_ - 2 * a0 + ap
xstar = np.where(np.abs(denom) > 1e-9, 0.5 * (am_ - ap) / np.where(np.abs(denom) > 1e-9, denom, 1), 0.0)
xstar = np.clip(xstar, -1, 1)
peak_log = a0 - 0.25 * (ap - am_) * xstar          # vertex value in log space
C3 = 1.0 - np.exp(np.minimum(a0 - peak_log, 0.0))  # fractional deficit, in [0,1)
C3 = np.clip(C3, 0, 1).astype(np.float32)
print(f"C3 deficit     median {np.median(C3):.5f}  mean {C3.mean():.5f}"
      f"  p95 {np.percentile(C3,95):.5f}")

# --- C4: clip / boundary flags ----------------------------------------------
clipped = (np.asarray(raw, np.float32) >= WHITE * 0.995).any(0)
boundary = (kmax <= 1) | (kmax >= n - 2)
C4 = (clipped | boundary).astype(np.float32)
print(f"C4 flags       clipped {clipped.mean():.4%}  boundary {boundary.mean():.4%}"
      f"  union {C4.mean():.4%}")

np.save(os.path.join(CACHE, "C1.npy"), C1)
np.save(os.path.join(CACHE, "C2.npy"), perplexity)
np.save(os.path.join(CACHE, "C3.npy"), C3)
np.save(os.path.join(CACHE, "C4.npy"), C4)
np.save(os.path.join(CACHE, "sigma_f.npy"), sigma_f)
np.save(os.path.join(CACHE, "kmax.npy"), kmax.astype(np.int16))

json.dump(dict(
    n_frames=int(n), crop=[int(HH), int(WW)], iso=ISO, g=G, rn_e=RN_E,
    cache_alignment_spearman=float(rho_align),
    sigma_f=dict(median=float(np.median(sigma_f)), p01=float(np.percentile(sigma_f, 1)),
                 p99=float(np.percentile(sigma_f, 99))),
    C1=dict(median=float(np.median(C1)), p95=float(np.percentile(C1, 95)),
            acc_median=float(np.median(nacc)), acc_p99=float(np.percentile(nacc, 99))),
    C2=dict(median=float(np.median(perplexity)), p99=float(np.percentile(perplexity, 99)),
            max=float(perplexity.max()), frac_within_1pct_of_1=frac_deg),
    C3=dict(median=float(np.median(C3)), mean=float(C3.mean()), p95=float(np.percentile(C3, 95))),
    C4=dict(clipped=float(clipped.mean()), boundary=float(boundary.mean()), union=float(C4.mean())),
    P2_degenerate=bool(frac_deg > 0.95),
    P5_c4_under_5pct=bool(C4.mean() < 0.05),
), open(os.path.join(OUT, "01-channels.json"), "w"), indent=1)
print("wrote 01-channels.json")

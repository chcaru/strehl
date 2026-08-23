"""M39 verification, script 01: the algebra of the noise correction, from scratch.

Independently derives (by Monte Carlo) the expected noise contribution to
mean(dx^2 + dy^2) for forward differences dx = v[i+1]-v[i], dy = v[i+w]-v[i]
under additive independent per-pixel noise of variance sigma_i^2.

Claim C under test: the contribution at pixel i is exactly
    2*sigma_i^2 + sigma_{i+1}^2 + sigma_{i+w}^2
Rival hypotheses are tested against the same data so the test can FAIL.
"""
import numpy as np

rng = np.random.default_rng(20260823)

W, H = 9, 7          # small so edge structure matters
TRIALS = 4_000_000

# A deliberately NON-uniform sigma field: a uniform field cannot distinguish
# any coefficient set that sums to 4, which is the whole point.
sigma = (1.0 + 4.0 * rng.random((H, W))).astype(np.float64)
# An arbitrary smooth signal, present to prove the cross term vanishes.
yy, xx = np.mgrid[0:H, 0:W]
signal = 100.0 + 7.0 * np.sin(0.7 * xx) * np.cos(0.4 * yy) + 3.0 * xx

def interior_sum(a):
    """Sum over the same index set the Rust code walks: y<H-1, x<W-1."""
    return a[:H-1, :W-1]

# ---- Monte Carlo: E[dx^2+dy^2] over the interior index set -----------------
acc = np.zeros((H-1, W-1))
BATCH = 20000
done = 0
while done < TRIALS:
    n = min(BATCH, TRIALS - done)
    v = signal[None, :, :] + rng.standard_normal((n, H, W)) * sigma[None, :, :]
    dx = v[:, :, 1:] - v[:, :, :-1]      # (n,H,W-1)
    dy = v[:, 1:, :] - v[:, :-1, :]      # (n,H-1,W)
    acc += (dx[:, :H-1, :] ** 2 + dy[:, :, :W-1] ** 2).sum(axis=0)
    done += n
mc = acc / TRIALS

# ---- the signal-only part (noise removed) ---------------------------------
sdx = signal[:, 1:] - signal[:, :-1]
sdy = signal[1:, :] - signal[:-1, :]
sig_part = sdx[:H-1, :] ** 2 + sdy[:, :W-1] ** 2

# ---- candidate noise models ------------------------------------------------
s2 = sigma ** 2
cands = {
    "CLAIM C  2*s_i^2 + s_{i+1}^2 + s_{i+w}^2":
        2 * s2[:H-1, :W-1] + s2[:H-1, 1:] + s2[1:, :W-1],
    "rival A  1*s_i^2 + s_{i+1}^2 + s_{i+w}^2":
        1 * s2[:H-1, :W-1] + s2[:H-1, 1:] + s2[1:, :W-1],
    "rival B  4*s_i^2 (all weight on i)":
        4 * s2[:H-1, :W-1],
    "rival C  2*(s_{i+1}^2 + s_{i+w}^2)":
        2 * (s2[:H-1, 1:] + s2[1:, :W-1]),
}

print("MC trials:", TRIALS)
print(f"{'model':46s} {'max |per-px err|':>17s} {'rel err on mean':>16s}")
mc_noise = mc - sig_part
for name, pred in cands.items():
    err = np.abs(mc_noise - pred)
    rel = abs(mc_noise.mean() - pred.mean()) / pred.mean()
    print(f"{name:46s} {err.max():17.5f} {rel:16.3e}")

# Scale of the quantity, so "small error" is meaningful.
print()
print("mean noise contribution (MC)   :", f"{mc_noise.mean():.6f}")
print("mean noise contribution CLAIM C:", f"{cands['CLAIM C  2*s_i^2 + s_{i+1}^2 + s_{i+w}^2'].mean():.6f}")
print("MC standard error on that mean :",
      f"{(mc_noise.std() / np.sqrt(TRIALS)):.6f}  (rough)")

# ---- and the identity that makes the hand calculation work -----------------
# If sigma^2 is affine in signal S, mean_i(sigma_i^2) = sigma^2(mean S) EXACTLY.
g, rd2 = 0.36630, 1.53846 ** 2
S = rng.random(50000) * 800
lhs = (g * S + rd2).mean()
rhs = g * S.mean() + rd2
print()
print("affine-variance identity: mean(sigma^2(S)) =", f"{lhs:.8f}",
      " sigma^2(mean S) =", f"{rhs:.8f}", " equal:", np.isclose(lhs, rhs))

"""Why does tune_uniq's fine_field disagree with measure_pair on C2?

fine_field re-implements measure_pair's stages so a threshold can be applied
after the fact.  A re-implementation that silently disagrees with the thing it
re-implements is worse than no measurement at all, so this pins down where the
two diverge before any tuning number is believed.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghostlib as G
import controls as C
import tune_uniq as T

ga = G.decode_plane(C.REF_A)["g"]
k, r2 = G.photon_transfer(ga)
rng = np.random.default_rng(7)
gb = C.add_shot_noise(C.warp_similarity(ga, **C.TRUE), k, r2, rng)

r = G.measure_pair(ga, gb, noise=(k, r2))
print("measure_pair ok=%s reason=%r census=%s" % (r.ok, r.reason,
                                                  r.census() if r.n_fine_total else {}))
print("  coarse: %d tiles, %d used" % (r.n_coarse, r.n_coarse_used))
s = G.resid_summary(r)
print("measure_pair :", {kk: round(v, 4) if isinstance(v, float) else v
                         for kk, v in s.items()})
if r.sim is not None:
    print("  sim  u=%.6g%+.6gj  b=%.4f%+.4fj  used=%d  mad=%.4f"
          % (r.sim.u.real, r.sim.u.imag, r.sim.b.real, r.sim.b.imag,
             r.sim.n_used, r.sim.mad))

resid, base, un, tot = T.fine_field(ga, gb, (k, r2))
m = np.abs(resid[base]) * 2
print("fine_field   : n=%d p50=%.4f p90=%.4f p99=%.4f max=%.4f"
      % (m.size, *[np.percentile(m, p) for p in (50, 90, 99)], m.max()))
big = np.nonzero(base & (np.abs(resid) * 2 > 2.0))[0]
print("  tiles over 2 sensor px:", big.size)
if big.size:
    print("  their uniq:", np.round(un[big][:20], 3))
    print("  their resid (plane px):", np.round(resid[big][:10], 2))

# The one structural difference between the two: measure_pair refines the COARSE
# displacements before fitting the similarity, fine_field does not.  If that is
# the cause, the two similarity fits will differ.
h, w = ga.shape
cy0, cx0 = (h - 1) / 2.0, (w - 1) / 2.0
oc = G.tile_origins((h, w), G.TILE_COARSE, G.STRIDE_COARSE, G.MAX_SHIFT_COARSE)
A = G.gather_tiles(ga, oc, G.TILE_COARSE)
B = G.gather_tiles(gb, oc, G.TILE_COARSE)
hfa, sa = G.hf_modulation(A, k, r2)
hfb, sb = G.hf_modulation(B, k, r2)
fok = ((hfa >= G.HF_SIG_MIN_REL * sa) & (hfb >= G.HF_SIG_MIN_REL * sb)
       & (np.abs(np.log(np.maximum(hfa, 1e-12) / np.maximum(hfb, 1e-12))) <= G.FOCUS_MATCH_MAX_LN))
dC, rhoC, edC, unC = G.zncc_shift(A, B, G.MAX_SHIFT_COARSE)
ok = fok & (rhoC >= G.RHO_FLOOR) & (unC >= 0.15) & ~edC & np.isfinite(dC).all(1)
pc = ((oc[:, 1] + G.TILE_COARSE / 2 - cx0) + 1j * (oc[:, 0] + G.TILE_COARSE / 2 - cy0))[ok]
s_raw = G.fit_similarity(pc, dC[ok, 1] + 1j * dC[ok, 0], rhoC[ok])
dR = G.refine_shift(A[ok], B[ok], dC[ok], usfac=G.USFAC)
s_ref = G.fit_similarity(pc, dR[:, 1] + 1j * dR[:, 0], rhoC[ok])
exp_u = C.TRUE["s"] * np.exp(1j * C.TRUE["rot"]) - 1.0
print("\nexpected     u=%.6g%+.6gj  b=%+.4f%+.4fj"
      % (exp_u.real, exp_u.imag, C.TRUE["tx"], C.TRUE["ty"]))
print("coarse RAW   u=%.6g%+.6gj  b=%+.4f%+.4fj  used=%d/%d"
      % (s_raw.u.real, s_raw.u.imag, s_raw.b.real, s_raw.b.imag, s_raw.n_used, int(ok.sum())))
print("coarse REFIN u=%.6g%+.6gj  b=%+.4f%+.4fj  used=%d/%d"
      % (s_ref.u.real, s_ref.u.imag, s_ref.b.real, s_ref.b.imag, s_ref.n_used, int(ok.sum())))
corner = (w / 2) + 1j * (h / 2)
print("prediction difference at the frame corner: %.3f plane px"
      % abs(s_raw.predict(np.array([corner]))[0] - s_ref.predict(np.array([corner]))[0]))

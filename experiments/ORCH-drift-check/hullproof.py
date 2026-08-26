"""Is a per-band convex merge a convex merge of the inputs? A computed answer.

`pyramid.rs`'s own log states the safety argument:

    "selection : SOFT -- weight = (band power above the noise floor)^exponent,
     a convex combination. Sign coherence is free: a convex combination cannot
     take adjacent coefficients from opposite-signed frames"

Convexity per band is real. The claim this file tests is the *inferred* one --
that it protects the reconstruction. It does not, and the reason is structural:
each band picks its own weights, so band 0 may be dominated by frame A while
band 5 is dominated by frame B. The reconstruction sums those, and a sum of
convex combinations drawn from DIFFERENT weightings is not a convex combination
of the original pixels.

This is decided by construction, not by measurement, so nothing here depends on
the codebase being correct or on my reading of it. Two controls are printed:

  1. SHARED weights (one weighting used for every band). Convexity IS preserved
     across the reconstruction, so violations must be exactly zero. If this
     control fails, the harness is broken and the main result means nothing.
  2. A single-frame passthrough, which must reproduce that frame exactly.
"""
import numpy as np

rng = np.random.default_rng(20260826)


def decompose(sig, levels):
    """1-D Laplacian pyramid. Returns [detail bands..., base]."""
    bands, cur = [], sig.astype(np.float64)
    for _ in range(levels):
        lo = np.convolve(cur, np.ones(5) / 5.0, mode="same")
        bands.append(cur - lo)
        cur = lo
    bands.append(cur)
    return bands


def reconstruct(bands):
    return np.sum(bands, axis=0)


def merge(frames, levels, shared_weights):
    """Per-band convex merge. shared_weights=True uses ONE weighting for all."""
    dec = [decompose(f, levels) for f in frames]
    nb = levels + 1
    out = []
    if shared_weights:
        w = rng.random(len(frames))
        w /= w.sum()
        per_band = [w] * nb
    else:
        per_band = []
        for b in range(nb):
            # weight by band power, as the real merge does
            p = np.array([np.abs(d[b]).mean() ** 4 for d in dec])
            p = p / p.sum() if p.sum() > 0 else np.ones(len(frames)) / len(frames)
            per_band.append(p)
    for b in range(nb):
        w = per_band[b]
        assert abs(w.sum() - 1.0) < 1e-12, "weights not convex"
        assert (w >= 0).all(), "weights not non-negative"
        out.append(sum(w[k] * dec[k][b] for k in range(len(frames))))
    return reconstruct(out)


def run(tag, shared, n_frames=8, n=512, levels=5, trials=200):
    worst, viol_px, tot_px = 0.0, 0, 0
    for _ in range(trials):
        base = np.cumsum(rng.normal(0, 1, n))
        frames = []
        for k in range(n_frames):
            # each frame sharp in a different region: the focus-stack situation
            w = np.exp(-((np.arange(n) - k * n / n_frames) ** 2) / (2 * (n / 12) ** 2))
            sm = np.convolve(base, np.ones(9) / 9.0, mode="same")
            frames.append(w * base + (1 - w) * sm + rng.normal(0, 0.05, n))
        frames = np.array(frames)
        out = merge(frames, levels, shared)
        lo, hi = frames.min(axis=0), frames.max(axis=0)
        eps = 1e-9
        below, above = out < lo - eps, out > hi + eps
        viol_px += int((below | above).sum())
        tot_px += n
        span = np.maximum(hi - lo, 1e-12)
        exc = np.maximum((lo - out) / span, (out - hi) / span).max()
        worst = max(worst, float(exc))
    pct = 100.0 * viol_px / tot_px
    print(f"{tag:52s} {viol_px:>9,} / {tot_px:,} px  {pct:6.2f}%   "
          f"worst excursion {worst:7.3f} x hull span")
    return viol_px


print("Does a per-band convex merge stay inside the per-pixel hull of its inputs?")
print("Hull = [min_k frame_k(x), max_k frame_k(x)]. Any output outside it is a")
print("value no input frame supports -- arithmetically impossible for a weighted")
print("combination of those frames.\n")

print(f"{'case':52s} {'violating':>9}   {'':>12}")
print("-" * 108)
c1 = run("CONTROL 1: shared weights across all bands", True)
c2 = run("MEASURED: independent per-band weights", False)

print()
# Control 2: single frame must pass through exactly
one = np.cumsum(rng.normal(0, 1, 512))[None, :]
out = merge(one, 5, False)
err = float(np.abs(out - one[0]).max())
print(f"CONTROL 2: single-frame passthrough max abs error = {err:.3e}")

print()
if c1 == 0 and c2 > 0:
    print("RESULT: with ONE weighting shared by every band, convexity is preserved")
    print("        and violations are exactly zero. With INDEPENDENT per-band")
    print("        weights -- what a multi-band focus merge does by definition --")
    print("        the reconstruction leaves the hull.")
    print()
    print("        Per-band convexity does not imply reconstruction convexity.")
    print("        The safety argument in the module's own log does not hold for")
    print("        the operation the module performs.")
elif c1 > 0:
    print("HARNESS BROKEN: the shared-weight control violates the hull, which is")
    print("        impossible. Do not trust the measured row.")
else:
    print("RESULT: no violations in either arm. The hypothesis is refuted and the")
    print("        clip must have another mechanism.")

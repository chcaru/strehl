"""Does the measured floor cost acuity?

This is the instrument for the owner's Q1: if the gate has been sitting at the
wrong multiple of the true noise power, then pixels were averaged that should
have selected (or vice versa), and averaging across a focus bracket where only
some frames are sharp does not remove noise from those pixels -- it removes
their DETAIL. So a floor correction that reduces noise is only a win if it does
not pay for it in sharpness.

Two statistics on the SAME tile sets, chosen once from a reference arm so that
an arm cannot move the statistic by moving the tile selection:

  flat  = high-pass rms over the least-structured tiles   -> NOISE proxy
  sharp = high-pass rms over the most-structured tiles    -> ACUITY proxy

COMMISSIONING (AGENTS.md sec 110.6 + sec 111.3: a planted defect AND a planted
improvement AND a healthy control that superficially resembles the defect):

  identity   - a byte copy. Both statistics must move exactly 0.0%. Anything
               else means the instrument is not deterministic.
  gain x1.02 - the HEALTHY CONTROL. Scaling brightness raises BOTH statistics by
               exactly 2%. An instrument that scores this as a defect is
               measuring exposure, not sharpness. It must move both EQUALLY,
               so the flat/sharp RATIO is what must stay flat.
  blur       - the PLANTED DEFECT for acuity. `sharp` must fall clearly.
  noise      - the PLANTED DEFECT for noise. `flat` must rise clearly.
  denoise-flat - the PLANTED IMPROVEMENT, and it is the exact shape of the
               change being claimed: smooth ONLY the flat tiles and leave the
               structured ones alone. `flat` must fall while `sharp` holds. An
               instrument that cannot score this as a gain would score every
               arm as a loss, which is how `overshoot_frac` certified a planted
               2 px ring as an improvement.
"""

import sys
import numpy as np
import tifffile

K = np.array([1.0, 4.0, 6.0, 4.0, 1.0])
K /= K.sum()
TILE = 32


def blur(a):
    """Separable [1 4 6 4 1]/16, edge-replicated. No downsample: this is the
    finest-octave high-pass complement, which is band 0 of the merge pyramid --
    the band where the floor error was measured at 1.18x/0.62x white."""
    out = a
    for axis in (0, 1):
        p = np.moveaxis(out, axis, 0)
        pad = np.concatenate([p[1:3][::-1], p, p[-3:-1][::-1]], axis=0)
        acc = np.zeros_like(p)
        for i, w in enumerate(K):
            acc += w * pad[i:i + p.shape[0]]
        out = np.moveaxis(acc, 0, axis)
    return out


def stats(img, flat_idx, sharp_idx):
    """High-pass rms over two fixed tile sets. Luma only: chroma high-pass is
    the statistic sec 111.4 showed is the same size as photon noise at these
    levels, so it cannot separate the arms and is not used here."""
    lo = blur(img)
    hp = img - lo
    h, w = img.shape
    th, tw = h // TILE, w // TILE
    hp2 = (hp[:th * TILE, :tw * TILE] ** 2).reshape(th, TILE, tw, TILE).mean(axis=(1, 3))
    f = hp2.reshape(-1)
    return float(np.sqrt(f[flat_idx].mean())), float(np.sqrt(f[sharp_idx].mean()))


def luma(path):
    a = tifffile.imread(path).astype(np.float64)
    if a.ndim == 3:
        a = 0.25 * a[..., 0] + 0.5 * a[..., 1] + 0.25 * a[..., 2]
    return a


def tiles(ref):
    """Tile selection from the STRUCTURE (the low-pass), not the high-pass.
    Selecting on the high-pass would select on the very quantity being
    compared, and every arm would score identically by construction."""
    lo = blur(ref)
    h, w = ref.shape
    th, tw = h // TILE, w // TILE
    v = lo[:th * TILE, :tw * TILE].reshape(th, TILE, tw, TILE).var(axis=(1, 3)).reshape(-1)
    order = np.argsort(v)
    n = max(1, len(order) // 10)
    return order[:n], order[-n:]


def main():
    ref_path = sys.argv[1]
    arms = sys.argv[2:]
    ref = luma(ref_path)
    flat_idx, sharp_idx = tiles(ref)
    print(f"reference   : {ref_path}")
    print(f"tiles       : {TILE}x{TILE}, {len(flat_idx)} flat + {len(sharp_idx)} sharp "
          f"(deciles of low-pass variance, FIXED across arms)")

    rng = np.random.default_rng(12345)
    lo = blur(ref)
    struct = np.zeros(ref.shape, bool)
    h, w = ref.shape
    th, tw = h // TILE, w // TILE
    m = np.zeros(th * tw, bool)
    m[sharp_idx] = True
    struct[:th * TILE, :tw * TILE] = np.repeat(np.repeat(m.reshape(th, tw), TILE, 0), TILE, 1)

    print("\n--- COMMISSIONING ---")
    print(f"{'arm':<16}{'flat':>12}{'sharp':>12}{'d flat %':>11}{'d sharp %':>11}  verdict")
    f0, s0 = stats(ref, flat_idx, sharp_idx)
    print(f"{'baseline':<16}{f0:12.2f}{s0:12.2f}{0.0:11.2f}{0.0:11.2f}")
    cases = [
        ("identity", ref.copy(), "both exactly 0.00"),
        ("gain x1.02", ref * 1.02, "both +2.00, EQUALLY"),
        ("blur (defect)", blur(ref), "sharp falls"),
        ("noise (defect)", ref + rng.normal(0, 50.0, ref.shape), "flat rises"),
        ("denoise-flat (IMPROVEMENT)", np.where(struct, ref, lo), "flat falls, sharp holds"),
    ]
    for name, arr, expect in cases:
        f, s = stats(arr, flat_idx, sharp_idx)
        print(f"{name:<16}{f:12.2f}{s:12.2f}{100 * (f / f0 - 1):11.2f}{100 * (s / s0 - 1):11.2f}"
              f"  expect {expect}")

    print("\n--- ARMS ---")
    print(f"{'arm':<28}{'flat(noise)':>13}{'sharp(acuity)':>15}{'d flat %':>11}{'d sharp %':>11}")
    base = None
    for p in arms:
        f, s = stats(luma(p), flat_idx, sharp_idx)
        if base is None:
            base = (f, s)
        print(f"{p.split(chr(92))[-1]:<28}{f:13.3f}{s:15.3f}"
              f"{100 * (f / base[0] - 1):11.2f}{100 * (s / base[1] - 1):11.2f}")


if __name__ == "__main__":
    main()
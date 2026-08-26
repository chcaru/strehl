"""Is the content the hull clamp removes SIGNAL or NOISE?

The question ORCH asked, and the one on which the whole recommendation turns.
It is NOT answerable by "does the clamped pixel lie outside the hull" -- in the
domain the clamp operates in, `p.clamp(lo,hi)` moves a pixel if and only if it
is outside [lo,hi], so that test is a tautology and returns 100% by arithmetic.

The non-tautological question is whether the removed amplitude is large or small
*compared to the noise*, and where it lives in scale.

METHOD
  delta = clamped - unclamped, from ONE binary, matched pair, determinism null 0.
  noise = the per-octave RMS of an adjacent-frame difference, (f_i - f_i+1)/sqrt2,
          which is dominated by sensor noise. Adjacent frames also differ slightly
          in focus, so this OVERSTATES the noise floor, which biases the verdict
          toward "noise" -- i.e. conservative against a "it is signal" finding.
  span  = hi - lo over all 205 aligned frames, the full observed range.

Everything is computed on the binned 2344x3520 CFA-quad grid, which is the grid
the hull cache lives on. The full-res pair is brought down by a 2x2 block mean,
which is exact for a difference because the block mean is linear.

Green only. Sections 16.5 established the two builds differ by a chromatic
aberration correction with green bit-identical and red/blue moved up to 3902 DN,
so green is the only channel where cross-build quantities are safe. Both arms
here come from one binary, but green also happens to be where G = 0.5*(G1+G2)
and the hull is best behaved.

INTERPRETATION, registered before running
  |delta| >> span  : exceeds the entire range of 205 observations. Cannot be
                     noise and cannot be detail any frame saw. Artifact.
  |delta| ~ sigma  : indistinguishable from sensor noise. The clamp is a denoiser.
  |delta| >> sigma but < span : real scene content that some frames saw.
"""

import sys
import numpy as np
import tifffile

ROOT = "C:\\dev\\strehl-out\\BUILD-HULL"
FRAMES = ROOT + "\\warpS\\frames\\frames"
NF = 205

# ---- registered predictions, printed before any result -------------------
PREDICTIONS = [
    ("ORCH", "removed content is predominantly SIGNAL at the fine octaves"),
    ("ORCH", "removed content is predominantly NOISE at the base octave"),
    ("BUILD-HULL", "removed content exceeds the noise floor at every octave, "
                   "because a clamp that only bound on noise could not move "
                   "24.6% of pixels or 1.9% of them by more than 1000 DN"),
]


def binom5(a, axis):
    """Separable 5-tap binomial blur, edge-replicated. Burt-Adelson kernel."""
    k = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32) / 16.0
    p = [(0, 0)] * a.ndim
    p[axis] = (2, 2)
    b = np.pad(a, p, mode="edge")
    out = np.zeros_like(a)
    for i, w in enumerate(k):
        sl = [slice(None)] * a.ndim
        sl[axis] = slice(i, i + a.shape[axis])
        out += w * b[tuple(sl)]
    return out


def blur(a):
    return binom5(binom5(a, 0), 1)


def laplacian_octaves(img, levels):
    """Non-decimated Laplacian: octave k = blur^k - blur^(k+1). Non-decimated so
    every octave stays on one grid and per-pixel comparison needs no resampling."""
    cur = img.astype(np.float32)
    outs = []
    for _ in range(levels):
        nxt = blur(cur)
        outs.append(cur - nxt)
        cur = nxt
    outs.append(cur)  # base
    return outs


def block2(a):
    """Exact 2x2 block mean onto the binned grid."""
    h, w = a.shape
    return a.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def green(path):
    return tifffile.imread(path)[:, :, 1].astype(np.float32)


def ncc_shift(a, b, rad=40):
    """Integer shift of b relative to a by peak normalised cross-correlation."""
    h, w = a.shape
    cy, cx = h // 2, w // 2
    half = 400
    A = a[cy - half:cy + half, cx - half:cx + half]
    A = A - A.mean()
    best, bdy, bdx = -2.0, 0, 0
    for dy in range(-rad, rad + 1, 2):
        for dx in range(-rad, rad + 1, 2):
            B = b[cy - half + dy:cy + half + dy, cx - half + dx:cx + half + dx]
            B = B - B.mean()
            d = np.sqrt((A * A).sum() * (B * B).sum())
            if d <= 0:
                continue
            c = float((A * B).sum() / d)
            if c > best:
                best, bdy, bdx = c, dy, dx
    return bdy, bdx, best


def main():
    print("=" * 74)
    print("REGISTERED PREDICTIONS (printed before any result)")
    for who, what in PREDICTIONS:
        print(f"  [{who:10s}] {what}")
    print("=" * 74)

    print("\n--- loading the matched pair -------------------------------------")
    cl = green(ROOT + "\\bl\\fb-clamped.tiff")
    un = green(ROOT + "\\bl\\fb-unclamped.tiff")
    print(f"clamped   {cl.shape}  unclamped {un.shape}")
    clb, unb = block2(cl), block2(un)
    del cl, un
    delta = clb - unb
    print(f"binned to {clb.shape}; delta range {delta.min():.1f} .. {delta.max():.1f} DN")

    lo = np.load(ROOT + "\\warpS\\cache\\lo.npy", mmap_mode="r")[:, :, 1].astype(np.float32)
    hi = np.load(ROOT + "\\warpS\\cache\\hi.npy", mmap_mode="r")[:, :, 1].astype(np.float32)
    span = hi - lo
    print(f"hull span: median {np.median(span):.1f} DN, mean {span.mean():.1f} DN")

    # ---- CONTROL: are the pair and the hull basis co-registered? ----------
    print("\n--- CONTROL 1: registration of the render against the hull basis --")
    # Reference is the binned `strehl stack` render, which section 16.6 already
    # scored against THIS cache. Frame 0 is a poor reference: it sits at one end
    # of the bracket and is defocused almost everywhere, so its correlation peak
    # is driven by whatever little structure is sharp there.
    ref = green(ROOT + "\\warp\\merge-S-pyramid.tiff")
    dy, dx, c = ncc_shift(ref, unb)
    print(f"measured shift blend-render vs strehl-stack : dy={dy} dx={dx} ncc={c:.4f}")
    # The plant composes with the baseline offset, so the potency test is on the
    # DIFFERENCE, not the absolute. Getting this wrong is what failed the first run.
    planted = np.roll(unb, (17, -11), axis=(0, 1))
    py, px, pc = ncc_shift(ref, planted)
    ry, rx = py - dy, px - dx
    print(f"PLANTED +17,-11 recovered as relative shift : dy={ry} dx={rx} ncc={pc:.4f}")
    ok_pot = (abs(ry - 17) <= 2 and abs(rx + 11) <= 2)
    print(f"planted shift recovered  : {'PASS' if ok_pot else 'FAIL'}  <- gates the rest")
    if not ok_pot:
        print("STOP: the shift finder cannot see a shift it was given. Result void.")
        return 1
    if dy or dx:
        print(f"applying integer shift ({dy},{dx}) to the pair. Integer only: a")
        print("sub-pixel resample would blur the very quantity being measured.")
        sy = slice(max(0, dy), delta.shape[0] + min(0, dy))
        sx = slice(max(0, dx), delta.shape[1] + min(0, dx))
        ty = slice(max(0, -dy), delta.shape[0] + min(0, -dy))
        tx = slice(max(0, -dx), delta.shape[1] + min(0, -dx))
        delta = delta[sy, sx]
        span = span[ty, tx]
        print(f"common overlap after shift : {delta.shape}")

    # ---- noise floor from adjacent-frame differences ----------------------
    print("\n--- noise floor from adjacent-frame differences -------------------")
    LEV = 6
    pairs = [(20, 21), (60, 61), (100, 101), (140, 141), (180, 181)]
    noise_oct = np.zeros(LEV + 1)
    prev = None
    for (i, j) in pairs:
        a = green(f"{FRAMES}\\f{i:04d}.tiff")
        b = green(f"{FRAMES}\\f{j:04d}.tiff")
        d = (a - b) / np.sqrt(2.0)
        for k, o in enumerate(laplacian_octaves(d, LEV)):
            noise_oct[k] += float(np.sqrt((o * o).mean()))
        prev = a
    noise_oct /= len(pairs)
    print("octave   noise RMS (DN)")
    for k in range(LEV + 1):
        nm = "base" if k == LEV else f"detail{k}"
        print(f"  {nm:8s} {noise_oct[k]:10.2f}")

    # ---- the measurement --------------------------------------------------
    print("\n--- delta decomposed by octave ------------------------------------")
    d_oct = laplacian_octaves(delta, LEV)
    print(f"{'octave':9s} {'|d| RMS':>10s} {'noise':>9s} {'ratio':>8s} "
          f"{'share%':>8s}  verdict")
    tot = sum(float((o * o).sum()) for o in d_oct)
    rows = []
    for k in range(LEV + 1):
        nm = "base" if k == LEV else f"detail{k}"
        r = float(np.sqrt((d_oct[k] ** 2).mean()))
        share = 100.0 * float((d_oct[k] ** 2).sum()) / tot
        ratio = r / noise_oct[k] if noise_oct[k] > 0 else float("nan")
        verdict = "SIGNAL" if ratio >= 3.0 else ("noise" if ratio <= 1.0 else "mixed")
        rows.append((nm, r, noise_oct[k], ratio, share, verdict))
        print(f"{nm:9s} {r:10.2f} {noise_oct[k]:9.2f} {ratio:8.2f} "
              f"{share:8.2f}  {verdict}")

    # ---- against the hull span -------------------------------------------
    print("\n--- delta against the full observed range -------------------------")
    moved = np.abs(delta) > 0.5
    n_moved = int(moved.sum())
    frac = 100.0 * n_moved / delta.size
    print(f"pixels moved by the clamp : {n_moved:,} ({frac:.4f}%)")
    if n_moved:
        rel = np.abs(delta[moved]) / np.maximum(span[moved], 1.0)
        for q in (50, 90, 99, 99.9):
            print(f"  |delta|/span p{q:<5} : {np.percentile(rel, q):8.4f}")
        print(f"  |delta| exceeds the whole 205-frame range on "
              f"{100.0 * float((rel > 1).mean()):.4f}% of moved px")
        a = np.abs(delta[moved])
        for q in (50, 90, 99):
            print(f"  |delta| p{q:<5} DN      : {np.percentile(a, q):8.1f}")

    # ---- scoring ----------------------------------------------------------
    print("\n" + "=" * 74)
    print("SCORING THE REGISTERED PREDICTIONS")
    fine = [r for r in rows if r[0] in ("detail0", "detail1")]
    base = [r for r in rows if r[0] == "base"][0]
    fine_sig = all(r[3] >= 3.0 for r in fine)
    base_noise = base[3] <= 1.0
    allsig = all(r[3] > 1.0 for r in rows)
    print(f"  ORCH  'signal at fine octaves'  : "
          f"{'CONFIRMED' if fine_sig else 'REFUTED'} "
          f"(detail0 ratio {fine[0][3]:.2f}, detail1 {fine[1][3]:.2f})")
    print(f"  ORCH  'noise at the base octave': "
          f"{'CONFIRMED' if base_noise else 'REFUTED'} "
          f"(base ratio {base[3]:.2f})")
    print(f"  HULL  'above noise everywhere'  : "
          f"{'CONFIRMED' if allsig else 'REFUTED'}")
    print("=" * 74)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""R3/R4 -- where does the null's excess gradient energy actually live?

R1 (mech1.py) falsified edge doubling as the cause: doubling a step HALVES
Tenengrad, exactly 0.5000. A seam gives 0.8258. The only thing measured to
RAISE gradient energy from a flat baseline is noise.

So this asks the question directly, on the real renders: decompose both arms
into octave bands and stratify by local structure, and see which band and which
stratum carries the null's excess.

Everything is computed on a COMMON classification derived from the mean of the
two arms, so no pixel is assigned to a different stratum in one arm than the
other. Whole-frame numbers are the sanity check against the orchestrator's
0.9790; the stratified numbers are the finding.

The pair is FOV- and resampler-matched by construction (M86's STREHL_ALIGN=zoom
null), so unlike every earlier comparison in this milestone no re-registration
is needed -- and must not be applied, because re-registering would remove the
very displacement under study.
"""

import json
import sys

import numpy as np
import tifffile


def load(path):
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path}: expected uint16, got {a.dtype}"
    g = a[:, :, 1] if a.ndim == 3 else a
    return g.astype(np.float32)


def block2(a):
    h, w = (a.shape[0] // 2) * 2, (a.shape[1] // 2) * 2
    return a[:h, :w].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def up2(a, shape):
    u = np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)
    return u[:shape[0], :shape[1]]


def tenengrad_map(g):
    """Per-pixel squared gradient magnitude, central differences."""
    gx = np.zeros_like(g)
    gy = np.zeros_like(g)
    gx[:, 1:-1] = g[:, 2:] - g[:, :-2]
    gy[1:-1, :] = g[2:, :] - g[:-2, :]
    return gx * gx + gy * gy


def pyramid(g, levels):
    ls = [g]
    for _ in range(levels):
        ls.append(block2(ls[-1]))
    return ls


def band_energies(g, levels=6):
    """Laplacian-style octave band energies. Band 0 is pixel scale."""
    ls = pyramid(g, levels)
    out = []
    for k in range(levels):
        u = up2(ls[k + 1], ls[k].shape)
        # block2 truncates an odd dimension, so the upsample can be one pixel
        # short. Crop both to the common extent rather than padding, which
        # would inject a fake edge into the band.
        h = min(ls[k].shape[0], u.shape[0])
        w = min(ls[k].shape[1], u.shape[1])
        b = ls[k][:h, :w] - u[:h, :w]
        out.append(float(np.mean(b.astype(np.float64) ** 2)))
    out.append(float(np.var(ls[levels].astype(np.float64))))
    return out


def strata(ref, nq=4):
    """Classify pixels by local structure on a COMMON reference.

    Structure is the local standard deviation of a 2x-downsampled copy, so the
    classification is driven by real detail rather than by pixel noise, then
    nearest-upsampled back. Identical for both arms by construction.
    """
    r = block2(ref)
    k = 8
    h, w = (r.shape[0] // k) * k, (r.shape[1] // k) * k
    t = r[:h, :w].reshape(h // k, k, w // k, k)
    sd = t.std(axis=(1, 3))
    sd_up = np.repeat(np.repeat(sd, k, axis=0), k, axis=1)
    sd_full = up2(sd_up, ref.shape)
    if sd_full.shape != ref.shape:
        pad = np.zeros(ref.shape, np.float32)
        pad[:sd_full.shape[0], :sd_full.shape[1]] = sd_full
        sd_full = pad
    edges = [np.quantile(sd, q) for q in np.linspace(0, 1, nq + 1)]
    edges[0], edges[-1] = -1.0, float(sd.max()) + 1.0
    return sd_full, edges


def report(a, z, label, fh):
    def p(s):
        print(s)
        fh.append(s)

    p(f"\n--- {label} ---")
    ta, tz = tenengrad_map(a), tenengrad_map(z)
    whole = float(ta.mean()) / float(tz.mean())
    p(f"  whole-frame tenengrad A/B = {whole:.4f}")

    ba, bz = band_energies(a), band_energies(z)
    bands = []
    p("  octave bands (band 0 = pixel scale):")
    for k, (x, y) in enumerate(zip(ba, bz)):
        r = x / y if y else float("nan")
        bands.append(r)
        p(f"    band {k} ({2**k:>2}px)  A {x:12.2f}  B {y:12.2f}  A/B {r:.4f}")

    sd, edges = strata((a + z) * 0.5)
    st = []
    p("  strata by local structure (common classification):")
    for i in range(len(edges) - 1):
        m = (sd >= edges[i]) & (sd < edges[i + 1])
        n = int(m.sum())
        if n == 0:
            continue
        x, y = float(ta[m].mean()), float(tz[m].mean())
        r = x / y if y else float("nan")
        st.append(dict(q=i, n=n, a=x, b=y, ratio=r))
        p(f"    q{i} sd<{edges[i+1]:8.1f}  n={n:>10}  A {x:11.1f}  B {y:11.1f}"
          f"  A/B {r:.4f}")
    return dict(label=label, whole=whole, bands=bands, strata=st)


def main(argv):
    d = r"C:\dev\strehl-out\M86-align"
    a = load(rf"{d}\bee-3-ALIGNED.tif")
    z = load(rf"{d}\bee3-zoomnull.tif")
    assert a.shape == z.shape, "arms are not FOV-matched"
    print("dims", a.shape)

    fh = []
    res = []
    # CONTROLS FIRST. A placebo that is not 1.0000 in every band and every
    # stratum means the wiring is wrong and no treatment number is admissible.
    res.append(report(z, z, "CONTROL placebo: zoomnull vs itself (want 1.0000)", fh))
    from scipy.ndimage import gaussian_filter
    res.append(report(gaussian_filter(z, 1.0), z,
                      "CONTROL plant: blurred(zoomnull) vs zoomnull (want << 1)", fh))
    res.append(report(z, gaussian_filter(z, 1.0),
                      "CONTROL plant: zoomnull vs blurred(zoomnull) (want >> 1)", fh))

    res.append(report(a, z, "TREATMENT aligned vs zoomnull (visually: aligned is BETTER)", fh))

    json.dump(res, open(argv[1], "w"), indent=1)
    print("\nwrote", argv[1])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

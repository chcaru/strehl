"""S5 — replace the vacuous N3 control, and remove the reference's circularity.

TWO PROBLEMS WITH S4, BOTH FOUND BY ITS OWN OUTPUT
--------------------------------------------------
N3 was supposed to be a blur-only control: same kernel, zero shift, to show the
improvement came from co-siting and not merely from resampling. It returned
numbers identical to `as-shipped` in every digit, which is the signature of a
control that did nothing. It did nothing for a real reason: the Keys kernel at
t = 0 is exactly [0, 1, 0, 0], the identity. There is no blur-only version of
this operation, because for a 4-tap interpolator the blur is inseparable from
the shift. The control was not weak, it was empty, and it is replaced here by
N4, which asks the same question a different way:

    N4  apply the SAME correction to GREEN, which does not need it.
        If the metric merely rewards resampling, green improves too. It must
        instead get markedly worse, because green was already correct.

The second problem is subtler. S4's reference is the demosaiced render, box
averaged. The demosaic co-sites its channels, so "co-sited binned resembles the
reference more" is at risk of being true by construction rather than by fact.
S3's green null (0.0005-0.0020 px) shows the two grids agree, which rules out a
global offset, but not the deeper worry.

C11 removes it entirely: a synthetic RGB scene, mosaicked to RGGB, binned both
ways, and compared against the true 2x-downsampled scene. No demosaic anywhere
in the loop, and the answer is known because I built the scene.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402
from s4_benefit import PAIRS, box2, cosite, field_rois, registration, resample_shift  # noqa: E402

S = 256


# ---------------------------------------------------------------- C11
def synth_rgb(n, cutoff, seed):
    """A synthetic colour scene: correlated luminance plus independent chroma.

    The channels must be correlated (real scenes are) or the demosaic-free
    binning comparison would be measuring three unrelated images. They must
    also not be identical, or there would be no chroma error to measure at all.
    Band-limited below the binned Nyquist so binning introduces no aliasing --
    aliasing is a separate defect and would contaminate this one.
    """
    rng = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    r = np.sqrt(fy**2 + fx**2)
    mask = r <= cutoff

    def band(x):
        return np.real(np.fft.ifft2(np.fft.fft2(x) * mask))

    lum = band(rng.standard_normal((n, n)))
    out = np.zeros((n, n, 3))
    for c in range(3):
        out[:, :, c] = lum + 0.35 * band(rng.standard_normal((n, n)))
    return out


def c11_synthetic():
    print("== C11: synthetic end-to-end, no demosaic in the loop ==")
    rows = []
    for seed in (21, 22, 23, 24, 25):
        scene = synth_rgb(1024, 0.20, seed)
        truth = np.stack([box2(scene[:, :, c]) for c in range(3)], axis=2)

        shipped = np.zeros_like(truth)
        shipped[:, :, 0] = scene[0::2, 0::2, 0]
        shipped[:, :, 1] = 0.5 * (scene[0::2, 1::2, 1] + scene[1::2, 0::2, 1])
        shipped[:, :, 2] = scene[1::2, 1::2, 2]

        fixed = cosite(shipped, +1.0)

        def chroma_rms(cand):
            e = []
            for hi in (0, 2):
                e.append(((truth[:, :, hi] - truth[:, :, 1])
                          - (cand[:, :, hi] - cand[:, :, 1])).ravel())
            return float(np.sqrt(np.mean(np.concatenate(e) ** 2)))

        cs, cf = chroma_rms(shipped), chroma_rms(fixed)
        rows.append({"seed": seed, "chroma_shipped": cs, "chroma_fixed": cf,
                     "ratio": cf / cs})
        print("  seed %d  chroma err shipped %.5f -> co-sited %.5f   (%.1f%% lower)"
              % (seed, cs, cf, 100 * (1 - cf / cs)))
    rat = float(np.mean([r["ratio"] for r in rows]))
    ok = rat < 0.75
    print("  mean ratio co-sited/shipped = %.4f   C11: %s (bar < 0.75)"
          % (rat, "PASS" if ok else "FAIL"))
    return ok, rows, rat


# ---------------------------------------------------------------- N4
def cosite_green(img, mag=0.25):
    """N4: apply the red correction to GREEN, which does not need it."""
    out = img.copy()
    out[:, :, 1] = resample_shift(img[:, :, 1], +mag, +mag)
    return out


def n4_control():
    print("\n== N4: apply the correction to green, which is already correct ==")
    rows = {}
    for name, (binf, demof) in PAIRS.items():
        ib = C.load_tif(os.path.join(C.OUT, binf)).astype(np.float64)
        idm = C.load_tif(os.path.join(C.OUT, demof)).astype(np.float64)
        ground = np.stack([box2(idm[:, :, c]) for c in range(3)], axis=2)
        h, w = ib.shape[0], ib.shape[1]
        rois = field_rois(h, w, S, nx=5, ny=4)

        base = registration(ground, ib, rois)
        gshift = registration(ground, cosite_green(ib), rois)
        rows[name] = {"green_before": base["G"], "green_after_shift": gshift["G"]}
        print("  %-13s green misregistration  %.4f -> %.4f px  (must get WORSE)"
              % (name, base["G"], gshift["G"]))
    ok = all(v["green_after_shift"] > 10 * v["green_before"] for v in rows.values())
    print("  N4: %s (a correction applied where none is needed must hurt)"
          % ("PASS" if ok else "FAIL"))
    return ok, rows


def main():
    out = {}
    ok11, rows11, rat = c11_synthetic()
    out["C11"] = {"rows": rows11, "mean_ratio": rat, "pass": bool(ok11)}
    ok4, rows4 = n4_control()
    out["N4"] = {"rows": rows4, "pass": bool(ok4)}
    out["N3_retired"] = (
        "vacuous: Keys at t=0 is the identity kernel, so a zero-shift resample "
        "is a no-op and the control returned digits identical to as-shipped. "
        "Replaced by N4."
    )
    C.jdump("s5_controls.json", out)
    print("\nBOTH CONTROLS PASS: %s" % (ok11 and ok4))
    return 0 if (ok11 and ok4) else 1


if __name__ == "__main__":
    sys.exit(main())

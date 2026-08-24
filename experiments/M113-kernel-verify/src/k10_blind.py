"""M113 K10 - IS FACT 1420'S INSTRUMENT IMAGE-BLIND?

K9 returned +0.1428 dex on nine different photographs with sd 0.0002. Nine
subjects -- a bee, foam, a steel ruler, a leaf, tweezers, lavender -- cannot
agree to four decimal places about anything real. Rule 12: the reading is the
hypothesis, so falsify it.

Hypothesis H: fact 1420's synthetic phase-average instrument does not measure
the photograph at all. band_ratio delta is a power-weighted average of the
kernel's |H(f)|^2 over two fixed bands; if |H|^2 varies slowly across each band,
the photograph's spectrum cancels and the reading collapses to a property of the
kernel COEFFICIENTS. If H is true, +0.1343 is a datasheet number for
Catmull-Rom vs Lanczos-3 that could have been computed with no camera, no
capture and no stack -- and it therefore cannot be evidence about bee-3-cpl,
about the corpus, or about the shipped pipeline.

Prediction registered before running: if H is true then
  A1 (closed form, flat P, NO IMAGE)      ~= +0.1428
  A2 (white noise, NO PHOTOGRAPH)         ~= +0.1428
  A3 (1/f^2 noise, NO PHOTOGRAPH)         ~= +0.1428
  A4 (nine real photographs)              == +0.1428  [K9, already measured]
If H is false, the noise arms should diverge from the photographs.
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "experiments", "M95-resample", "src"))
import x2_pairs as X  # noqa: E402
sys.path.insert(0, HERE)
from k9_stacks import PHASES, TILE, PAD, cr_w, l3_w, shift  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), "out")
BAND, LOW = X.BAND, X.LOWBAND


def analytic(wf):
    """Closed-form band_ratio delta for a flat power spectrum. No image."""
    n = 4096
    f = np.fft.fftfreq(n)
    fx, fy = np.meshgrid(f, f)
    r = np.zeros((n, n))
    acc_hi = np.zeros(len(PHASES))
    acc_lo = np.zeros(len(PHASES))
    for i, p in enumerate(PHASES):
        w, o = wf(p)
        hx = sum(wi * np.exp(2j * np.pi * fx * oi) for wi, oi in zip(w, o))
        hy = sum(wi * np.exp(2j * np.pi * fy * oi) for wi, oi in zip(w, o))
        h2 = np.abs(hx * hy) ** 2
        r = np.hypot(fx, fy)
        hi = (r >= BAND[0]) & (r < BAND[1])
        lo = (r >= LOW[0]) & (r < LOW[1])
        acc_hi[i] = h2[hi].mean()
        acc_lo[i] = h2[lo].mean()
    return float(np.mean(np.log10(acc_hi) - np.log10(acc_lo)))


def on_field(img):
    src = img
    base = X.band_ratio(src[PAD:-PAD, PAD:-PAD], 1.0)
    out = {}
    for nm, wf in (("cr", cr_w), ("l3", l3_w)):
        v = [X.band_ratio(shift(src, ph, wf)[PAD:-PAD, PAD:-PAD], 1.0) - base
             for ph in PHASES]
        out[nm] = float(np.mean(v))
    return out


def main():
    res, N = {}, TILE + 2 * PAD
    print("A1  closed form, flat power spectrum, NO IMAGE AT ALL")
    a_cr, a_l3 = analytic(cr_w), analytic(l3_w)
    print(f"    catmull-rom {a_cr:+.4f}   lanczos3 {a_l3:+.4f}   GAIN {a_l3-a_cr:+.4f} dex")
    res["A1_closed_form_no_image"] = dict(cr=a_cr, l3=a_l3, gain=a_l3 - a_cr)

    rng = np.random.default_rng(1420)
    print("\nA2/A3  synthetic fields, NO PHOTOGRAPH (mean of 24 draws)")
    for nm, gen in (("white noise", lambda: rng.standard_normal((N, N))),
                    ("1/f^2 noise", None),
                    ("gaussian blobs", None)):
        gs = []
        for _ in range(24):
            if nm == "white noise":
                im = rng.standard_normal((N, N))
            elif nm == "1/f^2 noise":
                f = np.fft.fftfreq(N)
                r = np.hypot(*np.meshgrid(f, f))
                r[0, 0] = 1e-6
                im = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((N, N))) / r))
            else:
                im = np.zeros((N, N))
                yy, xx = np.mgrid[0:N, 0:N]
                for _b in range(60):
                    cy, cx = rng.uniform(0, N, 2)
                    s = rng.uniform(1.0, 6.0)
                    im += rng.uniform(-1, 1) * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * s * s))
            d = on_field(im * 1000.0 + 20000.0)
            gs.append(d["l3"] - d["cr"])
        print(f"    {nm:16s} GAIN {np.mean(gs):+.4f} dex   sd {np.std(gs, ddof=1):.4f}")
        res[nm] = dict(gain=float(np.mean(gs)), sd=float(np.std(gs, ddof=1)))

    k9 = json.load(open(os.path.join(OUT, "k9_stacks.json")))
    photo = k9["_summary"]["mean"]
    print(f"\nA4  nine real photographs (K9)      GAIN {photo:+.4f} dex   "
          f"sd {k9['_summary']['sd']:.4f}")
    res["A4_nine_photographs"] = dict(gain=photo, sd=k9["_summary"]["sd"])

    print("\n--- VERDICT ON H ---")
    sp = [a_l3 - a_cr, res["white noise"]["gain"], res["1/f^2 noise"]["gain"],
          res["gaussian blobs"]["gain"], photo]
    print(f"    closed form / white / 1-over-f / blobs / photographs:")
    print("    " + "  ".join(f"{v:+.4f}" for v in sp))
    print(f"    total spread across ALL of them: {max(sp)-min(sp):.4f} dex")
    res["_verdict"] = dict(spread=float(max(sp) - min(sp)), values=[float(v) for v in sp],
                           image_blind=bool(max(sp) - min(sp) < 0.02))
    if max(sp) - min(sp) < 0.02:
        print("    H CONFIRMED: white noise reproduces the photographs. The")
        print("    instrument is image-blind; +0.1343 is a kernel datasheet number.")
    else:
        print("    H REFUTED: the photographs differ from noise.")
    json.dump(res, open(os.path.join(OUT, "k10_blind.json"), "w"), indent=1)
    print(f"\nwrote {os.path.join(OUT, 'k10_blind.json')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
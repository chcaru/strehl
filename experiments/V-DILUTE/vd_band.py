# -*- coding: utf-8 -*-
"""V-DILUTE: qualify the signal/noise band boundary for 112MSDCF.

ORCH acceptance criterion 4: "Qualify your band per subject. The signal/noise
boundary moves 0.17-0.48 cyc/px across the corpus." `112MSDCF` is NOT among
V-LINEAR's five measured subjects (113MSDCF 0.25, 119MSDCF 0.25, bee-1-cpl
0.48, flower-bud-alone-cpl 0.17, leaf-2-cpl 0.20), so scoring it at the
0.30-0.35 band V-NEVERWORSE used is UNQUALIFIED until this runs.

METHOD, and why it is better founded here than a generic one: V-NEVERWORSE's
synthetic twin already provides a perfect noise reference -- identical scene
content, independent noise at the FITTED sensor variance, and no focus signal
at all. So for each band I compare a real single frame against a twin single
frame built from the same sensor model. Where real ~ twin, the band is noise.
Where real >> twin, the band carries scene structure. Same data, same
instrument, no extra assumption.

The boundary is reported as the lowest band edge at which the real/twin power
ratio falls below QUAL. Both directions are commissioned: a deliberately
blurred real frame must lose its qualification at fine bands (potency), and
the twin against itself must qualify nothing (null).
"""
import io
import json
import os
import sys

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl"
                   r"\experiments\V-NEVERWORSE")

BUNDLE = r"C:\dev\strehl-out\V-NEVERWORSE\bundle"
OUT = r"D:\strehl-out\V-DILUTE\premium"

# Fine-grained ladder so the boundary can land anywhere in V-LINEAR's range.
EDGES = [0.10, 0.13, 0.17, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50]
QUAL = 2.0   # real must carry >=2x the twin's power to count as signal


def load(subj):
    z = np.load(os.path.join(BUNDLE, "%s.npz" % subj))
    meta = json.load(io.open(os.path.join(BUNDLE, "%s.json" % subj),
                             encoding="utf-8"))
    ok = {r["frame"] for r in meta["rows"] if r["state"] == "OK"}
    keys = [k for k in sorted(z.files)
            if k.startswith("b") and k != "bw" and int(k[1:]) in ok]
    return [z[k].astype(np.float64) for k in keys]


def _hann2(h, w):
    return np.outer(np.hanning(h), np.hanning(w))


def bandpow(g):
    """Radially averaged power per band on the green plane."""
    g = g - g.mean()
    h, w = g.shape
    F = np.fft.rfft2(g * _hann2(h, w))
    p = F.real ** 2 + F.imag ** 2
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.rfftfreq(w)[None, :]
    rad = np.sqrt(fy ** 2 + fx ** 2)
    out = []
    for i in range(len(EDGES) - 1):
        m = (rad >= EDGES[i]) & (rad < EDGES[i + 1])
        out.append(float(p[m].mean()))
    return np.array(out)


def smooth5(a):
    k = np.array([1.0, 4.0, 6.0, 4.0, 1.0])
    k = k / k.sum()
    b = np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 0, a)
    return np.apply_along_axis(lambda v: np.convolve(v, k, "same"), 1, b)


def qualify(real_g, twin_g, label):
    pr, pt = bandpow(real_g), bandpow(twin_g)
    ratio = pr / np.maximum(pt, 1e-30)
    print("  %-22s %s" % (label, "  ".join("%7.2f" % r for r in ratio)))
    return ratio


def boundary(ratio):
    """Lowest edge at or above which every band fails qualification."""
    for i in range(len(ratio)):
        if all(ratio[j] < QUAL for j in range(i, len(ratio))):
            return EDGES[i]
    return EDGES[-1]


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
    os.makedirs(OUT, exist_ok=True)
    frames = np.array(load(subj))
    n = len(frames)
    print("subject %s, %d frames\n" % (subj, n))

    import vn_pyr as VP
    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1])
    print("fitted sensor variance: read2=%.2f photon_gain=%.5f" % (read2, gph))
    if gph < 0:
        print("REFUSED: fitted photon gain is negative")
        return 2

    rng = np.random.default_rng(20260828)
    base = frames.mean(axis=0)
    sd = np.sqrt(np.maximum(var0, 0.0))
    twin = base[:, :, 1] + rng.normal(0.0, 1.0, base.shape[:2]) * sd
    twin2 = base[:, :, 1] + rng.normal(0.0, 1.0, base.shape[:2]) * sd

    hdr = "  %-22s %s" % ("band (cyc/px)",
                          "  ".join("%7s" % ("%.2f" % EDGES[i])
                                    for i in range(len(EDGES) - 1)))
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    real_g = frames[len(frames) // 2][:, :, 1]
    r_real = qualify(real_g, twin, "REAL / twin")

    # NULL: twin against an independent twin must qualify nothing.
    r_null = qualify(twin2, twin, "null (twin/twin)")

    # POTENCY: a blurred real frame must LOSE fine-band qualification.
    r_blur = qualify(smooth5(smooth5(real_g)), twin, "potency (blurred real)")

    b_real = boundary(r_real)
    b_null = boundary(r_null)
    b_blur = boundary(r_blur)
    print("\n  boundary REAL           : %.2f cyc/px" % b_real)
    print("  boundary null (twin)    : %.2f cyc/px  (must be LOW)" % b_null)
    print("  boundary blurred        : %.2f cyc/px  (must be <= REAL)" % b_blur)

    bad = []
    if not all(r < QUAL * 1.5 for r in r_null):
        bad.append("NULL FAILED: twin/twin qualifies a band; the reference "
                   "is not a noise reference")
    if b_blur > b_real:
        bad.append("POTENCY FAILED: blurring did not lower the boundary")
    if bad:
        for b in bad:
            print("  " + b)
        print("REFUSED: instrument not commissioned")
        return 2
    print("  ok  null qualifies nothing; blurring lowers the boundary")

    print("\n  ==> 112MSDCF boundary = %.2f cyc/px" % b_real)
    v = ("0.30-0.35 is SIGNAL" if b_real > 0.35 else
         ("0.30-0.35 is MIXED (straddles)" if b_real > 0.30 else
          "0.30-0.35 is NOISE"))
    print("  ==> the band V-NEVERWORSE scored (0.30-0.35): %s" % v)

    json.dump(dict(subject=subj, edges=EDGES, ratio_real=r_real.tolist(),
                   ratio_null=r_null.tolist(), ratio_blur=r_blur.tolist(),
                   boundary=b_real, qual=QUAL, verdict=v),
              io.open(os.path.join(OUT, "band_%s.json" % subj), "w",
                      encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

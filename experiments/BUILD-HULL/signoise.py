"""Absolute magnitude of the clamp's removal per octave, against the noise floor
of the thing it actually modifies.

`sigtest.py` compared the removal to the noise of a SINGLE frame, estimated from
adjacent-frame differences. That is the wrong reference and it is wrong in a
known direction: the merge averages ~200 frames, so its residual noise is far
below one frame's, and using single-frame noise biases every verdict toward
"this is only noise". That bias was declared in `sigtest.py` but it still has to
be removed before the verdict can be trusted.

The right reference is the noise present in the merged output itself. This uses
the standard Donoho-Johnstone robust estimator, `sigma = 1.4826 * MAD`, on the
finest octave of the UNCLAMPED render. Natural-image finest-octave coefficients
are sparse -- mostly noise with a small population of edges -- which is exactly
the condition that estimator is built for, and the median is insensitive to the
edge population.

COMMISSIONING. The estimator is not trusted on assertion. On flower-bud the
single-frame noise floor is known independently (59.83 DN, from adjacent-frame
differences over 5 disjoint pairs). The merge of N frames must come out BELOW
that, and by roughly sqrt(N) if the merge were a plain mean. An estimate that
comes out above the single-frame floor, or absurdly below it, fails and the
result is void.
"""

import os
import sys
import numpy as np
import tifffile

ROOT = "C:\\dev\\strehl-out\\BUILD-HULL"
LEV = 6

# Measured by sigtest.py from 5 disjoint adjacent-frame pairs on the warped
# flower-bud basis. Used only to bound the merged-output estimate.
FB_SINGLE_FRAME_DETAIL0_NOISE = 59.83
FB_NFRAMES = 205

PAIRS = [
    ("flower-bud-alone-cpl", "bl\\fb-clamped.tiff", "bl\\fb-unclamped.tiff", 205),
    ("coffee-bean", "bl\\cb-clamped.tiff", "bl\\cb-unclamped.tiff", 105),
    ("couch-fibers-cpl", "bl\\cf-clamped.tiff", "bl\\cf-unclamped.tiff", 299),
]


def binom5(a, axis):
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


def octaves(img, levels):
    cur = img.astype(np.float32)
    outs = []
    for _ in range(levels):
        nxt = blur(cur)
        outs.append(cur - nxt)
        cur = nxt
    outs.append(cur)
    return outs


def block2(a):
    h, w = a.shape
    return a[: h // 2 * 2, : w // 2 * 2].reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


def green(p):
    return tifffile.imread(p)[:, :, 1].astype(np.float32)


def donoho(d0):
    return 1.4826 * float(np.median(np.abs(d0 - np.median(d0))))


def main():
    print("=" * 92)
    print("Removal magnitude per octave vs the noise floor OF THE MERGED OUTPUT")
    print("=" * 92)

    requested, scored, missing = len(PAIRS), 0, []
    rows = []
    for subj, cp, up, nfr in PAIRS:
        if not (os.path.exists(ROOT + "\\" + cp) and os.path.exists(ROOT + "\\" + up)):
            missing.append(subj)
            continue
        un = block2(green(ROOT + "\\" + up))
        d = block2(green(ROOT + "\\" + cp)) - un
        un_oct = octaves(un, LEV)
        d_oct = octaves(d, LEV)
        sig = donoho(un_oct[0])
        rows.append((subj, nfr, sig, [float(np.sqrt((o * o).mean())) for o in d_oct]))
        scored += 1

    print(f"\npartition: requested {requested} = scored {scored} + missing {len(missing)}"
          + (f"  missing: {', '.join(missing)}" if missing else ""))
    assert scored + len(missing) == requested

    # ---- COMMISSIONING -----------------------------------------------------
    print("\n--- COMMISSIONING the noise estimator ------------------------------")
    fb = [r for r in rows if r[0] == "flower-bud-alone-cpl"]
    if not fb:
        print("flower-bud absent: estimator cannot be commissioned. Result void.")
        return 1
    sig_fb = fb[0][2]
    ideal = FB_SINGLE_FRAME_DETAIL0_NOISE / np.sqrt(FB_NFRAMES)
    print(f"single-frame detail0 noise (independent) : {FB_SINGLE_FRAME_DETAIL0_NOISE:8.2f} DN")
    print(f"plain mean of {FB_NFRAMES} frames would give     : {ideal:8.2f} DN")
    print(f"Donoho estimate on the merged output     : {sig_fb:8.2f} DN")
    below = sig_fb < FB_SINGLE_FRAME_DETAIL0_NOISE
    sane = sig_fb > ideal * 0.5
    print(f"  below the single-frame floor : {'PASS' if below else 'FAIL'}")
    print(f"  not absurdly below sqrt(N)   : {'PASS' if sane else 'FAIL'}")
    if not (below and sane):
        print("STOP: noise estimator failed commissioning. Result void.")
        return 1
    print("  estimator commissioned.")

    # ---- the table ---------------------------------------------------------
    print("\n--- removal RMS in units of the merged output's own noise ----------")
    names = [f"detail{k}" for k in range(LEV)] + ["base"]
    print(f"{'subject':22s} {'sigma':>8s} " + " ".join(f"{n:>8s}" for n in names))
    print("-" * 92)
    for subj, nfr, sig, r in rows:
        print(f"{subj:22s} {sig:8.2f} " + " ".join(f"{v / sig:8.2f}" for v in r))
    print("-" * 92)
    print("(values are removal RMS divided by sigma; >1 means the clamp removes")
    print(" more than the merge's own noise at that scale)")

    print("\n--- the same rows in absolute DN -----------------------------------")
    print(f"{'subject':22s} " + " ".join(f"{n:>8s}" for n in names))
    for subj, nfr, sig, r in rows:
        print(f"{subj:22s} " + " ".join(f"{v:8.2f}" for v in r))

    # ---- verdict -----------------------------------------------------------
    print("\n" + "=" * 92)
    print("VERDICT per subject, at the finest octave -- where detail lives")
    for subj, nfr, sig, r in rows:
        ratio = r[0] / sig
        if ratio <= 1.0:
            v = "below its own noise -- removing noise, not detail"
        elif ratio <= 3.0:
            v = "comparable to noise -- ambiguous"
        else:
            v = "ABOVE its own noise -- removing real fine detail"
        print(f"  {subj:22s} detail0 = {ratio:6.2f} x sigma  -> {v}")
    print("=" * 92)
    return 0


if __name__ == "__main__":
    sys.exit(main())

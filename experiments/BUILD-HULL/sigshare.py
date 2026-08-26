"""Does the base-octave dominance of the clamp's removal generalise?

`sigtest.py` measured flower-bud, the subject that clips. The 15% microcontrast
cost in section 16.7 was measured on `coffee-bean`, which does not clip, so the
retraction that result implies is only safe if the same octave structure holds
there. My own caveat, which ORCH endorsed: do not treat one subject as
cross-subject until a second subject says so.

This computes the octave energy share of `clamped - unclamped` only. It does not
need a hull cache or warped frames, so it runs on any matched pair. No noise
floor is computed for coffee-bean because no warped basis exists for it; the
claim under test here is the SHARE, which needs no noise model.
"""

import sys
import numpy as np
import tifffile

ROOT = "C:\\dev\\strehl-out\\BUILD-HULL"
LEV = 6

PAIRS = [
    ("flower-bud-alone-cpl", "bl\\fb-clamped.tiff", "bl\\fb-unclamped.tiff"),
    ("coffee-bean", "bl\\cb-clamped.tiff", "bl\\cb-unclamped.tiff"),
    ("couch-fibers-cpl", "bl\\cf-clamped.tiff", "bl\\cf-unclamped.tiff"),
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


def main():
    print("Octave energy share of (clamped - unclamped), green, camera-linear.")
    print("Claim under test: the removal is dominated by the BASE octave, i.e.")
    print("it is a pedestal correction and not a loss of fine detail.\n")

    requested, scored, missing = len(PAIRS), 0, []
    names = [f"detail{k}" for k in range(LEV)] + ["base"]
    print(f"{'subject':24s} " + " ".join(f"{n:>8s}" for n in names) + f" {'moved%':>8s}")
    print("-" * 100)
    results = {}
    import os
    for subj, cp, up in PAIRS:
        if not (os.path.exists(ROOT + "\\" + cp) and os.path.exists(ROOT + "\\" + up)):
            missing.append(subj)
            continue
        d = block2(green(ROOT + "\\" + cp)) - block2(green(ROOT + "\\" + up))
        oc = octaves(d, LEV)
        tot = sum(float((o * o).sum()) for o in oc)
        if tot <= 0:
            print(f"{subj:24s} " + " ".join(f"{0.0:8.2f}" for _ in names)
                  + f" {0.0:8.4f}   (clamp inert: delta is identically zero)")
            results[subj] = None
            scored += 1
            continue
        sh = [100.0 * float((o * o).sum()) / tot for o in oc]
        moved = 100.0 * float((np.abs(d) > 0.5).mean())
        print(f"{subj:24s} " + " ".join(f"{s:8.2f}" for s in sh) + f" {moved:8.4f}")
        results[subj] = sh
        scored += 1

    print("-" * 100)
    print(f"partition: requested {requested} = scored {scored} + missing {len(missing)}"
          + (f"  missing: {', '.join(missing)}" if missing else ""))
    assert scored + len(missing) == requested

    ok = [s for s in results.values() if s]
    if len(ok) >= 2:
        base = [s[-1] for s in ok]
        fine = [s[0] + s[1] for s in ok]
        print(f"\nbase-octave share across {len(ok)} subjects : "
              f"{min(base):.2f}% .. {max(base):.2f}%")
        print(f"detail0+detail1 share across {len(ok)} subjects: "
              f"{min(fine):.2f}% .. {max(fine):.2f}%")
        verdict = "CONFIRMED cross-subject" if min(base) > 90 else "NOT cross-subject"
        print(f"\nbase dominance (>90% on every scored subject): {verdict}")
    else:
        print("\nfewer than 2 scorable subjects: NOT cross-subject, do not generalise")
    return 0


if __name__ == "__main__":
    sys.exit(main())

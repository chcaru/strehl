"""Name the mechanism: recover the merge's per-pixel selection and rebuild from it.

The mechanism sweep established WHAT the coffee-bubbles excess is -- genuine
50-400 px structure in the master that no source frame carries -- and refuted
the two innocent explanations. This asks HOW the merge produced it.

A focus stacker chooses, per pixel, which frame is sharpest. That choice is
recoverable without instrumenting the binary: for each pixel, find the frame
whose value the master is closest to. If the merge selects rather than averages,
that nearest frame IS the selection, and its spatial structure is the selection
map.

The decisive step is the RECONSTRUCTION. Build a synthetic master by taking,
at every pixel, the value of the recovered selected frame -- nothing else, no
merge, no filtering -- and measure its blotch. If a pure selection from these
same 19 frames reproduces the excess, then the excess is selection-induced and
the mechanism is named. If it does not, the excess comes from something the
merge adds beyond choosing, and I must say so.

Everything is low-passed to 25 px first, so a few pixels of registration
residual cannot masquerade as a selection boundary. The band is 50-400 px, so
nothing measured here is lost by that.
"""
import argparse
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vn_bubbles as B  # noqa: E402
import vn_lib as L  # noqa: E402
import vn_mech as M  # noqa: E402
from orch_blotch import boxblur, LO_R, HI_R  # noqa: E402

SMOOTH = 12


def blotch(lum):
    band = boxblur(lum, LO_R // 2) - boxblur(lum, HI_R // 2)
    return float(np.std(band)) / max(float(np.mean(lum)), 1e-9)


def recover(mlum, flums, smooth=SMOOTH):
    """Per-pixel nearest frame, the reconstruction from it, and the residual."""
    ms = boxblur(mlum, smooth)
    fs = np.stack([boxblur(f, smooth) for f in flums], 0)
    d = np.abs(fs - ms[None, :, :])
    sel = np.argmin(d, axis=0)
    near = np.take_along_axis(d, sel[None], 0)[0]
    spread = fs.max(0) - fs.min(0)
    recon = np.take_along_axis(fs, sel[None], 0)[0]
    return sel, recon, near, spread, fs


def patchiness(sel, n):
    """Does the selection map have structure at the band's own scale?"""
    oh = np.stack([(sel == k).astype(np.float32) for k in range(n)], 0)
    b = np.stack([boxblur(o, LO_R // 2) - boxblur(o, HI_R // 2) for o in oh], 0)
    lab, nlab = ndimage.label(sel == sel)  # single region; kept for shape only
    runs = []
    for row in sel[::37]:
        c = 1
        for i in range(1, row.size):
            if row[i] == row[i - 1]:
                c += 1
            else:
                runs.append(c)
                c = 1
        runs.append(c)
    return float(np.abs(b).mean()), float(np.median(runs)), float(np.mean(runs))


def report(name, mlum, flums):
    n = len(flums)
    sel, recon, near, spread, fs = recover(mlum, flums)
    per = np.array([blotch(f) for f in flums])
    lo = B.loo_min(per[:, None])[:, 0]
    mb, rb = blotch(mlum), blotch(recon)
    frac = float(np.median(near / np.maximum(spread, 1e-6)))
    amp, medrun, meanrun = patchiness(sel, n)
    used = int(len(np.unique(sel)))
    print("  %-26s %8.5f %9.5f %8.4fx %8.4fx %7.3f %6.0f %5d"
          % (name, mb, rb, mb / max(per.min(), 1e-12),
             rb / max(per.min(), 1e-12), frac, medrun, used))
    return dict(master=mb, recon=rb, ratio_m=mb / max(per.min(), 1e-12),
                ratio_r=rb / max(per.min(), 1e-12), near_frac=frac,
                loo=float(np.median(per / np.maximum(lo, 1e-12))),
                med_run=medrun, mean_run=meanrun, sel_amp=amp, used=used)


def head():
    print("  %-26s %8s %9s %8s %8s %7s %6s %5s"
          % ("arm", "master", "recon", "m ratio", "r ratio", "near", "run",
             "used"))


def focus_synth(rng, n=10, size=600, moving=False, ndisc=26):
    """A synthetic focus stack with REAL frame diversity.

    B.synth's frames differ only by independent noise on a shared field, which
    makes "the merge selected" and "the merge averaged" produce the same image
    and leaves the selection map at run length 1 -- pure noise. Commissioning
    rejected two arms on that fixture and the fault was the fixture.

    Here each frame is sharp over a different depth band, so frames genuinely
    differ pixel by pixel, and `moving` displaces discrete discs between frames
    the way bubbles actually move between exposures.
    """
    yy, xx = np.mgrid[:size, :size].astype(np.float32)
    base = 8000.0 + 120.0 * np.sin(yy / 190.0) * np.cos(xx / 220.0)
    depth = (n - 1) * (0.5 + 0.5 * np.sin(yy / 260.0 + xx / 310.0))
    cy = rng.uniform(40, size - 40, ndisc)
    cx = rng.uniform(40, size - 40, ndisc)
    rad = rng.uniform(18, 40, ndisc)
    amp = rng.uniform(500, 1600, ndisc)
    # Independent per-disc motion. A single global offset per frame is a rigid
    # translation, which leaves every frame's band identical and cannot make
    # frames disagree at mid scale -- the real stack's frames correlate only
    # r=0.18 with each other at the worst tile, so the fixture has to move each
    # disc on its own or it is not modelling this subject at all.
    dy = rng.uniform(-55, 55, (n, ndisc)) if moving else np.zeros((n, ndisc))
    dx = rng.uniform(-55, 55, (n, ndisc)) if moving else np.zeros((n, ndisc))
    frames = []
    for k in range(n):
        s = base.copy()
        for i in range(ndisc):
            d = np.hypot(yy - (cy[i] + dy[k, i]), xx - (cx[i] + dx[k, i]))
            s = s + amp[i] * np.exp(-(d / rad[i]) ** 2)
        sig = 1.0 + 2.2 * np.abs(depth - k)
        levels = [ndimage.gaussian_filter(s, g) for g in (0.6, 3.0, 8.0, 16.0)]
        g = np.clip(sig, 0.6, 16.0)
        w = np.zeros(s.shape, np.float32)
        out = np.zeros(s.shape, np.float32)
        gs = (0.6, 3.0, 8.0, 16.0)
        for j in range(3):
            m = (g >= gs[j]) & (g <= gs[j + 1])
            t = np.zeros(s.shape, np.float32)
            t[m] = (g[m] - gs[j]) / (gs[j + 1] - gs[j])
            out[m] = levels[j][m] * (1 - t[m]) + levels[j + 1][m] * t[m]
            w[m] = 1
        out[w == 0] = levels[0][w == 0]
        frames.append((out + rng.normal(0, 25, s.shape)).astype(np.float32))
    return frames


def commission():
    rng = np.random.default_rng(31)
    frames = focus_synth(rng, n=10, size=600)
    mov = focus_synth(np.random.default_rng(31), n=10, size=600, moving=True)
    master = np.max(np.stack(frames, 0), 0) * 0 + frames[0]
    rows = []
    print("COMMISSIONING  selection recovery, synthetic FOCUS STACK")
    print("  'near' = |master - nearest frame| / frame spread. A SELECTING")
    print("  merge sits near 0; an AVERAGING one sits near 0.5.")
    print("")
    head()

    lab = rng.integers(0, len(frames), (6, 6))
    big = np.kron(lab, np.ones((100, 100), int))[:600, :600]

    def pick(fs):
        return np.take_along_axis(np.stack(fs, 0), big[None], 0)[0]

    base = report("placebo: master = frame 0", master, frames)
    rows.append(("placebo: master = frame 0", "near ~ 0, no excess",
                 base["near_frac"] < 0.10 and base["ratio_m"] < 1.25))

    # A master built BY selection must be recovered as one. This is the
    # positive control for the whole method.
    a = report("selection master, 100px patches", pick(frames), frames)
    rows.append(("selection master, 100px patches",
                 "recovered as a selection, runs >> 1",
                 a["near_frac"] < 0.10 and a["med_run"] > 20))

    # ... and it must be able to say NO. An AVERAGED master is not a selection
    # and must NOT be recovered as one, or the method confirms selection
    # whatever it is shown.
    a = report("averaged master (not a selection)",
               np.mean(np.stack(frames, 0), 0), frames)
    rows.append(("averaged master (not a selection)", "near >= 0.15",
                 a["near_frac"] >= 0.15))

    # THE MECHANISM CLAIM: selection over a MOVING subject makes mid-scale
    # excess; the identical selection over a STATIC one does not.
    amv = report("selection over MOVING frames", pick(mov), mov)
    ast = report("selection over STATIC frames", pick(frames), frames)
    rows.append(("selection over MOVING frames", "excess appears",
                 amv["ratio_m"] > 1.25))
    rows.append(("selection over STATIC frames", "no excess",
                 ast["ratio_m"] < 1.25))

    bad = [r for r in rows if not r[2]]
    print("")
    print("%d ok + %d failed = %d arms"
          % (len(rows) - len(bad), len(bad), len(rows)))
    for r in bad:
        print("  NOT COMMISSIONED: %s (required %s)" % (r[0], r[1]))
    return 0 if not bad else 1


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", action="store_true")
    a = ap.parse_args(argv)
    if a.commission:
        return commission()
    print("REFUSED  selection recovery is not commissioned and is not used.")
    print("")
    print("  Run --commission to see the table. 2 of 5 arms certify; 3 do not,")
    print("  and the reason is a property of focus stacks rather than a bug")
    print("  I could tune away:")
    print("")
    print("    placebo, master IS frame 0     near 0.000, run 600 px, 1 frame")
    print("    averaged master, static stack  near 0.046")
    print("")
    print("  Those are the two ENDPOINTS of the scale -- an exact selection and")
    print("  an outright average -- and they are 0.046 apart. Blur conserves")
    print("  flux, so at 50-400 px every frame of a static stack is nearly the")
    print("  same image, and choosing one is nearly the same as averaging them")
    print("  all. The recovered map's median run length is 2 px against a")
    print("  planted 100 px patch, because wherever two frames agree the")
    print("  per-pixel argmin is arbitrary.")
    print("")
    print("  So I cannot tell from the master alone whether the merge selected")
    print("  or blended, and I do not claim to. The mechanism is named in")
    print("  RESULT.md only as far as the COMMISSIONED instruments reach:")
    print("  genuine mid-scale structure, absent from all 19 frames, on a")
    print("  subject with heavy independent inter-frame motion.")
    print("")
    print("  One directional result did survive and is reported as suggestive")
    print("  only: with the identical planted selection map, moving frames give")
    print("  1.1125x and static frames 1.0571x, so selection over a moving")
    print("  subject does produce mid-scale excess. It did not reach the 1.25x")
    print("  bar I set before running it, and I am not counting it as evidence.")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

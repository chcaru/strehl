"""What a viewer would see in the difference between the two arms.

WHY THIS FILE EXISTS, AND WHAT IT IS NOT
----------------------------------------
The instruction for this build is to judge on pictures, and the standing rule is
that when a picture and a number disagree the picture wins. I cannot render an
image into my own eyes in this environment, and pretending otherwise would be
the exact failure mode this project keeps catching -- a claim with no instrument
under it. So this is NOT a substitute for the owner or a verifier looking. It is
a description, in numbers a human can check against the file, of the things a
human would be looking FOR.

It answers three questions about the difference between the untreated and
treated arms, inside the frozen ROIs:

  IS THERE STRUCTURE?      -- connected components of the difference that clear
                              a visibility threshold set from the LOCAL noise of
                              the untreated arm, not from a fixed DN. A change
                              that is smaller than the grain it sits in is not
                              visible however coherent it is.

  IS IT LINE-LIKE?         -- an "invented hard edge" is long, thin and
                              coherent. A coverage blob is compact. Elongation
                              (component length / width) separates them, and it
                              is the difference between the two artefacts this
                              build has produced.

  IS IT A STEP OR A RAMP?  -- a hard edge is a step, so the difference has a
                              large gradient concentrated on a thin line. A veil
                              being lifted is a ramp, so the same total change
                              is spread out. `step_ratio` is the difference's
                              own p99.9 gradient over its SD: high means the
                              change arrives suddenly, which is what reads as a
                              drawn line rather than as shading.

VISIBILITY THRESHOLD. Set at 3x the untreated arm's local high-pass SD inside
the same ROI. That is deliberately a LOCAL noise reference: a 200 DN change is
glaring in smooth defocused background and invisible in foliage, and a fixed
threshold would call those the same.
"""

import json
import os
import sys

import numpy as np
import tifffile


def read16(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p}: {a.dtype}"
    return a


def luma(a):
    return a.astype(np.float64).mean(axis=2) / 65535.0


def highpass(p):
    pad = np.pad(p, 1, mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    box = c[3:, 3:] - c[:-3, 3:] - c[3:, :-3] + c[:-3, :-3]
    return p - box / 9.0


def components(mask):
    """Connected components, 8-connected, iterative flood fill (no scipy dep)."""
    h, w = mask.shape
    lab = np.zeros((h, w), np.int32)
    cur = 0
    out = []
    for sy in range(h):
        for sx in range(w):
            if not mask[sy, sx] or lab[sy, sx]:
                continue
            cur += 1
            stack = [(sy, sx)]
            lab[sy, sx] = cur
            pts = []
            while stack:
                y, x = stack.pop()
                pts.append((y, x))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not lab[ny, nx]:
                            lab[ny, nx] = cur
                            stack.append((ny, nx))
            out.append(np.array(pts))
    return out


def describe(pts):
    """Elongation and size of one component, by its own principal axes."""
    if len(pts) < 8:
        return None
    c = pts - pts.mean(0)
    cov = (c.T @ c) / len(c)
    ev = np.linalg.eigvalsh(cov)
    ev = np.clip(ev, 1e-9, None)
    length = 4.0 * np.sqrt(ev[1])
    width = 4.0 * np.sqrt(ev[0])
    return len(pts), length, width, length / max(width, 1e-9)


def main():
    plan = json.load(open(sys.argv[1] if len(sys.argv) > 1 else r"C:\dev\strehl-out\roi-plan.json"))
    root = sys.argv[2] if len(sys.argv) > 2 else r"C:\dev\strehl-out\v2ab"
    only = sys.argv[3] if len(sys.argv) > 3 else None

    hdr = (
        f"{'subject':<22} {'roi':<7} {'vis thr':>8} {'vis%':>6} {'blobs':>6} "
        f"{'biggest px':>10} {'len':>6} {'wid':>6} {'elong':>6} {'step_ratio':>10} {'peak DN':>8}"
    )
    print(hdr)
    print("-" * len(hdr))
    for subject in sorted(os.listdir(root)):
        if only and subject != only:
            continue
        off_p = os.path.join(root, subject, "off", "linear.tif")
        on_p = os.path.join(root, subject, "on", "linear.tif")
        if not (os.path.exists(off_p) and os.path.exists(on_p)) or subject not in plan:
            continue
        lo, ln = luma(read16(off_p)), luma(read16(on_p))
        crop = plan[subject]["crop"]
        for cls, ptsl in plan[subject]["rois"].items():
            for i, (x, y) in enumerate(ptsl):
                sl = (slice(y, y + crop), slice(x, x + crop))
                a, b = lo[sl], ln[sl]
                d = (b - a) * 65535.0
                noise = float(highpass(a).std()) * 65535.0
                thr = 3.0 * noise
                mask = np.abs(d) > thr
                vis = 100.0 * mask.mean()
                comps = [c for c in (describe(p) for p in components(mask)) if c]
                comps.sort(key=lambda c: -c[0])
                gx = np.abs(np.diff(d, axis=1)).ravel()
                gy = np.abs(np.diff(d, axis=0)).ravel()
                g = np.concatenate([gx, gy])
                step = float(np.percentile(g, 99.9)) / max(float(d.std()), 1e-9)
                if comps:
                    n, L, W, E = comps[0]
                else:
                    n = L = W = E = 0
                print(
                    f"{subject:<22} {cls + str(i + 1):<7} {thr:>8.1f} {vis:>6.2f} "
                    f"{len(comps):>6} {n:>10} {L:>6.1f} {W:>6.1f} {E:>6.2f} "
                    f"{step:>10.2f} {np.abs(d).max():>8.1f}"
                )
        print()
    print("READING IT:")
    print("  vis%        fraction of the ROI where the change clears 3x the LOCAL grain.")
    print("              0 means nothing a viewer could see, whatever the metrics say.")
    print("  elong       >4 and long = a LINE. An invented hard edge looks like this.")
    print("              ~1-2 and compact = a BLOB. A coverage boundary looks like this.")
    print("  step_ratio  how suddenly the change arrives. High = a drawn edge.")
    print("              Low = shading, which is what lifting a veil should look like.")


if __name__ == "__main__":
    main()

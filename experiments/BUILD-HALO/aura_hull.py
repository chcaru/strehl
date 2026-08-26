"""The per-pixel distribution of frame values at a backdrop pixel, and whether
the merge lies inside the hull of its own inputs.

ORCH asks (question 3) for the per-pixel distribution of frame values at a
d=150 px backdrop pixel: if it is bimodal or heavily skewed dark, an
upper-envelope estimator is justified.

Answering that also settles two things his three-frame sample could not.

**The hull test, which is the load-bearing one.** A gated mean is a convex
combination of the admitted frames, so

    min_k frame_k(p)  <=  merge(p)  <=  max_k frame_k(p)

must hold at every pixel, and it holds for the far-field-referenced excess too,
because the reference is itself a convex combination of the same weights. If
the merge is darker than EVERY frame, it is not a weighted average of these
frames at all -- and then no reweighting fix can reach the clean value, because
no subset average can get there. That would move the defect out of sample
selection entirely. ORCH sampled three frames and reported the merge darker
than all three; with nine the answer may differ by band, and the distinction
decides whether his fix is even reachable.

**The ceiling on his fix.** If the unveiled backdrop is recoverable as an upper
envelope across frames, then max_k frame_k(p) should sit near 0 -- the far-field
level, which is what an unveiled backdrop must equal. If the max is still well
below 0, then no per-frame selection recovers a clean backdrop, because every
frame is veiled there, and the ceiling on ANY sample-selection fix is whatever
the best single frame achieves. That number is the target his own guard names.

Envelope caveat: nine frames sample a 205-frame bracket. The spill is monotone
in |k - 153| across all nine (the subject's focus is near frame 153), so f000,
the bracket endpoint furthest from focus, is the most veiled frame available and
bounds the dark edge of the hull. Frames between the samples cannot be darker
than f000 unless that monotonicity breaks, which is checked and reported.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy.ndimage import distance_transform_edt, binary_closing, binary_opening

SRC = Path(r"C:\dev\strehl-out\ORCH-rim")
OUT = Path(r"C:\dev\strehl-out\AURA")

FRAMES = {0: "f0-lin.tif", 25: "fb-f025-lin.tif", 51: "fb-f051-lin.tif",
          76: "fb-f076-lin.tif", 102: "frame102-lin.tif", 127: "fb-f127-lin.tif",
          153: "fb-f153-lin.tif", 178: "fb-f178-lin.tif", 204: "f204-lin.tif"}
MERGE = "merge-lin.tif"

TARGET = (140, 200)   # ORCH's target band, in TIFF px
FAR = (500, 900)
NSAMPLE = 40000
RNG = np.random.default_rng(20260825)


def luma(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    out = (0.2126 * a[..., 0].astype(np.float32)
           + 0.7152 * a[..., 1].astype(np.float32)
           + 0.0722 * a[..., 2].astype(np.float32)) if a.ndim == 3 \
        else a.astype(np.float32)
    del a
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    f = luma(SRC / FRAMES[102])
    backdrop = float(np.median(f))
    subject = f < 0.5 * backdrop
    del f
    subject = binary_closing(subject, np.ones((9, 9)))
    subject = binary_opening(subject, np.ones((9, 9)))
    dist = distance_transform_edt(~subject)

    tgt = (dist >= TARGET[0]) & (dist < TARGET[1]) & ~subject
    far = (dist >= FAR[0]) & (dist < FAR[1]) & ~subject
    del dist, subject

    idx = np.flatnonzero(tgt.ravel())
    if idx.size < NSAMPLE:
        print(f"  FATAL: target band has only {idx.size} px")
        return 2
    # One frozen pixel sample, drawn once and reused for every arm, so all arms
    # are read at the SAME pixels and no arm can move its own goalposts.
    pick = RNG.choice(idx, size=NSAMPLE, replace=False)
    far_idx = np.flatnonzero(far.ravel())
    del tgt, far
    print(f"target band d={TARGET[0]}-{TARGET[1]} px: {idx.size:,} px, "
          f"sampled {NSAMPLE:,}")

    keys = sorted(FRAMES)
    vals = np.zeros((len(keys), NSAMPLE), dtype=np.float32)
    for j, k in enumerate(keys):
        img = luma(SRC / FRAMES[k]).ravel()
        ref = float(np.median(img[far_idx]))
        vals[j] = img[pick] - ref
        del img
        print(f"  frame {k:3d}: median excess {np.median(vals[j]):9.1f} DN")

    img = luma(SRC / MERGE).ravel()
    ref = float(np.median(img[far_idx]))
    merge = img[pick] - ref
    del img
    print(f"  MERGE    : median excess {np.median(merge):9.1f} DN")

    # ---- monotonicity, so the envelope caveat is checked not assumed -------
    med = np.array([float(np.median(vals[j])) for j in range(len(keys))])
    focus_k = keys[int(np.argmax(med))]
    lo_side = med[: keys.index(focus_k) + 1]
    mono = bool(np.all(np.diff(lo_side) >= 0))
    print(f"\n  shallowest spill at frame {focus_k}; spill monotone on the "
          f"defocused side: {mono}")
    if not mono:
        print("  WARNING: f000 may not bound the dark edge of the hull")

    # ---- the hull test ----------------------------------------------------
    fmin = vals.min(axis=0)
    fmax = vals.max(axis=0)
    below = float((merge < fmin).mean())
    above = float((merge > fmax).mean())
    # How far outside, in DN, where it is outside at all.
    depth = float(np.median((fmin - merge)[merge < fmin])) if below else 0.0

    print()
    print(f"  merge BELOW every sampled frame : {100*below:6.2f}% of pixels")
    print(f"  merge ABOVE every sampled frame : {100*above:6.2f}% of pixels")
    if below:
        print(f"    median depth below the hull   : {depth:8.1f} DN")

    # Where in the frame distribution does the merge sit?
    rank = (vals < merge[None, :]).sum(axis=0) / len(keys)
    print(f"  merge's median rank within the 9 frames: {np.median(rank):.3f}"
          f"   (0.5 = a plain mean would sit here)")

    # ---- the distribution shape, which is ORCH's question 3 ---------------
    print()
    print("  per-pixel distribution across the 9 frames (median over pixels):")
    qs = [0, 12, 25, 50, 75, 88, 100]
    pct = np.percentile(vals, qs, axis=0)
    for q, row in zip(qs, pct):
        print(f"    p{q:3d} : {np.median(row):9.1f} DN")

    spread = np.median(fmax - fmin)
    skew_lo = np.median(np.median(vals, axis=0) - fmin)
    skew_hi = np.median(fmax - np.median(vals, axis=0))
    print(f"\n    full spread max-min      : {spread:9.1f} DN")
    print(f"    median - min (dark tail) : {skew_lo:9.1f} DN")
    print(f"    max - median (light tail): {skew_hi:9.1f} DN")
    print(f"    skew ratio dark/light    : {skew_lo / max(skew_hi, 1e-6):9.2f}"
          f"   (>1 means a long DARK tail)")

    # ---- the ceiling on any sample-selection fix --------------------------
    print()
    print("  what each estimator would deliver on this band (0 = clean "
          "backdrop):")
    print(f"    merge (shipped)          : {np.median(merge):9.1f} DN")
    print(f"    best single frame (f{focus_k:03d}) : "
          f"{med[keys.index(focus_k)]:9.1f} DN   <- ORCH's floor")
    print(f"    upper envelope (max_k)   : {np.median(fmax):9.1f} DN   "
          f"<- ORCH's proposed estimator")
    print(f"    p88 across frames        : {np.median(pct[5]):9.1f} DN")

    gain_env = np.median(merge) - np.median(fmax)
    print(f"\n    upper envelope beats the merge by {abs(gain_env):.1f} DN")
    if np.median(fmax) > -400:
        print("    => the unveiled backdrop IS recoverable from the stack.")
    else:
        print("    => even the least-veiled frame is still veiled here; no")
        print("       per-frame SELECTION recovers a clean backdrop, and the")
        print("       ceiling on any sample-selection fix is that number.")

    np.savez(OUT / "aura_hull.npz", keys=np.array(keys), vals=vals,
             merge=merge, pick=pick)

    # ---- the picture: the actual per-pixel through-frame curves -----------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(1, 2, figsize=(13, 5), dpi=110)
        sel = RNG.choice(NSAMPLE, size=60, replace=False)
        for s in sel:
            ax[0].plot(keys, vals[:, s], color="0.7", lw=0.7)
        ax[0].plot(keys, med, "o-", color="crimson", lw=2.5,
                   label="median across pixels")
        ax[0].axhline(float(np.median(merge)), color="navy", lw=2.5, ls="--",
                      label=f"MERGE ({np.median(merge):.0f} DN)")
        ax[0].axhline(0, color="k", lw=1, label="clean backdrop (far field)")
        ax[0].set_xlabel("frame index")
        ax[0].set_ylabel("backdrop excess over far field (DN)")
        ax[0].set_title(f"through-frame response, backdrop d={TARGET[0]}-"
                        f"{TARGET[1]} px")
        ax[0].legend(fontsize=8)
        ax[1].hist(vals.ravel()[RNG.choice(vals.size, 200000, replace=False)],
                   bins=120, color="0.5")
        ax[1].axvline(float(np.median(merge)), color="navy", lw=2, ls="--")
        ax[1].axvline(0, color="k", lw=1)
        ax[1].set_xlabel("frame value, excess over far field (DN)")
        ax[1].set_title("pooled distribution of frame values")
        fig.tight_layout()
        p = OUT / "AURA-hull.png"
        fig.savefig(p)
        assert p.read_bytes()[:4] == b"\x89PNG"
        print(f"\n  wrote {p}")
    except Exception as exc:  # noqa: BLE001
        print(f"  plot failed: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""S2 -- ROI selection, by the rule frozen in PRE-REGISTRATION.md.

Candidates are scored from the FRAMES alone. No merge output is read here, so
the windows cannot have been chosen to flatter or damn the merge.
"""

from __future__ import annotations

import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import m95lib as L  # noqa: E402

WIN = 512
STRIDE = 256
BORDER = 64
NSAMP = 20
USABLE_WHITE = 15360.0  # the binary's own usable white level; R4 re-derived it


def frame_paths():
    fs = sorted(f for f in os.listdir(L.STACK) if f.lower().endswith(".arw"))
    return [os.path.join(L.STACK, f) for f in fs]


def highpass_energy(plane: np.ndarray) -> np.ndarray:
    """Per-pixel squared high-pass response, sigma = 2 plane px."""
    lo = L.gaussian_blur(plane, 2.0)
    d = plane - lo
    return d * d


def main() -> int:
    paths = frame_paths()
    n = len(paths)
    idxs = np.linspace(0, n - 1, NSAMP).round().astype(int)
    print(f"stack          : {L.STACK}  ({n} frames)")
    print(f"sampled        : {list(idxs)}")

    drift = json.load(
        open(
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "out", "s1_drift.json"),
            encoding="utf-8",
        )
    )
    A = np.array(drift["a_re"]) + 1j * np.array(drift["a_im"])
    B = np.array(drift["b_re"]) + 1j * np.array(drift["b_im"])

    peak = None
    peak_idx = None
    clipped_any = None
    t0 = time.time()
    for k, i in enumerate(idxs):
        rf = L.decode_raw(paths[i])
        if clipped_any is None:
            clipped_any = np.zeros(
                (rf.cfa.shape[0] // 2, rf.cfa.shape[1] // 2), dtype=bool
            )
        g = L.green_mean_plane(rf.cfa) - 512.0
        e = highpass_energy(g)
        # A quad is "clipped" if any of its four samples is at or above the
        # usable white level.
        c = rf.cfa >= USABLE_WHITE
        cq = c[0::2, 0::2] | c[0::2, 1::2] | c[1::2, 0::2] | c[1::2, 1::2]
        h, w = e.shape
        clipped_any[:h, :w] |= cq[:h, :w]
        if peak is None:
            peak = e
            peak_idx = np.full(e.shape, i, dtype=np.int32)
        else:
            m = e > peak
            peak = np.where(m, e, peak)
            peak_idx = np.where(m, i, peak_idx)
        print(f"  [{k+1:2d}/{NSAMP}] frame {i:3d}  {time.time()-t0:6.1f}s", flush=True)

    H, W = peak.shape
    print(f"plane          : {W} x {H}   (rawpy visible area, binned)")
    print(f"ever clipped   : {100.0*clipped_any.mean():.4f}% of quads in the sampled frames")

    rows = []
    for y in range(BORDER, H - WIN - BORDER + 1, STRIDE):
        for x in range(BORDER, W - WIN - BORDER + 1, STRIDE):
            sl = (slice(y, y + WIN), slice(x, x + WIN))
            if clipped_any[sl].any():
                continue
            score = float(peak[sl].mean())
            cx, cy = x + WIN / 2, y + WIN / 2
            z = complex(cx, cy)
            t = A * z + B
            step = float(np.median(np.abs(np.diff(t))))
            span = float(np.abs(t - t[drift["reference"]]).max())
            # modal coarse peak frame in this window
            vals, cnts = np.unique(peak_idx[sl], return_counts=True)
            rows.append(
                dict(
                    x=x,
                    y=y,
                    cx=cx,
                    cy=cy,
                    score=score,
                    drift_per_step_px=step,
                    drift_span_px=span,
                    coarse_peak_frame=int(vals[np.argmax(cnts)]),
                )
            )

    rows.sort(key=lambda r: -r["score"])
    print(f"windows        : {len(rows)} candidates, none clipped")
    print()
    print("top 8 by through-focus peak detail:")
    for r in rows[:8]:
        print(
            f"  ({r['x']:5d},{r['y']:5d})  score {r['score']:11.1f}  "
            f"drift/step {r['drift_per_step_px']:6.3f} px  span {r['drift_span_px']:7.1f} px  "
            f"coarse peak frame {r['coarse_peak_frame']:3d}"
        )

    # Stratify by MEASURED local drift, which is what the pre-registration's
    # radius stratification was reaching for. Terciles of the candidate set.
    steps = np.array([r["drift_per_step_px"] for r in rows])
    q1, q2 = np.quantile(steps, [1 / 3, 2 / 3])
    print(f"\ndrift/step terciles over candidates: {q1:.3f} px, {q2:.3f} px")

    def best_in(lo, hi):
        cand = [r for r in rows if lo <= r["drift_per_step_px"] < hi]
        return cand[0] if cand else None

    chosen = {
        "ROI-LOWDRIFT": best_in(-1e9, q1),
        "ROI-MIDDRIFT": best_in(q1, q2),
        "ROI-HIGHDRIFT": best_in(q2, 1e9),
        "ROI-FLAT": rows[-1],
    }
    print()
    for name, r in chosen.items():
        print(
            f"{name:<14} ({r['x']:5d},{r['y']:5d})  score {r['score']:11.1f}  "
            f"drift/step {r['drift_per_step_px']:6.3f} px  coarse peak frame {r['coarse_peak_frame']:3d}"
        )

    out = {
        "win": WIN,
        "stride": STRIDE,
        "border": BORDER,
        "sampled_frames": [int(i) for i in idxs],
        "plane_shape": [int(H), int(W)],
        "clipped_frac": float(clipped_any.mean()),
        "n_candidates": len(rows),
        "terciles": [float(q1), float(q2)],
        "chosen": chosen,
        "all": rows,
    }
    dst = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out", "s2_rois.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote          : {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

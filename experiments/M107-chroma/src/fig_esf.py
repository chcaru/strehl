"""Render the evidence for individual ROIs: the ROI itself, and the per-channel
edge-spread scatter with its fit. Discipline: never interpret a spatial statistic
without rendering it.

Every panel states the stretch applied.
"""
import sys, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(__file__))
from common import (decode, frames, planes_of, plane_coords, esf_all_planes,
                    summarise, _erf_edge, OUT, PLANES)
from edges import green_of

COL = {"R": "#d62728", "G1": "#2ca02c", "G2": "#7fbf5f", "B": "#1f77b4"}


def panel(ax_img, ax_esf, cfa, x0, y0, size, title):
    roi = cfa[y0:y0 + size, x0:x0 + size]
    e = esf_all_planes(roi, x0=x0, y0=y0)
    g = green_of(roi)
    lo, hi = np.percentile(g, 1), np.percentile(g, 99)
    ax_img.imshow(g, cmap="gray", vmin=lo, vmax=hi, interpolation="nearest")
    ax_img.set_title(title, fontsize=7)
    ax_img.set_xticks([]); ax_img.set_yticks([])
    ax_img.set_xlabel(f"green plane, linear, stretch p1-p99 ({lo:.0f}-{hi:.0f} DN)",
                      fontsize=5)
    if e is None:
        ax_esf.text(0.5, 0.5, "no edge fit", ha="center"); return None
    n = np.array(e["normal"]); p = np.array(e["point"])
    pl = planes_of(roi)
    for name in PLANES:
        v = pl[name]
        X, Y = plane_coords(name, v.shape[0], v.shape[1], x0, y0)
        d = (X - p[0]) * n[0] + (Y - p[1]) * n[1]
        keep = np.abs(d) <= 12.0
        dd, vv = d[keep], v.astype(np.float64)[keep]
        f = e["planes"][name]
        # normalise each plane to its own fitted asymptotes so the four are
        # comparable in POSITION; amplitudes differ by scene colour and gains.
        a, b = None, None
        fit_d = np.linspace(-12, 12, 400)
        # recover a,b by least squares against the fitted shape
        from scipy.special import erf
        s = erf((dd - f["d0"]) / (np.sqrt(2) * f["w"]))
        A = np.vstack([np.ones_like(s), s]).T
        coef, *_ = np.linalg.lstsq(A, vv, rcond=None)
        a, b = coef
        norm = (vv - a) / (2 * b) + 0.5
        ax_esf.plot(dd, norm, ".", ms=1.2, color=COL[name], alpha=0.35)
        ax_esf.plot(fit_d, (_erf_edge(fit_d, a, b, f["d0"], f["w"]) - a) / (2 * b) + 0.5,
                    "-", lw=1.1, color=COL[name],
                    label=f"{name} d0={f['d0']:+.3f} w={f['w']:.2f}")
        ax_esf.axvline(f["d0"], color=COL[name], lw=0.6, ls=":")
    ax_esf.set_xlim(-8, 8); ax_esf.set_ylim(-0.15, 1.15)
    ax_esf.legend(fontsize=5, loc="lower right", framealpha=0.9)
    ax_esf.set_xlabel("distance along edge normal (sensel)", fontsize=6)
    ax_esf.set_ylabel("normalised to own asymptotes", fontsize=6)
    ax_esf.tick_params(labelsize=5)
    ax_esf.grid(alpha=0.25, lw=0.4)
    return summarise(e)


def main(stack, rois, out_name, size=96):
    fs = frames(stack)
    nrow = len(rois)
    fig, axes = plt.subplots(nrow, 2, figsize=(9.5, 2.4 * nrow),
                             gridspec_kw={"width_ratios": [1, 2.3]})
    if nrow == 1:
        axes = axes[None, :]
    for i, (k, x0, y0, tag) in enumerate(rois):
        cfa, _, _ = decode(fs[k])
        s = panel(axes[i, 0], axes[i, 1], cfa, x0, y0, size,
                  f"{stack} f{k} @({x0},{y0})  {tag}")
        if s:
            axes[i, 1].set_title(
                f"dR={s['dR']:+.3f}  dB={s['dB']:+.3f}  "
                f"G1-G2 null={s['null_dG']:+.3f} sensel", fontsize=7)
    fig.suptitle(
        "M107 Instrument A -- per-channel edge-spread fit on RAW CFA planes.\n"
        "Each plane is plotted at its TRUE sensel coordinate, so the CFA lattice "
        "offset is already removed; any separation of the dotted lines is optical.",
        fontsize=8)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    p = os.path.join(OUT, "fig", out_name)
    fig.savefig(p, dpi=150)
    print("wrote", p)


if __name__ == "__main__":
    main("tweezers-cpl",
         [(56, 4288, 4288, "the +1.8 sensel cluster"),
          (39, 1216, 1600, "a blown-up fit (dR=-265)"),
          (63, 4480, 1984, "small |dR|, tangential normal"),
          (67, 6400, 4288, "outer, +1.8 cluster")],
         "M107-fig1-esf-tweezers.png")

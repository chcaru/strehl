"""M107 figures 3-5.

fig3  the radial model for hypothesis (a): measured vs predicted per gated ROI,
      the signal against the NULL, and the permutation null distribution.
fig4  the fringing itself at 1:1 from the shipped render, with a scale bar and
      the per-channel decomposition that makes the fringe colour explicit.
fig5  the attribution summary: per-stack axial offset and the focus energy the
      shipped single election forfeits, both against their nulls.

Every panel states its stretch.  No diagnostic stretch is shown without saying
so on the figure.
"""
import sys, os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT

GAL = r"C:\dev\strehl-out\ORCH-gallery3"
FIG = os.path.join(OUT, "fig")


def J(name):
    d = json.load(open(os.path.join(OUT, "json", name)))
    return d["data"] if isinstance(d, dict) and "data" in d else d


def srgb_to_linear(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


# ---------------------------------------------------------------- fig 3
def fig3():
    from e2_lateral import gated, fit_radial
    rows = json.load(open(os.path.join(OUT, "json", "e1_raw_edges.json")))["rows"]
    keep, _ = gated(rows)
    fig, ax = plt.subplots(1, 3, figsize=(16, 5))

    for key, col, lab in (("dR", "tab:red", "R - G  (SIGNAL)"),
                          ("dB", "tab:blue", "B - G  (SIGNAL)"),
                          ("null_dG", "0.45", "G1 - G2  (NULL)")):
        f = fit_radial(keep, key)
        nx = np.array([r["normal"][0] for r in keep])
        ny = np.array([r["normal"][1] for r in keep])
        rx = np.array([r["rx"] for r in keep]); ry = np.array([r["ry"] for r in keep])
        cx, cy = f["centre_sensel"]
        pred = f["eps"] * ((rx - cx) * nx + (ry - cy) * ny)
        meas = np.array([r[key] for r in keep])
        ax[0].scatter(pred, meas, s=34, c=col, alpha=0.85,
                      label=f"{lab}   R²={f['r2']:+.4f}")
    lim = 3.0
    ax[0].plot([-lim, lim], [-lim, lim], "k--", lw=1, label="y = x (perfect model)")
    ax[0].set_xlim(-lim, lim); ax[0].set_ylim(-lim, lim)
    ax[0].set_xlabel("radial model prediction  eps*((r-r0).n)   [source sensel]")
    ax[0].set_ylabel("measured displacement along edge normal  [source sensel]")
    ax[0].set_title(f"(a) lateral CA: radial model vs measurement\n"
                    f"{len(keep)} gated ROIs, 2 stacks. Stretch: none, linear axes.",
                    fontsize=9)
    ax[0].legend(fontsize=7); ax[0].grid(alpha=0.3)

    # permutation nulls
    for key, col, lab in (("dR", "tab:red", "R - G (SIGNAL)"),
                          ("null_dG", "0.45", "G1 - G2 (NULL)")):
        f = fit_radial(keep, key)
        d = np.array([r[key] for r in keep])
        nx = np.array([r["normal"][0] for r in keep])
        ny = np.array([r["normal"][1] for r in keep])
        rx = np.array([r["rx"] for r in keep]); ry = np.array([r["ry"] for r in keep])
        ss_tot = float(np.sum((d - d.mean()) ** 2))
        rng = np.random.default_rng(107); nullv = []
        for _ in range(2000):
            p = rng.permutation(len(keep))
            A = np.column_stack([rx * nx[p] + ry * ny[p], -nx[p], -ny[p]])
            c2, *_ = np.linalg.lstsq(A, d, rcond=None)
            nullv.append(1 - np.sum((d - A @ c2) ** 2) / max(ss_tot, 1e-12))
        ax[1].hist(nullv, bins=50, alpha=0.5, color=col,
                   label=f"{lab} permuted normals")
        ax[1].axvline(f["r2"], color=col, lw=2,
                      label=f"{lab} actual R²={f['r2']:+.4f}")
    ax[1].set_xlabel("R² of the radial fit")
    ax[1].set_ylabel("permutations (of 2000)")
    ax[1].set_title("Permutation null: edge normals shuffled between ROIs.\n"
                    "Destroys the geometric pairing, preserves both marginals.\n"
                    "Stretch: none, linear axes.", fontsize=9)
    ax[1].legend(fontsize=7)

    # magnitude vs radius
    r = np.array([x["radius"] for x in keep])
    for key, col, lab in (("dR", "tab:red", "|R - G|  SIGNAL"),
                          ("dB", "tab:blue", "|B - G|  SIGNAL"),
                          ("null_dG", "0.45", "|G1 - G2|  NULL")):
        ax[2].scatter(r, np.abs([x[key] for x in keep]), s=30, c=col,
                      alpha=0.85, label=lab)
    f = fit_radial(keep, "dR")
    rr = np.linspace(0, r.max() * 1.05, 50)
    ax[2].plot(rr, abs(f["eps"]) * rr, "r--", lw=1,
               label=f"|eps_R| * r,  eps_R = {f['eps']*1e6:+.0f} ppm")
    ax[2].set_xlabel("ROI radius from frame centre  [source sensel]")
    ax[2].set_ylabel("|displacement|  [source sensel]")
    ax[2].set_title("Magnitude vs radius. Lateral CA is linear through zero;\n"
                    "cos(normal, radial) scatters points BELOW the line only.\n"
                    "Stretch: none, linear axes.", fontsize=9)
    ax[2].legend(fontsize=7); ax[2].grid(alpha=0.3)

    fig.suptitle("M107 fig3 -- hypothesis (a), lateral chromatic aberration. "
                 "Instrument A on RAW CFA planes, sampled at true sensel "
                 "coordinates so co-siting is removed by construction.",
                 fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p = os.path.join(FIG, "M107-fig3-lateral-radial.png")
    fig.savefig(p, dpi=110); print("wrote", p)


# ---------------------------------------------------------------- fig 4
def _pick_roi(img, S, rmin_frac=0.45):
    """Find the S x S window, at radius >= rmin_frac of the half-diagonal, where
    edge-scale chroma fringing is strongest.

    Fringing is NOT the same thing as subject colour: a brown hair has R > G
    everywhere on it and that is chromaticity, not a fringe.  A fringe is an
    edge-scale SIGN REVERSAL of R-G across the edge.  So the ROI is chosen on
    the high-pass of R-G, weighted by green edge energy, which is zero for a
    uniformly coloured region however saturated it is.
    """
    from scipy.ndimage import gaussian_filter, uniform_filter, sobel
    lin = srgb_to_linear(img.astype(np.float64) / 65535.0)
    g = lin[..., 1]
    d = lin[..., 0] - g
    hp = d - gaussian_filter(d, 6.0)                    # edge-scale chroma only
    ge = np.hypot(sobel(g, 0, mode="nearest"), sobel(g, 1, mode="nearest"))
    score = uniform_filter(np.abs(hp) * ge, 65, mode="nearest")
    H, W = g.shape
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx - W / 2.0, yy - H / 2.0)
    score[r < rmin_frac * np.hypot(W / 2.0, H / 2.0)] = 0
    score[: S, :] = 0; score[-S:, :] = 0
    score[:, : S] = 0; score[:, -S:] = 0
    iy, ix = np.unravel_index(np.argmax(score), score.shape)
    return int(ix - S // 2), int(iy - S // 2)


def fig4():
    """1:1 crops of the shipped render with the per-channel decomposition."""
    from scipy.ndimage import gaussian_filter
    picks = [("bee-3-cpl", "bee hairs (orchestrator saw magenta/orange)"),
             ("leaf-2-cpl", "leaf edge (orchestrator saw cyan)"),
             ("tweezers-cpl", "tweezers metal (achromatic subject)")]
    n = len(picks)
    S = 220
    fig, ax = plt.subplots(n, 3, figsize=(14, 4.6 * n))
    for i, (stack, lab) in enumerate(picks):
        img = tifffile.imread(os.path.join(GAL, f"{stack}.tif"))
        H, W = img.shape[:2]
        x, y = _pick_roi(img, S)
        c = img[y:y + S, x:x + S].astype(np.float64) / 65535.0
        rad = np.hypot(x + S / 2 - W / 2.0, y + S / 2 - H / 2.0)

        ax[i, 0].imshow(np.clip(c, 0, 1), interpolation="nearest")
        ax[i, 0].set_title(f"{stack}  --  {lab}\n1:1, no resampling. ROI centre "
                           f"r = {rad:.0f} px from frame centre", fontsize=8)
        ax[i, 0].set_xlabel("Stretch: NONE. Shipped --srgb --auto-exposure "
                            "output, shown as encoded.", fontsize=7)
        ax[i, 0].plot([10, 110], [S - 12, S - 12], "-", color="w", lw=3)
        ax[i, 0].plot([10, 110], [S - 12, S - 12], "-", color="k", lw=1)
        ax[i, 0].text(12, S - 18, "100 output px", color="w", fontsize=7)

        lin = srgb_to_linear(c)
        g = lin[..., 1]
        for j, (ch, name) in enumerate(((0, "R - G"), (2, "B - G"))):
            d = lin[..., ch] - g
            hp = d - gaussian_filter(d, 6.0)
            v = float(np.percentile(np.abs(hp), 99.5)) or 1e-6
            im = ax[i, 1 + j].imshow(hp, cmap="coolwarm", vmin=-v, vmax=v,
                                     interpolation="nearest")
            ax[i, 1 + j].set_title(f"{name}, high-passed (sigma = 6 px)",
                                   fontsize=8)
            ax[i, 1 + j].set_xlabel(
                f"DIAGNOSTIC STRETCH: coolwarm, symmetric +/-{v:.4f} in linear\n"
                f"reflectance (99.5th pct of |high-pass|). The low-frequency\n"
                f"SUBJECT COLOUR is removed, so what remains is edge-scale only.\n"
                f"A fringe reads as a RED/BLUE PAIR straddling one edge.",
                fontsize=6.5)
            plt.colorbar(im, ax=ax[i, 1 + j], fraction=0.046)
        for a in ax[i]:
            a.set_xticks([]); a.set_yticks([])
    fig.suptitle("M107 fig4 -- the fringing itself, in the shipped demosaic "
                 "render. ROIs chosen automatically as the strongest edge-scale "
                 "chroma in the outer frame.\nColour matrix NOT inverted, so "
                 "these amplitudes are LOWER BOUNDS.", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.subplots_adjust(hspace=0.55)
    p = os.path.join(FIG, "M107-fig4-fringe-crops.png")
    fig.savefig(p, dpi=110); print("wrote", p)


# ---------------------------------------------------------------- fig 5
def fig5():
    e6 = J("e6_all.json")
    e3 = J("e3_argmax.json")
    seen, rows = set(), []
    for r in e6:
        if r["tag"] in ("payoff", "no-CPL") and r["stack"] not in seen:
            seen.add(r["stack"]); rows.append(r)
    for r in e3:
        if r["stack"] not in seen:
            seen.add(r["stack"])
            rows.append({"stack": r["stack"], "median_dR": r["median_dR"],
                         "median_dB": r["median_dB"],
                         "median_null": r["median_null"]})
    rows.sort(key=lambda r: r["stack"])
    names = [r["stack"] + ("" if "cpl" in r["stack"] else "  (no CPL)")
             for r in rows]
    x = np.arange(len(rows)); w = 0.27

    fig, ax = plt.subplots(1, 2, figsize=(15, 5.5))
    ax[0].bar(x - w, [r["median_dR"] for r in rows], w, color="tab:red",
              label="k_R - k_G  SIGNAL")
    ax[0].bar(x, [r["median_dB"] for r in rows], w, color="tab:blue",
              label="k_B - k_G  SIGNAL")
    ax[0].bar(x + w, [r["median_null"] for r in rows], w, color="0.45",
              label="k_G1 - k_G2  NULL")
    for xi, r in zip(x, rows):
        ax[0].annotate(f"{r['median_null']:+.4f}", (xi + w, 0),
                       textcoords="offset points", xytext=(0, 6),
                       ha="center", fontsize=6, rotation=90, color="0.25")
    ax[0].axhline(0, color="k", lw=0.8)
    ax[0].set_xticks(x); ax[0].set_xticklabels(names, rotation=20, ha="right",
                                               fontsize=7)
    ax[0].set_ylabel("frame-of-best-focus offset  [frames]")
    ax[0].set_title("(b) axial CA: every stack puts BOTH R and B before green.\n"
                    "The NULL bar is the same quantity between the two greens.\n"
                    "Stretch: none, linear axis.", fontsize=9)
    ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3, axis="y")

    have = [r for r in rows if "median_loss_R" in r]
    xx = np.arange(len(have))
    ax[1].bar(xx - w, [r["median_loss_R"] * 100 for r in have], w,
              color="tab:red", label="R forfeited")
    ax[1].bar(xx, [r["median_loss_B"] * 100 for r in have], w,
              color="tab:blue", label="B forfeited")
    ax[1].bar(xx + w, [r["median_loss_NULL"] * 100 for r in have], w,
              color="0.45", label="NULL floor (G1 elected at G2's frame)")
    for xi, r in zip(xx, have):
        ax[1].annotate(f"{r['median_loss_NULL']*100:.2f}%", (xi + w, 0),
                       textcoords="offset points", xytext=(0, 6),
                       ha="center", fontsize=6, rotation=90, color="0.25")
    ax[1].set_xticks(xx)
    ax[1].set_xticklabels([r["stack"] for r in have], rotation=20, ha="right",
                          fontsize=7)
    ax[1].set_ylabel("gradient energy forfeited to the shared election  [%]")
    ax[1].set_title("What the single election costs the off-channels.\n"
                    "Stretch: none, linear axis.", fontsize=9)
    ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3, axis="y")

    fig.suptitle("M107 fig5 -- hypothesis (b) attribution and cost. "
                 "Instrument B, RAW CFA planes, no demosaic anywhere in the "
                 "measurement path.", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    p = os.path.join(FIG, "M107-fig5-axial-summary.png")
    fig.savefig(p, dpi=110); print("wrote", p)


if __name__ == "__main__":
    which = sys.argv[1:] or ["3", "4", "5"]
    if "3" in which: fig3()
    if "4" in which: fig4()
    if "5" in which: fig5()

"""H5: does the focus measure reward edge DENSITY rather than edge SHARPNESS?

THE HYPOTHESIS (owner's). A box mean of |grad| answers "how much edge energy is in
this window", not "is this window in focus". Blur approximately conserves total
variation, so for a fringe of fine hairs over a bright backdrop the defocused frame
can carry as much or more windowed gradient energy than the focused one: each hair
smears wider, the smears overlap, and more of them fall inside the window. If the
defocused sum wins, the election renders that pixel from a frame in which the hair
fringe has smeared into a pale wash over the backdrop -- a bright scalloped band
whose lobes sit at hair positions, which is what the picture shows.

THE PREDICTION IT MAKES. A statistic that is not TV-conserving should not be fooled.
Peak gradient falls monotonically under blur, so a box MAX of |grad| should elect
the focused frame where the box MEAN elects a defocused one -- at defect pixels,
and not at control pixels.

WHAT IS COMPARED. Six statistics over the identical window (r = 13), on the identical
ladder frames, with the identical median-over-centre readout:

  mean|g|      what focus.rs ships
  mean|g|^2    same family, more weight on peaks
  mean|g|^4    further along that family
  max|g|       H5's proposal, the extreme of that family
  hp mean|g|   BUILD-ELECT section 4's proposal: high-pass first, then box mean
  hp max|g|    both remedies at once

All six are O(1) per pixel with integral images or van Herk/Gil-Werman, so this is a
choice of statistic and not a speed trade.

THE CONTROL THAT MATTERS. mean|g| must reproduce the shipped election, or the
comparison is not about the shipped election. And at ROIs where the shipped election
is correct by eye, max|g| must AGREE with it. A statistic that disagrees everywhere
is not a fix, it is a different bug.
"""
import argparse
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, maximum_filter, uniform_filter

WINDOW_RADIUS = 13
LOW_SIGMA = 8.0
MEASURE_HALF = 60

SUBJECTS = {
    "flower-bud": {
        "out": pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT"),
        "ref": np.array([17000.0, 17000.0, 17000.0]),
        # (median, p5, p95) elected index from the align-off election, as in
        # focusdecomp.py. The band is the honest target: an ROI elects a spread of
        # indices, not one, and scoring against the median alone failed a control
        # (subject-sharp, shipped median f66 over a band [36,74]) that was in fact
        # electing the same mode.
        "elected": {"pale-wash": (133, 110, 156), "leaf-infocus": (37, 34, 40),
                    "dark-patch": (22, 21, 46), "subject-sharp": (66, 36, 74)},
        # ROIs where the shipped election is correct by eye: max must agree here
        "controls": ["leaf-infocus", "subject-sharp"],
        "defects": ["pale-wash"],
    },
    "bee": {
        "out": pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee"),
        "ref": np.array([19093.0, 20163.0, 21361.0]),
        "elected": None,     # read from bee-rois.json
        "controls": ["leg-good", "bee-sharp"],
        "defects": ["blob", "fringe", "fringe-ok"],
    },
}


def sobel_mag(a):
    """focus.rs gradient_magnitude, including its 0.125 scaling and edge clamp."""
    p = np.pad(a, 1, mode="edge")
    gx = (p[:-2, 2:] + 2.0 * p[1:-1, 2:] + p[2:, 2:]
          - p[:-2, :-2] - 2.0 * p[1:-1, :-2] - p[2:, :-2]) * 0.125
    gy = (p[2:, :-2] + 2.0 * p[2:, 1:-1] + p[2:, 2:]
          - p[:-2, :-2] - 2.0 * p[:-2, 1:-1] - p[:-2, 2:]) * 0.125
    return np.hypot(gx, gy)


def stats_of(L):
    """The six statistics, all over the same (2r+1)^2 window, plus two diagnostics."""
    n = 2 * WINDOW_RADIUS + 1
    low = gaussian_filter(L, LOW_SIGMA, mode="nearest")
    g = sobel_mag(L)
    gh = sobel_mag(L - low)
    gl = sobel_mag(low)
    return {
        "mean|g|":   uniform_filter(g, n, mode="nearest"),
        "mean|g|^2": uniform_filter(g ** 2, n, mode="nearest") ** 0.5,
        "mean|g|^4": uniform_filter(g ** 4, n, mode="nearest") ** 0.25,
        "max|g|":    maximum_filter(g, size=n, mode="nearest"),
        "hp mean|g|": uniform_filter(gh, n, mode="nearest"),
        "hp max|g|":  maximum_filter(gh, size=n, mode="nearest"),
        # Diagnostics, not candidate statistics: the peak gradient carried by the
        # veil ramp alone and by the texture alone. If the ramp's best peak beats
        # the texture's best peak, then NO order statistic of |grad| on the full
        # luma can elect the texture frame, and H5's axis is the wrong axis.
        "_lp max|g|": maximum_filter(gl, size=n, mode="nearest"),
        "_hp max|g|": maximum_filter(gh, size=n, mode="nearest"),
    }


CANDIDATES = ["mean|g|", "mean|g|^2", "mean|g|^4", "max|g|", "hp mean|g|", "hp max|g|"]


def centre(a):
    c = a.shape[0] // 2
    return a[c - MEASURE_HALF:c + MEASURE_HALF, c - MEASURE_HALF:c + MEASURE_HALF]


def tone(rgb, ref):
    return np.clip(rgb.astype(np.float64) / (ref / 0.92), 0, 1) ** (1 / 2.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", choices=list(SUBJECTS), default="flower-bud")
    ap.add_argument("--tag", default="crops")
    args = ap.parse_args()

    cfg = SUBJECTS[args.subject]
    OUT = cfg["out"]
    PICS = OUT / "pics"
    PICS.mkdir(parents=True, exist_ok=True)
    elected = cfg["elected"] or {
        k: (v["elected"], v["p5"], v["p95"]) for k, v in
        json.loads((OUT / "bee-rois.json").read_text()).items()}

    files = sorted((OUT / f"ladder-{args.tag}").glob("f*.npz"))
    if not files:
        raise SystemExit(f"no ladder frames in {OUT / f'ladder-{args.tag}'}")
    frames = np.array([int(f.stem[1:]) for f in files])
    names = list(np.load(files[0]).keys())
    keys = list(stats_of(np.zeros((8, 8))).keys())
    print(f"{args.subject}: {len(frames)} frames {frames[0]}..{frames[-1]}, "
          f"ROIs {names}")

    curves = {n: {k: [] for k in keys} for n in names}
    keep = {n: [] for n in names}
    for f in files:
        z = np.load(f)
        for n in names:
            g = z[n].astype(np.float64)[:, :, 1]
            L = 0.25 * (g[0::2, 0::2] + g[0::2, 1::2] + g[1::2, 0::2] + g[1::2, 1::2])
            for k, v in stats_of(L).items():
                curves[n][k].append(float(np.median(centre(v))))
            keep[n].append(z[n][125:375, 125:375])
        print(f"  {f.stem} done", flush=True)

    print(f"\n{'=' * 92}\nCOMMISSIONING: does mean|g| reproduce the shipped election?"
          f"\n{'=' * 92}")
    step = int(np.median(np.diff(frames)))
    in_band = lambda a, n: elected[n][1] - step <= a <= elected[n][2] + step
    comm = 0
    for n in names:
        a = int(frames[int(np.argmax(curves[n]["mean|g|"]))])
        hit = in_band(a, n)
        comm += hit
        print(f"  {n:<15} mean|g| argmax f{a:<4} shipped f{elected[n][0]:<5.0f} "
              f"band [{elected[n][1]:.0f},{elected[n][2]:.0f}]  "
              f"{'HIT' if hit else 'MISS'}")
    print(f"  -> {comm}/{len(names)}")
    if comm < len(names) - 1:
        raise SystemExit("mean|g| does not reproduce the shipped election here; "
                         "the comparison below would not be about the shipped "
                         "election. Stopping.")

    print(f"\n{'=' * 92}\nH5: argmax per statistic, and each statistic's dynamic "
          f"range (max/min)\n{'=' * 92}")
    hdr = "".join(f"{k:>13}" for k in CANDIDATES)
    print(f"  {'roi':<15}{'shipped':>9}{hdr}")
    res = {}
    for n in names:
        cells = ""
        res[n] = {}
        for k in keys:
            v = np.array(curves[n][k])
            a = int(frames[int(np.argmax(v))])
            dr = float(v.max() / max(v.min(), 1e-12))
            res[n][k] = {"argmax": a, "range": dr, "peak": float(v.max())}
            if k in CANDIDATES:
                cells += f"{f'f{a} ({dr:.1f}x)':>13}"
        print(f"  {n:<15}{elected[n][0]:>9.0f}{cells}")

    print(f"\n{'-' * 92}\nWHY: peak gradient carried by the veil ramp vs by the "
          f"texture\n{'-' * 92}")
    print(f"  {'roi':<15}{'best lp max|g|':>16}{'at':>6}{'best hp max|g|':>16}"
          f"{'at':>6}   ramp beats texture?")
    for n in names:
        lp, hp = res[n]["_lp max|g|"], res[n]["_hp max|g|"]
        wins = lp["peak"] > hp["peak"]
        lp_at, hp_at = f"f{lp['argmax']}", f"f{hp['argmax']}"
        print(f"  {n:<15}{lp['peak']:>16.1f}{lp_at:>6}"
              f"{hp['peak']:>16.1f}{hp_at:>6}   {'YES' if wins else 'no'}")

    print(f"\n{'-' * 92}\nVERDICT\n{'-' * 92}")
    verdict = {}
    for n in names:
        m, mx = res[n]["mean|g|"]["argmax"], res[n]["max|g|"]["argmax"]
        hp = res[n]["hp mean|g|"]["argmax"]
        agree_ctrl = in_band(mx, n)
        moved = abs(mx - m) > 2 * step
        toward = abs(mx - hp) < abs(m - hp)
        verdict[n] = {"mean": m, "max": mx, "hp": hp, "moved": moved,
                      "toward_texture": bool(toward), "agrees_shipped": bool(agree_ctrl)}
        if n in cfg["controls"]:
            tag = ("CONTROL OK: max agrees with the correct shipped election"
                   if agree_ctrl else
                   "CONTROL BROKEN: max disagrees where the election is right")
        elif n in cfg["defects"]:
            tag = (f"max moves the election f{m} -> f{mx}, "
                   f"{'toward' if toward else 'AWAY from'} the texture answer f{hp}"
                   if moved else
                   f"max does NOT move the election (still f{mx}): H5 fails here")
        else:
            tag = f"mean f{m}, max f{mx}, texture f{hp}"
        print(f"  {n:<15} {tag}")

    ctrl_ok = all(verdict[n]["agrees_shipped"] for n in cfg["controls"])
    def_fixed = [n for n in cfg["defects"]
                 if verdict[n]["moved"] and verdict[n]["toward_texture"]]
    print(f"\n  controls preserved: {ctrl_ok}"
          f"    defect ROIs where max|g| helps: {def_fixed} of {cfg['defects']}")
    print(f"  H5 {'SUPPORTED' if ctrl_ok and len(def_fixed) == len(cfg['defects']) else 'NOT SUPPORTED'} "
          f"on {args.subject}")

    fig, axes = plt.subplots(1, len(names), figsize=(5.0 * len(names), 4.4))
    for ax, n in zip(np.atleast_1d(axes), names):
        for k, c, ls in (("mean|g|", "k", "-"), ("mean|g|^2", "tab:purple", ":"),
                         ("mean|g|^4", "tab:brown", ":"), ("max|g|", "tab:red", "-"),
                         ("hp mean|g|", "tab:blue", "--")):
            v = np.array(curves[n][k]); ax.plot(frames, v / v.max(), c, ls=ls,
                                                label=k, lw=1.8)
        ax.axvline(elected[n][0], color="tab:green", ls="--", lw=1.5, label="shipped")
        ax.set_title(f"{n}\nmean f{res[n]['mean|g|']['argmax']}  "
                     f"max f{res[n]['max|g|']['argmax']}", fontsize=10)
        ax.set_xlabel("frame"); ax.set_ylabel("statistic (norm.)")
        ax.grid(alpha=.3); ax.legend(fontsize=7)
    fig.suptitle(f"H5 on {args.subject}: box mean vs box max of |grad|, same window "
                 f"r={WINDOW_RADIUS}", fontsize=13)
    fig.tight_layout()
    p1 = PICS / f"H5-curves-{args.subject}.png"
    fig.savefig(p1, dpi=110); plt.close(fig)

    # The picture that decides it: for each ROI, the frame mean elects beside the
    # frame max elects. If H5 is right the second is visibly the sharper one.
    fig, axes = plt.subplots(len(names), 3, figsize=(11, 3.7 * len(names)))
    for r, n in enumerate(names):
        im = int(np.argmin(np.abs(frames - res[n]["mean|g|"]["argmax"])))
        ix = int(np.argmin(np.abs(frames - res[n]["max|g|"]["argmax"])))
        ih = int(np.argmin(np.abs(frames - res[n]["hp mean|g|"]["argmax"])))
        for c, (i, t) in enumerate(((im, f"mean|g| elects f{frames[im]}"),
                                    (ix, f"max|g| elects f{frames[ix]}"),
                                    (ih, f"hp mean|g| elects f{frames[ih]}"))):
            axes[r, c].imshow(tone(keep[n][i], cfg["ref"]), interpolation="nearest")
            axes[r, c].set_title(t, fontsize=10)
            axes[r, c].set_xticks([]); axes[r, c].set_yticks([])
        axes[r, 0].set_ylabel(n, fontsize=10)
    fig.suptitle(f"{args.subject}: the frame each statistic elects. Which is sharper?",
                 fontsize=13)
    fig.tight_layout()
    p2 = PICS / f"H5-choice-{args.subject}.png"
    fig.savefig(p2, dpi=100); plt.close(fig)

    (OUT / f"h5-{args.subject}.json").write_text(json.dumps(
        {"frames": frames.tolist(), "curves": curves, "res": res,
         "verdict": verdict}, indent=1))
    print(f"\nwrote {p1}\nwrote {p2}")


if __name__ == "__main__":
    main()

"""H4 on bee-1-cpl: does the data have an answer the election missed?

H4 is the null the brief requires me to try to ACCEPT: the patch may be the correct
answer to a bad capture. The test it prescribes is to extract the through-focus
response at pixels inside a patch and look at it. If there is a clear peak the
election missed, it is a software defect. If the curve is flat or the peak sits at
the bracket boundary, the data has no answer and the product should report that
rather than fabricate detail.

This runs the focus.rs replica from focusdecomp.py (same Sobel x0.125 -> box mean
r=13 -> divide by green_luma_sigma), commissions it against the shipped align-off
election, then splits luma into a low-frequency part (the veil ramp) and a
high-frequency part (real surface texture). The high-pass curve is the one H4 is
about: only texture can be resolved detail, a smooth ramp cannot.

Two things must both be produced, because this project has shipped defects that
were invisible in scalars and obvious in pictures:
  a curve per ROI, and a contact sheet of the actual pixels through focus.

CONTROLS. bee-sharp is a region where the election is correct by eye. If the H4
test declares that the control has no answer, the test is broken and its verdict
on the defect ROIs is worthless. That check is printed as a pass/fail, not assumed.
"""
import argparse
import json
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter, uniform_filter

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee")
PICS = OUT / "pics"

WINDOW_RADIUS = 13
LOW_SIGMA = 8.0
MEASURE_HALF = 60
GAIN_DN_PER_E = 0.229
READ_E = 1.47
K_OUT = 65535.0 / (15360.0 - 512.0)
REF = np.array([19093.0, 20163.0, 21361.0])

NFRAMES = 299
PEAK_RATIO = 1.30       # a peak must clear its own floor by this to count as a peak
EDGE_STEPS = 1          # argmax this close to frame 0 or 298 counts as a boundary
MISS_STEPS = 16         # election is "wrong" if it lands this far from the texture peak


def sobel_mag(a):
    p = np.pad(a, 1, mode="edge")
    gx = (p[:-2, 2:] + 2.0 * p[1:-1, 2:] + p[2:, 2:]
          - p[:-2, :-2] - 2.0 * p[1:-1, :-2] - p[2:, :-2]) * 0.125
    gy = (p[2:, :-2] + 2.0 * p[2:, 1:-1] + p[2:, 2:]
          - p[:-2, :-2] - 2.0 * p[:-2, 1:-1] - p[:-2, 2:]) * 0.125
    return np.hypot(gx, gy)


def luma_sigma(luma_out_dn):
    s = np.maximum(luma_out_dn, 0.0) / K_OUT
    read_dn = READ_E * GAIN_DN_PER_E
    return np.sqrt(0.5 * (GAIN_DN_PER_E * s + read_dn * read_dn)) * K_OUT


def focus_of(grad_src, luma_full, normalise):
    f = uniform_filter(sobel_mag(grad_src), size=2 * WINDOW_RADIUS + 1, mode="nearest")
    return f / np.maximum(luma_sigma(luma_full), 1e-6) if normalise else f


def centre(a):
    c = a.shape[0] // 2
    return a[c - MEASURE_HALF:c + MEASURE_HALF, c - MEASURE_HALF:c + MEASURE_HALF]


def tone(rgb):
    return np.clip(rgb.astype(np.float64) / (REF / 0.92), 0, 1) ** (1 / 2.2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="crops")
    ap.add_argument("--normalise", type=int, default=0)
    args = ap.parse_args()
    PICS.mkdir(parents=True, exist_ok=True)

    src = OUT / f"ladder-{args.tag}"
    files = sorted(src.glob("f*.npz"))
    if not files:
        raise SystemExit(f"no frames in {src}")
    frames = [int(f.stem[1:]) for f in files]
    step = int(np.median(np.diff(frames))) if len(frames) > 1 else 1
    elected = json.loads((OUT / "bee-rois.json").read_text())
    names = [n for n in np.load(files[0]).keys()]
    print(f"{len(frames)} frames {frames[0]}..{frames[-1]} step~{step}; ROIs {names}")

    curves = {n: {"full": [], "low": [], "high": []} for n in names}
    keep = {n: [] for n in names}
    for f in files:
        z = np.load(f)
        for n in names:
            rgb = z[n].astype(np.float64)
            g = rgb[:, :, 1]
            L = 0.25 * (g[0::2, 0::2] + g[0::2, 1::2] + g[1::2, 0::2] + g[1::2, 1::2])
            low = gaussian_filter(L, LOW_SIGMA, mode="nearest")
            for k, v in (("full", L), ("low", low), ("high", L - low)):
                curves[n][k].append(float(np.median(centre(
                    focus_of(v, L, bool(args.normalise))))))
            keep[n].append(z[n][125:375, 125:375])
        print(f"  {f.stem} done", flush=True)

    print(f"\n{'=' * 78}\nCOMMISSIONING: replica argmax vs the shipped align-off election"
          f"\n{'=' * 78}")
    band = median = 0
    for n in names:
        a = frames[int(np.argmax(curves[n]["full"]))]
        e = elected[n]
        hit = e["p5"] - step <= a <= e["p95"] + step
        near = abs(a - e["elected"]) <= step
        band += hit; median += near
        print(f"  {n:<11} replica f{a:<4} shipped f{e['elected']:<5.0f} "
              f"band [{e['p5']:>3.0f},{e['p95']:>3.0f}]  "
              f"band {'HIT ' if hit else 'MISS'}  median {'HIT' if near else 'MISS'}")
    print(f"  -> band {band}/{len(names)}   median {median}/{len(names)}")
    if band < len(names) - 1:
        print("  WARNING: replica only partly commissioned; treat its split with care.")

    print(f"\n{'=' * 78}\nH4: is there a texture peak the election missed?"
          f"   (normalise={args.normalise})\n{'=' * 78}")
    print(f"  {'roi':<11} {'elect':>6} {'full':>6} {'high':>6} {'ratio':>7} "
          f"{'edge?':>6} {'e@end':>6} {'miss':>6}  verdict")
    verdicts = {}
    for n in names:
        hi = np.array(curves[n]["high"])
        af = frames[int(np.argmax(curves[n]["full"]))]
        ah = frames[int(np.argmax(curves[n]["high"]))]
        ratio = float(hi.max() / max(hi.min(), 1e-9))
        at_edge = ah <= frames[0] + EDGE_STEPS * step or ah >= NFRAMES - 1 - EDGE_STEPS * step
        e = elected[n]["elected"]
        # The elected index itself running to a bracket end is its own symptom: an
        # argmax that never turned over had nothing to turn over on.
        elect_at_end = e <= EDGE_STEPS * step or e >= NFRAMES - 1 - EDGE_STEPS * step
        missed = abs(e - ah) > MISS_STEPS
        if ratio < PEAK_RATIO:
            v = "H4 ACCEPTED: texture curve flat, no answer in the data"
        elif at_edge:
            v = "H4 ACCEPTED: texture peak at bracket boundary, coverage gap"
        elif missed:
            v = "H4 REJECTED: clear peak, election missed it"
        else:
            v = "election correct: peak found"
        verdicts[n] = {"full": af, "high": ah, "ratio": ratio, "edge": bool(at_edge),
                       "elect_at_end": bool(elect_at_end), "missed": bool(missed),
                       "verdict": v, "elected": e}
        print(f"  {n:<11} {e:>6.0f} {af:>6} {ah:>6} {ratio:>7.2f} "
              f"{str(at_edge):>6} {str(elect_at_end):>6} {str(missed):>6}  {v}")

    ctrl = verdicts.get("bee-sharp", {}).get("verdict", "")
    ok = ctrl.startswith("election correct")
    print(f"\n  CONTROL bee-sharp -> {'PASS' if ok else 'FAIL'}: {ctrl}")
    if not ok:
        print("  The control region is correct by eye. If the test cannot say so,\n"
              "  its verdicts on the defect ROIs do not stand.")

    fig, axes = plt.subplots(1, len(names), figsize=(4.9 * len(names), 4.3))
    for ax, n in zip(np.atleast_1d(axes), names):
        for k, c in (("full", "k"), ("high", "tab:red"), ("low", "tab:blue")):
            v = np.array(curves[n][k]); ax.plot(frames, v / v.max(), c, label=k, lw=1.8)
        ax.axvline(verdicts[n]["elected"], color="tab:green", ls="--", lw=1.5,
                   label="elected")
        ax.set_title(f"{n}\nfull f{verdicts[n]['full']}  texture f{verdicts[n]['high']}"
                     f"  ratio {verdicts[n]['ratio']:.2f}", fontsize=10)
        ax.set_xlabel("frame"); ax.set_ylabel("focus measure (norm.)")
        ax.grid(alpha=.3); ax.legend(fontsize=8)
    fig.suptitle("bee-1-cpl through-focus response, focus.rs replica split into "
                 "veil (low) and texture (high)")
    fig.tight_layout()
    p1 = PICS / f"BEE-H4-curves-n{args.normalise}.png"
    fig.savefig(p1, dpi=110); plt.close(fig)

    # Span the whole bracket, and force-include the rung nearest each ROI's elected
    # frame. The first version stepped range(0, len(frames), len(frames)//9), stopped
    # at f192, and showed the elected frame for none of the far ROIs; the second
    # spanned the bracket but still missed bee-sharp's f48. A sheet that answers
    # "is there a sharp frame" must contain the frame under suspicion for every row.
    near = {int(np.argmin(np.abs(np.array(frames) - v["elected"])))
            for v in verdicts.values()}
    sel = sorted(set(np.linspace(0, len(frames) - 1, 10).astype(int).tolist()) | near)
    fig, axes = plt.subplots(len(names), len(sel),
                             figsize=(2.35 * len(sel), 2.5 * len(names)))
    for r, n in enumerate(names):
        nr = int(np.argmin(np.abs(np.array(frames) - verdicts[n]["elected"])))
        for c, i in enumerate(sel):
            ax = axes[r, c]
            ax.imshow(tone(keep[n][i]), interpolation="nearest")
            ax.set_xticks([]); ax.set_yticks([])
            if i == nr:
                for s in ax.spines.values():
                    s.set_color("red"); s.set_linewidth(3)
            if r == 0:
                ax.set_title(f"f{frames[i]}", fontsize=10)
            if c == 0:
                ax.set_ylabel(f"{n}\nelect f{verdicts[n]['elected']:.0f}", fontsize=9)
    fig.suptitle("bee-1-cpl: the actual pixels through focus. Is there a sharp frame?"
                 "   (red border = the frame the binary elected)", fontsize=13)
    fig.tight_layout()
    p2 = PICS / "BEE-H4-sheet.png"
    fig.savefig(p2, dpi=100); plt.close(fig)

    (OUT / f"bee-h4-n{args.normalise}.json").write_text(json.dumps(
        {"frames": frames, "curves": curves, "verdicts": verdicts}, indent=1))
    print(f"\nwrote {p1}\nwrote {p2}")


if __name__ == "__main__":
    main()

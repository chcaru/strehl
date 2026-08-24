"""M77 arm G0 -- ROI selection, per the rule fixed in PREREGISTRATION.md section 4.

ROI selection is the whole experiment. The corpus has been bitten here before and
it is recorded in shipped source: flat_ratio.rs:15-23 states the four flat ROIs
the corpus published are 53.3%, 50.9%, 80.0% and 72.2% scene structure by
variance, and that one of them "is not even detail-free". M73 section 5.5 adds
that on wrapped-text the label stock's own texture supplies most of the focus
signal, so "low gradient" does not mean "flat" on that subject.

THIS SCRIPT READS INPUT FRAMES ONLY. No merge output at any gate enters ROI
selection, which is what keeps the ROI choice from being circular with the sweep
that reads it.

Both statistics are reimplementations of shipped Rust, and each is checked
against its shipped constant rather than retyped:
  contam = hp_sd / (HP_NOISE_GAIN * model_sigma)      flat_ratio.rs
  cg     = sqrt(max(0, raw_rms^2 - noise_rms^2))      merge_cmd.rs:305
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m77  # noqa: E402

TILE = 256
STRIDE = 128
EDGE = 32
MIN_FRAMES = 12


def tiles_for(h, w):
    ys = list(range(EDGE, h - TILE - EDGE + 1, STRIDE))
    xs = list(range(EDGE, w - TILE - EDGE + 1, STRIDE))
    return [(x, y) for y in ys for x in xs]


def frame_indices(n):
    """At least MIN_FRAMES, always including first, middle and last."""
    if n <= MIN_FRAMES:
        return list(range(n))
    step = max(1, n // MIN_FRAMES)
    idx = set(range(0, n, step))
    idx.update({0, n // 2, n - 1})
    return sorted(idx)


def hp_sd(a):
    """x - box_9(x), sd over the VALID INTERIOR. flat_ratio.rs convention."""
    r = m77.HP_BOX_RADIUS
    m = m77.box_mean(a, r)
    resid = (a - m)[r:-r, r:-r]
    return float(resid.std())


def corrected_gradient(a, sigma):
    """merge_cmd.rs:305 detail_metrics, corrected_rms limb."""
    dx = a[:-1, 1:] - a[:-1, :-1]
    dy = a[1:, :-1] - a[:-1, :-1]
    s0 = sigma[:-1, :-1]
    s1 = sigma[:-1, 1:]
    sw = sigma[1:, :-1]
    raw = float(np.sqrt(np.mean(dx * dx + dy * dy)))
    noise = float(np.sqrt(np.mean(2.0 * s0 * s0 + s1 * s1 + sw * sw)))
    return float(np.sqrt(max(0.0, raw * raw - noise * noise))), raw, noise


def scan(stack, which_frames):
    files = m77.stack_files(stack)
    iso = m77.iso_of(files[0])
    idx = [i for i in frame_indices(len(files)) if i in which_frames] \
        if which_frames is not None else frame_indices(len(files))
    plane0 = m77.green_luma_plane(files[idx[0]])
    h, w = plane0.shape
    tl = tiles_for(h, w)
    contam = np.zeros((len(tl), len(idx)))
    cg = np.zeros((len(tl), len(idx)))
    for j, fi in enumerate(idx):
        plane = plane0 if j == 0 else m77.green_luma_plane(files[fi])
        for t, (x, y) in enumerate(tl):
            a = plane[y:y + TILE, x:x + TILE]
            mu = float(a.mean())
            msig = m77.green_luma_sigma(mu, iso)
            contam[t, j] = hp_sd(a) / (m77.HP_NOISE_GAIN * msig) if msig > 0 else np.inf
            sig = m77.green_luma_sigma_map(a, iso)
            cg[t, j] = corrected_gradient(a, sig)[0]
    return tl, idx, contam, cg, iso, (h, w)


def pick(tl, contam, cg):
    flat_score = contam.max(axis=1)
    detail_score = cg.max(axis=1)
    fi = int(np.argmin(flat_score))
    di = int(np.argmax(detail_score))
    return fi, di, flat_score, detail_score


def adjacent(a, b):
    return abs(a[0] - b[0]) <= STRIDE and abs(a[1] - b[1]) <= STRIDE


def main():
    m77.banner("M77 arm G0 -- ROI selection (input frames only)")
    print(f"  tile {TILE}  stride {STRIDE}  edge {EDGE}  >= {MIN_FRAMES} frames")
    print(f"  HP_BOX_SIDE {m77.HP_BOX_SIDE}  HP_NOISE_GAIN {m77.HP_NOISE_GAIN:.6f}"
          "   (parsed from crates/, not retyped)")
    out = {}
    for stack in m77.STACKS:
        tl, idx, contam, cg, iso, shape = scan(stack, None)
        fi, di, fs, ds = pick(tl, contam, cg)
        flat_roi, detail_roi = tl[fi], tl[di]

        # K5: even/odd split of the SAME sampled frames.
        ev = {v for k, v in enumerate(idx) if k % 2 == 0}
        od = {v for k, v in enumerate(idx) if k % 2 == 1}
        cols_e = [k for k, v in enumerate(idx) if v in ev]
        cols_o = [k for k, v in enumerate(idx) if v in od]
        fe, de, _, _ = pick(tl, contam[:, cols_e], cg[:, cols_e])
        fo, do, _, _ = pick(tl, contam[:, cols_o], cg[:, cols_o])
        k5_flat = adjacent(tl[fe], tl[fo])
        k5_det = adjacent(tl[de], tl[do])

        # K2: detail cg vs flat cg, in the frame where detail is strongest.
        best_col = int(np.argmax(cg[di]))
        k2_ratio = cg[di, best_col] / cg[fi, best_col] if cg[fi, best_col] > 0 else np.inf

        print(f"\n  --- {stack}  ISO {iso:g}  plane {shape[1]}x{shape[0]}  "
              f"{len(tl)} tiles x {len(idx)} frames")
        print(f"      FLAT   x{flat_roi[0]},y{flat_roi[1]}  contam(max over frames) "
              f"= {fs[fi]:.4f}   [K1 bar < 1.10 -> "
              f"{'MET' if fs[fi] < 1.10 else 'NOT MET'}]")
        print(f"             corpus's published flat ROIs, for scale: 1.2756x and "
              f"1.3490x (flat_ratio.rs)")
        print(f"      DETAIL x{detail_roi[0]},y{detail_roi[1]}  cg(max over frames)  "
              f"= {ds[di]:.4f}")
        print(f"      K2 detail/flat cg = {k2_ratio:.2f}x  [bar >= 3x -> "
              f"{'MET' if k2_ratio >= 3.0 else 'NOT MET'}]")
        print(f"      K5 even/odd stability: flat {'MET' if k5_flat else 'NOT MET'}"
              f"   detail {'MET' if k5_det else 'NOT MET'}")
        out[stack] = {
            "iso": iso, "plane": shape, "n_tiles": len(tl), "frames": idx,
            "flat_roi": {"x": flat_roi[0], "y": flat_roi[1], "w": TILE, "h": TILE,
                         "contam_max": float(fs[fi])},
            "detail_roi": {"x": detail_roi[0], "y": detail_roi[1], "w": TILE, "h": TILE,
                           "cg_max": float(ds[di])},
            "k1_met": bool(fs[fi] < 1.10),
            "k2_ratio": float(k2_ratio), "k2_met": bool(k2_ratio >= 3.0),
            "k5_flat_met": bool(k5_flat), "k5_detail_met": bool(k5_det),
            "contam_range": [float(fs.min()), float(fs.max())],
        }
    (m77.OUT / "01-rois.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\n  wrote out/01-rois.json")


if __name__ == "__main__":
    main()

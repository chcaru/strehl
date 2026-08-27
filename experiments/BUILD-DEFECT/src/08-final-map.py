"""08-final-map.py -- the shippable defect map, with 04's two defects repaired.

04 got two things wrong and both are recorded rather than quietly fixed:

  * it excluded a 31-quad border because the high-pass radius is 30.  The
    high-pass is THREE passes, so its support half-width is 90; 05 measured the
    artefact's actual reach as ~40 quads (ring median -0.93% at d=0, -0.098% at
    d=30, -0.003% at d=40, flat at +0.02..0.06% beyond).  This ships 60.
  * it read `hot-recur.npy` as (4, H, W) when 03 wrote (H, W, 4), so its hot
    arm indexed the first four ROWS of the sensor and emitted 22 sites instead
    of 14,626.  An impossible number is the only reason that was caught.

And one bar is changed for a stated reason rather than a better result: the
seed depth goes from -1.0% to -0.5%, because a per-capture seed must be above
the noisiest capture's residual rms (0.4882%, 01) and below a real mote, and
-1.0% is above the two shallower motes.  07 re-ran the independent-roll null at
every point of a 24-setting sweep; it returned ZERO components everywhere, so
the null admits this change rather than being relaxed by it.
"""

import json
import math
import pathlib
import time

import numpy as np
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
T0 = time.time()
CROSS = np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


HP_RADIUS, HP_PASS, BP_RADIUS = 30, 3, 2
SEED_DEPTH = 0.005
RECURRENCE = 15
FLOOR_DEPTH = 0.005
BORDER = 60
MIN_COMPONENT = 25
HOT_RECURRENCE = 6

CAMERA = "ILCE-7CM2"
SENSOR_W, SENSOR_H = 7032, 4688
COVERED_W, COVERED_H = 7028, 4688
APERTURE = 5.6


def box_smooth(a, radius, npass):
    cur = a.astype(np.float64)
    win = 2 * radius + 1
    for _ in range(npass):
        cur = ndimage.uniform_filter1d(cur, win, axis=1, mode="nearest")
        cur = ndimage.uniform_filter1d(cur, win, axis=0, mode="nearest")
    return cur


def main():
    res = np.load(OUT / "dust-residual-per-tag.npy")
    ntag, h, w = res.shape
    total = w * h
    assert (w, h) == (COVERED_W // 2, COVERED_H // 2)
    log(f"{ntag} captures, {w}x{h} quads, border {BORDER}")

    inside = np.zeros((h, w), bool)
    inside[BORDER:h - BORDER, BORDER:w - BORDER] = True
    n_border = total - int(inside.sum())

    med = np.median(res, axis=0).astype(np.float32)
    band = box_smooth(med, BP_RADIUS, 1).astype(np.float32)
    seen = (res <= -SEED_DEPTH).sum(axis=0).astype(np.int16)

    recurrent = (seen >= RECURRENCE) & inside
    deep = recurrent & (band <= -FLOOR_DEPTH)
    lab, ncomp = ndimage.label(deep, structure=CROSS)
    sizes = np.bincount(lab.ravel())
    keep_ids = [i for i in range(1, ncomp + 1) if sizes[i] >= MIN_COMPONENT]
    keep = np.isin(lab, keep_ids) if keep_ids else np.zeros((h, w), bool)
    log(f"    border {n_border}  recurrent {int(recurrent.sum())}  "
        f"deep {int(deep.sum())}  components {ncomp}  "
        f"too small {ncomp - len(keep_ids)}  kept {int(keep.sum())}")

    # ---- attenuation calibration, per component area ----------------------
    log("plant calibration of the high-pass attenuation, by disc area")
    yy, xx = np.mgrid[0:h, 0:w]
    centres = [(600, 900), (1200, 1800), (1800, 2700)]
    calib = []
    for radius in (3, 5, 8, 12, 18, 25, 35):
        depth = 0.025
        field = np.ones((h, w), np.float64)
        mask = np.zeros((h, w), bool)
        for (cy, cx) in centres:
            mask |= ((yy - cy) ** 2 + (xx - cx) ** 2) <= radius * radius
        field[mask] *= (1.0 - depth)
        r = field / box_smooth(field, HP_RADIUS, HP_PASS) - 1.0
        core = np.zeros((h, w), bool)
        for (cy, cx) in centres:
            core |= ((yy - cy) ** 2 + (xx - cx) ** 2) <= max(1, radius // 2) ** 2
        rec = -float(np.median(r[core]))
        area = int(mask.sum() / len(centres))
        calib.append(dict(radius=radius, area=area, planted=depth,
                          recovered=rec, alpha=rec / depth))
        log(f"    radius {radius:3d}  area {area:6d}  planted {depth*100:5.2f}%  "
            f"recovered {rec*100:5.2f}%  alpha {rec/depth:.4f}")
    areas = [c["area"] for c in calib]
    alphas = [c["alpha"] for c in calib]

    def alpha_for(area):
        return float(np.interp(area, areas, alphas))

    # ---- dust rows --------------------------------------------------------
    dust_rows, comp_report, refused = [], [], 0
    for cid in sorted(keep_ids, key=lambda i: -sizes[i]):
        m = lab == cid
        area = int(sizes[cid])
        a = alpha_for(area)
        gain = 1.0 / (1.0 + med[m] / a)
        ys, xs = np.nonzero(m)
        ok = np.isfinite(gain) & (gain >= 1.0) & (gain <= 1.25)
        refused += int((~ok).sum())
        for x, y, g in zip(xs[ok], ys[ok], gain[ok]):
            dust_rows.append((int(x), int(y), float(g)))
        comp_report.append(dict(
            area=area, alpha=a, cx=float(xs.mean()), cy=float(ys.mean()),
            diam_quads=float(2 * math.sqrt(area / math.pi)),
            depth_med_pct=float(np.median(med[m]) * 100),
            depth_min_pct=float(med[m].min() * 100),
            gain_med=float(np.median(gain[ok])) if ok.any() else None,
            gain_max=float(gain[ok].max()) if ok.any() else None,
            seen_med=float(np.median(seen[m])), seen_min=int(seen[m].min()),
            edge=int(min(xs.min(), w - 1 - xs.max(), ys.min(), h - 1 - ys.max()))))
        c = comp_report[-1]
        log(f"    mote area {area:5d} (d~{c['diam_quads']:5.1f}) at "
            f"({c['cx']:6.0f},{c['cy']:6.0f}) edge {c['edge']:4d}  "
            f"median {c['depth_med_pct']:+6.2f}%  worst {c['depth_min_pct']:+6.2f}%  "
            f"seen {c['seen_med']:4.1f}/18  alpha {a:.3f}  "
            f"gain med {c['gain_med']:.4f} max {c['gain_max']:.4f}")
    log(f"    {len(dust_rows)} dust quads, {refused} refused for gain range")

    # ---- hot rows (03 wrote (H, W, 4), NOT (4, H, W)) ---------------------
    recur = np.load(OUT / "hot-recur.npy")
    exc = np.load(OUT / "hot-excess-e.npy")
    assert recur.shape == (h, w, 4), recur.shape
    PLANE_OFF = [(0, 0), (1, 0), (0, 1), (1, 1)]   # RGGB: R G1 / G2 B
    NAMES = ["R", "G1", "G2", "B"]
    hot_rows, strata = [], {}
    for p, (ox, oy) in enumerate(PLANE_OFF):
        sel = recur[:, :, p] >= HOT_RECURRENCE
        ys, xs = np.nonzero(sel)
        es = exc[:, :, p][sel]
        for x, y, e in zip(xs, ys, es):
            hot_rows.append((int(2 * x + ox), int(2 * y + oy), float(e)))
        strata[NAMES[p]] = int(sel.sum())
    hot_rows.sort(key=lambda r: (r[1], r[0]))
    amps = np.array([r[2] for r in hot_rows])
    log(f"    {len(hot_rows)} hot sites {strata}")
    ladder = {}
    for lo, hi in ((0, 2), (2, 4), (4, 8), (8, 16), (16, 10 ** 9)):
        ladder[f"{lo}-{hi}"] = int(((amps >= lo) & (amps < hi)).sum())
    log(f"    amplitude ladder (e-): {ladder}")
    n_ship = int((amps >= 8.0).sum())
    log(f"    at the reproducible floor (>= 8 e-): {n_ship}")

    # ---- partition --------------------------------------------------------
    n_inside = total - n_border
    n_rec = int(recurrent.sum())
    n_deep = int(deep.sum())
    n_kept = int(keep.sum())
    part = dict(total=total, border_excluded=n_border, examined=n_inside,
                not_recurrent=n_inside - n_rec,
                recurrent_but_shallow=n_rec - n_deep,
                deep_but_too_small=n_deep - n_kept,
                emitted=len(dust_rows), refused_gain=refused)
    s = sum(v for k, v in part.items() if k not in ("total", "examined"))
    log(f"    partition {s} of {total}  {'OK' if s == total else 'MISMATCH'}")
    assert s == total, part

    # ---- write ------------------------------------------------------------
    path = OUT / f"defect-map-{CAMERA}.txt"
    prov = [
        f"built {time.strftime('%Y-%m-%dT%H:%M:%S')} by experiments/BUILD-DEFECT/src/08-final-map.py",
        "hot: 242 darks, 11 ISO groups x 20 frames (2 stabilisation shots dropped),",
        "hot: 1/100 s, ISO 50-2000, D:\\macro-dark-frames. 6-sigma same-plane neighbour",
        f"hot: excess, recurrence >= {HOT_RECURRENCE}/11 groups. Census {len(hot_rows)}, which",
        "hot: reproduces M101's 14604 to +0.2% and M48c's 13650 to +7.2%.",
        "hot: MEASURED IMMATERIAL on this body (M101): in-situ amplitude 1.5 DN, the",
        "hot: election does not prefer a hot pixel below 100-250 DN. Ships OFF.",
        f"hot: split-half reproducibility is 1.000 only above 8 e- ({n_ship} sites).",
        "dust: 18 flat captures (9 shutter speeds x 2 CPL states, ~40 min, moving cloud)",
        "dust: x 20 frames, D:\\personal\\macro\\flat-fields, f/5.6 at 200 mm, ISO 100.",
        f"dust: high-pass r={HP_RADIUS} x{HP_PASS} passes, band-pass r={BP_RADIUS},",
        f"dust: seed {SEED_DEPTH*100:.2f}% (above the noisiest capture's 0.4882% residual rms),",
        f"dust: recurrence >= {RECURRENCE}/18, floor {FLOOR_DEPTH*100:.2f}%, border {BORDER} quads",
        "dust: (measured: the high-pass edge artefact reaches ~40 quads), component",
        f"dust: floor {MIN_COMPONENT} quads. Attenuation calibrated by planted discs, per area.",
        "dust: NULL (all 18 captures rolled independently) returns 0 components at every",
        "dust: one of 24 sweep settings; the real arm returns the components below.",
        f"geometry: rawler active {SENSOR_W}x{SENSOR_H}; rawpy visible {COVERED_W}x{COVERED_H}.",
        f"geometry: the last {SENSOR_W-COVERED_W} sensor columns are UNMEASURED, not clean.",
    ]
    for c in comp_report:
        prov.append(f"mote: {c['area']} quads (d~{c['diam_quads']:.0f}) at quad "
                    f"({c['cx']:.0f},{c['cy']:.0f}), median {c['depth_med_pct']:.2f}%, "
                    f"worst {c['depth_min_pct']:.2f}%, seen {c['seen_med']:.0f}/18")
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("strehl-defect-map 1\n")
        f.write(f"camera {CAMERA}\n")
        f.write(f"sensor {SENSOR_W} {SENSOR_H}\n")
        f.write(f"covered {COVERED_W} {COVERED_H}\n")
        f.write(f"aperture {APERTURE}\n")
        for p_ in prov:
            f.write(f"# {p_}\n")
        f.write(f"hot {len(hot_rows)}\n")
        for x, y, e in hot_rows:
            f.write(f"h {x} {y} {e:.4f}\n")
        f.write(f"dust {len(dust_rows)}\n")
        for x, y, g in sorted(dust_rows, key=lambda r: (r[1], r[0])):
            f.write(f"d {x} {y} {g:.6f}\n")
        f.write("end\n")
    log(f"wrote {path}  {path.stat().st_size/1e6:.3f} MB")

    (DATA / "08-map.json").write_text(json.dumps(dict(
        params=dict(hp_radius=HP_RADIUS, hp_pass=HP_PASS, bp_radius=BP_RADIUS,
                    seed=SEED_DEPTH, recurrence=RECURRENCE, floor=FLOOR_DEPTH,
                    border=BORDER, min_component=MIN_COMPONENT,
                    hot_recurrence=HOT_RECURRENCE),
        partition=part, components=comp_report, calibration=calib,
        hot=dict(total=len(hot_rows), per_plane=strata, ladder=ladder,
                 at_reproducible_floor=n_ship),
        map_path=str(path), map_bytes=path.stat().st_size,
        dust_quads=len(dust_rows)), indent=1), encoding="utf-8")
    log("wrote data/08-map.json")


if __name__ == "__main__":
    main()

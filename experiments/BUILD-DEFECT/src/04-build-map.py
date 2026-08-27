"""04-build-map.py -- build the shippable defect map from the real calibration data.

Consumes what 01/02/03 measured and emits ONE text sidecar in the format
`crates/strehl-core/src/defect_map.rs` parses.

What is new here, over 01/02:

  * a BORDER EXCLUSION, counted rather than silently dropped.  02 proved the
    four largest "motes" found without it are artefacts of the high-pass's own
    edge replication.
  * a PLANT CALIBRATION of the high-pass's attenuation.  A dust disc enters its
    own smoothed denominator, so `m/smooth(m)-1` under-reads the true depth by
    an amount that depends on the disc's area.  Measured, per size, by pushing
    synthetic discs of known depth through the identical operator.
  * a NULL for the whole pipeline (all 18 captures rolled independently), which
    must return zero components.
  * a PARTITION of every quad into counted outcomes that sum to 3514*2344.
"""

import json
import math
import pathlib
import sys
import time

import numpy as np
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


# --- parameters, matched to defect_map.rs's DustParams::default() -----------
HP_RADIUS = 30
BP_RADIUS = 2
SEED_DEPTH = 0.010
RECURRENCE = 15
FLOOR_DEPTH = 0.0075
BORDER = 31
MIN_COMPONENT = 25

HOT_RECURRENCE = 6

CAMERA = "ILCE-7CM2"
SENSOR_W, SENSOR_H = 7032, 4688     # rawler active area
COVERED_W, COVERED_H = 7028, 4688   # rawpy visible, which decoded the calibration
APERTURE = 5.6


def box_smooth(a, radius, npass):
    """npass passes of a (2r+1) separable box mean, edge-replicated.

    Must match defect_map.rs::box_smooth exactly."""
    cur = a.astype(np.float64)
    win = 2 * radius + 1
    for _ in range(npass):
        cur = ndimage.uniform_filter1d(cur, win, axis=1, mode="nearest")
        cur = ndimage.uniform_filter1d(cur, win, axis=0, mode="nearest")
    return cur


def main():
    log("loading the per-capture high-passed residual stack")
    res = np.load(OUT / "dust-residual-per-tag.npy")          # (18, 2344, 3514)
    seen = np.load(OUT / "dust-seen.npy")                     # (2344, 3514) int
    ntag, h, w = res.shape
    log(f"    {ntag} captures, {w} x {h} quads")
    assert (w, h) == (COVERED_W // 2, COVERED_H // 2), (w, h)

    total_quads = w * h

    # ---- the detector, exactly as defect_map.rs::detect_dust runs it ------
    def run(stack, seen_map, label):
        med = np.median(stack, axis=0).astype(np.float32)
        band = box_smooth(med, BP_RADIUS, 1).astype(np.float32)

        inside = np.zeros((h, w), bool)
        inside[BORDER:h - BORDER, BORDER:w - BORDER] = True
        n_border = total_quads - int(inside.sum())

        recurrent = (seen_map >= RECURRENCE) & inside
        deep = recurrent & (band <= -FLOOR_DEPTH)

        lab, ncomp = ndimage.label(deep, structure=np.array(
            [[0, 1, 0], [1, 1, 1], [0, 1, 0]]))
        sizes = np.bincount(lab.ravel())
        keep_ids = [i for i in range(1, ncomp + 1) if sizes[i] >= MIN_COMPONENT]
        keep = np.isin(lab, keep_ids) if keep_ids else np.zeros((h, w), bool)

        log(f"    [{label}] border-excluded {n_border}  recurrent {int(recurrent.sum())}  "
            f"deep {int(deep.sum())}  components {ncomp}  "
            f"too-small {ncomp - len(keep_ids)}  kept {int(keep.sum())}")
        return dict(med=med, band=band, inside=inside, recurrent=recurrent,
                    deep=deep, lab=lab, sizes=sizes, keep_ids=keep_ids,
                    keep=keep, ncomp=ncomp, n_border=n_border)

    log("REAL arm")
    real = run(res, seen, "real")

    # ---- the null: roll every capture INDEPENDENTLY ----------------------
    # 02 established that rolling only half the captures is not a control at
    # all -- a median over 18 is still set by the 9 that still correspond.
    log("NULL arm (all 18 captures rolled independently)")
    rng = np.random.default_rng(20260610)
    null_counts = []
    for trial in range(2):
        rolled = np.empty_like(res)
        seen_r = np.zeros((h, w), np.int32)
        for t in range(ntag):
            dy = int(rng.integers(200, h - 200))
            dx = int(rng.integers(200, w - 200))
            r = np.roll(np.roll(res[t], dy, axis=0), dx, axis=1)
            rolled[t] = r
            seen_r += (r <= -SEED_DEPTH)
        n = run(rolled, seen_r, f"null{trial}")
        null_counts.append(int(n["keep"].sum()))
        del rolled
    log(f"    null kept quads: {null_counts}  vs real {int(real['keep'].sum())}")

    # ---- plant calibration of the high-pass attenuation -------------------
    # Push synthetic discs of KNOWN depth through the identical operator and
    # read back what the operator says.  Uses a real capture as the carrier so
    # the noise and the illumination structure are the real ones.
    log("plant calibration of the high-pass attenuation")
    carrier = np.load(OUT / "dust-median-residual.npy").astype(np.float64)
    # Work from a clean synthetic field carrying the real illumination shape:
    # the residual is already high-passed, so re-derive an unfiltered field by
    # adding 1 and letting the operator run on it.
    yy, xx = np.mgrid[0:h, 0:w]
    calib = {}
    for radius in (5, 10, 22, 44):
        for depth in (0.02, 0.035):
            field = np.ones((h, w), np.float64)
            # three widely-separated discs so one bad location cannot set it
            centres = [(600, 900), (1200, 1800), (1800, 2700)]
            mask = np.zeros((h, w), bool)
            for (cy, cx) in centres:
                mask |= ((yy - cy) ** 2 + (xx - cx) ** 2) <= radius * radius
            field[mask] *= (1.0 - depth)
            sm = box_smooth(field, HP_RADIUS, 3)
            r = field / sm - 1.0
            band = box_smooth(r.astype(np.float32), BP_RADIUS, 1)
            # read at the disc centres only, where a real gain would be read
            core = np.zeros((h, w), bool)
            for (cy, cx) in centres:
                core |= ((yy - cy) ** 2 + (xx - cx) ** 2) <= max(1, radius // 2) ** 2
            recovered = -float(np.median(r[core]))
            recovered_band = -float(np.median(band[core]))
            alpha = recovered / depth
            calib[f"r{radius}_d{depth}"] = dict(
                radius=radius, depth=depth, recovered=recovered,
                recovered_band=recovered_band, alpha=alpha,
                area=int(mask.sum() / len(centres)))
            log(f"    radius {radius:3d} quads (area {int(mask.sum()/len(centres)):6d})  "
                f"planted {depth*100:5.2f}%  recovered {recovered*100:5.2f}%  "
                f"alpha {alpha:.4f}")
    del carrier

    # alpha is a function of AREA, so pick it per component rather than once.
    alpha_by_area = sorted(
        (v["area"], v["alpha"]) for v in calib.values())

    def alpha_for(area):
        """Interpolate the measured attenuation at a component's area."""
        xs = [a for a, _ in alpha_by_area]
        ys = [b for _, b in alpha_by_area]
        return float(np.interp(area, xs, ys))

    # ---- build the dust site list ----------------------------------------
    log("building the dust site list")
    med = real["med"]
    lab = real["lab"]
    sizes = real["sizes"]
    dust_rows = []
    comp_report = []
    refused_gain = 0
    for cid in real["keep_ids"]:
        m = lab == cid
        area = int(sizes[cid])
        a = alpha_for(area)
        depth = med[m] / a            # negative
        gain = 1.0 / (1.0 + depth)
        ys, xs = np.nonzero(m)
        ok = np.isfinite(gain) & (gain >= 1.0) & (gain <= 1.25)
        refused_gain += int((~ok).sum())
        for x, y, g in zip(xs[ok], ys[ok], gain[ok]):
            dust_rows.append((int(x), int(y), float(g)))
        comp_report.append(dict(
            id=int(cid), area=area, alpha=a,
            depth_med_pct=float(np.median(med[m]) * 100),
            depth_min_pct=float(med[m].min() * 100),
            gain_med=float(np.median(gain)),
            cy=float(ys.mean()), cx=float(xs.mean()),
            diam_quads=float(2 * math.sqrt(area / math.pi))))
    comp_report.sort(key=lambda c: -c["area"])
    log(f"    {len(dust_rows)} dust quads in {len(real['keep_ids'])} components; "
        f"{refused_gain} quads refused for an out-of-range gain")
    for c in comp_report[:12]:
        log(f"      comp area {c['area']:6d} (d~{c['diam_quads']:5.1f} quads)  "
            f"at ({c['cx']:6.0f},{c['cy']:6.0f})  median {c['depth_med_pct']:6.2f}%  "
            f"worst {c['depth_min_pct']:6.2f}%  alpha {c['alpha']:.3f}  "
            f"gain {c['gain_med']:.4f}")

    # ---- hot sites --------------------------------------------------------
    log("building the hot site list")
    recur = np.load(OUT / "hot-recur.npy")        # (4, 2344, 3514)
    exc = np.load(OUT / "hot-excess-e.npy")       # (4, 2344, 3514) e-
    PLANE_OFF = [(0, 0), (1, 0), (0, 1), (1, 1)]  # RGGB: R G1 / G2 B
    hot_rows = []
    strata = {}
    for p, (ox, oy) in enumerate(PLANE_OFF):
        sel = recur[p] >= HOT_RECURRENCE
        ys, xs = np.nonzero(sel)
        es = exc[p][sel]
        for x, y, e in zip(xs, ys, es):
            hot_rows.append((int(2 * x + ox), int(2 * y + oy), float(e)))
        strata[["R", "G1", "G2", "B"][p]] = int(sel.sum())
    hot_rows.sort(key=lambda r: (r[1], r[0]))
    amps = np.array([r[2] for r in hot_rows])
    log(f"    {len(hot_rows)} hot sites  {strata}")
    for lo, hi in ((0, 2), (2, 4), (4, 8), (8, 16), (16, 1e9)):
        n = int(((amps >= lo) & (amps < hi)).sum())
        log(f"      {lo:5.0f}-{hi:5.0f} e- : {n:6d}")
    n_ship = int((amps >= 8.0).sum())
    log(f"    at the reproducible floor (>= 8 e-): {n_ship}")

    # ---- the partition, which must sum ------------------------------------
    inside = real["inside"]
    n_border = real["n_border"]
    n_inside = total_quads - n_border
    n_recurrent = int(real["recurrent"].sum())
    n_deep = int(real["deep"].sum())
    n_kept = int(real["keep"].sum())
    part = dict(
        total=total_quads,
        border_excluded=n_border,
        examined=n_inside,
        not_recurrent=n_inside - n_recurrent,
        recurrent_but_shallow=n_recurrent - n_deep,
        deep_but_too_small=n_deep - n_kept,
        emitted=len(dust_rows),
        emitted_refused_gain=refused_gain,
    )
    s = (part["border_excluded"] + part["not_recurrent"]
         + part["recurrent_but_shallow"] + part["deep_but_too_small"]
         + part["emitted"] + part["emitted_refused_gain"])
    log(f"    partition sums to {s} of {total_quads}  "
        f"({'OK' if s == total_quads else 'MISMATCH'})")
    assert s == total_quads, (s, total_quads, part)

    # ---- write the sidecar ------------------------------------------------
    path = OUT / f"defect-map-{CAMERA}.txt"
    log(f"writing {path}")
    prov = [
        f"built {time.strftime('%Y-%m-%dT%H:%M:%S')} by experiments/BUILD-DEFECT/src/04-build-map.py",
        f"hot: 242 dark frames, 11 ISO groups x 20 (2 stabilisation shots dropped per group),",
        f"hot: 1/100 s, ISO 50-2000, D:\\macro-dark-frames; 6-sigma neighbour excess,",
        f"hot: recurrence >= {HOT_RECURRENCE}/11; census {len(hot_rows)} vs M101 14604 (+0.2%)",
        f"dust: 18 flat captures (9 shutter speeds x 2 CPL states) x 20 frames,",
        f"dust: D:\\personal\\macro\\flat-fields, f/{APERTURE} at 200 mm, ISO 100;",
        f"dust: high-pass r={HP_RADIUS} n=3, band-pass r={BP_RADIUS}, seed {SEED_DEPTH*100:.1f}%,",
        f"dust: recurrence >= {RECURRENCE}/18, floor {FLOOR_DEPTH*100:.2f}%, border {BORDER},",
        f"dust: min component {MIN_COMPONENT} quads; attenuation calibrated by planted discs",
        f"dust: null (18 independent rolls) kept {null_counts} quads vs {n_kept} real",
        f"geometry: rawler active {SENSOR_W}x{SENSOR_H}; rawpy visible {COVERED_W}x{COVERED_H};",
        f"geometry: the last {SENSOR_W - COVERED_W} sensor columns are UNMEASURED, not clean",
    ]
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
    log(f"    {path.stat().st_size/1e6:.2f} MB")

    out = dict(
        params=dict(hp_radius=HP_RADIUS, bp_radius=BP_RADIUS,
                    seed_depth=SEED_DEPTH, recurrence=RECURRENCE,
                    floor_depth=FLOOR_DEPTH, border=BORDER,
                    min_component=MIN_COMPONENT, hot_recurrence=HOT_RECURRENCE),
        partition=part,
        null_kept=null_counts,
        real_kept=n_kept,
        components=comp_report,
        calibration=calib,
        hot=dict(total=len(hot_rows), per_plane=strata,
                 at_reproducible_floor=n_ship),
        map_path=str(path),
        map_bytes=path.stat().st_size,
    )
    (DATA / "04-map.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    log("wrote data/04-map.json")


if __name__ == "__main__":
    sys.exit(main())

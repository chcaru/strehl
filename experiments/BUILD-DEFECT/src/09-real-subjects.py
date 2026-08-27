"""THE DECIDING MEASUREMENT: is the dust in the owner's actual photographs?

Everything up to here was measured on flat fields -- a white sheet of paper.  A
map built from flats and never seen in a photograph is a map of the paper.  The
mission is print quality on macro subjects, so the question that decides whether
this feature ships is:

    at the four sensor coordinates the flats nominate, is there a fixed
    multiplicative dip in REAL SUBJECT captures, and how deep?

The confound is obvious and fatal if ignored: a subject has detail, and the
high-pass residual of a photograph is dominated by that detail, not by dust.  A
focus bracket makes it worse, because the subject is nearly stationary from
frame to frame, so subject detail is nearly as "fixed" as dust is.  Averaging
frames WITHIN one stack therefore cannot separate them.

The discriminator is BETWEEN SUBJECTS.  A bee, a flower and a sheet of wrapped
text share no detail whatsoever; they share exactly one thing, which is the
sensor.  So:

    per subject: median over frames of the high-pass residual  ->  S_k
    across subjects: median over k of S_k                      ->  D

Subject detail is independent across k and the median kills it.  Dust is common
to every k and survives at full depth.  That is the same recurrence argument
that built the map, but now the "captures" are photographs of different things
on different days.

CONTROLS (a search that cannot fail is not a search -- AGENTS.md):

  A. ROLL NULL.  Roll each subject's S_k by its own large random offset, so no
     two correspond, and rebuild D.  If the pipeline manufactures dips, it
     manufactures them here too.
  B. LOCATION NULL.  Score the four real footprints against 200 random
     footprints of matched area drawn from the same interior.  This asks
     whether -1% is even unusual on this statistic.
  C. AN IMPROVEMENT ARM.  Plant a KNOWN 2.5% disc into every subject at a
     location that has no mote, and require the statistic to find it at the
     calibrated depth.  Without this arm a blind statistic and a working one
     look identical when the answer happens to be "nothing there".

Reports depth per subject as well as pooled, because "the mote is in the pooled
median" and "the mote is in every photograph" are different claims and only the
second one justifies shipping a correction that runs on every frame.
"""

import json
import pathlib
import time

import numpy as np
import rawpy
from scipy import ndimage

HERE = pathlib.Path(__file__).resolve().parents[1]
OUT = HERE / "out"
DATA = HERE / "data"
MACRO = pathlib.Path(r"D:\personal\macro")
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


HP_RADIUS, HP_PASS, BP_RADIUS = 30, 3, 2
BORDER = 60
FRAMES_PER_SUBJECT = 10
N_LOCATION_NULL = 200
PLANT_DEPTH = 0.025
PLANT_RADIUS = 11  # quads; area ~380, close to the largest real mote (396)
# Where the planted improvement goes.  Deep interior, and checked below to be
# far from every real mote so the two arms cannot be reading each other.
PLANT_AT = (1200, 1400)

SUBJECTS = [
    "bee-3-cpl",
    "flower-inner-edge-cpl",
    "wrapped-text-1",
    "dry-erase-marker-head-cpl",
    "lavendar-cpl",
    "couch-fibers-cpl",
]


def box_smooth(a, radius, npass):
    cur = a.astype(np.float64)
    win = 2 * radius + 1
    for _ in range(npass):
        cur = ndimage.uniform_filter1d(cur, win, axis=1, mode="nearest")
        cur = ndimage.uniform_filter1d(cur, win, axis=0, mode="nearest")
    return cur


def quad_mean(raw, black):
    """Black-subtracted mean of the four CFA samples of every quad.

    Working on the quad average rather than one plane is deliberate: dust is
    achromatic (it attenuates all four planes by the same factor) so the quad
    mean is the highest-SNR estimator of it, and it makes the lattice square.
    """
    v = raw.astype(np.float64) - black
    return 0.25 * (v[0::2, 0::2] + v[0::2, 1::2] + v[1::2, 0::2] + v[1::2, 1::2])


def residual(q):
    """Per-frame normalised high-pass residual, identical operator to 01/08."""
    lo = box_smooth(q, HP_RADIUS, HP_PASS)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(lo > 1.0, q / lo - 1.0, np.nan)
    return box_smooth(np.nan_to_num(r), BP_RADIUS, 1)


def plant(q, cy, cx, radius, depth):
    h, w = q.shape
    yy, xx = np.ogrid[:h, :w]
    d2 = (yy - cy) ** 2 + (xx - cx) ** 2
    return q * np.where(d2 <= radius * radius, 1.0 - depth, 1.0)


def load_map_motes():
    """The four motes, as connected components, from the shipping map."""
    txt = (OUT / "defect-map-ILCE-7CM2.txt").read_text(encoding="utf-8")
    quads = []
    for line in txt.splitlines():
        if line.startswith("d "):
            _, px, py, gain = line.split()
            quads.append((int(px), int(py), float(gain)))
    return quads


def components(quads, shape):
    m = np.zeros(shape, bool)
    for px, py, _ in quads:
        m[py, px] = True
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(lab == i)
        out.append(
            dict(
                id=i,
                area=int(ys.size),
                cy=int(round(ys.mean())),
                cx=int(round(xs.mean())),
                mask=(lab == i),
            )
        )
    out.sort(key=lambda c: -c["area"])
    return out


def score(D, mask):
    v = D[mask]
    v = v[np.isfinite(v)]
    if v.size == 0:
        return dict(n=0, median=float("nan"), p10=float("nan"))
    return dict(
        n=int(v.size),
        median=float(np.median(v)),
        p10=float(np.percentile(v, 10)),
    )


def main():
    OUT.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    rng = np.random.default_rng(20240611)

    quads = load_map_motes()
    log(f"map: {len(quads)} dust quads")

    per_subject = []
    used = []
    shape = None
    planted_stack = []
    for name in SUBJECTS:
        d = MACRO / name
        arws = sorted(d.glob("*.ARW"))
        if not arws:
            log(f"  {name}: NO ARW, skipped")
            continue
        take = arws[:: max(1, len(arws) // FRAMES_PER_SUBJECT)][:FRAMES_PER_SUBJECT]
        rs, ps = [], []
        aperture = None
        for p in take:
            with rawpy.imread(str(p)) as raw:
                black = float(np.mean(raw.black_level_per_channel))
                vis = raw.raw_image_visible
                q = quad_mean(vis, black)
            if shape is None:
                shape = q.shape
            if q.shape != shape:
                log(f"  {name}: geometry {q.shape} != {shape}, REFUSED")
                rs = []
                break
            rs.append(residual(q))
            ps.append(residual(plant(q, PLANT_AT[0], PLANT_AT[1], PLANT_RADIUS, PLANT_DEPTH)))
        if not rs:
            continue
        try:
            import exifread  # noqa: F401
        except Exception:
            pass
        per_subject.append(np.median(np.stack(rs), axis=0))
        planted_stack.append(np.median(np.stack(ps), axis=0))
        used.append(dict(name=name, frames=len(rs), first=take[0].name))
        log(f"  {name}: {len(rs)} frames, rms {np.std(per_subject[-1]) * 100:.4f}%")
        del rs, ps

    if len(per_subject) < 3:
        raise SystemExit(f"only {len(per_subject)} subjects loaded; the brief requires 3")

    S = np.stack(per_subject)
    D = np.median(S, axis=0)
    Dplant = np.median(np.stack(planted_stack), axis=0)
    h, w = D.shape
    log(f"pooled over {S.shape[0]} subjects, {h}x{w} quads, rms {np.std(D) * 100:.4f}%")

    # -- A. roll null -------------------------------------------------------
    rolled = np.stack(
        [
            np.roll(s, (int(rng.integers(200, h - 200)), int(rng.integers(200, w - 200))), (0, 1))
            for s in S
        ]
    )
    Dnull = np.median(rolled, axis=0)
    log(f"roll null rms {np.std(Dnull) * 100:.4f}%")
    del rolled

    comps = components(quads, (h, w))
    log(f"{len(comps)} motes in the map")

    # -- the four real footprints, real arm vs roll null ---------------------
    rows = []
    for c in comps:
        real = score(D, c["mask"])
        null = score(Dnull, c["mask"])
        rows.append(
            dict(
                area=c["area"],
                quad=[c["cx"], c["cy"]],
                real_median_pct=100 * real["median"],
                real_p10_pct=100 * real["p10"],
                null_median_pct=100 * null["median"],
                per_subject_pct=[100 * float(np.median(s[c["mask"]])) for s in S],
            )
        )
        log(
            f"  mote {c['area']:4d} quads at ({c['cx']:4d},{c['cy']:4d}): "
            f"real {100 * real['median']:+.4f}% p10 {100 * real['p10']:+.4f}%  "
            f"roll-null {100 * null['median']:+.4f}%"
        )
        log(
            "      per subject: "
            + " ".join(f"{v:+.3f}%" for v in rows[-1]["per_subject_pct"])
        )

    # -- B. location null ---------------------------------------------------
    log("location null: 200 random footprints of matched area, deep interior")
    loc_null = {}
    for c in comps:
        ys, xs = np.nonzero(c["mask"])
        dy, dx = ys - ys.min(), xs - xs.min()
        hh, ww = dy.max() + 1, dx.max() + 1
        meds = []
        for _ in range(N_LOCATION_NULL):
            oy = int(rng.integers(BORDER, h - BORDER - hh))
            ox = int(rng.integers(BORDER, w - BORDER - ww))
            meds.append(float(np.median(D[oy + dy, ox + dx])))
        meds = np.array(meds)
        real = float(np.median(D[c["mask"]]))
        below = int(np.sum(meds <= real))
        loc_null[c["area"]] = dict(
            real_pct=100 * real,
            null_median_pct=100 * float(np.median(meds)),
            null_p1_pct=100 * float(np.percentile(meds, 1)),
            null_min_pct=100 * float(meds.min()),
            n_null_at_least_as_deep=below,
            p_value=(below + 1) / (N_LOCATION_NULL + 1),
        )
        log(
            f"  mote {c['area']:4d}: real {100 * real:+.4f}%  null median "
            f"{100 * float(np.median(meds)):+.4f}%  null 1st pct "
            f"{100 * float(np.percentile(meds, 1)):+.4f}%  "
            f"{below}/{N_LOCATION_NULL} nulls at least as deep  p={(below + 1) / (N_LOCATION_NULL + 1):.4f}"
        )

    # -- C. the improvement arm --------------------------------------------
    yy, xx = np.ogrid[:h, :w]
    pm = ((yy - PLANT_AT[0]) ** 2 + (xx - PLANT_AT[1]) ** 2) <= PLANT_RADIUS**2
    for c in comps:
        assert not (pm & c["mask"]).any(), "plant overlaps a real mote"
    unplanted_here = float(np.median(D[pm]))
    planted_here = float(np.median(Dplant[pm]))
    log(
        f"plant arm: {PLANT_DEPTH * 100:.1f}% disc r={PLANT_RADIUS} at "
        f"{PLANT_AT}: unplanted {100 * unplanted_here:+.4f}%, planted "
        f"{100 * planted_here:+.4f}%, delta {100 * (planted_here - unplanted_here):+.4f}%"
    )

    result = dict(
        subjects=used,
        pooled_rms_pct=100 * float(np.std(D)),
        roll_null_rms_pct=100 * float(np.std(Dnull)),
        motes=rows,
        location_null=loc_null,
        plant=dict(
            depth_pct=100 * PLANT_DEPTH,
            radius_quads=PLANT_RADIUS,
            at=list(PLANT_AT),
            unplanted_pct=100 * unplanted_here,
            planted_pct=100 * planted_here,
            recovered_pct=100 * (planted_here - unplanted_here),
        ),
    )
    (DATA / "09-real.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    log("wrote data/09-real.json")


if __name__ == "__main__":
    main()

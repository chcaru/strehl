"""Can the photograph search be made to pass its own null?

Script 10's blind search over the pooled residual of six subjects returned 5-102
components -- and its roll null returned 1-42 at every one of fifteen settings.
A search whose null is never clean cannot distinguish dust from "what six
medianed subject residuals look like", so 10 correctly refused to name a
shipping setting.

The arithmetic says why.  The survival test is "negative in every subject", so
under the null a quad survives with probability 2^-k for k subjects: at k = 6
that is 1.6% of 8.2 million quads, which is 128,000 surviving quads and plenty
of accidental 12-quad clusters.  At k = 12 it is 2.4e-4, or 2,000 quads spread
over the whole sensor, and a 12-quad cluster becomes very unlikely.

So the null is not a property of the data, it is a property of k.  This script
raises k to twelve unrelated subjects and re-runs the identical search.  If the
null goes to zero the search becomes able to fail, and whatever it then returns
is a real find; if it does not, the honest report is that this method cannot
answer the question and the flats-nominated footprints (script 09) are the only
evidence available.

The improvement arm rides along at every null-clean setting, because a search
that returns nothing and a search that is blind produce the same log line.
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
FRAMES_PER_SUBJECT = 8
MIN_COMPONENT = 12
PLANT_DEPTH = 0.025
PLANT_RADIUS = 11
PLANT_AT = (1200, 1400)

SUBJECTS = [
    "bee-1-cpl",
    "bee-3-cpl",
    "coffee-bean",
    "couch-fibers-cpl",
    "dry-erase-marker-head-cpl",
    "flower-bud-alone-cpl",
    "flower-inner-edge-cpl",
    "lavendar-cpl",
    "leaf-2-cpl",
    "pencil-steep-angle-cpl",
    "tweezers-cpl",
    "wrapped-text-1",
]


def box_smooth(a, radius, npass):
    cur = a.astype(np.float64)
    win = 2 * radius + 1
    for _ in range(npass):
        cur = ndimage.uniform_filter1d(cur, win, axis=1, mode="nearest")
        cur = ndimage.uniform_filter1d(cur, win, axis=0, mode="nearest")
    return cur


def quad_mean(raw, black):
    v = raw.astype(np.float64) - black
    return 0.25 * (v[0::2, 0::2] + v[0::2, 1::2] + v[1::2, 0::2] + v[1::2, 1::2])


def residual(q):
    lo = box_smooth(q, HP_RADIUS, HP_PASS)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(lo > 1.0, q / lo - 1.0, np.nan)
    return box_smooth(np.nan_to_num(r), BP_RADIUS, 1)


def plant(q, cy, cx, radius, depth):
    h, w = q.shape
    yy, xx = np.ogrid[:h, :w]
    return q * np.where((yy - cy) ** 2 + (xx - cx) ** 2 <= radius * radius, 1.0 - depth, 1.0)


def find(D, allneg, seed, floor, interior):
    m = (D <= -seed) & allneg & interior
    if not m.any():
        return []
    lab, n = ndimage.label((D <= -floor) & allneg & interior, structure=np.ones((3, 3)))
    out = []
    for i in sorted(set(np.unique(lab[m])) - {0}):
        sel = lab == i
        area = int(sel.sum())
        if area < MIN_COMPONENT:
            continue
        ys, xs = np.nonzero(sel)
        out.append(
            dict(
                area=area,
                cx=int(round(xs.mean())),
                cy=int(round(ys.mean())),
                median=float(np.median(D[sel])),
                worst=float(D[sel].min()),
            )
        )
    out.sort(key=lambda c: c["median"])
    return out


def main():
    rng = np.random.default_rng(2718281)
    per_subject, planted, used = [], [], []
    for name in SUBJECTS:
        arws = sorted((MACRO / name).glob("*.ARW"))
        if not arws:
            log(f"  {name}: NO ARW, skipped")
            continue
        take = arws[:: max(1, len(arws) // FRAMES_PER_SUBJECT)][:FRAMES_PER_SUBJECT]
        rs, ps = [], []
        for p in take:
            with rawpy.imread(str(p)) as raw:
                black = float(np.mean(raw.black_level_per_channel))
                q = quad_mean(raw.raw_image_visible, black)
            rs.append(residual(q))
            ps.append(residual(plant(q, PLANT_AT[0], PLANT_AT[1], PLANT_RADIUS, PLANT_DEPTH)))
        per_subject.append(np.median(np.stack(rs), axis=0).astype(np.float32))
        planted.append(np.median(np.stack(ps), axis=0).astype(np.float32))
        used.append(name)
        log(f"  {name}: {len(rs)} frames, rms {np.std(per_subject[-1]) * 100:.4f}%")
        del rs, ps

    S = np.stack(per_subject)
    k = S.shape[0]
    D = np.median(S, axis=0)
    allneg = (S < 0).all(axis=0)
    Sp = np.stack(planted)
    Dp = np.median(Sp, axis=0)
    allneg_p = (Sp < 0).all(axis=0)
    h, w = D.shape
    interior = np.zeros((h, w), bool)
    interior[BORDER : h - BORDER, BORDER : w - BORDER] = True
    log(
        f"k={k} subjects, pooled rms {np.std(D) * 100:.4f}%, "
        f"all-negative {allneg.sum()} quads ({100 * allneg.mean():.4f}%, "
        f"chance 2^-{k} = {100 * 2.0**-k:.4f}%)"
    )

    nulls = []
    for _ in range(3):
        R = np.stack(
            [
                np.roll(
                    s,
                    (int(rng.integers(200, h - 200)), int(rng.integers(200, w - 200))),
                    (0, 1),
                )
                for s in S
            ]
        )
        nulls.append((np.median(R, axis=0), (R < 0).all(axis=0)))
        del R
    log(f"null all-negative {[int(a.sum()) for _, a in nulls]} quads")

    rows = []
    for seed in (0.0075, 0.010, 0.015, 0.020):
        for floor in (0.005, 0.0075):
            if floor > seed:
                continue
            real = find(D, allneg, seed, floor, interior)
            nc = [len(find(dn, an, seed, floor, interior)) for dn, an in nulls]
            got = find(Dp, allneg_p, seed, floor, interior)
            hit = [c for c in got if (c["cy"] - PLANT_AT[0]) ** 2 + (c["cx"] - PLANT_AT[1]) ** 2 <= 400]
            rows.append(
                dict(
                    seed_pct=100 * seed,
                    floor_pct=100 * floor,
                    real=len(real),
                    null=nc,
                    plant_found=bool(hit),
                    plant_median_pct=100 * hit[0]["median"] if hit else None,
                    plant_area=hit[0]["area"] if hit else 0,
                    top=real[:6],
                )
            )
            log(
                f"  seed {seed * 100:5.2f}% floor {floor * 100:5.2f}%: real {len(real):3d}, "
                f"null {nc}, plant "
                + (
                    f"FOUND area {hit[0]['area']} median {100 * hit[0]['median']:+.3f}%"
                    if hit
                    else "MISSED"
                )
            )
            for c in real[:6]:
                log(
                    f"      area {c['area']:4d} at ({c['cx']:4d},{c['cy']:4d}) "
                    f"median {100 * c['median']:+.3f}% worst {100 * c['worst']:+.3f}%"
                )

    clean = [r for r in rows if max(r["null"]) == 0 and r["plant_found"]]
    if clean:
        b = clean[0]
        log(
            f"SHIPPING SETTING seed {b['seed_pct']:.2f}% floor {b['floor_pct']:.2f}%: "
            f"{b['real']} components, null 0/0/0, plant found at "
            f"{b['plant_median_pct']:+.3f}%"
        )
    else:
        log("SHIPPING SETTING: NONE -- no setting is both null-clean and not blind")

    (DATA / "11-photograph-dust-k12.json").write_text(
        json.dumps(dict(subjects=used, k=k, sweep=rows), indent=1), encoding="utf-8"
    )
    np.save(OUT / "11-pooled-k12.npy", D)
    np.save(OUT / "11-allneg-k12.npy", allneg)
    log("wrote data/11-photograph-dust-k12.json")


if __name__ == "__main__":
    main()

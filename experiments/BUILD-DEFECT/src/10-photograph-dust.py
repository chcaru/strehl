"""What dust is ACTUALLY in the owner's photographs?

Script 09 returned a result that kills the flats-derived dust map as a shipping
artefact: of the four motes the flat fields nominate, three read POSITIVE in the
pooled real-subject residual (+0.39%, +0.41%, +0.54%) at p ~ 0.83-0.85 against a
200-draw location null, i.e. indistinguishable from nothing.  Only the smallest
component, 29 quads at quad (3209,116), reads negative -- -2.39%, negative in
6 of 6 subjects, p = 0.0299.

The plant arm in 09 rules out the boring explanation.  A known 2.5% disc planted
into the same six subjects and pushed through the identical operator is
recovered at -2.2853%.  The statistic is not blind, so "+0.39%" means the mote
is not there, not that the measurement cannot see it.

So the flats nominated defects the photographs do not have.  This script asks
the question the other way round, and it is the one that decides what ships:

    SEARCH THE PHOTOGRAPHS THEMSELVES.  Take the pooled residual over six
    unrelated subjects, and look for fixed multiplicative dips with

      * a FLOOR, swept, so the search can return nothing;
      * a ROLL NULL rebuilt at every setting, so a setting that manufactures
        components is visible as such;
      * a SIGN-CONSISTENCY requirement across all six subjects, which is the
        between-subject analogue of the flats' 15/18 recurrence;
      * an IMPROVEMENT ARM, so a setting that is blind is visible as such.

If this returns nothing, the honest answer is that this body has no dust worth
correcting in these photographs, and the correct thing to ship is a working
mechanism that is off, plus the measurement that says why.
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
MIN_COMPONENT = 12
PLANT_DEPTH = 0.025
PLANT_RADIUS = 11
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


def find(D, S, seed, floor, need_all_negative, interior):
    """Components of `D` below `seed`, grown to `floor`, that every subject in
    `S` also reads negative.  Returns a list of dicts; may be empty."""
    m = (D <= -seed) & interior
    if not m.any():
        return []
    grown = (D <= -floor) & interior
    lab, n = ndimage.label(grown, structure=np.ones((3, 3)))
    keep = set(np.unique(lab[m])) - {0}
    out = []
    for i in sorted(keep):
        sel = lab == i
        area = int(sel.sum())
        if area < MIN_COMPONENT:
            continue
        per = [float(np.median(s[sel])) for s in S]
        if need_all_negative and not all(v < 0 for v in per):
            continue
        ys, xs = np.nonzero(sel)
        out.append(
            dict(
                area=area,
                cx=int(round(xs.mean())),
                cy=int(round(ys.mean())),
                median=float(np.median(D[sel])),
                worst=float(D[sel].min()),
                per_subject=per,
            )
        )
    out.sort(key=lambda c: c["median"])
    return out


def main():
    rng = np.random.default_rng(31415926)

    per_subject, planted, used = [], [], []
    shape = None
    for name in SUBJECTS:
        arws = sorted((MACRO / name).glob("*.ARW"))
        take = arws[:: max(1, len(arws) // FRAMES_PER_SUBJECT)][:FRAMES_PER_SUBJECT]
        rs, ps = [], []
        for p in take:
            with rawpy.imread(str(p)) as raw:
                black = float(np.mean(raw.black_level_per_channel))
                q = quad_mean(raw.raw_image_visible, black)
            if shape is None:
                shape = q.shape
            rs.append(residual(q))
            ps.append(residual(plant(q, PLANT_AT[0], PLANT_AT[1], PLANT_RADIUS, PLANT_DEPTH)))
        per_subject.append(np.median(np.stack(rs), axis=0))
        planted.append(np.median(np.stack(ps), axis=0))
        used.append(name)
        log(f"  {name}: {len(rs)} frames")
        del rs, ps

    S = np.stack(per_subject)
    D = np.median(S, axis=0)
    Dp = np.median(np.stack(planted), axis=0)
    h, w = D.shape

    interior = np.zeros((h, w), bool)
    interior[BORDER : h - BORDER, BORDER : w - BORDER] = True

    # The null: each subject rolled by its own large offset, so no two
    # correspond.  Rebuilt from the SAME per-subject maps, so it differs from
    # the real arm in exactly one thing -- whether the sensor coordinates line
    # up.  Three independent draws, because one draw of a null is an anecdote.
    nulls = []
    for t in range(3):
        rolled = np.stack(
            [
                np.roll(
                    s,
                    (int(rng.integers(200, h - 200)), int(rng.integers(200, w - 200))),
                    (0, 1),
                )
                for s in S
            ]
        )
        nulls.append((np.median(rolled, axis=0), rolled))
    log(f"pooled rms {np.std(D) * 100:.4f}%, null rms {np.std(nulls[0][0]) * 100:.4f}%")

    rows = []
    for seed in (0.005, 0.0075, 0.010, 0.015, 0.020, 0.030):
        for floor in (0.005, 0.0075, 0.010):
            if floor > seed:
                continue
            real = find(D, S, seed, floor, True, interior)
            nc = [len(find(dn, sn, seed, floor, True, interior)) for dn, sn in nulls]
            rows.append(
                dict(
                    seed_pct=100 * seed,
                    floor_pct=100 * floor,
                    real=len(real),
                    null=nc,
                    top=real[:4],
                )
            )
            log(
                f"  seed {seed * 100:5.2f}% floor {floor * 100:5.2f}%: "
                f"real {len(real):3d} components, null {nc}"
            )

    # The improvement arm, at every setting that returned zero on the null.
    yy, xx = np.ogrid[:h, :w]
    pm = ((yy - PLANT_AT[0]) ** 2 + (xx - PLANT_AT[1]) ** 2) <= PLANT_RADIUS**2
    Sp = np.stack(planted)
    plant_rows = []
    for r in rows:
        if max(r["null"]) != 0:
            continue
        got = find(Dp, Sp, r["seed_pct"] / 100, r["floor_pct"] / 100, True, interior)
        hit = [c for c in got if pm[c["cy"], c["cx"]]]
        plant_rows.append(
            dict(
                seed_pct=r["seed_pct"],
                floor_pct=r["floor_pct"],
                found_plant=bool(hit),
                plant_area=hit[0]["area"] if hit else 0,
                plant_median_pct=100 * hit[0]["median"] if hit else None,
                total=len(got),
            )
        )
        log(
            f"  PLANT seed {r['seed_pct']:5.2f}% floor {r['floor_pct']:5.2f}%: "
            f"{'FOUND' if hit else 'MISSED'}"
            + (
                f" area {hit[0]['area']} median {100 * hit[0]['median']:+.3f}%"
                if hit
                else ""
            )
            + f" (total components with the plant in: {len(got)})"
        )

    best = None
    for r in rows:
        if max(r["null"]) == 0 and r["real"] > 0:
            pr = next(
                (p for p in plant_rows if p["seed_pct"] == r["seed_pct"] and p["floor_pct"] == r["floor_pct"]),
                None,
            )
            if pr and pr["found_plant"]:
                best = r
                break
    if best:
        log(
            f"SHIPPING SETTING seed {best['seed_pct']:.2f}% floor "
            f"{best['floor_pct']:.2f}%: {best['real']} components, null 0/0/0, plant FOUND"
        )
        for c in best["top"]:
            log(
                f"    area {c['area']:4d} at ({c['cx']:4d},{c['cy']:4d}) median "
                f"{100 * c['median']:+.3f}% worst {100 * c['worst']:+.3f}%  per subject "
                + " ".join(f"{100 * v:+.2f}" for v in c["per_subject"])
            )
    else:
        log("SHIPPING SETTING: NONE -- no setting is both null-clean and not blind")

    (DATA / "10-photograph-dust.json").write_text(
        json.dumps(
            dict(subjects=used, sweep=rows, plant=plant_rows, chosen=best),
            indent=1,
        ),
        encoding="utf-8",
    )
    np.save(OUT / "10-pooled.npy", D.astype(np.float32))
    log("wrote data/10-photograph-dust.json and out/10-pooled.npy")


if __name__ == "__main__":
    main()

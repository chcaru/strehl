"""The photograph search, third attempt -- and the arm that saved it.

Script 11 raised the subject count to twelve and the roll null finally went to
0/0/0 at seed 2.00%, with the real arm returning 50 components.  Fifty
components, a clean null, a tidy story.  It is wrong.

The improvement arm missed at every one of the eight settings.  A 2.5% disc
planted into all twelve subjects -- a defect deeper than three of the four motes
the flats nominate -- was not found by the search that was about to report 50
finds.  The search was BLIND, and a blind search with a clean null returns its
least-bad candidates and calls them dust.  This is precisely the failure
AGENTS.md describes, and the only reason it is visible is that the commissioning
suite plants an improvement and not only degradations.

The cause is the survival test, not the depth.  Script 11 required a quad to be
negative in EVERY subject.  That is a sign test, it carries no depth
information, and on photographs whose per-subject residual rms is 0.96% to 9.39%
a 2.3% dip does not flip the sign of a subject that was at +5%.  Requiring
twelve independent sign flips is a filter on subject texture, not on dust: it
kept 21,504 quads where chance alone predicts 2,009, and every one of the 50
survivors is a place where twelve photographs happened to agree in sign.

So this script scores DEPTH -- the pooled median at the footprint, which is what
script 09 used and which recovered the plant at -2.2853%.  Same null, same
plant, same sweep, one statistic changed.

Also renders the top candidates, because a number that nobody looked at is a
number nobody checked.
"""

import json
import pathlib
import struct
import time
import zlib

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
N_LOCATION_NULL = 400
CACHE = OUT / "12-subject-stack.npy"

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


def write_png(path, img):
    """Greyscale 8-bit PNG, hand-rolled: PIL mis-reads this project's TIFFs and
    is not trusted here either."""
    h, w = img.shape
    raw = b"".join(b"\x00" + img[y].tobytes() for y in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))

    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def find(D, seed, floor, interior):
    m = (D <= -seed) & interior
    if not m.any():
        return []
    lab, _ = ndimage.label((D <= -floor) & interior, structure=np.ones((3, 3)))
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
                ys=ys,
                xs=xs,
            )
        )
    out.sort(key=lambda c: c["median"])
    return out


def load_stack():
    if CACHE.exists():
        log(f"reusing {CACHE.name}")
        return np.load(CACHE), np.load(OUT / "12-plant-stack.npy"), SUBJECTS
    per, pl = [], []
    for name in SUBJECTS:
        arws = sorted((MACRO / name).glob("*.ARW"))
        take = arws[:: max(1, len(arws) // FRAMES_PER_SUBJECT)][:FRAMES_PER_SUBJECT]
        rs, ps = [], []
        for p in take:
            with rawpy.imread(str(p)) as raw:
                black = float(np.mean(raw.black_level_per_channel))
                q = quad_mean(raw.raw_image_visible, black)
            rs.append(residual(q))
            ps.append(residual(plant(q, PLANT_AT[0], PLANT_AT[1], PLANT_RADIUS, PLANT_DEPTH)))
        per.append(np.median(np.stack(rs), axis=0).astype(np.float32))
        pl.append(np.median(np.stack(ps), axis=0).astype(np.float32))
        log(f"  {name}: {len(rs)} frames, rms {np.std(per[-1]) * 100:.4f}%")
        del rs, ps
    S, P = np.stack(per), np.stack(pl)
    np.save(CACHE, S)
    np.save(OUT / "12-plant-stack.npy", P)
    return S, P, SUBJECTS


def main():
    rng = np.random.default_rng(16180339)
    S, P, used = load_stack()
    k = S.shape[0]
    D = np.median(S, axis=0)
    Dp = np.median(P, axis=0)
    h, w = D.shape
    interior = np.zeros((h, w), bool)
    interior[BORDER : h - BORDER, BORDER : w - BORDER] = True
    log(f"k={k}, pooled rms {np.std(D) * 100:.4f}%, plant-arm rms {np.std(Dp) * 100:.4f}%")

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
        nulls.append(np.median(R, axis=0))
        del R

    rows = []
    for seed in (0.010, 0.015, 0.020, 0.025, 0.030, 0.040):
        for floor in (0.0075, 0.010, 0.015):
            if floor > seed:
                continue
            real = find(D, seed, floor, interior)
            nc = [len(find(dn, seed, floor, interior)) for dn in nulls]
            got = find(Dp, seed, floor, interior)
            hit = [
                c
                for c in got
                if (c["cy"] - PLANT_AT[0]) ** 2 + (c["cx"] - PLANT_AT[1]) ** 2 <= 900
            ]
            rows.append(
                dict(
                    seed_pct=100 * seed,
                    floor_pct=100 * floor,
                    real=len(real),
                    null=nc,
                    plant_found=bool(hit),
                    plant_area=hit[0]["area"] if hit else 0,
                    plant_median_pct=100 * hit[0]["median"] if hit else None,
                )
            )
            log(
                f"  seed {seed * 100:5.2f}% floor {floor * 100:5.2f}%: real {len(real):4d}, "
                f"null {nc}, plant "
                + (
                    f"FOUND area {hit[0]['area']:4d} median {100 * hit[0]['median']:+.3f}%"
                    if hit
                    else "MISSED"
                )
            )

    clean = [r for r in rows if max(r["null"]) == 0 and r["plant_found"]]
    chosen = clean[0] if clean else None
    if not chosen:
        log("SHIPPING SETTING: NONE -- no setting is both null-clean and not blind")
        (DATA / "12-photograph-depth.json").write_text(
            json.dumps(dict(subjects=used, k=k, sweep=rows, chosen=None), indent=1),
            encoding="utf-8",
        )
        return

    seed, floor = chosen["seed_pct"] / 100, chosen["floor_pct"] / 100
    log(
        f"SHIPPING SETTING seed {chosen['seed_pct']:.2f}% floor {chosen['floor_pct']:.2f}%: "
        f"{chosen['real']} components, null 0/0/0, plant FOUND at "
        f"{chosen['plant_median_pct']:+.3f}% (area {chosen['plant_area']})"
    )
    cands = find(D, seed, floor, interior)

    # Location null on each survivor: 400 random footprints of the same shape
    # from the same interior.  A component that is not unusual on this
    # statistic is not a find, however deep it looks.
    out_c = []
    for c in cands[:24]:
        dy, dx = c["ys"] - c["ys"].min(), c["xs"] - c["xs"].min()
        hh, ww = int(dy.max()) + 1, int(dx.max()) + 1
        meds = np.empty(N_LOCATION_NULL)
        for j in range(N_LOCATION_NULL):
            oy = int(rng.integers(BORDER, h - BORDER - hh))
            ox = int(rng.integers(BORDER, w - BORDER - ww))
            meds[j] = np.median(D[oy + dy, ox + dx])
        below = int((meds <= c["median"]).sum())
        sel = (c["ys"], c["xs"])
        out_c.append(
            dict(
                area=c["area"],
                quad=[c["cx"], c["cy"]],
                median_pct=100 * c["median"],
                worst_pct=100 * c["worst"],
                per_subject_pct=[100 * float(np.median(s[sel])) for s in S],
                n_subjects_negative=int(sum(float(np.median(s[sel])) < 0 for s in S)),
                loc_null_median_pct=100 * float(np.median(meds)),
                loc_null_p1_pct=100 * float(np.percentile(meds, 1)),
                p_value=(below + 1) / (N_LOCATION_NULL + 1),
            )
        )
        log(
            f"    area {c['area']:5d} at ({c['cx']:4d},{c['cy']:4d}) median "
            f"{100 * c['median']:+.3f}% worst {100 * c['worst']:+.3f}%  "
            f"{out_c[-1]['n_subjects_negative']:2d}/{k} subjects negative  "
            f"p={out_c[-1]['p_value']:.4f}"
        )

    # Look at the survivors.  128 = zero, +/- 4% full scale.
    for i, c in enumerate(cands[:6]):
        y0, x0 = max(0, c["cy"] - 90), max(0, c["cx"] - 90)
        tile = D[y0 : y0 + 180, x0 : x0 + 180]
        img = np.clip(128 + tile * (127 / 0.04), 0, 255).astype(np.uint8)
        write_png(OUT / f"12-cand-{i}-{c['cx']}-{c['cy']}.png", img)
    log(f"wrote {min(6, len(cands))} candidate PNGs")

    (DATA / "12-photograph-depth.json").write_text(
        json.dumps(
            dict(subjects=used, k=k, sweep=rows, chosen=chosen, candidates=out_c), indent=1
        ),
        encoding="utf-8",
    )
    log("wrote data/12-photograph-depth.json")


if __name__ == "__main__":
    main()

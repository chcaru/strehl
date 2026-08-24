"""M101 script 06 - D1: do the darks' defects appear in the owner's photographs?

bee-3-cpl is ISO 100, 1/5 s. Dark group 118MSDCF is ISO 100, 1/100 s. Same gain,
20x the exposure, so this is the corpus's first exposure lever on the fork
registered in section 1.2:

  H_dark-current : excess is thermally generated charge, ~20x the dark excess
  H_fixed        : excess is a fixed per-site offset,     ~1x

Statistic: per-site median across frames of the same-plane 8-neighbour excess.
The scene translates up to 232.7 px across the stack, so scene structure at a
fixed sensor coordinate decorrelates while a sensor-fixed defect adds coherently.
The median across frames is used rather than the mean because scene texture is
heavy-tailed.

Controls carried beside every number:
  placebo 1  shift control - defect map rolled by an even offset, preserving CFA
             phase and every spatial statistic, destroying correspondence
  placebo 2  uniform random coordinates
  positive   the always-hot sites (11/11) must read higher than the >= 6/11 set

Reads  : D:\\personal\\macro\\... (READ ONLY), defectmap-final.npz
Writes : C:\\dev\\strehl-out\\M101\\06-insitu.json
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import rawpy

OUT = Path(r"C:\dev\strehl-out\M101")
PLANES = ["R", "G1", "G2", "B"]
PLANE_OFF = {"R": (0, 0), "G1": (0, 1), "G2": (1, 0), "B": (1, 1)}
BLACK = 512.0
GAIN_DIVISOR = 436.8
N_FRAMES = 48
SHIFT = (64, 64)   # even in both axes: preserves CFA phase
SEED = 101
B5_BAR = 5.0       # defect excess must exceed shift control by >= 5x


def med8(plane):
    p = np.pad(plane, 1, mode="edge")
    h, w = plane.shape
    st = np.empty((8, h, w), dtype=np.float32)
    i = 0
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            if dy == 1 and dx == 1:
                continue
            st[i] = p[dy:dy + h, dx:dx + w]
            i += 1
    part = np.partition(st, (3, 4), axis=0)
    return 0.5 * (part[3] + part[4])


_SITES = None


def _init(sites):
    global _SITES
    _SITES = sites


def frame_job(path):
    with rawpy.imread(str(path)) as raw:
        v = raw.raw_image_visible.astype(np.float32)  # rule 32
    out = {}
    for pk in PLANES:
        oy, ox = PLANE_OFF[pk]
        pl = v[oy::2, ox::2] - BLACK
        e = pl - med8(pl)
        for grp, (yy, xx) in _SITES[pk].items():
            out[f"{pk}|{grp}|exc"] = e[yy, xx].astype(np.float32)
            out[f"{pk}|{grp}|val"] = pl[yy, xx].astype(np.float32)
    return out


def stats(a, label):
    return {"label": label, "n": int(a.size),
            "mean_dn": round(float(np.mean(a)), 4),
            "median_dn": round(float(np.median(a)), 4),
            "p90_dn": round(float(np.percentile(a, 90)), 4),
            "max_dn": round(float(np.max(a)), 3),
            "sem_dn": round(float(np.std(a) / np.sqrt(a.size)), 5)}


def main():
    stack_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(r"D:\personal\macro\bee-3-cpl")
    files = sorted(stack_dir.glob("*.ARW"))
    assert files, f"no ARW under {stack_dir}"
    idx = np.linspace(0, len(files) - 1, N_FRAMES).astype(int)
    picks = [files[i] for i in idx]
    print(f"{stack_dir.name}: {len(files)} frames, sampling {len(picks)}", flush=True)

    dm = np.load(OUT / "defectmap-final.npz")
    amp = np.load(OUT / "defectmap-amp.npz")
    rng = np.random.default_rng(SEED)

    sites, meta = {}, {}
    for pk in PLANES:
        shape = tuple(dm[f"shape_{pk}"])
        defect = np.unpackbits(dm[f"{pk}-defect"],
                               count=shape[0] * shape[1]).astype(bool).reshape(shape)
        always = np.unpackbits(dm[f"{pk}-always"],
                               count=shape[0] * shape[1]).astype(bool).reshape(shape)
        a_e = amp[f"{pk}-amp_e"]
        yy, xx = np.nonzero(defect)
        ay, ax = np.nonzero(always)
        sy = (yy + SHIFT[0]) % shape[0]
        sx = (xx + SHIFT[1]) % shape[1]
        ry = rng.integers(1, shape[0] - 1, size=yy.size)
        rx = rng.integers(1, shape[1] - 1, size=xx.size)
        g = {"defect": (yy, xx), "shift": (sy, sx), "random": (ry, rx)}
        if ay.size:
            g["always"] = (ay, ax)
        # amplitude strata, in electrons
        for lo, hi in ((1, 2), (2, 4), (4, 8), (8, 1e9)):
            sel = defect & (a_e >= lo) & (a_e < hi)
            if sel.sum() >= 20:
                g[f"amp{lo:g}-{hi:g}" if hi < 1e8 else f"amp{lo:g}+"] = np.nonzero(sel)
        sites[pk] = g
        meta[pk] = {k: int(v[0].size) for k, v in g.items()}
        meta[pk]["dark_amp_e_median_at_defect"] = round(float(np.median(a_e[defect])), 4)
    print("  site counts:", json.dumps(meta), flush=True)

    acc = {}
    with ProcessPoolExecutor(max_workers=8, initializer=_init, initargs=(sites,)) as ex:
        for i, out in enumerate(ex.map(frame_job, picks)):
            for k, v in out.items():
                acc.setdefault(k, []).append(v)
            if (i + 1) % 8 == 0:
                print(f"  {i+1}/{len(picks)}", flush=True)

    res = {"stack": stack_dir.name, "n_frames_total": len(files),
           "n_frames_used": len(picks), "frame_index": idx.tolist(),
           "shift": list(SHIFT), "site_counts": meta, "planes": {}}
    gain100 = 100 / GAIN_DIVISOR
    for pk in PLANES:
        entry = {}
        for grp in sites[pk]:
            exc = np.median(np.stack(acc[f"{pk}|{grp}|exc"]), axis=0)
            val = np.median(np.stack(acc[f"{pk}|{grp}|val"]), axis=0)
            s = stats(exc, grp)
            s["scene_median_dn"] = round(float(np.median(val)), 2)
            s["excess_e"] = round(s["median_dn"] / gain100, 4)
            entry[grp] = s
        d, sh = entry["defect"]["median_dn"], entry["shift"]["median_dn"]
        entry["B5_ratio_defect_over_shift"] = round(d / sh, 3) if sh else None
        entry["B5_pass"] = bool(sh and abs(d / sh) >= B5_BAR)
        entry["insitu_minus_shift_dn"] = round(d - sh, 4)
        entry["insitu_minus_shift_e"] = round((d - sh) / gain100, 4)
        res["planes"][pk] = entry
        print(f"  {pk}: defect={d:+.3f} shift={sh:+.3f} random="
              f"{entry['random']['median_dn']:+.3f} DN  "
              f"net={entry['insitu_minus_shift_e']:+.2f} e-", flush=True)

    with open(OUT / f"06-insitu-{stack_dir.name}.json", "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(f"wrote 06-insitu-{stack_dir.name}.json", flush=True)


if __name__ == "__main__":
    main()

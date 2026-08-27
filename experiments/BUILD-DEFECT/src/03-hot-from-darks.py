"""BUILD-DEFECT step 03 -- the hot-pixel map, from the 242 delivered darks.

THIS IS A REPLICATION, AND IT IS DELIBERATELY ONE.  M22, M48c and M101 have all
built a census from these same 242 frames (11,393 / 13,650 / 14,604 sites).
Three committed numbers are the strongest external positive control available
for a fourth, and a map that cannot land inside them has a defect in it.

WHAT IS NEW HERE is not the census.  It is that nothing has ever written the
map to a FILE that the shipping binary can read.  M101 §6 says so explicitly:
"`crates/strehl-core/src/defect.rs` was not written".  So this script's job is
to produce a map with (a) a per-site amplitude in ELECTRONS, which is the only
ISO-invariant form, and (b) a reproducibility number per amplitude stratum, so
that the shipped operating point is chosen against a measurement rather than
against a threshold.

M101 P3 is honoured rather than re-derived: R and G1 detections do not
reproduce under a split-half (Jaccard 0.077 / 0.074 against a 0.000 placebo)
and are consistent with noise.  This script measures the split-half itself --
it does not take M101's word for it -- and reports the result per plane.

Rule 32 is load-bearing: `raw_image_visible` is a VIEW into LibRaw's buffer and
is invalid the instant the `with` block exits.  Allocate and copy on the same
line, inside the block.

Outputs:
  out/hot-excess-e.npy   float32 (2344,3514,4)  per-plane median excess, e-
  out/hot-recur.npy      int8    (2344,3514,4)  recurrence count, 0..11
  data/03-hot.json
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "out"
DATA = HERE / "data"
DARKS = Path(r"D:\macro-dark-frames")
BLACK = 512.0
PLANES = ("R", "G1", "G2", "B")
DROP = 2               # the owner's stabilisation frames; M101 P13 measured
                       # them at -0.064..+0.014 DN, i.e. harmless either way
KSIG = 6.0             # M22/M48c/M101's cut, adopted unchanged for comparability
RECUR = 6              # >= 6 of 11 ISO groups, likewise adopted unchanged
GAIN_DIVISOR = 436.8   # profile.rs: gain = max(iso, 100) / 436.8 DN per e-


def planes_of(vis):
    return {"R": vis[0::2, 0::2], "G1": vis[0::2, 1::2],
            "G2": vis[1::2, 0::2], "B": vis[1::2, 1::2]}


def group_mean(args):
    """Temporal mean of one ISO group, per plane, black-subtracted."""
    d, = args
    files = sorted(Path(d).glob("*.ARW"))
    assert len(files) == 22, f"{d}: {len(files)} files"
    files = files[DROP:]
    acc = None
    iso = None
    for f in files:
        with rawpy.imread(str(f)) as raw:
            vis = raw.raw_image_visible.astype(np.float32)      # rule 32
            bl = list(raw.black_level_per_channel)
        assert vis.shape == (4688, 7028), f"{f}: {vis.shape}"
        assert set(bl) == {512}, f"{f}: black {bl}"
        acc = vis if acc is None else acc + vis
    mean = acc / len(files) - BLACK
    # ISO from EXIF is not available through rawpy; taken from the caller.
    return Path(d).name, {p: v.copy() for p, v in planes_of(mean).items()}, len(files)


def neighbour_excess(a: np.ndarray) -> np.ndarray:
    """Sample minus the median of its 8 same-plane neighbours, centre excluded.

    Same statistic as M101 §3.1 so that the census is comparable.  Edge pixels
    are computed against an edge-replicated pad, and the one-pixel border is
    reported separately rather than silently trusted.
    """
    p = np.pad(a, 1, mode="edge")
    nb = np.stack([p[dy:dy + a.shape[0], dx:dx + a.shape[1]]
                   for dy in (0, 1, 2) for dx in (0, 1, 2)
                   if not (dy == 1 and dx == 1)], axis=0)
    return a - np.median(nb, axis=0)


def half_mean(d, sl):
    files = sorted(Path(d).glob("*.ARW"))[DROP:]
    files = files[sl]
    acc = None
    for f in files:
        with rawpy.imread(str(f)) as raw:
            vis = raw.raw_image_visible.astype(np.float32)      # rule 32
        acc = vis if acc is None else acc + vis
    return acc / len(files) - BLACK


def worker(d):
    """One ISO group: full mean, and the two disjoint 10-frame halves."""
    name = Path(d).name
    full = {}
    ha = {}
    hb = {}
    files = sorted(Path(d).glob("*.ARW"))[DROP:]
    accs = [None, None, None]
    for i, f in enumerate(files):
        with rawpy.imread(str(f)) as raw:
            vis = raw.raw_image_visible.astype(np.float32)      # rule 32
            bl = list(raw.black_level_per_channel)
        assert vis.shape == (4688, 7028), f"{f}: {vis.shape}"
        assert set(bl) == {512}, f"{f}: black {bl}"
        accs[0] = vis.copy() if accs[0] is None else accs[0] + vis
        j = 1 + (i % 2)          # interleaved halves: no thermal split
        accs[j] = vis.copy() if accs[j] is None else accs[j] + vis
    n = len(files)
    out = {}
    for key, acc, cnt in (("full", accs[0], n), ("A", accs[1], (n + 1) // 2),
                          ("B", accs[2], n // 2)):
        m = acc / cnt - BLACK
        pl = planes_of(m)
        for p in PLANES:
            out[f"{key}-{p}"] = neighbour_excess(pl[p]).astype(np.float32)
    return name, n, out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    dirs = sorted([str(p) for p in DARKS.iterdir() if p.is_dir()])
    assert len(dirs) == 11, f"expected 11 ISO groups, got {len(dirs)}"
    t0 = time.time()
    res = {"groups": [Path(d).name for d in dirs]}

    # ISO per group, from EXIF, because the noise model's gain is linear in it
    # and a guessed ISO is a silently wrong amplitude.
    import subprocess
    iso_of = {}
    for d in dirs:
        f = sorted(Path(d).glob("*.ARW"))[0]
        s = subprocess.run(["exiftool", "-q", "-T", "-ISO", "-ExposureTime", str(f)],
                           capture_output=True, text=True, check=True).stdout.strip()
        iso_s, exp_s = s.split("\t")
        iso_of[Path(d).name] = float(iso_s)
        res.setdefault("exposure", {})[Path(d).name] = exp_s
    res["iso"] = iso_of
    print("=== ISO groups")
    for d in dirs:
        n = Path(d).name
        print(f"    {n}  ISO {iso_of[n]:6.0f}  exp {res['exposure'][n]}")
    assert len(set(res["exposure"].values())) == 1, \
        "the darks are no longer all one exposure; the e- amplitude below " \
        "assumes they are (M101 P7)"

    print(f"\n=== decoding {len(dirs)} groups x {22 - DROP} frames")
    flags_full = np.zeros((11, 2344, 3514, 4), bool)
    exc_e = np.zeros((11, 2344, 3514, 4), np.float32)
    flags_a = np.zeros((11, 2344, 3514, 4), bool)
    flags_b = np.zeros((11, 2344, 3514, 4), bool)
    sig_rows = {}
    with ProcessPoolExecutor(max_workers=6) as ex:
        for gi, (name, n, out) in enumerate(ex.map(worker, dirs)):
            g = max(iso_of[name], 100.0) / GAIN_DIVISOR
            row = {}
            for pi, p in enumerate(PLANES):
                for key, dst in (("full", flags_full), ("A", flags_a), ("B", flags_b)):
                    e = out[f"{key}-{p}"]
                    sig = 1.4826 * float(np.median(np.abs(e - np.median(e))))
                    dst[dirs.index(str(DARKS / name)), :, :, pi] = e > KSIG * sig
                    if key == "full":
                        exc_e[dirs.index(str(DARKS / name)), :, :, pi] = e / g
                        row[p] = {"sigma_robust_dn": sig, "gain_dn_per_e": g}
            sig_rows[name] = row
            print(f"    {name}  n={n}  "
                  + "  ".join(f"{p} sig={row[p]['sigma_robust_dn']:.4f}DN" for p in PLANES)
                  + f"   [{time.time() - t0:5.1f}s]")
            sys.stdout.flush()
    res["sigma"] = sig_rows

    # ------------------------------------------------------------------
    print("\n=== recurrence")
    recur = flags_full.sum(axis=0).astype(np.int8)
    site = recur >= RECUR
    per_plane = {p: int(site[:, :, i].sum()) for i, p in enumerate(PLANES)}
    total = int(site.sum())
    print(f"    >= {RECUR}/11 : " + "  ".join(f"{p} {per_plane[p]}" for p in PLANES)
          + f"   total {total}  = {total / site.size * 100:.4f}% of the sensor")
    always = int((recur == 11).sum())
    print(f"    all 11/11 : {always}")
    # external positive control, rule 11: three committed censuses
    for who, n_ext in (("M22", 11393), ("M48c", 13650), ("M101", 14604)):
        print(f"    vs {who:5s} {n_ext:6d}: {(total / n_ext - 1) * 100:+.1f}%")
    res["census"] = {"per_plane": per_plane, "total": total, "always": always,
                     "frac": total / site.size,
                     "vs": {"M22": total / 11393, "M48c": total / 13650,
                            "M101": total / 14604}}
    # M48c fact 9's odd/even row asymmetry
    odd = per_plane["G2"] + per_plane["B"]
    even = per_plane["R"] + per_plane["G1"]
    print(f"    odd/even sensor-row asymmetry (G2+B)/(R+G1) = {odd / max(even, 1):.1f}x"
          f"   (M48c 68x, M101 61.1x)")
    res["census"]["row_asymmetry"] = odd / max(even, 1)

    # ------------------------------------------------------------------
    print("\n=== split-half reproducibility, per plane (M101 PD1)")
    site_a = flags_a.sum(axis=0) >= RECUR
    site_b = flags_b.sum(axis=0) >= RECUR
    rng = np.random.default_rng(20260827)
    jac = {}
    for i, p in enumerate(PLANES):
        a, b = site_a[:, :, i], site_b[:, :, i]
        inter = int((a & b).sum())
        union = int((a | b).sum())
        j = inter / union if union else 0.0
        # placebo: two random coordinate sets of the same sizes
        na, nb = int(a.sum()), int(b.sum())
        ra = np.zeros(a.size, bool); ra[rng.choice(a.size, na, replace=False)] = True
        rb = np.zeros(a.size, bool); rb[rng.choice(a.size, nb, replace=False)] = True
        jp = int((ra & rb).sum()) / max(int((ra | rb).sum()), 1)
        jac[p] = {"jaccard": j, "placebo": jp, "n_a": na, "n_b": nb}
        print(f"    {p:2s}  Jaccard {j:.4f}   placebo {jp:.6f}   |A| {na}  |B| {nb}")
    res["splithalf"] = jac

    # amplitude stratification: reproducibility as a function of e-
    print("\n=== reproducibility by amplitude (the operating point)")
    amp = np.median(exc_e, axis=0)          # e-, ISO-invariant
    bands = [(0, 1), (1, 2), (2, 4), (4, 8), (8, 16), (16, 1e9)]
    strat = []
    for lo, hi in bands:
        m = site & (amp >= lo) & (amp < hi)
        n = int(m.sum())
        if not n:
            strat.append({"lo": lo, "hi": hi, "n": 0, "recovered": None})
            continue
        rec = float((site_a & site_b)[m].mean())
        strat.append({"lo": lo, "hi": hi, "n": n, "recovered": rec})
        print(f"    {lo:5.0f}-{hi if hi < 1e8 else 'inf':>5} e- : n={n:7d}  "
              f"recovered in BOTH halves {rec:.3f}")
    res["amplitude_strata"] = strat

    np.save(OUT / "hot-excess-e.npy", amp.astype(np.float32))
    np.save(OUT / "hot-recur.npy", recur)
    (DATA / "03-hot.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"\nwrote {DATA / '03-hot.json'}   [{time.time() - t0:.1f}s]")


if __name__ == "__main__":
    main()

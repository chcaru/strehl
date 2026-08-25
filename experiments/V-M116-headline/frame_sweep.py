"""V-M116 probe 3: THE decisive test of "the sharpest single source frame".

M116 defined "sharpest" as the frame that wins the most pixels in A0's election
map -- a plurality of an ALIGNED arm's index map, applied to an UNALIGNED
comparison. That is a frame choice made by the pipeline under test, and it is
not a sharpness statistic.

This script removes the question entirely: it renders EVERY one of the 100
source frames alone, through the exact B0 recipe (--limit 1 --gate 4,
STREHL_ALIGN=0, pinned binary), and scores each with the same masks M116 used.
The merge is then compared against the MAXIMUM over all 100 frames, not against
one frame chosen by the merge.

Writes only under C:\\dev\\strehl-out\\V-M116\\. D:\\ is read only.
"""
import csv, json, os, shutil, subprocess, sys, time
from pathlib import Path
import numpy as np
import tifffile

EXE = Path(r"C:\dev\strehl-out\M116-tree\target\release\strehl.exe")
LIB = Path(r"D:\personal\macro")
M116 = Path(r"C:\dev\strehl-out\M116\measure")
OUT = Path(r"C:\dev\strehl-out\V-M116")
SCRATCH = OUT / "scratch"
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]
LIMIT = 100


def load_green(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} loaded as {a.dtype}, NOT uint16"
    return a[:, :, 1].astype(np.float64)


def box(a, k):
    h = k // 2
    pad = np.pad(a, ((h, k - 1 - h), (h, k - 1 - h)), mode="edge")
    c = np.pad(pad.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    return (c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)


def structure(g):
    hh, ww = g.shape[0] // 4, g.shape[1] // 4
    small = g[:hh * 4, :ww * 4].reshape(hh, 4, ww, 4).mean(axis=(1, 3))
    m1, m2 = box(small, 33), box(small * small, 33)
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    up = np.repeat(np.repeat(sd, 4, 0), 4, 1)
    out = np.zeros(g.shape, np.float64)
    out[:up.shape[0], :up.shape[1]] = up[:g.shape[0], :g.shape[1]]
    if up.shape[0] < g.shape[0]: out[up.shape[0]:, :] = out[up.shape[0] - 1, :]
    if up.shape[1] < g.shape[1]: out[:, up.shape[1]:] = out[:, up.shape[1] - 1][:, None]
    return out


def render_single(arw: Path, dst: Path) -> float:
    one = SCRATCH / "one"
    if one.exists(): shutil.rmtree(one)
    one.mkdir(parents=True)
    shutil.copy2(arw, one / arw.name)
    env = dict(os.environ)
    for v in ("STREHL_WARPMAP", "STREHL_PHOTOMETRIC", "STREHL_SOFT_GATE",
              "STREHL_FIX_CA", "STREHL_FIX_HALO", "STREHL_SMOOTH",
              "STREHL_DUMP_NEFF", "STREHL_CACHE_DIR", "STREHL_CAPTURES"):
        env.pop(v, None)
    env["STREHL_ALIGN"] = "0"
    t = time.time()
    r = subprocess.run([str(EXE), "stack", str(one), "--limit", "1", "--gate", "4",
                        "--out", str(dst)], env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"render failed {arw}: {r.returncode}\n{r.stdout[-2000:]}")
    shutil.rmtree(one, ignore_errors=True)
    return time.time() - t


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    rows = []
    for s in SUBJECTS:
        st = structure(load_green(M116 / f"{s}__M0u.tif"))
        mflat = st <= np.quantile(st, 0.20)
        mdet = st >= np.quantile(st, 0.80)
        frames = sorted((LIB / s).glob("*.ARW"))[:LIMIT]
        assert len(frames) == LIMIT, f"{s}: {len(frames)} frames"
        tmp = SCRATCH / f"{s}-frame.tif"
        for k, f in enumerate(frames):
            dt = render_single(f, tmp)
            g = load_green(tmp)
            h = g - box(g, 5)
            sf, sd_ = float(h[mflat].std()), float(h[mdet].std())
            rows.append(dict(subject=s, k=k, file=f.name,
                             sd_flat=sf, sd_det=sd_,
                             N=float(np.log10(sf)), D=float(np.log10(sd_)),
                             Q=float(np.log10(sd_) - np.log10(sf)),
                             mean=float(g.mean()), secs=round(dt, 2)))
            print(f"{s:14s} k={k:3d} {f.name:14s} D={np.log10(sd_):+.5f} "
                  f"N={np.log10(sf):+.5f} Q={np.log10(sd_)-np.log10(sf):+.5f} ({dt:.1f}s)",
                  flush=True)
        tmp.unlink(missing_ok=True)
    with open(OUT / "frame_sweep.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"wrote {OUT/'frame_sweep.csv'}  ({len(rows)} rows)")


main()

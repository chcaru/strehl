"""Corpus-wide softness verdict: is the master sharper than its per-site best frame?

Two subjects settled the question; 26 decide whether it is a corpus result and
whether the advantage tracks the merge regime. The estimation thesis predicts
the gain is LARGEST where the merge averages many frames into each coefficient
and SMALLEST where it degenerates to picking one, because a selector is bounded
above by the frame it picked and an estimator is not. Two points are a line
through anything. This measures all of them.

WHAT IS REUSED AND WHAT IS NOT. Every primitive -- the detail statistic, the
noise-floor subtraction, the per-site envelope, the registration -- is imported
from softness_verdict3.py rather than reimplemented, so the corpus run cannot
silently drift from the instrument that was commissioned by eye on two subjects.
The seven commissioning arms are re-run ON EACH SUBJECT rather than carried over,
because a commissioning is a statement about a data set and not a property of
the code: an arm that passes on a flower bud says nothing about a ruler.

REFUSALS ARE NOT PASSES. Every subject lands in exactly one of four states and
the four sum to the corpus. A subject outside the instrument's regime is refused
with a named reason and reported as a refusal, never omitted and never averaged
in. The partition is printed with the result so a refusal cannot be read as a
win. Refusal reasons, all of them regime statements about this instrument:

  too-few-frames  fewer than 8 frames cannot form a per-site envelope worth the
                  name; the max over a handful of frames is a weak ceiling and a
                  weak ceiling flatters the master.
  parity-failed   the two arms are not on a common linear scale, so a ratio of
                  their detail energies is not a ratio of their sharpness.
  too-few-sites   fewer than 30 live blocks leaves the median and its bootstrap
                  CI dominated by which blocks happened to clear the floor.
  arm-failed      any of the seven commissioning arms failed on this subject's
                  data. An instrument that fails an arm reports nothing.
  render-failed   strehl returned nonzero or produced no file.

TILE SELECTION IS AUTOMATIC AND STATED. Hand-picking a tile per subject is how a
corpus result gets quietly tuned. The tile is the window of size TILE maximising
summed low-frequency contrast in the master, which puts it where there is
structure to measure without any knowledge of where the master happens to do
well. The chosen origin is recorded per subject so any row can be re-cut.

Usage:
  python corpus_softness.py --out rows.tsv                # whole corpus
  python corpus_softness.py --only lead-1-cpl --tile 2600,1400 --size 2048
  python corpus_softness.py --only flower-bud-alone-cpl --frames 14 --stride 16
"""

import argparse
import pathlib
import shutil
import subprocess
import sys
import time

import numpy as np
import tifffile
import cv2

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from softness_verdict3 import (  # noqa: E402
    luma_linear, detail, contrast, shift_of, warp, build_envelope, boot_ci,
)

EXE = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
SRC = pathlib.Path(r"D:\personal\macro")
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\V-EYES\corpus")

TILE = 2048
BLOCK = 64
MIN_FRAMES = 8
MIN_SITES = 30
TARGET_FRAMES = 13

COLS = ["subject", "state", "reason", "n_frames", "n_sampled", "stride",
        "tile_x", "tile_y", "size", "n_sites", "ratio", "ci_lo", "ci_hi",
        "softer_pct", "avg_index", "avg_bands", "parity", "arms", "secs"]


def luma32(a):
    """Deliberately the instrument's own float64 luma, not a cheaper float32 one.

    A float32 path was tried first and reproduced the validated `lead-1-cpl`
    result as 1.5186 against 1.5357, a 1.1% drift, and moved the live-site count
    by one block because the 65th-percentile contrast floor landed either side of
    a block. That is small and it is also unnecessary doubt: a corpus driver that
    cannot exactly reproduce the number it is scaling up has to defend two
    discrepancies at once. Precision is cheaper than that argument.
    """
    return luma_linear(a)


def render(args, log=None):
    r = subprocess.run([EXE] + args, capture_output=True, text=True)
    if log is not None:
        log.write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
    return r.returncode


def parse_avg(text):
    """The merge's averaged-vs-selected split, coarsest band first, base last."""
    for line in text.splitlines():
        if line.strip().startswith("averaged"):
            vals = [float(v.rstrip("%")) for v in line.split(":")[1].split()]
            return vals
    return []


def pick_tile(mfull, size):
    """Window of `size` maximising summed low-frequency contrast in the master."""
    c = contrast(mfull, BLOCK)
    k = size // BLOCK
    integ = cv2.boxFilter(c.astype(np.float32), -1, (k, k), normalize=False)
    h, w = c.shape
    half = k // 2
    valid = integ[half:h - k + half + 1, half:w - k + half + 1]
    if valid.size == 0:
        return 0, 0
    by, bx = np.unravel_index(int(np.argmax(valid)), valid.shape)
    return int(bx * BLOCK), int(by * BLOCK)


def arms_pass(master, tiles, floors, env, md, live, base, cfloor):
    """All seven arms, re-run on THIS subject's data. Subject side and reference
    side, because a suite that only perturbs the subject cannot see a broken
    reference -- which is exactly how instrument v2 shipped an inverted envelope
    past five passing arms."""
    def med(sub, e=env):
        return float(np.median((sub / np.maximum(e, 1e-12))[live]))

    d = cv2.GaussianBlur(master.astype(np.float32), (0, 0), 1.2)
    u = np.clip(master + 1.0 * (master - d), 0, None)
    noisy = master + np.random.default_rng(3).normal(
        0, float(np.sqrt(max(np.median(floors), 0))) * 2.0, master.shape)
    eb, _, _ = build_envelope(
        [cv2.GaussianBlur(t.astype(np.float32), (0, 0), 1.2) for t in tiles],
        BLOCK, cfloor)
    es, _, _ = build_envelope(
        [np.clip(t + 1.0 * (t - cv2.GaussianBlur(t.astype(np.float32), (0, 0), 1.2)),
                 0, None) for t in tiles], BLOCK, cfloor)

    checks = [
        ("NULL", med(md, md), lambda v: abs(v - 1) < 1e-6),
        ("DEFECT", med(detail(d, BLOCK)[0]), lambda v: v < base),
        ("IMPROVE", med(detail(u, BLOCK)[0]), lambda v: v > base),
        ("NOISE", med(detail(noisy, BLOCK)[0]), lambda v: v <= base * 1.10),
        ("CEILING", med(env), lambda v: v >= 0.999),
        ("REF-BLUR", med(md, eb), lambda v: v > base),
        ("REF-SHARP", med(md, es), lambda v: v < base),
    ]
    failed = [n for n, v, ok in checks if not ok(v)]
    return failed, {n: v for n, v, _ in checks}


def measure(subject, size, tile, want_frames, stride_override, keep):
    t0 = time.time()
    row = {c: "" for c in COLS}
    row["subject"] = subject
    src = SRC / subject
    frames = sorted(src.glob("*.ARW"))
    row["n_frames"] = len(frames)

    if len(frames) < MIN_FRAMES:
        row.update(state="refused", reason="too-few-frames",
                   secs=round(time.time() - t0, 1))
        return row

    out = SCRATCH / subject
    out.mkdir(parents=True, exist_ok=True)
    mtif = out / "MASTER.tiff"
    mlog = out / "MASTER.log"

    if not mtif.exists():
        if render(["stack", str(src), "--out", str(mtif),
                   "--linear-srgb", "--demosaic"], mlog) != 0 or not mtif.exists():
            row.update(state="failed", reason="render-failed",
                       secs=round(time.time() - t0, 1))
            return row

    bands = parse_avg(mlog.read_text(encoding="utf-8", errors="replace"))
    body = bands[:-1] if len(bands) > 1 else bands
    row["avg_bands"] = "/".join(f"{v:.1f}" for v in body)
    row["avg_index"] = round(float(np.mean(body)), 2) if body else ""

    if stride_override:
        # Preserved so the validated two-subject runs can be reproduced exactly.
        stride = stride_override
        picks = frames[::stride][:max(want_frames, MIN_FRAMES)]
    else:
        # Span the WHOLE bracket. The obvious `frames[::N//want][:want]` truncates
        # the focus range whenever N is close to want: at N=22, want=13 it takes
        # frames 0..12 and the deepest nine focus positions never enter the
        # reference at all, so the ceiling is missing the very frames that are
        # sharp over part of the subject's depth. linspace keeps the endpoints and
        # spreads the rest, so the sampled bracket always covers the sweep and the
        # only thing that varies with n is DENSITY, which is the quantity
        # density_check.py bounds. Mixing a range bias into a density bias would
        # make neither recoverable.
        n = min(max(want_frames, MIN_FRAMES), len(frames))
        idx = sorted(set(int(round(v)) for v in np.linspace(0, len(frames) - 1, n)))
        picks = [frames[i] for i in idx]
        stride = round((len(frames) - 1) / max(n - 1, 1), 2)
    row["stride"] = stride
    row["n_sampled"] = len(picks)

    ftifs = []
    for f in picks:
        ft = out / f"frame-{f.stem}.tiff"
        if not ft.exists():
            d = out / "one"
            if d.exists():
                shutil.rmtree(d)
            d.mkdir(parents=True)
            shutil.copy2(f, d / f.name)
            rc = render(["stack", str(d), "--out", str(ft),
                         "--linear-srgb", "--demosaic"])
            shutil.rmtree(d, ignore_errors=True)
            if rc != 0 or not ft.exists():
                continue
        ftifs.append(ft)

    if len(ftifs) < MIN_FRAMES:
        row.update(state="failed", reason="render-failed",
                   n_sampled=len(ftifs), secs=round(time.time() - t0, 1))
        return row

    mfull = luma32(tifffile.imread(str(mtif)))
    if tile:
        tx, ty = tile
    else:
        tx, ty = pick_tile(mfull, size)
    tx = int(np.clip(tx, 0, mfull.shape[1] - size))
    ty = int(np.clip(ty, 0, mfull.shape[0] - size))
    row.update(tile_x=tx, tile_y=ty, size=size)
    master = mfull[ty:ty + size, tx:tx + size].copy()
    del mfull

    tiles, floors = [], []
    for ft in ftifs:
        t = luma32(tifffile.imread(str(ft)))[
            ty:ty + size, tx:tx + size].copy()
        dx, dy = shift_of(master, t)
        t = warp(t, dx, dy)
        tiles.append(t)
        floors.append(detail(t, BLOCK)[1])

    mm = float(np.mean(master))
    fm = float(np.mean([np.mean(t) for t in tiles]))
    row["parity"] = round(mm / max(fm, 1e-9), 4)
    if abs(mm / max(fm, 1e-9) - 1.0) > 0.25:
        row.update(state="refused", reason="parity-failed",
                   secs=round(time.time() - t0, 1))
        if not keep:
            shutil.rmtree(out, ignore_errors=True)
        return row

    cm = contrast(master, BLOCK)
    cfloor = float(np.percentile(cm, 65))
    env, _, valid = build_envelope(tiles, BLOCK, cfloor)
    live = (cm > cfloor) & valid
    md, _ = detail(master, BLOCK)
    row["n_sites"] = int(live.sum())

    if live.sum() < MIN_SITES:
        row.update(state="refused", reason="too-few-sites",
                   secs=round(time.time() - t0, 1))
        if not keep:
            shutil.rmtree(out, ignore_errors=True)
        return row

    vals = (md / np.maximum(env, 1e-12))[live]
    base = float(np.median(vals))
    failed, arm_vals = arms_pass(master, tiles, floors, env, md, live, base, cfloor)
    row["arms"] = "all-pass" if not failed else "FAIL:" + ",".join(failed)

    if failed:
        row.update(state="refused", reason="arm-failed",
                   secs=round(time.time() - t0, 1))
        if not keep:
            shutil.rmtree(out, ignore_errors=True)
        return row

    lo, hi = boot_ci(vals)
    row.update(state="measured", ratio=round(base, 4), ci_lo=round(lo, 4),
               ci_hi=round(hi, 4),
               softer_pct=round(100 * float((vals < 1).mean()), 1),
               secs=round(time.time() - t0, 1))
    if not keep:
        shutil.rmtree(out, ignore_errors=True)
    return row


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(SCRATCH / "rows.tsv"))
    p.add_argument("--only", action="append")
    p.add_argument("--tile")
    p.add_argument("--size", type=int, default=TILE)
    p.add_argument("--frames", type=int, default=TARGET_FRAMES)
    p.add_argument("--stride", type=int)
    p.add_argument("--keep", action="store_true")
    a = p.parse_args()

    tile = tuple(int(v) for v in a.tile.split(",")) if a.tile else None
    outp = pathlib.Path(a.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if outp.exists():
        for ln in outp.read_text(encoding="utf-8").splitlines()[1:]:
            if ln.strip():
                done.add(ln.split("\t")[0])
    else:
        outp.write_text("\t".join(COLS) + "\n", encoding="utf-8")

    subjects = a.only or sorted(
        d.name for d in SRC.iterdir()
        if d.is_dir() and any(d.glob("*.ARW")))

    for s in subjects:
        if s in done and not a.only:
            print(f"{s:<38} already done, skipping", flush=True)
            continue
        try:
            row = measure(s, a.size, tile, a.frames, a.stride, a.keep)
        except Exception as e:  # noqa: BLE001
            row = {c: "" for c in COLS}
            row.update(subject=s, state="failed", reason=f"exception:{type(e).__name__}")
            print(f"  {s}: {e}", flush=True)
        with outp.open("a", encoding="utf-8") as fh:
            fh.write("\t".join(str(row[c]) for c in COLS) + "\n")
        print(f"{row['subject']:<38} {row['state']:<9} "
              f"{row['reason'] or 'ratio ' + str(row['ratio']):<16} "
              f"sites={row['n_sites']} avg={row['avg_index']} "
              f"{row['secs']}s", flush=True)


if __name__ == "__main__":
    main()

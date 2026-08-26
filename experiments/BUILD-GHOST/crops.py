"""BUILD-GHOST Part 3 -- motion-sited 1:1 crops of the delivered masters.

WHY NOT printqa.py
------------------
experiments/ORCH-drift-check/printqa.py sites its panels by GRADIENT percentile:
it finds the most detailed, most transitional and flattest places in a frame.
That is the right tool for judging sharpening and halos and the wrong one for
judging ghosts, because a ghost is not where the gradient is extreme, it is
where the SUBJECT MOVED.  This tool sites its crops at the coordinates Part 1's
residual field nominated, which is the only reason the crops are worth looking
at.  (printqa.py belongs to BUILD-TRIAGE for the duration; it is read, never
edited, and never imported.)

RULES OBSERVED
--------------
* No resampling, ever.  A 1:1 crop or nothing -- a ghost that survives a
  downscale is a bad ghost, and a downscale can also manufacture one.
* The masters are sRGB-toned (ImageDescription records black 0.020125,
  white 0.999720).  Nothing here derives a comparative NUMBER from them; they
  are opened to be LOOKED AT.  The 16->8 bit conversion below is for display
  only and is applied identically to every panel of every sheet.
* Each sheet carries a CONTROL panel from a quiet part of the SAME master, so
  the eye is comparing like with like inside one tone treatment.

USAGE
    python experiments/BUILD-GHOST/crops.py --top 8
    python experiments/BUILD-GHOST/crops.py --subject bee-3-cpl --subject foam
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghostlib as G

SHIP = r"C:\dev\strehl-out\SHIP-V1"
OUT = r"C:\dev\strehl-out\BUILD-GHOST"
CROP = 512          # sensor px, i.e. master px, i.e. 1:1
GAP = 12
LABEL_H = 22


def sha256_head(path: str, nbytes: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read(nbytes))
    return h.hexdigest()[:16]


def load_master(subject: str) -> tuple[np.ndarray, dict]:
    p = os.path.join(SHIP, subject + ".tiff")       # .tiff, NOT .tif
    with tifffile.TiffFile(p) as tf:
        a = tf.asarray()
        desc = tf.pages[0].tags.get("ImageDescription")
        desc = desc.value if desc is not None else ""
    assert a.dtype == np.uint16, f"{p} is {a.dtype}, expected uint16"
    return a, {"path": p, "shape": list(a.shape), "dtype": str(a.dtype),
               "sha256_first_1MiB": sha256_head(p), "description": desc}


def to8(a16: np.ndarray) -> np.ndarray:
    """Display conversion only.  Identical for every panel, so nothing is
    stretched into or out of visibility relative to anything else."""
    return (a16 >> 8).astype(np.uint8)


def crop_at(master: np.ndarray, cy: int, cx: int, size: int = CROP) -> tuple[np.ndarray, int, int]:
    h, w = master.shape[:2]
    y = int(np.clip(cy - size // 2, 0, max(h - size, 0)))
    x = int(np.clip(cx - size // 2, 0, max(w - size, 0)))
    return master[y:y + size, x:x + size], y, x


def draw_text(img: np.ndarray, x: int, y: int, text: str) -> None:
    """5x7 bitmap glyphs, drawn at 2x.  A dependency-free label so a crop sheet
    can never be mistaken for a different crop sheet."""
    F = _FONT
    for ch in text.upper():
        g = F.get(ch, F["?"])
        for r in range(7):
            for c in range(5):
                if g[r] & (1 << (4 - c)):
                    img[y + 2 * r:y + 2 * r + 2, x + 2 * c:x + 2 * c + 2] = 255
        x += 12
        if x > img.shape[1] - 14:
            return


_FONT = {
    " ": [0, 0, 0, 0, 0, 0, 0], "?": [0x0E, 0x11, 0x01, 0x06, 0x04, 0, 0x04],
    "0": [0x0E, 0x11, 0x13, 0x15, 0x19, 0x11, 0x0E], "1": [0x04, 0x0C, 0x04, 0x04, 0x04, 0x04, 0x0E],
    "2": [0x0E, 0x11, 0x01, 0x02, 0x04, 0x08, 0x1F], "3": [0x1F, 0x02, 0x04, 0x02, 0x01, 0x11, 0x0E],
    "4": [0x02, 0x06, 0x0A, 0x12, 0x1F, 0x02, 0x02], "5": [0x1F, 0x10, 0x1E, 0x01, 0x01, 0x11, 0x0E],
    "6": [0x06, 0x08, 0x10, 0x1E, 0x11, 0x11, 0x0E], "7": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x08, 0x08],
    "8": [0x0E, 0x11, 0x11, 0x0E, 0x11, 0x11, 0x0E], "9": [0x0E, 0x11, 0x11, 0x0F, 0x01, 0x02, 0x0C],
    "A": [0x0E, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11], "B": [0x1E, 0x11, 0x11, 0x1E, 0x11, 0x11, 0x1E],
    "C": [0x0E, 0x11, 0x10, 0x10, 0x10, 0x11, 0x0E], "D": [0x1C, 0x12, 0x11, 0x11, 0x11, 0x12, 0x1C],
    "E": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x1F], "F": [0x1F, 0x10, 0x10, 0x1E, 0x10, 0x10, 0x10],
    "G": [0x0E, 0x11, 0x10, 0x17, 0x11, 0x11, 0x0F], "H": [0x11, 0x11, 0x11, 0x1F, 0x11, 0x11, 0x11],
    "I": [0x0E, 0x04, 0x04, 0x04, 0x04, 0x04, 0x0E], "J": [0x07, 0x02, 0x02, 0x02, 0x02, 0x12, 0x0C],
    "K": [0x11, 0x12, 0x14, 0x18, 0x14, 0x12, 0x11], "L": [0x10, 0x10, 0x10, 0x10, 0x10, 0x10, 0x1F],
    "M": [0x11, 0x1B, 0x15, 0x15, 0x11, 0x11, 0x11], "N": [0x11, 0x19, 0x15, 0x13, 0x11, 0x11, 0x11],
    "O": [0x0E, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E], "P": [0x1E, 0x11, 0x11, 0x1E, 0x10, 0x10, 0x10],
    "Q": [0x0E, 0x11, 0x11, 0x11, 0x15, 0x12, 0x0D], "R": [0x1E, 0x11, 0x11, 0x1E, 0x14, 0x12, 0x11],
    "S": [0x0F, 0x10, 0x10, 0x0E, 0x01, 0x01, 0x1E], "T": [0x1F, 0x04, 0x04, 0x04, 0x04, 0x04, 0x04],
    "U": [0x11, 0x11, 0x11, 0x11, 0x11, 0x11, 0x0E], "V": [0x11, 0x11, 0x11, 0x11, 0x11, 0x0A, 0x04],
    "W": [0x11, 0x11, 0x11, 0x15, 0x15, 0x15, 0x0A], "X": [0x11, 0x11, 0x0A, 0x04, 0x0A, 0x11, 0x11],
    "Y": [0x11, 0x11, 0x0A, 0x04, 0x04, 0x04, 0x04], "Z": [0x1F, 0x01, 0x02, 0x04, 0x08, 0x10, 0x1F],
    "-": [0, 0, 0, 0x1F, 0, 0, 0], ".": [0, 0, 0, 0, 0, 0x0C, 0x0C], ":": [0, 0x0C, 0x0C, 0, 0x0C, 0x0C, 0],
    "/": [0x01, 0x02, 0x02, 0x04, 0x08, 0x08, 0x10], "+": [0, 0x04, 0x04, 0x1F, 0x04, 0x04, 0],
    "(": [0x02, 0x04, 0x08, 0x08, 0x08, 0x04, 0x02], ")": [0x08, 0x04, 0x02, 0x02, 0x02, 0x04, 0x08],
    "=": [0, 0, 0x1F, 0, 0x1F, 0, 0], "_": [0, 0, 0, 0, 0, 0, 0x1F], "#": [0x0A, 0x1F, 0x0A, 0x0A, 0x1F, 0x0A, 0],
    "%": [0x18, 0x19, 0x02, 0x04, 0x08, 0x13, 0x03], "@": [0x0E, 0x11, 0x17, 0x15, 0x17, 0x10, 0x0E],
    ",": [0, 0, 0, 0, 0x0C, 0x04, 0x08], "'": [0x0C, 0x04, 0x08, 0, 0, 0, 0],
}


def sheet(panels: list[tuple[np.ndarray, str]], title: str) -> np.ndarray:
    n = len(panels)
    cols = min(n, 3)
    rows = (n + cols - 1) // cols
    ph = CROP + LABEL_H
    H = LABEL_H + rows * (ph + GAP) + GAP
    W = cols * (CROP + GAP) + GAP
    out = np.zeros((H, W, 3), np.uint8)
    draw_text(out, GAP, 4, title[:W // 12])
    for i, (img, lab) in enumerate(panels):
        r, c = divmod(i, cols)
        y = LABEL_H + GAP + r * (ph + GAP)
        x = GAP + c * (CROP + GAP)
        draw_text(out, x, y + 4, lab[:40])
        h, w = img.shape[:2]
        out[y + LABEL_H:y + LABEL_H + h, x:x + w] = img
    return out


def quiet_site(master: np.ndarray) -> tuple[int, int]:
    """A textured but motion-free control site from the same master: the tile
    with median gradient energy among a coarse scan, away from the border.  A
    control panel with no detail in it could not express a ghost and would not
    be a control."""
    h, w = master.shape[:2]
    step = 512
    ys = np.arange(step, h - step, step)
    xs = np.arange(step, w - step, step)
    best = []
    for y in ys[::2]:
        for x in xs[::2]:
            t = master[y:y + 128, x:x + 128, 1].astype(np.float32)
            best.append((float(np.abs(np.diff(t, axis=0)).mean()), int(y), int(x)))
    best.sort()
    _, y, x = best[int(0.80 * (len(best) - 1))]      # detailed, but not the extreme
    return y + 64, x + 64


def sites_for(rec: dict, n_sites: int) -> list[dict]:
    """Rank the nominated cluster sites across every pair of this subject.

    Sorted by peak residual x coherence: a real moving thing produces a
    CONTIGUOUS patch of tiles whose residual vectors POINT THE SAME WAY, while
    detector noise is spatially white and directionally random.  Ranking on
    magnitude alone would send the eye to the unluckiest tile in the corpus
    rather than to the largest thing that moved.
    """
    cands = []
    for p in rec.get("pairs", []):
        for c in p.get("clusters", []) or []:
            cands.append({**c, "i": p["i"], "k": p["k"], "a": p["a"], "b": p["b"]})
    cands.sort(key=lambda c: -(c["peak_sensor_px"] * max(c["coherence"], 0.05)
                               * np.sqrt(c["n_tiles"])))
    picked: list[dict] = []
    for c in cands:
        cy, cx = c["peak_plane_yx"]
        if any(abs(cy - q["peak_plane_yx"][0]) < 128 and abs(cx - q["peak_plane_yx"][1]) < 128
               for q in picked):
            continue                                  # do not show the same place twice
        picked.append(c)
        if len(picked) >= n_sites:
            break
    return picked


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default=os.path.join(OUT, "data", "sweep.json"))
    ap.add_argument("--subject", action="append", default=None)
    ap.add_argument("--top", type=int, default=0,
                    help="take the N subjects with the largest K16 p99")
    ap.add_argument("--sites", type=int, default=5)
    ap.add_argument("--out", default=os.path.join(OUT, "crops"))
    args = ap.parse_args()

    with open(args.sweep) as fh:
        sw = json.load(fh)
    byname = {r["subject"]: r for r in sw["subjects"] if "fatal" not in r}

    if args.subject:
        names = [n for n in args.subject]
    elif args.top:
        rank = sorted(byname.values(),
                      key=lambda r: -max((b.get("p99_max", 0.0)
                                          for b in r.get("by_k", {}).values()), default=0.0))
        names = [r["subject"] for r in rank[:args.top]]
    else:
        names = sorted(byname)

    os.makedirs(args.out, exist_ok=True)

    manifest = []
    print(f"cropping {len(names)} subjects at 1:1, {args.sites} motion sites + "
          f"1 control each", flush=True)

    for name in names:
        rec = byname.get(name)
        if rec is None:
            print(f"  {name:38s} NOT IN SWEEP -- skipped", flush=True)
            manifest.append({"subject": name, "status": "not_in_sweep"})
            continue
        try:
            master, meta = load_master(name)
        except Exception as e:                        # noqa: BLE001
            print(f"  {name:38s} MASTER UNREADABLE: {e}", flush=True)
            manifest.append({"subject": name, "status": "master_unreadable", "error": str(e)})
            continue

        picked = sites_for(rec, args.sites)
        panels, sites = [], []
        for j, c in enumerate(picked):
            cy = int(round(c["peak_plane_yx"][0] * G.PLANE_TO_SENSOR))
            cx = int(round(c["peak_plane_yx"][1] * G.PLANE_TO_SENSOR))
            img, y0, x0 = crop_at(master, cy, cx)
            lab = (f"M{j + 1} {c['peak_sensor_px']:.2f}PX COH{c['coherence']:.2f} "
                   f"N{c['n_tiles']} K{c['k']} @{y0},{x0}")
            panels.append((to8(img), lab))
            # Each panel also written on its own, because a six-panel sheet gets
            # shrunk to fit a screen and a shrunk 1:1 crop is not a 1:1 crop.
            solo = os.path.join(args.out, f"{name}__M{j + 1}.png")
            _write_png(solo, to8(img))
            sites.append({"panel": f"M{j + 1}", "master_y": y0, "master_x": x0,
                          "size": CROP, "png": solo, **c})
        qy, qx = quiet_site(master)
        img, y0, x0 = crop_at(master, qy, qx)
        panels.append((to8(img), f"CONTROL (NO MOTION FOUND) @{y0},{x0}"))
        solo = os.path.join(args.out, f"{name}__CONTROL.png")
        _write_png(solo, to8(img))
        sites.append({"panel": "CONTROL", "master_y": y0, "master_x": x0,
                      "size": CROP, "png": solo})

        k16 = rec.get("by_k", {}).get("16", {})
        p99_16 = k16.get("p99_med")
        slope = rec.get("k_slope")
        title = (f"{name}  1:1 NO RESAMPLING  "
                 f"K16 P99={f'{p99_16:.3f}' if p99_16 is not None else 'N/A'} "
                 f"SENSOR PX  SLOPE={f'{slope:+.2f}' if slope is not None else 'N/A'}")
        sh = sheet(panels, title)
        out_path = os.path.join(args.out, f"{name}.png")
        _write_png(out_path, sh)
        print(f"  {name:38s} {len(picked)} motion sites + control -> {out_path}", flush=True)
        manifest.append({"subject": name, "status": "ok", "sheet": out_path,
                         "master": meta, "sites": sites,
                         "n_motion_sites": len(picked)})

    ok = sum(1 for m in manifest if m["status"] == "ok")
    bad = len(manifest) - ok
    print(f"\nsubjects examined {len(manifest)}   sheets written {ok}   "
          f"skipped {bad}   (sums to {ok + bad})")
    mp = os.path.join(args.out, "manifest.json")
    with open(mp, "w") as fh:
        json.dump(manifest, fh, indent=2, default=float)
    print(f"wrote {mp}")
    return 0


def _write_png(path: str, a: np.ndarray) -> None:
    import zlib
    import struct
    h, w = a.shape[:2]
    raw = b"".join(b"\x00" + a[r].tobytes() for r in range(h))

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        fh.write(chunk(b"IDAT", zlib.compress(raw, 6)))
        fh.write(chunk(b"IEND", b""))


if __name__ == "__main__":
    raise SystemExit(main())

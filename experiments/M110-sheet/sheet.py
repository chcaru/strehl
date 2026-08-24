"""M110-sheet: a reproducible comparison-sheet harness.

WHY THIS EXISTS
---------------
M110 P10 measured that an archived render stops being reproducible within
minutes: the binary that made M110's B6 TIFFs was rebuilt eight minutes after
them, and six agents mutate the render path continuously. A one-off sheet is
stale before anyone looks at it. So this builds the INSTRUMENT, not the artefact
-- one command regenerates a dated sheet against whatever `HEAD` is now.

WHAT IT GUARANTEES
------------------
1. SELF-DATING. Every run writes `manifest.json` carrying `git rev-parse HEAD`,
   whether the tree was dirty, the sha256 of the `strehl.exe` that produced the
   pixels, the full argv of every arm, exit codes, and wall-clock. A sheet that
   cannot name its own binary is worthless (P10).

2. 1:1 CROPS ONLY. Fact 1359: a Laplacian metric rated a visibly mosaicked
   render 2.73x sharper than the correct one, and a halo correction reported
   +72.9% while erasing the bee's abdomen hairs. Only 100% crops caught those.
   Nothing here resizes except an integer NEAREST magnify, which copies pixels.

3. FIXED CROPS. Coordinates live in `subjects.json`, chosen ONCE by `scout` and
   frozen. They are never re-chosen per arm -- re-choosing per arm would let
   each arm show its own best region, which is how a comparison lies.

4. PINNED EXPOSURE. `--auto-exposure` is scene-dependent, and M100 declined to
   make it the default precisely because "a silent, scene-dependent gain makes
   two renders incomparable" (`merge_cmd.rs:3156`). Every arm of a subject is
   rendered at one frozen `--exposure`, recorded in `subjects.json`.

5. CACHE-COLLISION GUARD. `StackIdentity` covers neither `reference` nor
   `resampler` (fact 1446) and this matrix varies `resampler` on purpose. Every
   arm gets its own explicit sidecar and output path, and the run FAILS if two
   arms of a subject produce identical bytes -- that is exactly what the defect
   would look like, and it would read as "the kernel makes no difference".

Exit codes are read through Python's `subprocess.returncode`, which is immune to
the `$LASTEXITCODE` corruption of rule 47 / fact 1443.

The 1:1 tiling and 8-bit conversion follow the committed
`experiments/ORCH-drift-check/sheet3.py` and `kernel_crops.py`; this does not
invent a third approach.

USAGE
    python sheet.py scout   [--limit N] [--subject NAME ...]
    python sheet.py render  [--limit N] [--subject NAME ...]
    python sheet.py figure  [--subject NAME ...]
    python sheet.py all     [--limit N] [--subject NAME ...]
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SUBJECTS_PATH = HERE / "subjects.json"
OUT_ROOT = Path(r"C:\dev\strehl-out\M110-sheet")
BINARY = REPO / ".cargo-target-m110" / "release" / "strehl.exe"

# The arms matrix. Adding an arm is adding a dict: `env` and the extra flags for
# each stage. Kept as data so M107's CA and M97's merge wiring drop in without
# touching any logic below.
ARMS: list[dict] = [
    {"name": "default", "align": [], "merge": [], "env": {},
     "note": "shipped default (catmull-rom)"},
    {"name": "lanczos3", "align": ["--resampler", "lanczos3"], "merge": [], "env": {},
     "note": "M95 kernel, landed switchable at 843f6e1"},
]

CROP = 560          # 1:1 window, in output pixels
ROLES = ["detail", "silhouette", "specular", "smooth", "corner"]


# --------------------------------------------------------------------------
# provenance
# --------------------------------------------------------------------------
def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True)
    return r.stdout.strip()


def provenance() -> dict:
    dirty = git("status", "--porcelain")
    return {
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "generated_local": _dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "git_head": git("rev-parse", "HEAD"),
        "git_head_subject": git("log", "-1", "--pretty=%s"),
        "git_dirty": bool(dirty),
        "git_dirty_files": [ln[3:] for ln in dirty.splitlines()] if dirty else [],
        "binary": {
            "path": str(BINARY),
            "sha256": sha256_file(BINARY),
            "mtime": _dt.datetime.fromtimestamp(BINARY.stat().st_mtime).isoformat(timespec="seconds"),
            "size": BINARY.stat().st_size,
        },
        "host": os.environ.get("COMPUTERNAME", "?"),
        "python": sys.version.split()[0],
        "numpy": np.__version__,
    }


def run(argv: list[str], env_extra: dict | None = None) -> dict:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    t0 = time.time()
    r = subprocess.run(argv, capture_output=True, text=True, env=env)
    return {
        "argv": argv,
        "env_extra": env_extra or {},
        "exit": r.returncode,          # immune to the rule-47 pipeline defect
        "seconds": round(time.time() - t0, 1),
        "stderr_tail": r.stderr.strip().splitlines()[-40:],
        "stdout_tail": r.stdout.strip().splitlines()[-20:],
    }


# --------------------------------------------------------------------------
# config
# --------------------------------------------------------------------------
def load_subjects() -> dict:
    return json.loads(SUBJECTS_PATH.read_text(encoding="utf-8"))


def save_subjects(cfg: dict) -> None:
    SUBJECTS_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def pick(cfg: dict, names: list[str] | None) -> list[dict]:
    subs = cfg["subjects"]
    if not names:
        return subs
    by = {s["name"]: s for s in subs}
    missing = [n for n in names if n not in by]
    if missing:
        sys.exit(f"unknown subject(s): {missing}")
    return [by[n] for n in names]


# --------------------------------------------------------------------------
# render
# --------------------------------------------------------------------------
def arm_paths(subject: str, arm: str) -> tuple[Path, Path]:
    d = OUT_ROOT / subject
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{arm}.warp.json", d / f"{arm}.tif"


def render_arm(sub: dict, arm: dict, limit: int | None, exposure_flag: str | None) -> dict:
    stack = sub["dir"]
    sidecar, tif = arm_paths(sub["name"], arm["name"])
    lim = ["--limit", str(limit)] if limit else []

    a = run([str(BINARY), "align", stack, *lim, *arm["align"], "--out", str(sidecar)],
            arm["env"])
    if a["exit"] != 0:
        return {"stage": "align", "align": a, "ok": False}

    merge_env = dict(arm["env"])
    merge_env["STREHL_WARPMAP"] = str(sidecar)
    expo = [exposure_flag] if exposure_flag else ["--auto-exposure"]
    m = run([str(BINARY), "stack", stack, *lim, "--srgb", *expo, *arm["merge"],
             "--out", str(tif)], merge_env)
    if m["exit"] != 0:
        return {"stage": "merge", "align": a, "merge": m, "ok": False}

    recorded = None
    for ln in sidecar.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.startswith("resampler "):
            recorded = ln.split(None, 1)[1].strip()
            break

    return {
        "ok": True,
        "note": arm["note"],
        "align": a,
        "merge": m,
        "sidecar": str(sidecar),
        "sidecar_resampler": recorded,
        "tif": str(tif),
        "tif_sha256": sha256_file(tif),
        "tif_bytes": tif.stat().st_size,
        "seconds": round(a["seconds"] + m["seconds"], 1),
    }


EXPO_RE = re.compile(r"--exposure=(-?\d+\.\d+)")


def cmd_scout(args) -> int:
    """Choose, ONCE, the pinned exposure and the fixed crop coordinates.

    Selection rules, applied identically to every subject and stated so they can
    be argued with:
      detail     - tile of maximal mean |gradient| (finest structure)
      silhouette - tile of maximal luminance p95-p05 spread (a hard boundary)
      specular   - tile with the highest 99.9th-percentile luminance (highlight)
      smooth     - tile of minimal |gradient| among tiles above the 20th
                   percentile of brightness (defocus, not black border)
      corner     - the corner tile, among the four, with the most gradient
                   energy; purely geometric placement, content only breaks the
                   tie. Lateral CA is radial and zero at centre, so a
                   centre-only sheet cannot see it at all.
    Chosen on the DEFAULT arm only, then frozen. Never re-chosen per arm.
    """
    cfg = load_subjects()
    for sub in pick(cfg, args.subject):
        print(f"\n=== scouting {sub['name']} ===")
        arm = ARMS[0]
        res = render_arm(sub, arm, args.limit, None)
        if not res["ok"]:
            print(f"  FAILED at {res['stage']}")
            print("\n".join(res[res["stage"]]["stderr_tail"]))
            return 1

        stops = None
        for ln in res["merge"]["stderr_tail"]:
            m = EXPO_RE.search(ln)
            if m:
                stops = m.group(1)
        if stops is None:
            for ln in res["merge"]["stderr_tail"]:
                if "exposure" in ln:
                    print("   exposure line:", ln)
            print("  WARNING: could not parse an --exposure flag; leaving it unpinned")
        else:
            sub["exposure"] = f"--exposure={stops}"
            print(f"  pinned exposure: {sub['exposure']}")

        img = load8(Path(res["tif"]))
        sub["shape"] = [int(img.shape[1]), int(img.shape[0])]
        sub["crops"] = scout_crops(img)
        for c in sub["crops"]:
            print(f"  {c['role']:<11} @ ({c['x']},{c['y']})  {c['why']}")
        save_subjects(cfg)
    print(f"\nwrote {SUBJECTS_PATH}")
    return 0


def scout_crops(img: np.ndarray) -> list[dict]:
    h, w = img.shape[:2]
    g = img[:, :, 1].astype(np.float32)
    step = CROP // 2
    ys = list(range(0, h - CROP, step))
    xs = list(range(0, w - CROP, step))

    grad, spread, hi, bright = {}, {}, {}, {}
    for y in ys:
        for x in xs:
            t = g[y:y + CROP:3, x:x + CROP:3]
            gr = float(np.abs(np.diff(t, axis=0)).mean() + np.abs(np.diff(t, axis=1)).mean())
            grad[(y, x)] = gr
            spread[(y, x)] = float(np.percentile(t, 95) - np.percentile(t, 5))
            hi[(y, x)] = float(np.percentile(t, 99.9))
            bright[(y, x)] = float(t.mean())

    out = []
    used: list[tuple[int, int]] = []

    def far(c) -> bool:
        return all(abs(c[0] - u[0]) >= CROP or abs(c[1] - u[1]) >= CROP for u in used)

    def take(role, ranked, why):
        for c in ranked:
            if far(c):
                used.append(c)
                out.append({"role": role, "x": int(c[1]), "y": int(c[0]), "why": why})
                return
        c = ranked[0]
        used.append(c)
        out.append({"role": role, "x": int(c[1]), "y": int(c[0]), "why": why + " (overlaps)"})

    take("detail", sorted(grad, key=grad.get, reverse=True), "max mean |gradient|")
    take("silhouette", sorted(spread, key=spread.get, reverse=True), "max luma p95-p05")
    take("specular", sorted(hi, key=hi.get, reverse=True), "max luma p99.9")
    floor = np.percentile(list(bright.values()), 20)
    smooth_rank = sorted([c for c in grad if bright[c] >= floor], key=grad.get)
    take("smooth", smooth_rank or sorted(grad, key=grad.get), "min |gradient| above p20 brightness")

    inset = 48
    corners = [(inset, inset), (inset, w - CROP - inset),
               (h - CROP - inset, inset), (h - CROP - inset, w - CROP - inset)]
    best = max(corners, key=lambda c: grad.get((c[0] // step * step, c[1] // step * step), 0.0))
    out.append({"role": "corner", "x": int(best[1]), "y": int(best[0]),
                "why": f"geometric corner, {inset}px inset; radial max for lateral CA"})
    return out


def cmd_render(args) -> int:
    cfg = load_subjects()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    man = provenance()
    man["crop_px"] = CROP
    man["limit"] = args.limit
    man["arms"] = [{"name": a["name"], "note": a["note"],
                    "align": a["align"], "merge": a["merge"], "env": a["env"]} for a in ARMS]
    man["subjects"] = {}
    failures = []

    for sub in pick(cfg, args.subject):
        print(f"\n=== rendering {sub['name']} ({len(ARMS)} arms) ===")
        entry = {"dir": sub["dir"], "exposure": sub.get("exposure"), "arms": {}}
        for arm in ARMS:
            print(f"  {arm['name']:<10} ...", end="", flush=True)
            res = render_arm(sub, arm, args.limit, sub.get("exposure"))
            entry["arms"][arm["name"]] = res
            if not res["ok"]:
                print(f" FAILED at {res['stage']} (exit {res[res['stage']]['exit']})")
                print("   " + "\n   ".join(res[res["stage"]]["stderr_tail"][-8:]))
                failures.append(f"{sub['name']}/{arm['name']}")
            else:
                print(f" ok  {res['seconds']}s  sha {res['tif_sha256'][:12]}"
                      f"  resampler={res['sidecar_resampler']}")

        # fact 1446 guard: two arms sharing bytes is what the unkeyed cache
        # produces, and it would read as "the kernel makes no difference".
        good = {k: v["tif_sha256"] for k, v in entry["arms"].items() if v.get("ok")}
        dupes = [(a, b) for i, a in enumerate(good) for b in list(good)[i + 1:]
                 if good[a] == good[b]]
        entry["distinct_hashes_ok"] = not dupes
        entry["duplicate_pairs"] = dupes
        if dupes:
            print(f"  *** CACHE COLLISION: identical bytes for {dupes} ***")
            failures.append(f"{sub['name']} duplicate arm bytes {dupes}")
        else:
            print(f"  arms byte-distinct: OK ({len(good)} arms)")
        man["subjects"][sub["name"]] = entry

    man["failures"] = failures
    mp = OUT_ROOT / "manifest.json"
    mp.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {mp}")
    return 1 if failures else 0


# --------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------
def load8(p: Path) -> np.ndarray:
    """16-bit -> 8-bit by the high byte, as sheet3.py does. No tone change."""
    a = tifffile.imread(p)
    if a.dtype == np.uint16:
        return (a >> 8).astype(np.uint8)
    return a.astype(np.uint8)


def font(size: int):
    for name in ("consola.ttf", "arial.ttf", "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def cmd_figure(args) -> int:
    cfg = load_subjects()
    man = json.loads((OUT_ROOT / "manifest.json").read_text(encoding="utf-8"))
    f_lab, f_hdr = font(15), font(18)

    for sub in pick(cfg, args.subject):
        name = sub["name"]
        entry = man["subjects"].get(name)
        if not entry:
            print(f"skip {name}: not in manifest")
            continue
        arms = [a for a in ARMS if entry["arms"].get(a["name"], {}).get("ok")]
        if len(arms) < 2:
            print(f"skip {name}: fewer than two good arms")
            continue
        imgs = {a["name"]: load8(Path(entry["arms"][a["name"]]["tif"])) for a in arms}
        crops = sub["crops"]

        for scale, tag in ((1, "100"), (2, "200")):
            pad, lab, hdr = 10, 30, 96
            cw = CROP * scale
            W = pad + len(arms) * (cw + pad)
            H = hdr + len(crops) * (lab + cw + pad) + 34
            canvas = Image.new("RGB", (W, H), (18, 18, 20))
            d = ImageDraw.Draw(canvas)

            d.text((pad, 8), f"strehl  --  {name}  --  1:1 pixels"
                             + (f", magnified x{scale} NEAREST (real pixels)" if scale > 1 else "")
                             + "   NO resize / NO sharpening / NO tone change",
                   fill=(240, 240, 245), font=f_hdr)
            d.text((pad, 32), f"HEAD {man['git_head'][:12]}"
                              f"{'  DIRTY' if man['git_dirty'] else ''}"
                              f"   strehl.exe sha256 {man['binary']['sha256'][:16]}"
                              f"   built {man['binary']['mtime']}",
                   fill=(150, 200, 150), font=f_lab)
            d.text((pad, 50), f"rendered {man['generated_local']}"
                              f"   exposure {entry.get('exposure') or 'auto'}"
                              f"   limit {man.get('limit') or 'none (full stack)'}"
                              f"   crop {CROP}px",
                   fill=(150, 200, 150), font=f_lab)
            d.text((pad, 68), "Crop coordinates are frozen in subjects.json and identical "
                              "for every arm. Downscaling hides softness; this figure never "
                              "downscales.",
                   fill=(170, 170, 180), font=f_lab)

            y = hdr
            for c in crops:
                x = pad
                for a in arms:
                    arm = a["name"]
                    tile = imgs[arm][c["y"]:c["y"] + CROP, c["x"]:c["x"] + CROP]
                    im = Image.fromarray(tile)
                    if scale > 1:
                        im = im.resize((cw, cw), Image.NEAREST)
                    canvas.paste(im, (x, y + lab))
                    sha = entry["arms"][arm]["tif_sha256"][:8]
                    d.text((x, y + 6),
                           f"{c['role']}  @({c['x']},{c['y']})  |  {arm}"
                           + ("   <- SHIPPED DEFAULT" if arm == "default" else "")
                           + f"   [{sha}]",
                           fill=(245, 220, 120), font=f_lab)
                    d.rectangle([x - 1, y + lab - 1, x + cw, y + lab + cw],
                                outline=(90, 90, 95))
                    x += cw + pad
                y += lab + cw + pad

            dst = OUT_ROOT / name / f"SHEET-{name}-{tag}.png"
            canvas.save(dst)
            print(f"wrote {dst}  {canvas.size}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("scout", "render", "figure", "all"):
        p = sp.add_parser(nm)
        p.add_argument("--subject", action="append")
        if nm != "figure":
            p.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    if not BINARY.exists():
        sys.exit(f"missing binary: {BINARY}")

    if args.cmd == "scout":
        return cmd_scout(args)
    if args.cmd == "render":
        return cmd_render(args)
    if args.cmd == "figure":
        return cmd_figure(args)
    rc = cmd_render(args)
    return cmd_figure(args) or rc


if __name__ == "__main__":
    sys.exit(main())

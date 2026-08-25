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
#
# TO ARM A PENDING ARM: fill in `align` / `merge` / `env` with the EXACT string
# its owning milestone reports, then set `enabled: True`. Nothing else changes.
#
# `enabled: False` exists because a guessed flag is worse than a missing arm.
# When `OpticalProfile` had zero consumers, `STREHL_FIX_CA=1` set a variable no
# render path read: an invented CA arm would have rendered bytes identical to
# the default and the sheet would have reported "the correction does not help".
# A silent no-op is a false negative wearing the costume of a result, so pending
# arms are skipped loudly instead.

# The CA key, copied from the source of truth
# (crates/strehl-core/src/optics.rs::A7C2_FE100GM_2XTC_X4CPL.key) rather than
# from a relayed message. It is CASE-SENSITIVE and a near-miss is an ERROR, not
# a silent no-op -- but the error arrives per frame from
# `warp_frame_in_place`, AFTER a full decode (~53 s on bee-3-cpl), so in a batch
# a typo reads as a slow arm rather than a config error. `assert_ca_key()`
# below fails in milliseconds instead.
CA_KEY = "a7c2-fe100gm-2xtc-x4cpl"

ARMS: list[dict] = [
    {"name": "default", "align": [], "merge": [], "env": {}, "enabled": True,
     "note": "shipped default (catmull-rom), CA off"},
    {"name": "lanczos3", "align": ["--resampler", "lanczos3"], "merge": [], "env": {},
     "enabled": True,
     "note": "M95 kernel, landed switchable at 843f6e1. Set on the ALIGN stage because "
             "`strehl stack` has no --resampler flag at all: a merge's kernel comes "
             "entirely from whichever sidecar it reads."},
    {"name": "ca", "align": [], "merge": [], "env": {"STREHL_FIX_CA": CA_KEY},
     "enabled": True,
     "note": "M107 lateral-CA, landed 4bc9abf, wired in align_cmd.rs::warp_frame_in_place. "
             "RADIAL TERM ONLY -- the fitted translation is recorded but zeroed. "
             "eps_b is None: blue was never fitted, every fitted ROI was red, so this is a "
             "RED-ONLY correction applied to red/cyan fringe pairs and at most half of each "
             "fringe can move. Support is r <= 0.788, declared but UNENFORCED, so the "
             "corner is a 1.27x extrapolation of the model's shape, not data.",
     "env_note": "environment variable, NOT argv; unset/0/off means off"},
    {"name": "ca+lanczos3", "align": ["--resampler", "lanczos3"], "merge": [],
     "env": {"STREHL_FIX_CA": CA_KEY}, "enabled": True,
     "note": "The actual candidate configuration and the only arm that answers the owner's "
             "question: sharpening makes fringes more conspicuous, so neither CA nor "
             "lanczos3 alone settles it. Same eps_b/support caveats as `ca`."},
]

# CA is NOT in the warp cache key, and deliberately so: `active_profile()` is
# read at exactly one site, `warp_frame_in_place`, which is not among
# `solve_map`'s callers, so no CA setting can change the WarpMap. Adding it
# would force a full re-solve per toggle for a bit-identical map.
#
# The consequence is in our favour and worth stating: ONE CA-unaware sidecar is
# shared by every arm, so the registration is held EXACTLY fixed across the A/B
# and the only thing that varies is the gather. This is the opposite of the
# resampler, which the solve genuinely does read -- hence the sidecar assertion
# in render_arm, which applies to the kernel and not to CA.
CA_NULL_SHA = "e400a63aa9f6ab1f1957940d7bd9d4965d67e01f6f0e1a0a7abc30d8e7f17112"

CROP = 560          # 1:1 window, in output pixels
ROLES = ["detail", "silhouette", "specular", "clipped", "smooth", "corner",
         "fringe", "neutral"]
FULL = 65535        # 16-bit sRGB TIFF full scale
HOT = 0.99 * FULL   # "genuinely blown", not merely bright


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
def assert_ca_key() -> None:
    """Fail in milliseconds on a bad CA key instead of 53 s per frame.

    `active_profile()` is resolved per frame inside `warp_frame_in_place`, not
    at startup, so a mistyped key exits 1 only AFTER a full decode. In a batch
    that reads as a slow arm, not a config error.

    The key is checked against the Rust source rather than against this file's
    own constant, which would only prove the constant equals itself.
    """
    src = REPO / "crates" / "strehl-core" / "src" / "optics.rs"
    text = src.read_text(encoding="utf-8", errors="replace")
    needle = f'key: "{CA_KEY}"'
    if needle not in text:
        sys.exit(f"CA key {CA_KEY!r} does not appear as a `key:` in {src}.\n"
                 f"The key is CASE-SENSITIVE and a near-miss is an error, not a "
                 f"no-op. Copy it from the OpticalProfile record.")
    for arm in ARMS:
        got = arm["env"].get("STREHL_FIX_CA")
        if got is not None and got != CA_KEY:
            sys.exit(f"arm {arm['name']!r} sets STREHL_FIX_CA={got!r}, "
                     f"expected {CA_KEY!r}")


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

    # `strehl stack` has no --resampler flag: the merge's kernel is set entirely
    # by whichever sidecar it reads. That makes the kernel field ONE-SIDED --
    # an arm can silently inherit a kernel from an unrelated earlier command and
    # nothing in its own log would say so. Assert the sidecar records what this
    # arm actually asked for, rather than trusting that it must.
    want = "catmull-rom"
    if "--resampler" in arm["align"]:
        want = arm["align"][arm["align"].index("--resampler") + 1]
    ok_res = recorded == want

    return {
        "ok": ok_res,
        "note": arm["note"],
        "align": a,
        "merge": m,
        "sidecar": str(sidecar),
        "sidecar_resampler": recorded,
        "resampler_wanted": want,
        "resampler_ok": ok_res,
        "stage": None if ok_res else "resampler",
        "tif": str(tif),
        "tif_sha256": sha256_file(tif),
        "tif_bytes": tif.stat().st_size,
        # Per ARM, not per run. A partial re-run leaves arms in one manifest that
        # were made by different binaries, and the run-level block records only
        # the latest. Without this a preserved arm cannot say what produced it --
        # which is P10 biting the instrument built to prevent P10.
        "binary_sha256": sha256_file(BINARY),
        "binary_mtime": _dt.datetime.fromtimestamp(
            BINARY.stat().st_mtime).isoformat(timespec="seconds"),
        "rendered_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
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

        raw = load_raw(Path(res["tif"]))
        sub["shape"] = [int(raw.shape[1]), int(raw.shape[0])]
        sub["crops"] = scout_crops(raw)
        sub["scouted_from"] = {"tif": res["tif"], "sha256": res["tif_sha256"],
                               "limit": args.limit}
        for c in sub["crops"]:
            print(f"  {c['role']:<11} @ ({c['x']},{c['y']})  {c['why']}")
        save_subjects(cfg)
    print(f"\nwrote {SUBJECTS_PATH}")
    return 0


def cmd_recrop(args) -> int:
    """Re-choose crops from the default arm ALREADY on disk, without re-rendering.

    For when the role list changes and a fresh render would be pure cost. It is
    honest only because it records the sha256 of the TIFF it read, so a crop set
    can always be traced to the exact bytes it was chosen on -- the P10 lesson
    applied to configuration rather than to output.
    """
    cfg = load_subjects()
    for sub in pick(cfg, args.subject):
        tif = OUT_ROOT / sub["name"] / "default.tif"
        if not tif.exists():
            print(f"skip {sub['name']}: no {tif}")
            continue
        print(f"\n=== recropping {sub['name']} from {tif.name} ===")
        raw = load_raw(tif)
        sub["shape"] = [int(raw.shape[1]), int(raw.shape[0])]
        fresh = scout_crops(raw)

        # Rule 24 is "choose by geometry, ONCE". A crop set that silently moves
        # when the role list grows destroys every before/after already taken on
        # it, so adding a role must ADD a role and nothing else. Existing roles
        # keep their frozen coordinates and their original `why`; only genuinely
        # new roles are appended. `--refreeze` is the explicit opt-out.
        old = {c["role"]: c for c in sub.get("crops", [])}
        if args.refreeze or not old:
            sub["crops"] = fresh
            sub["scouted_from"] = {"tif": str(tif), "sha256": sha256_file(tif),
                                   "limit": None, "recrop": True, "refroze_all": True}
        else:
            added = [c for c in fresh if c["role"] not in old]
            sub["crops"] = list(sub["crops"]) + added
            sub.setdefault("scouted_from", {})["added_roles"] = {
                "roles": [c["role"] for c in added],
                "tif": str(tif), "sha256": sha256_file(tif),
                "kept_frozen": sorted(old),
            }
            for c in sub["crops"]:
                mark = "NEW  " if c["role"] in {a["role"] for a in added} else "frozen"
                print(f"  [{mark}] {c['role']:<11} @ ({c['x']},{c['y']})")
            save_subjects(cfg)
            continue
        for c in sub["crops"]:
            print(f"  {c['role']:<11} @ ({c['x']},{c['y']})  {c['why']}")
        save_subjects(cfg)
    print(f"\nwrote {SUBJECTS_PATH}")
    return 0


def scout_crops(raw: np.ndarray) -> list[dict]:
    img = to8(raw)
    h, w = img.shape[:2]
    g = img[:, :, 1].astype(np.float32)
    step = CROP // 2
    ys = list(range(0, h - CROP, step))
    xs = list(range(0, w - CROP, step))

    grad, spread, hi, bright, blown = {}, {}, {}, {}, {}
    chroma, rnorm = {}, {}
    cy, cx = h / 2.0, w / 2.0
    rmax = float(np.hypot(cy, cx))
    for y in ys:
        for x in xs:
            t = g[y:y + CROP:3, x:x + CROP:3]
            gr = float(np.abs(np.diff(t, axis=0)).mean() + np.abs(np.diff(t, axis=1)).mean())
            grad[(y, x)] = gr
            spread[(y, x)] = float(np.percentile(t, 95) - np.percentile(t, 5))
            hi[(y, x)] = float(np.percentile(t, 99.9))
            bright[(y, x)] = float(t.mean())
            blown[(y, x)] = neutrality(raw[y:y + CROP:3, x:x + CROP:3])[0]
            tile = img[y:y + CROP:3, x:x + CROP:3].astype(np.float32)
            luma = (0.2126 * tile[:, :, 0] + 0.7152 * tile[:, :, 1]
                    + 0.0722 * tile[:, :, 2])
            chroma[(y, x)] = float(np.abs(tile[:, :, 0] - luma).mean())
            rnorm[(y, x)] = float(np.hypot(y + CROP / 2 - cy, x + CROP / 2 - cx) / rmax)

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

    # The magenta-clipping site. Selected on the PHYSICAL condition -- the most
    # genuinely blown pixels -- not on how magenta the tile looks. Selecting on
    # the defect's appearance would choose the window where the defect is
    # loudest, which is choosing the answer; selecting on blown-ness picks the
    # place where the render is obliged to be neutral and is therefore a fair
    # test both before and after the fix. Falls back to the next-brightest tile
    # if this subject has nothing genuinely clipped, and says so.
    if max(blown.values(), default=0.0) > 0.0:
        take("clipped", sorted(blown, key=blown.get, reverse=True),
             "max fraction of pixels with red AND blue >= 99% full scale")
    else:
        take("clipped", sorted(hi, key=hi.get, reverse=True),
             "NO GENUINELY CLIPPED PIXELS in this subject; fell back to max luma p99.9")

    floor = np.percentile(list(bright.values()), 20)
    smooth_rank = sorted([c for c in grad if bright[c] >= floor], key=grad.get)
    take("smooth", smooth_rank or sorted(grad, key=grad.get), "min |gradient| above p20 brightness")

    inset = 48
    corners = [(inset, inset), (inset, w - CROP - inset),
               (h - CROP - inset, inset), (h - CROP - inset, w - CROP - inset)]
    best = max(corners, key=lambda c: grad.get((c[0] // step * step, c[1] // step * step), 0.0))
    out.append({"role": "corner", "x": int(best[1]), "y": int(best[0]),
                "why": f"geometric corner, {inset}px inset; radial max for lateral CA"})

    # Lateral CA is RADIAL: the correction is eps_r * r, identically zero at the
    # optical centre. A high-contrast edge in the middle of the frame therefore
    # cannot show the fix working no matter how sharp it is. So the fringe site
    # is the strongest edge among tiles that are actually far enough out to
    # carry a fringe -- geometry first, contrast second, and never appearance.
    far_out = [c for c in grad if rnorm[c] >= 0.55]
    take("fringe", sorted(far_out or list(grad), key=grad.get, reverse=True),
         "max |gradient| among tiles at radius >= 0.55; CA is radial so a centre "
         "edge cannot show the correction")

    # Where M107's COST lands, and the discriminator for this sheet. The
    # correction removed 54% of the top |R-Y| decile but changed decile 1 --
    # near-neutral pixels -- by +583%, with 44.7% of them flipping chroma sign.
    # A percentage that large on a near-zero baseline can be invisible or a new
    # artefact and the percentage alone cannot tell you which, so we need a tile
    # that is near-neutral AND textured: flat neutral hides injected chroma
    # against nothing, whereas texture gives the eye a reference. Selected on
    # minimum |R-Y| among tiles with above-median gradient.
    tex_floor = float(np.median(list(grad.values())))
    textured = [c for c in chroma if grad[c] >= tex_floor]
    take("neutral", sorted(textured or list(chroma), key=chroma.get),
         "min mean |R-Y| among tiles with above-median gradient: near-neutral but "
         "textured, where M107's +583% decile-1 chroma injection would land")
    return out


def cmd_render(args) -> int:
    cfg = load_subjects()
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    prov = provenance()
    want = getattr(args, "arm", None)
    arms = [a for a in ARMS if not want or a["name"] in want]
    if want and not arms:
        print(f"no arm matches {want}; known: {[a['name'] for a in ARMS]}")
        return 2
    if any(a["env"].get("STREHL_FIX_CA") for a in arms if a.get("enabled", True)):
        assert_ca_key()
        print(f"CA key verified against optics.rs: {CA_KEY}")

    # Merge into any existing manifest rather than replacing it, so re-running
    # ONE subject does not silently delete the others' entries and leave
    # `figure` skipping them. Provenance is recorded PER SUBJECT because a
    # partial re-run happens under a different binary than the rest -- which is
    # the P10 hazard exactly, and a single global block would paper over it.
    mp = OUT_ROOT / "manifest.json"
    man = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
    man.update(prov)
    man["crop_px"] = CROP
    man["limit"] = args.limit
    man["arms"] = [{"name": a["name"], "note": a["note"], "enabled": a.get("enabled", True),
                    "align": a["align"], "merge": a["merge"], "env": a["env"]} for a in ARMS]
    man.setdefault("subjects", {})
    failures = []

    for sub in pick(cfg, args.subject):
        print(f"\n=== rendering {sub['name']} ({sum(1 for a in arms if a.get('enabled', True))} "
              f"of {len(ARMS)} arms enabled) ===")
        entry = {"dir": sub["dir"], "exposure": sub.get("exposure"), "arms": {},
                 "provenance": prov, "limit": args.limit}
        if want:
            # An arm-filtered run must not delete the arms it did not run. Keep
            # their entries, but mark them STALE: they were made by a different
            # binary, and after P10 that is not a detail.
            prev = man["subjects"].get(sub["name"], {})
            for k, v in (prev.get("arms") or {}).items():
                if k not in want:
                    v = dict(v)
                    v["stale"] = True
                    v["stale_vs"] = prov.get("head")
                    v["provenance"] = prev.get("provenance")
                    entry["arms"][k] = v
        for arm in arms:
            if not arm.get("enabled", True):
                print(f"  {arm['name']:<12} .. PENDING, skipped (not run, not a no-op arm)")
                entry["arms"][arm["name"]] = {"ok": False, "pending": True,
                                              "note": arm["note"]}
                continue
            print(f"  {arm['name']:<12} ...", end="", flush=True)
            res = render_arm(sub, arm, args.limit, sub.get("exposure"))
            entry["arms"][arm["name"]] = res
            if not res["ok"]:
                st = res.get("stage") or "?"
                if st == "resampler":
                    print(f" FAILED: sidecar records resampler "
                          f"{res['sidecar_resampler']!r}, arm asked for "
                          f"{res['resampler_wanted']!r}")
                else:
                    print(f" FAILED at {st} (exit {res[st]['exit']})")
                    print("   " + "\n   ".join(res[st]["stderr_tail"][-8:]))
                failures.append(f"{sub['name']}/{arm['name']}")
            else:
                print(f" ok  {res['seconds']}s  sha {res['tif_sha256'][:12]}"
                      f"  resampler={res['sidecar_resampler']}")

        # fact 1446 guard: two arms sharing bytes is what the unkeyed cache
        # produces, and it would read as "the kernel makes no difference".
        # Only arms rendered in THIS run can be compared -- a stale arm's hash
        # came from another binary, so agreement or disagreement with it says
        # nothing about the cache.
        fresh = {k: v["tif_sha256"] for k, v in entry["arms"].items()
                 if v.get("ok") and not v.get("stale")}
        dupes = [(a, b) for i, a in enumerate(fresh) for b in list(fresh)[i + 1:]
                 if fresh[a] == fresh[b]]
        entry["distinct_hashes_ok"] = not dupes
        entry["duplicate_pairs"] = dupes
        if dupes:
            print(f"  *** CACHE COLLISION: identical bytes for {dupes} ***")
            failures.append(f"{sub['name']} duplicate arm bytes {dupes}")
        else:
            print(f"  arms byte-distinct: OK ({len(fresh)} arms)")

        # `strehl stack` has no --resampler flag, so a merge's kernel comes only
        # from the sidecar it reads. With ONE arm there is nothing to disagree
        # with it: a lone arm can inherit a kernel from an unrelated earlier
        # command and the byte-distinctness assertion above is vacuous. Say so
        # rather than let a one-armed run look as guarded as a two-armed one.
        # A deliberate --arm run is still unguarded; it is just not a failure.
        entry["arms_run"] = len(fresh)
        entry["comparison_guarded"] = len(fresh) >= 2
        entry["deliberate_single_arm"] = bool(want) and len(fresh) < 2
        if len(fresh) < 2:
            print(f"  *** ONLY {len(fresh)} ARM RAN: byte-distinctness is vacuous and the "
                  f"kernel is unguarded"
                  + (" (deliberate --arm run) ***" if want else " ***"))
            if not want:
                failures.append(f"{sub['name']} unguarded: {len(fresh)} arm(s)")
        man["subjects"][sub["name"]] = entry

    man["failures"] = failures
    mp.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")
    print(f"\nwrote {mp}")
    return 1 if failures else 0


# --------------------------------------------------------------------------
# figure
# --------------------------------------------------------------------------
def load_raw(p: Path) -> np.ndarray:
    """The TIFF as written. 16-bit for --srgb output; needed unshifted because
    clipping lives in the top 1% and >>8 cannot tell 65280 from 65535."""
    return tifffile.imread(p)


def to8(a: np.ndarray) -> np.ndarray:
    return (a >> 8).astype(np.uint8) if a.dtype == np.uint16 else a.astype(np.uint8)


def load8(p: Path) -> np.ndarray:
    """16-bit -> 8-bit by the high byte, as sheet3.py does. No tone change."""
    return to8(load_raw(p))


def highlight_stats(win: np.ndarray, region: np.ndarray | None = None) -> dict:
    """Two-sided blown-highlight neutrality.

    The one-sided readout below selects on RED AND BLUE being pinned, then
    measures green against them. That selection is the blindness: it forces the
    comparison baseline to the container ceiling, so a green EXCESS has nowhere
    to register.

    Worse than under-reporting, once you know what the fix does. `e9ad010`
    applies a saturation ceiling to the colour matrix, so a ceiling computed too
    low clamps RED AND BLUE DOWN -- which would drop them below the 99% mask
    entirely and report "too few blown px to score". The instrument would go
    quiet exactly when the port was worst.

    So select channel-agnostically -- blown in AT LEAST ONE channel -- which is
    the physical condition "this is a blown highlight" and survives either
    failure direction:

        magenta   R,B pinned, G below  ->  off < 0
        green     G pinned, R,B below  ->  off > 0

    Both have the full range of the container available, because whichever
    channel is low is the one carrying the signal.

    `region` overrides the selection with a frozen mask. THE SELECTION IS NOT
    INVARIANT UNDER THE THING IT MEASURES: any change that lowers a channel can
    push a pixel below HOT and out of the population, which moves the mean for
    a reason that is not the neutrality of the pixels that remain. Freezing the
    mask on a reference separates the instrument's GAIN from that population
    shift. On real data there is no reference, so the free selection is what
    ships and the shift is a systematic -- measured, not assumed, by bars B1/B2
    in neutrality_control.py. `region_n` is reported so a shift is visible.
    """
    if win.dtype != np.uint16:
        return {"off": None, "region_n": 0, "region_frac": 0.0}
    r, g, b = (win[:, :, i].astype(np.float32) for i in range(3))
    if region is None:
        region = np.maximum(np.maximum(r, g), b) >= HOT
    n = int(region.sum())
    out = {"region_frac": float(region.mean()), "region_n": n}
    if n < 64:
        out["off"] = None
        return out
    rr, gg, bb = r[region], g[region], b[region]
    out["off"] = float(((gg - 0.5 * (rr + bb)) / FULL).mean())

    # Which channel is actually pinned. This is the most diagnostic single
    # output: neutral clips all three together, magenta spares green, a
    # low ceiling spares red and blue.
    out["c_r"] = float((rr >= HOT).mean())
    out["c_g"] = float((gg >= HOT).mean())
    out["c_b"] = float((bb >= HOT).mean())
    out["asym"] = out["c_g"] - 0.5 * (out["c_r"] + out["c_b"])

    # Headroom for a planted signal, in each direction, as the 5th percentile:
    # 95% of region pixels have at least this much room. Both directions are
    # measured by LOWERING a channel, which is how both real failures arise --
    # magenta leaves green low, a low ceiling leaves red and blue low -- and
    # lowering always has room where raising hits the container ceiling.
    out["head_magenta"] = float(np.percentile(gg / FULL, 5))
    out["head_green"] = float(np.percentile(np.minimum(rr, bb) / FULL, 5))

    # The old one-sided core statistic, kept so earlier numbers stay comparable
    # and so its disappearance is itself visible.
    core = (r >= HOT) & (b >= HOT)
    cn = int(core.sum())
    out["core_n"] = cn
    out["core_frac"] = float(core.mean())
    out["core_off"] = (float(((g[core] - 0.5 * (r[core] + b[core])) / FULL).mean())
                       if cn >= 64 else None)
    return out


def neutrality(win: np.ndarray) -> tuple[float, float | None]:
    """Blown fraction, and the green offset on blown pixels.

    ONE-SIDED. Superseded as the primary readout by `highlight_stats` above and
    kept because earlier numbers in the report were taken with it, and because
    its silence under a green overshoot is itself a result worth being able to
    reproduce. Do not use it alone to clear a highlight change.

    A blown highlight is physically neutral: nothing in the scene is brighter
    than the clip point in two channels and coloured in the third. So on pixels
    where red AND blue are both clipped, mean (G - (R+B)/2) / full-scale should
    be ~0.
    """
    if win.dtype != np.uint16:
        return 0.0, None
    r, g, b = (win[:, :, i].astype(np.float32) for i in range(3))
    blown = (r >= HOT) & (b >= HOT)
    frac = float(blown.mean())
    if int(blown.sum()) < 64:
        return frac, None
    off = float(((g[blown] - 0.5 * (r[blown] + b[blown])) / FULL).mean())
    return frac, off


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
        imgs, neut = {}, {}
        crops = sub["crops"]
        clip = next((c for c in crops if c["role"] == "clipped"), None)
        for a in arms:
            raw = load_raw(Path(entry["arms"][a["name"]]["tif"]))
            if clip:
                neut[a["name"]] = highlight_stats(
                    raw[clip["y"]:clip["y"] + CROP, clip["x"]:clip["x"] + CROP])
            imgs[a["name"]] = to8(raw)
            del raw

        for scale, tag in ((1, "100"), (2, "200")):
            pad, lab, hdr = 10, 46, 96
            cw = CROP * scale
            W = pad + len(arms) * (cw + pad)
            H = hdr + len(crops) * (lab + cw + pad) + 34
            canvas = Image.new("RGB", (W, H), (18, 18, 20))
            d = ImageDraw.Draw(canvas)

            d.text((pad, 8), f"strehl  --  {name}  --  1:1 pixels"
                             + (f", magnified x{scale} NEAREST (real pixels)" if scale > 1 else "")
                             + "   NO resize / NO sharpening / NO tone change",
                   fill=(240, 240, 245), font=f_hdr)
            pv = entry.get("provenance", man)
            d.text((pad, 32), f"HEAD {pv['git_head'][:12]}"
                              f"{'  DIRTY' if pv['git_dirty'] else ''}"
                              f"   strehl.exe sha256 {pv['binary']['sha256'][:16]}"
                              f"   built {pv['binary']['mtime']}",
                   fill=(150, 200, 150), font=f_lab)
            d.text((pad, 50), f"rendered {pv['generated_local']}"
                              f"   exposure {entry.get('exposure') or 'auto'}"
                              f"   limit {entry.get('limit') or 'none (full stack)'}"
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
                    d.text((x, y + 4),
                           f"{c['role']}  @({c['x']},{c['y']})  |  {arm}"
                           + ("   <- SHIPPED DEFAULT" if arm == "default" else "")
                           + f"   [{sha}]",
                           fill=(245, 220, 120), font=f_lab)
                    sub2, col2 = c.get("why", ""), (150, 150, 160)
                    if c["role"] == "clipped" and arm in neut:
                        s = neut[arm]
                        off = s.get("off")
                        if off is None:
                            sub2 = (f"blown {s['region_frac'] * 100:.2f}% of tile "
                                    f"-- too few to score")
                        else:
                            # neutral clips all three channels together
                            sub2 = (f"blown {s['region_frac'] * 100:.2f}%   "
                                    f"off {off:+.4f} (0=neutral, -mag, +green)   "
                                    f"pinned r{s['c_r']:.2f} g{s['c_g']:.2f} b{s['c_b']:.2f}")
                            col2 = ((250, 140, 200) if off < -0.02 else
                                    (150, 250, 150) if off > 0.02 else (140, 230, 160))
                    d.text((x, y + 24), sub2, fill=col2, font=f_lab)
                    d.rectangle([x - 1, y + lab - 1, x + cw, y + lab + cw],
                                outline=(90, 90, 95))
                    x += cw + pad
                y += lab + cw + pad

            dst = OUT_ROOT / name / f"SHEET-{name}-{tag}.png"
            canvas.save(dst)
            print(f"wrote {dst}  {canvas.size}")
    return 0


def cmd_survey(args) -> int:
    """Per subject, read the frozen `clipped` tile off the default arm on disk.

    Two-sided: `off` is the channel-agnostic statistic from `highlight_stats`,
    negative for magenta and positive for a green overshoot, and `c_r/c_g/c_b`
    say which channel is actually pinned. `core` is the old one-sided number,
    shown alongside so its silence is visible rather than absent.
    """
    cfg = load_subjects()
    hdr = (f"{'subject':<20} {'blown%':>7} {'off':>9} {'core':>9} "
           f"{'c_r':>6} {'c_g':>6} {'c_b':>6} {'asym':>7}   verdict")
    print(hdr)
    print("-" * len(hdr))
    for sub in pick(cfg, args.subject):
        tif = OUT_ROOT / sub["name"] / "default.tif"
        clip = next((c for c in sub.get("crops", []) if c["role"] == "clipped"), None)
        if not tif.exists() or not clip:
            print(f"{sub['name']:<20}   no default.tif or no clipped crop")
            continue
        raw = load_raw(tif)
        s = highlight_stats(raw[clip["y"]:clip["y"] + CROP, clip["x"]:clip["x"] + CROP])
        del raw
        off = s.get("off")
        if off is None:
            print(f"{sub['name']:<20} {s['region_frac'] * 100:>6.3f}%   "
                  f"too few blown px to score")
            continue
        core = s.get("core_off")
        verdict = ("MAGENTA" if off < -0.02 else
                   "GREEN OVERSHOOT" if off > 0.02 else "neutral")
        print(f"{sub['name']:<20} {s['region_frac'] * 100:>6.3f}% {off:>+9.4f} "
              f"{(f'{core:+.4f}' if core is not None else 'n/a'):>9} "
              f"{s['c_r']:>6.3f} {s['c_g']:>6.3f} {s['c_b']:>6.3f} "
              f"{s['asym']:>+7.3f}   {verdict}")
    print("\noff < 0 magenta, off > 0 green. c_x = fraction of the blown region "
          "with channel x pinned;\nneutral clipping pins all three together. "
          "Headroom both ways is reported by neutrality_control.py.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for nm in ("scout", "recrop", "render", "figure", "all", "survey"):
        p = sp.add_parser(nm)
        p.add_argument("--subject", action="append")
        if nm in ("scout", "render", "all"):
            p.add_argument("--limit", type=int, default=None)
        if nm in ("render", "all"):
            p.add_argument("--arm", action="append",
                           help="render only these arms. A run of fewer than two "
                                "arms is recorded as comparison_guarded=false: "
                                "with no second arm to disagree, the fact-1446 "
                                "byte-distinctness check is vacuous.")
        if nm == "recrop":
            p.add_argument("--refreeze", action="store_true",
                           help="re-choose EVERY role, moving frozen crops. Off by "
                                "default: adding a role must add a role and nothing "
                                "else, or every before/after already taken is void.")
    args = ap.parse_args()

    if args.cmd == "recrop":
        return cmd_recrop(args)
    if args.cmd == "survey":
        return cmd_survey(args)
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

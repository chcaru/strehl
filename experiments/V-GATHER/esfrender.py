"""Render the ESF arm matrix for the gather flip, from ONE pinned binary.

Geometry is BUILD-SHARP's exactly: --gate 0 (which infers the estimator
backend), BINNED output (no --demosaic, no --srgb), so m88blib's hardcoded
10.24 um pitch and its 2x sensor-coordinate mapping are both satisfied.

Arms:
  cr-plane   ALIGN=1 FULLRES=0 catmull-rom   <- BUILD-SHARP's b-g0-cr
  cr-fullres ALIGN=1 FULLRES=1 catmull-rom   <- the flip
  nn-plane   ALIGN=1 FULLRES=0 nearest       <- BUILD-SHARP's b-g0-nn
  nn-fullres ALIGN=1 FULLRES=1 nearest
  na-plane   ALIGN=0 FULLRES=0 catmull-rom   } specificity control: with no
  na-fullres ALIGN=0 FULLRES=1 catmull-rom   } warp the flag is UNREACHABLE,
                                             } so these two must be BYTE-IDENTICAL

The warp cache is isolated PER RESAMPLER because the CLI states a sidecar's
own recorded resampler wins over --resampler.  Both gather arms share one
cache dir so they provably use the SAME warp map.
"""
import hashlib, json, os, re, subprocess, sys, time
from pathlib import Path

EXE = r"C:\dev\strehl-out\V-GATHER\strehl-pinned.exe"
OUT = Path(r"C:\dev\strehl-out\V-GATHER\esf")
SRC = Path(r"D:\personal\macro")
OUT.mkdir(parents=True, exist_ok=True)

ARMS = [
    ("cr-plane",   "1", "0", "catmull-rom"),
    ("cr-fullres", "1", "1", "catmull-rom"),
    ("nn-plane",   "1", "0", "nearest"),
    ("nn-fullres", "1", "1", "nearest"),
    ("na-plane",   "0", "0", "catmull-rom"),
    ("na-fullres", "0", "1", "catmull-rom"),
]

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def render(subject, arm, align, fullres, resampler, fix_ca="off"):
    tif = OUT / f"{subject}--{arm}.tif"
    log = OUT / f"{subject}--{arm}.log"
    if tif.exists() and log.exists():
        return {"subject": subject, "arm": arm, "cached": True,
                "sha": sha(tif), "bytes": tif.stat().st_size}
    env = dict(os.environ)
    env["STREHL_ALIGN"] = align
    env["STREHL_FULLRES_GATHER"] = fullres
    env["STREHL_FIX_CA"] = fix_ca
    env["STREHL_CACHE_DIR"] = str(OUT / f"warpcache-{resampler}")
    env.pop("STREHL_WARPMAP", None)
    Path(env["STREHL_CACHE_DIR"]).mkdir(parents=True, exist_ok=True)
    cmd = [EXE, "stack", str(SRC / subject), "--out", str(tif),
           "--gate", "0", "--resampler", resampler]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    el = time.perf_counter() - t0
    txt = r.stdout + r.stderr
    log.write_text(txt, encoding="utf-8", errors="replace")
    d = {"subject": subject, "arm": arm, "align": align, "fullres": fullres,
         "resampler": resampler, "rc": r.returncode, "wall_s": round(el, 1)}
    for k, pat in [("backend", r"merge\s+:\s*(\S+)"),
                   ("alignment", r"alignment\s+:\s*([^\n]{0,80})"),
                   ("planes", r"planes\s+:\s*(\d+ x \d+)"),
                   ("resampler_line", r"resampler\s*:\s*([^\n]{0,70})"),
                   ("sidecar", r"(sidecar[^\n]{0,90})")]:
        m = re.search(pat, txt)
        d[k] = m.group(1).strip() if m else None
    if r.returncode != 0:
        d["err"] = txt[-1500:]
    elif tif.exists():
        d["sha"] = sha(tif)
        d["bytes"] = tif.stat().st_size
    return d

if __name__ == "__main__":
    plan = [("109MSDCF", ARMS),
            ("tweezers-cpl", ARMS),
            ("highly-angled-ruler-mm-cpl", ARMS[:2])]
    res = []
    for subject, arms in plan:
        for arm, al, fr, rs in arms:
            d = render(subject, arm, al, fr, rs)
            res.append(d)
            print(json.dumps({k: v for k, v in d.items()
                              if k in ("subject", "arm", "rc", "wall_s",
                                       "backend", "alignment", "planes", "sha")}),
                  flush=True)
    (OUT / "esfrender.json").write_text(json.dumps(res, indent=1))

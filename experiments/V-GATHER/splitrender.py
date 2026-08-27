import json, os, subprocess, sys, time, hashlib
from pathlib import Path

EXE = r"C:\dev\strehl-out\V-GATHER\strehl-pinned.exe"
OUT = Path(r"C:\dev\strehl-out\V-GATHER")
SPLIT = OUT / "split"

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def render(srcdir, arm, outp):
    env = dict(os.environ)
    env["STREHL_FULLRES_GATHER"] = arm
    env["STREHL_FIX_CA"] = "off"
    cmd = [EXE, "stack", str(srcdir), "--linear-srgb", "--demosaic",
           "--out", str(outp)]
    t0 = time.perf_counter()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    el = time.perf_counter() - t0
    log = r.stdout + r.stderr
    (OUT / ("log-" + outp.stem + ".txt")).write_text(log, encoding="utf-8", errors="replace")
    d = {"src": str(srcdir), "arm": arm, "out": str(outp), "rc": r.returncode,
         "wall_s": round(el, 1)}
    if outp.exists():
        d["sha"] = sha(outp)
        d["bytes"] = outp.stat().st_size
    if r.returncode != 0:
        d["err"] = log[-1500:]
    return d

if __name__ == "__main__":
    res = []
    for subj in ("foam", "wrapped-text-1"):
        for half in ("even", "odd"):
            for arm in ("0", "1"):
                src = SPLIT / f"{subj}-{half}"
                outp = OUT / f"sp-{subj}-{half}-g{arm}.tiff"
                d = render(src, arm, outp)
                res.append(d)
                print(json.dumps(d), flush=True)
    (OUT / "splitrender.json").write_text(json.dumps(res, indent=1))

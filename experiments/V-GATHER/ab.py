import json, os, subprocess, sys, time, hashlib, re
from pathlib import Path

EXE = r"C:\dev\strehl-out\V-GATHER\strehl-pinned.exe"
OUT = Path(r"C:\dev\strehl-out\V-GATHER")
SRC = Path(r"D:\personal\macro")

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def render(subject, arm, limit, tag, extra=None, out=True):
    """arm: '0' or '1'. Returns dict."""
    env = dict(os.environ)
    env["STREHL_FULLRES_GATHER"] = arm
    env["STREHL_FIX_CA"] = "off"
    outp = OUT / f"{subject}-{tag}-g{arm}.tiff"
    cmd = [EXE, "stack", str(SRC / subject), "--limit", str(limit),
           "--linear-srgb", "--demosaic"]
    if out:
        cmd += ["--out", str(outp)]
    if extra:
        cmd += extra
    t0 = time.perf_counter()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    el = time.perf_counter() - t0
    log = r.stdout + r.stderr
    d = {"subject": subject, "arm": arm, "limit": limit, "tag": tag,
         "wall_s": el, "rc": r.returncode,
         "out": str(outp) if out else None}
    for key, pat in [
        ("align_s",   r"alignment\s+: ON \(solved\), reference frame (\d+), (\d+) placed / (\d+) refused, ([\d.]+) s"),
        ("workers",   r"memory plan\s+: (\d+) workers x ([\d.]+) MB"),
        ("planes",    r"planes\s+: (\d+) x (\d+)"),
        ("coverage",  r"field of view scaled to ([\d.]+)"),
    ]:
        m = re.search(pat, log)
        d[key] = m.groups() if m else None
    for m in re.finditer(r"^\s*([a-z][a-z \-]{2,20}?)\s+:\s*([\d.]+)\s*s\s*$", log, re.M):
        d.setdefault("stage_s", {})[m.group(1).strip()] = float(m.group(2))
    tl = re.findall(r"(?:total|elapsed|wrote|merge)[^\n]*", log, re.I)
    d["tail"] = tl[-6:]
    if out and outp.exists():
        d["bytes"] = outp.stat().st_size
        d["sha"] = sha(outp)
    if r.returncode != 0:
        d["err"] = log[-2000:]
    (OUT / f"log-{subject}-{tag}-g{arm}.txt").write_text(log, encoding="utf-8", errors="replace")
    return d

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "probe":
        subj, lim = sys.argv[2], int(sys.argv[3])
        for arm in ("1", "0"):
            d = render(subj, arm, lim, "probe")
            print(json.dumps(d, indent=1))

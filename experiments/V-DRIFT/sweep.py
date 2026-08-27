"""Drive `strehl align` across stack depths and span sets, and record what it found.

The two quantities this lane turns on are both already computed by the product
and written to the sidecar:

  cycle-floor-px  self-inconsistency of the raw pairwise measurements, computed
                  from the data alone with no solver involved. It bounds what
                  ANY solver can achieve, so it measures how hard the subject
                  is to register -- "difficulty".

  heldout-px      train the solve on spans < 40, then measure corner error on
                  the held-out spans >= 40. This is exactly "how well does a
                  short-range-only solve predict long-range geometry", which is
                  the accumulation question -- "does error compound along a
                  chain of short steps".

Sweeping depth on ONE subject with `--limit` holds the optics, the subject and
the capture constant and varies only how many frames the solve must span. If
held-out error grows with depth while the cycle floor stays flat, error is
accumulating. If both grow together, the far end of the stack is simply harder
to measure and no solver change will help.

Unlike V-SPEED, nothing here is a wall-clock number, so the loaded host cannot
bias the result -- but `--repeat` checks that claim rather than asserting it.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

STREHL = r"C:\dev\strehl-out\acceptance-pins\9b05d0b7\target\release\strehl.exe"
STREHL_SHA_PREFIX = "44C2F2CD2E5B2894"
OUT = r"C:\dev\strehl-out\V-DRIFT"

PATTERNS = {
    "frames": r"(\d+) frames, digest",
    "digest": r"digest ([0-9a-f]+)",
    "reference": r"reference frame (\d+)",
    "edges_measured": r"measured (\d+)/(\d+) edges",
    "refused_pct": r"([\d.]+)% refused",
    "placed": r"placed (\d+)/(\d+) frames",
    "drift": r"total corner drift frame 0 -> \d+: ([\d.]+) plane px",
    "heldout": r"held-out corner error \(median\): ([\d.]+) plane px",
    "cycle_floor": r"cycle-consistency floor: ([\d.]+) plane px",
}


def check_binary():
    h = hashlib.sha256(open(STREHL, "rb").read()).hexdigest().upper()
    if not h.startswith(STREHL_SHA_PREFIX):
        sys.exit(f"REFUSING TO RUN: strehl SHA-256 {h} does not start with {STREHL_SHA_PREFIX}")
    return h


def parse_log(text):
    out = {}
    for key, pat in PATTERNS.items():
        m = re.search(pat, text)
        if not m:
            out[key] = None
        elif key in ("edges_measured", "placed"):
            out[key] = int(m.group(1))
            out[key + "_of"] = int(m.group(2))
        elif key == "digest":
            out[key] = m.group(1)
        else:
            out[key] = float(m.group(1))
    return out


def solve(subject, srcdir, limit=None, spans=None, tag="", reference=None):
    label = f"{subject}-L{limit or 'all'}-{tag or 'ladder'}"
    wmdir = os.path.join(OUT, "wm")
    logdir = os.path.join(OUT, "logs")
    os.makedirs(wmdir, exist_ok=True)
    os.makedirs(logdir, exist_ok=True)
    wmpath = os.path.join(wmdir, f"{label}.warpmap.txt")
    logpath = os.path.join(logdir, f"{label}.log")

    cmd = [STREHL, "align", srcdir, "--out", wmpath]
    if limit:
        cmd += ["--limit", str(limit)]
    if spans:
        for s in spans:
            cmd += ["--spans", str(s)]
    if reference is not None:
        cmd += ["--reference", str(reference)]

    t0 = time.perf_counter()
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    wall = time.perf_counter() - t0
    text = (p.stdout or "") + (p.stderr or "")
    open(logpath, "w", encoding="utf-8").write(text)

    rec = {
        "label": label, "subject": subject, "limit": limit,
        "spans": spans or "default", "tag": tag or "ladder",
        "reference_arg": reference, "rc": p.returncode,
        "wall_s": round(wall, 2), "warpmap": wmpath,
        "sha_ok": True,
    }
    rec.update(parse_log(text))
    if p.returncode != 0:
        rec["error"] = text.strip()[-400:]
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outfile")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--limits", type=int, nargs="+", required=True)
    ap.add_argument("--spans", type=int, nargs="+", default=None)
    ap.add_argument("--tag", default="")
    ap.add_argument("--reference", type=int, default=None)
    ap.add_argument("--repeat", type=int, default=1,
                    help="solve each point N times to test determinism")
    a = ap.parse_args()

    sha = check_binary()
    print(f"strehl SHA-256 {sha[:16]}... OK")
    path = os.path.join(OUT, a.outfile)
    print(f"{'label':<34}{'heldout':>9}{'cycle':>8}{'drift':>9}{'ref%':>7}{'wall':>8}")
    print("-" * 75)
    with open(path, "a", encoding="utf-8") as fh:
        for limit in a.limits:
            for rep in range(a.repeat):
                r = solve(a.subject, a.dir, limit, a.spans, a.tag, a.reference)
                r["rep"] = rep
                r["digest_of_wm"] = (
                    hashlib.sha256(open(r["warpmap"], "rb").read()).hexdigest()[:16]
                    if os.path.exists(r["warpmap"]) else None
                )
                fh.write(json.dumps(r) + "\n")
                fh.flush()
                ho = f"{r['heldout']:.3f}" if r.get("heldout") else "-"
                cy = f"{r['cycle_floor']:.3f}" if r.get("cycle_floor") else "-"
                dr = f"{r['drift']:.1f}" if r.get("drift") else "-"
                rf = f"{r['refused_pct']:.1f}" if r.get("refused_pct") is not None else "-"
                print(f"{r['label']:<34}{ho:>9}{cy:>8}{dr:>9}{rf:>7}{r['wall_s']:>8.1f}")


if __name__ == "__main__":
    main()

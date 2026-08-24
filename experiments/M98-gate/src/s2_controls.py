"""M98 S2 -- controls.  Every one names the input that makes it fail (rule 20),
and the negative control is registered at an EXACT value (rule 39, fact 1231).

  EQ   two invocations, identical arguments -> identical output.
       Bar: exactly 100.000000% of pixels equal, and SHA-256 equal.
  NC1  THE NEGATIVE CONTROL MADE TO GO RED.  Flip exactly one pixel by exactly
       one LSB.  EQ must read exactly (1 - 1/(W*H*3)) and go RED.  If it still
       reads 100.000000%, the comparison is not reading the file and every
       equality claim in this milestone is void.
  PC   POWER CONTROL.  Plant a Gaussian of sigma = 0.30 px into BOTH halves at
       gate 4 and re-measure dsig.  Bar: recovered in [0.25, 0.35] px.  If it
       reads under 0.25 px the instrument cannot see an effect the size M92
       reports and NO NULL IN THIS MILESTONE MEANS ANYTHING.
  PL1  PLACEBO.  Re-render the same gate twice; dsig between the two pairs must
       be exactly 0.000000 px.
  PL2  PLACEBO.  Swap the half labels A<->B; every dsig must move < 1e-9 px.

Usage:  python s2_controls.py <stack>
"""
import json
import os
import shutil
import subprocess
import sys
import time

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m98lib as M98  # noqa: E402
import m57lib as K    # noqa: E402

STACK = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
BIN = r"C:\dev\blog\death-of-software\projects\strehl\.cargo-target-m98\release\strehl.exe"
CTL = os.path.join(M98.RENDERS, "controls")
os.makedirs(CTL, exist_ok=True)
PLANT_SIGMA = 0.30


def render(dirname, gate, out, align=None):
    env = dict(os.environ)
    if align is None:
        env.pop("STREHL_ALIGN", None)
    else:
        env["STREHL_ALIGN"] = align
    r = subprocess.run([BIN, "stack", dirname, "--gate", f"{gate:g}", "-o", out],
                       env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[-2000:])
    return r.stdout


def pct_equal(p1, p2):
    a = tifffile.imread(p1)
    b = tifffile.imread(p2)
    if a.shape != b.shape:
        return 0.0, a.size
    return float((a == b).sum()) / a.size * 100.0, a.size


def main():
    t0 = time.time()
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    out = {}
    log("=" * 78)
    log(f"M98 S2 -- controls on {STACK}")
    log("=" * 78)

    src = os.path.join(M98.FRAMES, f"{STACK}-A")

    # ---------------------------------------------------------------- EQ
    e1 = os.path.join(CTL, f"{STACK}-eq1.tif")
    e2 = os.path.join(CTL, f"{STACK}-eq2.tif")
    for p in (e1, e2):
        if not os.path.exists(p):
            render(src, 2.0, p)
    pe, npx = pct_equal(e1, e2)
    h1, h2 = M98.sha256(e1), M98.sha256(e2)
    eq_ok = (pe == 100.0) and (h1 == h2)
    log(f"\nEQ   two identical invocations, gate 2, alignment ON")
    log(f"     pixels compared : {npx}")
    log(f"     equal           : {pe:.6f}%   BAR: exactly 100.000000%")
    log(f"     sha256 A        : {h1}")
    log(f"     sha256 B        : {h2}")
    log(f"     EQ: {'GREEN' if eq_ok else 'RED'}")
    out["EQ"] = dict(pct=pe, npx=int(npx), sha_a=h1, sha_b=h2, ok=bool(eq_ok))

    # ---------------------------------------------------------------- NC1
    nc = os.path.join(CTL, f"{STACK}-nc1.tif")
    shutil.copyfile(e2, nc)
    a = tifffile.imread(nc)
    y, x, c = a.shape[0] // 3, a.shape[1] // 3, 1
    before = int(a[y, x, c])
    a[y, x, c] = np.uint16(before + 1) if before < 65535 else np.uint16(before - 1)
    tifffile.imwrite(nc, a)
    pn, _ = pct_equal(e1, nc)
    expect = (1.0 - 1.0 / npx) * 100.0
    nc_ok = (pn != 100.0) and abs(pn - expect) < 1e-9
    log(f"\nNC1  the negative control MADE TO GO RED: one pixel, one LSB")
    log(f"     planted at      : (y={y}, x={x}, c={c})  {before} -> {int(a[y, x, c])}")
    log(f"     equal           : {pn:.6f}%   EXPECTED exactly {expect:.6f}%")
    log(f"     EQ bar of exactly 100.000000% now reads: "
        f"{'RED (correct)' if pn != 100.0 else 'GREEN (WRONG -- the bar is inert)'}")
    log(f"     NC1: {'GREEN' if nc_ok else 'RED'}")
    out["NC1"] = dict(pct=pn, expect=expect, ok=bool(nc_ok))

    # ------------------------------------------------------- grid & terciles
    g0a = M98.green(M98.render_path(STACK, "ALN", 0.0, "A"))
    h, w = g0a.shape
    grid = M98.roi_grid(h, w)
    hp = [M98.hp_sd(M98.crop(g0a, xy)) for xy in grid]
    ter = M98.terciles(hp)

    # ---------------------------------------------------------------- PC
    pa = M98.green(M98.render_path(STACK, "ALN", 4.0, "A"))
    pb = M98.green(M98.render_path(STACK, "ALN", 4.0, "B"))
    log(f"\nPC   POWER CONTROL: planted Gaussian sigma = {PLANT_SIGMA:.2f} px in BOTH halves at gate 4")
    log(f"     {'ROI':>4} {'hp_sd':>8} {'recovered px':>13} {'SE':>8}")
    rec = []
    for k in ter["high"]:
        ca, cb = M98.crop(pa, grid[k]), M98.crop(pb, grid[k])
        ba = M98.gauss_blur_fft(ca, PLANT_SIGMA)
        bb = M98.gauss_blur_fft(cb, PLANT_SIGMA)
        d = K.dsig(K.RingStats(ca, cb), K.RingStats(ba, bb))
        rec.append(d["px"])
        log(f"     {k:>4} {hp[k]:>8.2f} {d['px']:>+13.5f} {d['se_px']:>8.5f}")
    s = M98.stats_across(rec)
    pc_ok = 0.25 <= s["mean"] <= 0.35
    log(f"     mean {s['mean']:+.5f} px over {s['n']} ROIs   BAR [0.25, 0.35]  "
        f"-> {'GREEN' if pc_ok else 'RED'}")
    log(f"     if RED and below 0.25: the instrument cannot see M92's effect size "
        f"and no null here means anything.")
    out["PC"] = dict(plant_sigma=PLANT_SIGMA, per_roi=rec,
                     **{k: v for k, v in s.items()}, ok=bool(pc_ok))

    # ---------------------------------------------------------------- PL1
    q1a = M98.green(e1)
    q2a = M98.green(e2)
    pb2 = M98.green(M98.render_path(STACK, "ALN", 2.0, "B"))
    log(f"\nPL1  PLACEBO: the same gate rendered twice.  dsig must be exactly 0.")
    worst = 0.0
    for k in ter["high"]:
        d = K.dsig(K.RingStats(M98.crop(q1a, grid[k]), M98.crop(pb2, grid[k])),
                   K.RingStats(M98.crop(q2a, grid[k]), M98.crop(pb2, grid[k])),
                   jack=False)
        worst = max(worst, abs(d["px"]) if np.isfinite(d["px"]) else np.inf)
    pl1_ok = worst == 0.0
    log(f"     max |dsig| over {len(ter['high'])} ROIs = {worst:.9f} px   "
        f"BAR exactly 0.000000  -> {'GREEN' if pl1_ok else 'RED'}")
    out["PL1"] = dict(max_abs=worst, ok=bool(pl1_ok))

    # ---------------------------------------------------------------- PL2
    log(f"\nPL2  PLACEBO: swap the half labels A<->B at every gate.")
    worst2 = 0.0
    planes = {g: (M98.green(M98.render_path(STACK, "ALN", g, "A")),
                  M98.green(M98.render_path(STACK, "ALN", g, "B")))
              for g in M98.GATES}
    for g in M98.GATES:
        for k in ter["high"]:
            a0, b0 = (M98.crop(p, grid[k]) for p in planes[0.0])
            ag, bg = (M98.crop(p, grid[k]) for p in planes[g])
            d1 = K.dsig(K.RingStats(a0, b0), K.RingStats(ag, bg), jack=False)
            d2 = K.dsig(K.RingStats(b0, a0), K.RingStats(bg, ag), jack=False)
            if np.isfinite(d1["px"]) and np.isfinite(d2["px"]):
                worst2 = max(worst2, abs(d1["px"] - d2["px"]))
    pl2_ok = worst2 < 1e-9
    log(f"     max |dsig(A,B) - dsig(B,A)| = {worst2:.3e} px   BAR < 1e-9  "
        f"-> {'GREEN' if pl2_ok else 'RED'}")
    out["PL2"] = dict(max_abs=worst2, ok=bool(pl2_ok))

    log(f"\nSUMMARY: " + "  ".join(
        f"{k}={'GREEN' if v.get('ok') else 'RED'}" for k, v in out.items()))
    log(f"({time.time()-t0:.0f}s)")

    with open(os.path.join(M98.OUT, f"s2_controls_{STACK}.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    with open(os.path.join(M98.OUT, f"s2_controls_{STACK}.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

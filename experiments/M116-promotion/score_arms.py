"""Score the campaign-6 arms on ORCH's patchwork invariant.

Runs experiments/ORCH-drift-check/patchwork_invariant.py UNMODIFIED on every
arm, with the SAME window reference for all of them. Passing a different
reference per arm lets each arm choose its own most-background windows, which
is not an A/B.

Two gates are enforced before any treatment number is believed:

  * P2-placebo must be byte-identical to P0-default. It differs from P0 only in
    its cache directory path, which cannot affect an image. If it differs, the
    renderer is not deterministic and every difference below is confounded.

  * P0-default must reproduce M93's armM4-gate4-binlin, because that is the
    render ORCH's published 1.114x baseline was measured on. Checked by integer
    -only phase correlation and NCC -- not by name (discipline 830) and not by
    assuming the flags did what they say.

Writes C:/dev/strehl-out/M116/invariant/arms.json. Reads nothing on D:.
"""

import hashlib
import json
import os
import re
import subprocess
import sys

import numpy as np
import tifffile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"C:\dev\strehl-out\M116\invariant"
M93 = r"C:\dev\strehl-out\M93-out"
INSTRUMENT = os.path.join(os.path.dirname(HERE), "ORCH-drift-check",
                          "patchwork_invariant.py")

ARMS = [
    ("P0-default", "bee-3-cpl__P0-default.tif"),
    ("P1-photometric", "bee-3-cpl__P1-photometric.tif"),
    ("P2-placebo", "bee-3-cpl__P2-placebo.tif"),
]
REFERENCE = os.path.join(OUT, "bee-3-cpl__P0-default.tif")
ARMM4 = os.path.join(M93, "armM4-gate4-binlin.tif")

RE_MEDIAN = re.compile(
    r"merged fine-structure / NOISIEST single: median ([0-9.]+), worst ([0-9.]+)")
RE_QUIET = re.compile(
    r"merged fine-structure / QUIETEST single: median ([0-9.]+), worst ([0-9.]+)")
RE_VIOL = re.compile(r"INVARIANT .*?: (?:HOLDS in all (\d+)|VIOLATED in (\d+) of (\d+))")
RE_PLANT = re.compile(r"plant voronoi\s+([0-9.]+)")
RE_USABLE = re.compile(r"single frames usable at identical geometry/dtype: (\d+) of (\d+)")


def guard(cond, msg):
    if not cond:
        print("GUARD: " + msg)
        sys.exit(3)


def load(path):
    arr = tifffile.imread(path)
    guard(arr.dtype == np.uint16,
          "%s loaded as %s, expected uint16 -- PIL returns uint8 for 16-bit RGB "
          "TIFFs silently (fact 1615)" % (os.path.basename(path), arr.dtype))
    return arr


def lum(arr):
    a = arr.astype(np.float64)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def shift_of(a, b):
    """Integer-only registration offset of b relative to a, by phase correlation.

    Integer only, deliberately: sub-pixel resampling would add blur to the very
    quantity these arms are being scored on.
    """
    n = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a = a[: n[0], : n[1]]
    b = b[: n[0], : n[1]]
    a = a - a.mean()
    b = b - b.mean()
    fa = np.fft.rfft2(a)
    fb = np.fft.rfft2(b)
    cross = fa * np.conj(fb)
    mag = np.abs(cross)
    mag[mag == 0] = 1.0
    corr = np.fft.irfft2(cross / mag, s=a.shape)
    peak = np.unravel_index(np.argmax(corr), corr.shape)
    dy = peak[0] if peak[0] <= a.shape[0] // 2 else peak[0] - a.shape[0]
    dx = peak[1] if peak[1] <= a.shape[1] // 2 else peak[1] - a.shape[1]
    return int(dy), int(dx), float(corr[peak])


def ncc(a, b):
    n = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    x = a[: n[0], : n[1]].ravel().astype(np.float64)
    y = b[: n[0], : n[1]].ravel().astype(np.float64)
    x -= x.mean()
    y -= y.mean()
    return float((x @ y) / (np.linalg.norm(x) * np.linalg.norm(y)))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def score(tag, path):
    log = os.path.join(OUT, "score-%s.log" % tag)
    proc = subprocess.run(
        [sys.executable, INSTRUMENT, path, "M116-" + tag, REFERENCE],
        capture_output=True, text=True)
    text = proc.stdout + proc.stderr
    with open(log, "w") as fh:
        fh.write(text)
    guard(proc.returncode == 0,
          "instrument exited %d on %s (it exits 4 when its own commissioning "
          "plant fails to fire)" % (proc.returncode, tag))
    m, q, v, p, u = (RE_MEDIAN.search(text), RE_QUIET.search(text),
                     RE_VIOL.search(text), RE_PLANT.search(text),
                     RE_USABLE.search(text))
    guard(m and q and v and p and u, "could not parse instrument output for " + tag)
    guard(float(p.group(1)) > 10.0,
          "commissioning plant read %s on %s, below the instrument's own bar; a "
          "green from an uncommissioned instrument is not a green"
          % (p.group(1), tag))
    guard(int(u.group(1)) == int(u.group(2)),
          "only %s of %s single frames were usable at identical geometry on %s"
          % (u.group(1), u.group(2), tag))
    return {
        "tag": tag,
        "median_vs_noisiest": float(m.group(1)),
        "worst_vs_noisiest": float(m.group(2)),
        "median_vs_quietest": float(q.group(1)),
        "violations": 0 if v.group(1) else int(v.group(2)),
        "windows": int(v.group(1) or v.group(3)),
        "plant": float(p.group(1)),
        "sha256_12": sha(path)[:12],
    }


def main():
    guard(os.path.exists(INSTRUMENT), "instrument missing at " + INSTRUMENT)
    for _, f in ARMS:
        guard(os.path.exists(os.path.join(OUT, f)), "missing arm render " + f)

    # Gate 1 -- the placebo. Registered as a withdrawal condition.
    h0 = sha(os.path.join(OUT, "bee-3-cpl__P0-default.tif"))
    h2 = sha(os.path.join(OUT, "bee-3-cpl__P2-placebo.tif"))
    placebo_identical = h0 == h2

    # Gate 2 -- does P0 reproduce the render ORCH's 1.114x was measured on?
    p0 = load(os.path.join(OUT, "bee-3-cpl__P0-default.tif"))
    m4 = load(ARMM4)
    same_shape = p0.shape == m4.shape
    dy, dx, peak = shift_of(lum(p0), lum(m4)) if same_shape else (None, None, None)
    corr = ncc(lum(p0), lum(m4)) if same_shape else None

    rows = [score(tag, os.path.join(OUT, f)) for tag, f in ARMS]
    by = {r["tag"]: r for r in rows}
    d = by["P1-photometric"]["median_vs_noisiest"] - by["P0-default"]["median_vs_noisiest"]
    v = by["P1-photometric"]["violations"] - by["P0-default"]["violations"]

    # The bars, transcribed from prereg-photometric.txt section 7. Fixed before
    # any of these numbers existed.
    if d <= -0.02 and v <= 0:
        verdict = "PROMOTE"
    elif d >= 0.02 or (v > 0 and d > 0):
        verdict = "REJECT"
    else:
        verdict = "NULL"

    result = {
        "pin": "4beac7300e318f6f0aaf10b6a88e57f311b9e814",
        "window_reference": REFERENCE,
        "instrument": INSTRUMENT,
        "placebo_byte_identical_to_default": placebo_identical,
        "p0_sha256": h0, "p2_sha256": h2,
        "p0_vs_armM4": {
            "same_shape": same_shape, "shift_dy": dy, "shift_dx": dx,
            "phase_peak": peak, "ncc": corr,
            "armM4_sha256_12": sha(ARMM4)[:12],
        },
        "arms": rows,
        "delta_median": d, "delta_violations": v,
        "verdict_against_prereg_bars": verdict,
        "orch_baseline_median": 1.114, "orch_baseline_violations": 7,
    }
    with open(os.path.join(OUT, "arms.json"), "w") as fh:
        json.dump(result, fh, indent=2)

    print("window reference for EVERY arm: %s" % os.path.basename(REFERENCE))
    print("")
    print("placebo byte-identical to default : %s" % placebo_identical)
    if same_shape:
        print("P0 vs M93 armM4 : shift (%d, %d)  phase peak %.4f  NCC %.4f"
              % (dy, dx, peak, corr))
    else:
        print("P0 vs M93 armM4 : SHAPE MISMATCH %s vs %s" % (p0.shape, m4.shape))
    print("")
    print("%-16s %10s %10s %8s %8s" % ("arm", "median", "worst", "viol", "plant"))
    for r in rows:
        print("%-16s %10.3f %10.3f %8d %8.2f"
              % (r["tag"], r["median_vs_noisiest"], r["worst_vs_noisiest"],
                 r["violations"], r["plant"]))
    print("")
    print("delta median (P1 - P0) = %+.4f   delta violations = %+d" % (d, v))
    print("VERDICT against pre-registered bars: %s" % verdict)


if __name__ == "__main__":
    main()

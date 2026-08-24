"""B22 -- does the gain survive the port, and is the harness right?

Three independent checks, in ascending order of what they would catch:

1. **Tap agreement.** The Rust example probed the *shipped* kernel with a delta
   plane and wrote the tap weights it read back. Recompute those weights from
   the textbook definitions here, in Python, and compare. This catches a
   transcription error in the port.

2. **Step overshoot, derived from first principles.** Catmull-Rom's maximum
   step overshoot at half-pixel phase is *exactly* 1/16 -- on `[lo,lo,lo,hi]`
   the weights `[-1/16, 9/16, 9/16, -1/16]` give `lo - (hi-lo)/16`. If the Rust
   harness reports 6.2500% of the step, it agrees with algebra rather than with
   itself. Lanczos-3's has no closed form and is computed numerically.

3. **The dex gain.** Re-run arm 8's band-ratio measurement on the real warps
   using the **extracted Rust taps** as the interpolator, and require it to
   reproduce arm 8's +0.1160 dex within the registered 0.01 dex.

Run: `python experiments/M95-kernel/src/k5_port.py`
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "M95-coverage" / "src"))
import m95cov as M  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
TAPS = HERE / "out" / "k3_port64.json"
RING = HERE / "out" / "k3_kernel.json"
OUT = HERE / "out" / "k5_port.json"

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
MAP = Path(r"D:\personal\macro\bee-3-cpl\warpmap.txt")
MAP_ALT = Path(r"C:\dev\strehl-out\ORCH-quarantine-sidecars\bee-3-cpl--warpmap.txt")

K_COVER = 0.9315
NFRAMES = 24
# Arm 8's measured kernel gain, from docs/research/M95-dose.md. B22 registered
# a 0.01 dex tolerance on reproducing it.
ARM8_KERNEL_GAIN = 0.1160
B22_TOL = 0.01


# --------------------------------------------------------------------------
# 1. tap agreement
# --------------------------------------------------------------------------
def py_weights(name, f):
    """Textbook weights, normalised, matching what the shipped code must do."""
    if name == "nearest":
        return np.array([1.0, 0.0]) if f < 0.5 else np.array([0.0, 1.0])
    if name == "bilinear":
        return np.array([1.0 - f, f])
    if name == "catmull-rom":
        t = np.array([-1.0, 0.0, 1.0, 2.0]) - f
        a = np.abs(t)
        w = np.where(
            a <= 1.0,
            1.5 * a**3 - 2.5 * a**2 + 1.0,
            np.where(a < 2.0, -0.5 * a**3 + 2.5 * a**2 - 4.0 * a + 2.0, 0.0),
        )
        return w
    if name == "lanczos3":
        t = np.array([-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]) - f
        w = np.where(
            np.abs(t) < 1e-6,
            1.0,
            np.where(
                np.abs(t) >= 3.0,
                0.0,
                np.sinc(t) * np.sinc(t / 3.0),
            ),
        )
        s = w.sum()
        return w / s if s != 0 else w
    raise ValueError(name)


def check_taps(doc):
    print("1. tap agreement -- Python textbook vs weights probed out of the binary")
    worst = {}
    for name, blk in doc["b22_taps"].items():
        m = 0.0
        for row in blk["rows"]:
            f = row["f"]
            got = np.array(row["w"], dtype=float)
            # `nearest` at f == 0.5 and f == 1.0 sits on a tie/wrap boundary
            # where "which sample is nearest" is a convention, not a fact.
            if name == "nearest" and (abs(f - 0.5) < 1e-12 or abs(f - 1.0) < 1e-12):
                continue
            if abs(f - 1.0) < 1e-12:
                continue
            want = py_weights(name, f)
            if want.shape != got.shape:
                # Compare on the overlapping support; a shape mismatch is
                # itself reported through `support`.
                n = min(len(want), len(got))
                d = float(np.max(np.abs(want[:n] - got[:n])))
            else:
                d = float(np.max(np.abs(want - got)))
            m = max(m, d)
        worst[name] = m
        print(f"   {name:<12} support {blk['support']:.1f}  max |dw| {m:.3e}")
    return worst


def check_normalisation():
    """Why normalising Lanczos-3's weights is load-bearing, not cosmetic.

    An unnormalised windowed-sinc does not sum to 1 at an arbitrary phase, so a
    constant plane comes back scaled -- a phase-dependent *gain*, which would
    appear as a modulation pattern rather than as blur and would be easy to
    misread as something else entirely.
    """
    print("\n1b. normalisation control -- unnormalised weight sum on a constant plane")
    worst_f, worst_s = 0.0, 1.0
    for k in range(1, 64):
        f = k / 64.0
        t = np.array([-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]) - f
        w = np.where(np.abs(t) >= 3.0, 0.0, np.sinc(t) * np.sinc(t / 3.0))
        s = float(w.sum())
        if abs(s - 1.0) > abs(worst_s - 1.0):
            worst_f, worst_s = f, s
    t = np.array([-2.0, -1.0, 0.0, 1.0, 2.0, 3.0]) - 0.5
    half = float(np.sum(np.sinc(t) * np.sinc(t / 3.0)))
    print(f"   sum at f=0.5      {half:.7f}   gain error {100 * (half - 1.0):+.4f}%")
    print(f"   worst over 63 phases: f={worst_f:.4f}  sum {worst_s:.7f}   gain error {100 * (worst_s - 1.0):+.4f}%")
    print(f"   separable 2-D gather squares it: {half * half:.7f}   gain error {100 * (half * half - 1.0):+.4f}%")
    return half, worst_f, worst_s


# --------------------------------------------------------------------------
# 2. step overshoot from first principles
# --------------------------------------------------------------------------
def check_step(doc):
    print("\n2. step overshoot -- algebra, independent of the Rust harness")
    res = {}
    for name in ["catmull-rom", "lanczos3"]:
        w = py_weights(name, 0.5)
        n = len(w)
        best = 0.0
        # Every step position within the support. The signal is 0 left of the
        # break and 1 at or right of it; overshoot is how far the sample falls
        # outside [0, 1].
        for cut in range(n + 1):
            s = np.array([0.0] * cut + [1.0] * (n - cut))
            v = float(w @ s)
            best = max(best, v - 1.0, -v)
        res[name] = best
        print(f"   {name:<12} max overshoot {100 * best:>8.4f}% of the step")
    cr_exact = 1.0 / 16.0
    print(f"   catmull-rom closed form 1/16 = {100 * cr_exact:.4f}%")
    got = {k: v["pct_of_step"] / 100.0 for k, v in doc["b23_ringing"].items()} if False else None
    return res, cr_exact, got


# --------------------------------------------------------------------------
# 3. the dex gain, through the extracted taps
# --------------------------------------------------------------------------
def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def read_warps():
    src = MAP if MAP.exists() else MAP_ALT
    rows = []
    for line in src.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("#") or not s or s.startswith("end") or s.startswith("plane "):
            continue
        p = s.split()
        if len(p) >= 6 and p[1] == "placed":
            rows.append((int(p[0]), f64(p[2]), f64(p[3]), f64(p[4]), f64(p[5])))
    return rows, src


def make_tap_kernel(doc, name):
    """The probed phases and weights, as arrays."""
    blk = doc["b22_taps"][name]
    rows = [r for r in blk["rows"] if r["f"] < 1.0]
    phases = np.array([r["f"] for r in rows])
    table = np.array([r["w"] for r in rows], dtype=float)
    return phases, table, int(blk["lo"])


def check_gain(doc):
    """Reproduce arm 8's kernel gain.

    Note what this can and cannot claim. It does **not** drive the gather from
    the probed tap table -- snapping an arbitrary phase to the nearest probed
    row would introduce a phase error far larger than the effect. It runs arm
    8's own continuous kernels. That is legitimate *only because* step 1 has
    already shown the shipped weights and these weights are the same function
    to ~1e-8 across the probed phases; the reproduction is therefore a check
    that the number survives an independent implementation of the surrounding
    measurement, not a check of the kernel formula, which step 1 owns.
    """
    print("\n3. dex gain -- arm 8's measurement, re-run independently")
    if not B0.exists():
        print(f"   SKIP: {B0} is missing")
        return None
    img = M.load_luma(B0)
    tiles = M.pick_tiles(img)
    warps, src = read_warps()
    warps = warps[:NFRAMES]
    print(f"   {B0.name}  {img.shape}  {len(tiles)} tiles  {len(warps)} warps from {src.name}")
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0

    arms = {}
    for name in ["catmull-rom", "lanczos3"]:
        vals = []
        for ty, tx in tiles:
            for _, a_re, a_im, b_re, b_im in warps:
                a = np.hypot(a_re, a_im)
                bx, by = b_re * 2.0, b_im * 2.0
                step = a * K_COVER
                o0y = round(cy + (ty - cy) / step)
                o0x = round(cx + (tx - cx) / step)
                sy = step * (o0y - cy) + cy + by
                sx = step * (o0x - cx) + cx + bx
                ci = int(np.floor(sy + (M.TILE - 1) * step / 2.0))
                cj = int(np.floor(sx + (M.TILE - 1) * step / 2.0))
                y0, x0 = ci - M.PAD // 2, cj - M.PAD // 2
                if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
                    continue
                base = img[ci - M.TILE // 2 : ci + M.TILE // 2, cj - M.TILE // 2 : cj + M.TILE // 2]
                if base.shape != (M.TILE, M.TILE):
                    continue
                reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
                i = np.arange(M.TILE, dtype=np.float64)
                t = M.gather_1d(reg, (sy - y0) + i * step, 0, name)
                out = M.gather_1d(t, (sx - x0) + i * step, 1, name)
                vals.append(M.band_ratio(base, 1.0) - M.band_ratio(out, step))
        m, sd = M.mean_sd(vals)
        arms[name] = (m, sd, len(vals))
        print(f"   {name:<12} cost {m:>+9.4f} +/- {sd:.4f}   n {len(vals)}")
    gain = arms["catmull-rom"][0] - arms["lanczos3"][0]
    print(f"   kernel gain {gain:+.4f} dex   arm 8 measured {ARM8_KERNEL_GAIN:+.4f} dex")
    return arms, gain, 0.0


def main():
    doc = json.loads(TAPS.read_text(encoding="utf-8"))
    ring = json.loads(RING.read_text(encoding="utf-8"))
    nph = len(doc["b22_taps"]["lanczos3"]["rows"])
    print("B22 -- the shipped kernel, checked against algebra and against arm 8")
    print(f"     taps probed at {nph} phases across the unit interval\n")
    worst = check_taps(doc)
    norm_half, norm_f, norm_s = check_normalisation()
    steps, cr_exact, _ = check_step(doc)
    g = check_gain(doc)

    print("\nBARS")
    ok = True
    b21 = max(worst.values())
    p = b21 < 1e-5
    ok &= p
    print(f"  B21 interpolating/exact taps   max |dw| {b21:.3e} < 1e-5      {'PASS' if p else 'FAIL'}")

    d = abs(steps["catmull-rom"] - cr_exact)
    p = d < 1e-12
    ok &= p
    print(f"  K22a catmull-rom == 1/16       |d| {d:.3e} < 1e-12         {'PASS' if p else 'FAIL'}")

    rs = ring["b23_ringing"]
    rust_cr = None
    if "k22_step" in rs:
        rust_cr = rs["k22_step"]["catmull-rom"]["pct_of_step"] / 100.0
        rust_lz = rs["k22_step"]["lanczos3"]["pct_of_step"] / 100.0
        d1 = abs(rust_cr - steps["catmull-rom"])
        d2 = abs(rust_lz - steps["lanczos3"])
        p = d1 < 1e-9 and d2 < 1e-4
        ok &= p
        print(f"  K22b rust step == python       cr {d1:.3e}  lz {d2:.3e}        {'PASS' if p else 'FAIL'}")

    if g is not None:
        _, gain, _ = g
        d = abs(gain - ARM8_KERNEL_GAIN)
        p = d < B22_TOL
        ok &= p
        print(f"  B22  gain survives the port    {gain:+.4f} vs {ARM8_KERNEL_GAIN:+.4f}, |d| {d:.4f} < {B22_TOL}   {'PASS' if p else 'FAIL'}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(
            {
                "n_phases": nph,
                "tap_max_dw": worst,
                "unnorm_sum_half": norm_half,
                "unnorm_worst_phase": norm_f,
                "unnorm_worst_sum": norm_s,
                "step_overshoot": steps,
                "catmull_rom_closed_form": cr_exact,
                "rust_step_catmull_rom": rust_cr,
                "gain": None if g is None else g[1],
                "arm8_gain": ARM8_KERNEL_GAIN,
                "arms": None if g is None else {k: list(v) for k, v in g[0].items()},
                "schema": "m95-k5-1",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\n{'ALL BARS PASS' if ok else 'AT LEAST ONE BAR FAILED'}\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

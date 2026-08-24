"""K17 -- re-price "crop instead of upsample" against a PINNED 299-frame solve.

The orchestrator has re-raised, as facts 1400/1402 and "the cheapest real
sharpness gain on the table", the proposal M95 arm 5 already priced: stop
stretching the coverage-cropped field back to sensor dimensions, emit the
cropped region at its native sampling instead.

Arm 5 registered bars for exactly this in experiments/M95-coverage/
PRE-REGISTRATION.md *before* running, and reported the fix DEAD. This script
re-prints the decisive comparison from code run in this session, because a
number recalled from an earlier artifact is not a measurement.

WHY IT HAD TO BE RE-RUN RATHER THAN CITED
-----------------------------------------
x8_fix.py reads D:\\personal\\macro\\bee-3-cpl\\warpmap.txt with a fallback to
the quarantined copy. That original is gone (quarantined), and the quarantined
`bee-3-cpl--warpmap.txt` holds an EIGHT-frame solve under a different stack
digest. Re-running x8 today would silently read 8 frames where arm 5 read 299.
This script takes a pinned 299-frame sidecar and HARD-ERRORS on any other
frame count, digest or reference frame.

WHAT K0 CAUGHT ON THE FIRST RUN, AND WHY THE SIDECAR CHANGED
-----------------------------------------------------------
The first run of this script FAILED K0: it was pointed at a pinned solve whose
reference frame is 0, and derived k = 0.997438 against the tool's 0.9315.
k17b_kdiag.py then derived k for every available bee-3-cpl solve and found six
independent `reference 149` solves all giving k = 0.931464, agreeing with the
tool to 3.6e-5. The re-implementation was right; the sidecar was unrepresentative.

That is itself the finding: **k is a function of the reference frame.** A
reference at one end of the focus bracket needs a 0.26% crop; a reference in the
middle needs 6.85%, a 26x difference. The merge's automatic path uses
merge_reference(n) = n/2, so the shipped render is the 6.85% one, and the pinned
sidecar used here is now a reference-149 solve to match.

BARS
----
Reused verbatim from experiments/M95-coverage/PRE-REGISTRATION.md, registered
before arm 5 ran and long before this request existed:

WHAT IS MEASURED
----------------
  NOW  : source = k * a * (p - c) + c + b   -- what fit_to_cover ships today
  FIX  : source =     a * (p - c) + c + b   -- the proposal, native sampling
  SNAP : integer translation, unit scale    -- the geometry floor

k is NOT taken from the tool's printed line. It is re-derived here by
re-implementing fit_to_cover's bisection from the placements, and cross-checked
against the printed 0.9315.

  B2-SHIPS  the crop ships if  cost(FIX) < cost(NOW) - 0.10 dex
  B2-DEAD   the crop is dead if cost(FIX) > cost(NOW) - 0.03 dex
  K1 NULL   identity warp, no coverage: |cost| < 0.005 dex
  K3 POS    a planted sigma=0.30 px Gaussian must register >= 0.15 dex
            (discipline 594: the instrument must be shown saying otherwise)

Registered NOW, before this script was run, for the claim that is new in this
request -- "a global non-integer scale means no output pixel is ever a
pass-through, so the resampler kernel is applied continuously to every pixel":

  K0 DERIVE my re-derived k must match the tool's printed 0.9315 within 0.001,
            else my re-implementation is wrong and I report no arm numbers.
  P1 POWER  SNAP must place >= 95% of sample positions within 0.05 px of an
            integer. SNAP is integer-by-construction, so if the phase metric
            cannot see that, it cannot see anything and I report no phase
            numbers. This is the phase metric's positive control.
  P2 CLAIM  the composition claim is SUPPORTED if FIX puts >= 50% of positions
            within 0.05 px of an integer, and REFUTED if it puts < 15% there
            (uniform phase gives 10%). Between the two is partial support and
            is reported as such.

Registered NOW, before running, for the lever k17b exposed:

  R5 REF    the reference frame is a resampling lever if the NOW arm costs at
            least 0.03 dex less on the reference-0 solve than on the
            reference-149 solve; it is not a lever if the two are within
            0.03 dex. This prices the GATHER only -- both arms are scored
            against the same unresampled base -- and says nothing about which
            reference registers more accurately, which needs its own arm.
"""
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "M95-coverage" / "src"))
import m95cov as M  # noqa: E402

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
PIN = Path(r"C:\dev\strehl-out\M95-crop\bee-3-cpl-ref149.warpmap.txt")
PIN_REF0 = Path(
    r"C:\dev\strehl-out\M95-pin\experiments\M86-alignment\out\warpmap-bee-3-cpl.txt"
)
OUT = Path(__file__).resolve().parents[1] / "out" / "k17_crop.json"

WANT_FRAMES = 299
WANT_DIGEST = "8d023c0fe355d109"
WANT_REF = 149
TOOL_PRINTED_K = 0.9315
MARGIN = 3.0
NFRAMES = 24
NEAR_INT = 0.05


def f64(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def read_map(path, want_ref=None):
    """Parse a sidecar, hard-erroring unless it is the pinned 299-frame solve."""
    if not path.exists():
        raise SystemExit(f"PINNED SIDECAR MISSING: {path}")
    plane = digest = None
    declared = reference = None
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith("plane "):
            plane = tuple(int(v) for v in s.split()[1].split("x"))
        elif s.startswith("stack-digest "):
            digest = s.split()[1]
        elif s.startswith("frames "):
            declared = int(s.split()[1])
        elif s.startswith("reference "):
            reference = int(s.split()[1])
        elif not s or s.startswith("#") or s.startswith("end"):
            continue
        else:
            p = s.split()
            if len(p) >= 6 and p[1] == "placed":
                rows.append((int(p[0]), f64(p[2]), f64(p[3]), f64(p[4]), f64(p[5])))
    if digest != WANT_DIGEST:
        raise SystemExit(f"WRONG STACK: digest {digest} != {WANT_DIGEST}")
    if declared != WANT_FRAMES or len(rows) != WANT_FRAMES:
        raise SystemExit(
            f"WRONG BRACKET: declared {declared}, {len(rows)} placed rows, "
            f"want {WANT_FRAMES}. Refusing to measure on a partial solve."
        )
    if want_ref is not None and reference != want_ref:
        raise SystemExit(
            f"WRONG REFERENCE: sidecar reference {reference}, want {want_ref}. "
            f"k depends on the reference frame, so this solve is not the one "
            f"the merge renders."
        )
    return plane, rows, digest, reference


def derive_k(plane, rows, margin=MARGIN):
    """Re-implement fit_to_cover's bisection from the placements.

    s.then(t) with s a pure scale k about the centre gives
    a = k*t.a, b = t.b, so source = k*t.a*(p - c) + t.b + c.
    """
    w, h = float(plane[0]), float(plane[1])
    cx, cy = w * 0.5, h * 0.5
    a = np.array([complex(r[1], r[2]) for r in rows])
    b = np.array([complex(r[3], r[4]) for r in rows])
    corners = np.array(
        [complex(0.0, 0.0), complex(w - 1.0, 0.0),
         complex(0.0, h - 1.0), complex(w - 1.0, h - 1.0)]
    )
    c = complex(cx, cy)

    def covers(k):
        q = k * a[:, None] * (corners[None, :] - c) + b[:, None] + c
        return bool(
            np.all(
                (q.real >= margin)
                & (q.imag >= margin)
                & (q.real <= w - 1.0 - margin)
                & (q.imag <= h - 1.0 - margin)
            )
        )

    if covers(1.0):
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if covers(mid):
            lo = mid
        else:
            hi = mid
    return lo


def arm(img, tiles, warps, k, use_cover, snap=False):
    """Gather every (tile, frame) pair; return costs, steps and phase fractions."""
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    kc = k if use_cover else 1.0
    costs, steps, phase = [], [], []
    for ty, tx in tiles:
        for _, a_re, a_im, b_re, b_im in warps:
            if snap:
                a, bx, by = 1.0, round(b_re * 2.0), round(b_im * 2.0)
            else:
                a, bx, by = np.hypot(a_re, a_im), b_re * 2.0, b_im * 2.0
            step = a * kc
            o0y = round(cy + (ty - cy) / step)
            o0x = round(cx + (tx - cx) / step)
            sy = step * (o0y - cy) + cy + by
            sx = step * (o0x - cx) + cx + bx
            ci = int(np.floor(sy + (M.TILE - 1) * step / 2.0))
            cj = int(np.floor(sx + (M.TILE - 1) * step / 2.0))
            y0, x0 = ci - M.PAD // 2, cj - M.PAD // 2
            if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
                continue
            reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
            i = np.arange(M.TILE, dtype=np.float64)
            vy = (sy - y0) + i * step
            vx = (sx - x0) + i * step
            t = M.gather_1d(reg, vy, 0)
            g = M.gather_1d(t, vx, 1)
            base = img[
                ci - M.TILE // 2 : ci + M.TILE // 2, cj - M.TILE // 2 : cj + M.TILE // 2
            ]
            costs.append(M.band_ratio(base, 1.0) - M.band_ratio(g, step))
            steps.append(step)
            for v in (vy, vx):
                d = np.abs(v - np.round(v))
                phase.append(float(np.mean(d <= NEAR_INT)))
    return np.array(costs), np.array(steps), np.array(phase)


def main():
    if not B0.exists():
        raise SystemExit(f"MISSING BASE IMAGE: {B0}")
    plane, rows, digest, reference = read_map(PIN, want_ref=WANT_REF)
    img = M.load_luma(B0)
    tiles = M.pick_tiles(img)
    idx = np.linspace(0, len(rows) - 1, NFRAMES).round().astype(int)
    warps = [rows[i] for i in idx]

    print("=" * 72)
    print("K17  crop-instead-of-upsample, re-priced on a pinned solve")
    print("=" * 72)
    print(f"  base image      : {B0.name}  {img.shape[1]}x{img.shape[0]}")
    print(f"  sidecar         : {PIN}")
    print(f"  stack digest    : {digest}   reference frame: {reference}")
    print(f"  placed frames   : {len(rows)}  (plane {plane[0]}x{plane[1]})")
    print(f"  frames sampled  : {NFRAMES}      tiles: {len(tiles)}")

    k = derive_k(plane, rows)
    dk = abs(k - TOOL_PRINTED_K)
    ok_k = dk < 0.001
    print()
    print("--- K0 DERIVE: k re-derived from the placements, not read off ---")
    print(f"  fit_to_cover bisection, margin {MARGIN}  ->  k = {k:.6f}")
    print(f"  tool printed                              k = {TOOL_PRINTED_K:.6f}")
    print(f"  |difference| {dk:.6f}   bar < 0.001   {'PASS' if ok_k else 'FAIL'}")
    print(f"  field of view kept {100 * k:.2f}%, upsampled by 1/k = {1 / k:.4f}x")
    res = {
        "digest": digest,
        "frames": len(rows),
        "k_derived": k,
        "k_tool": TOOL_PRINTED_K,
        "K0_derive_pass": ok_k,
    }
    if not ok_k:
        print("\nK0 FAILED -- my re-implementation disagrees with the tool.")
        print("Reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    print()
    print("--- CONTROLS ---")
    ident = [(0, 1.0, 0.0, 0.0, 0.0)]
    c_id, _, _ = arm(img, tiles, ident, k, use_cover=False)
    ok_null = abs(c_id.mean()) < 0.005
    print(f"  K1 NULL   identity warp, no coverage  {c_id.mean():+.6f} dex  "
          f"bar |x|<0.005  {'PASS' if ok_null else 'FAIL'}")
    blurred = [M.band_ratio(
        img[ty : ty + M.TILE, tx : tx + M.TILE], 1.0
    ) - M.band_ratio(
        M.fourier_blur(img[ty : ty + M.TILE, tx : tx + M.TILE], 0.30), 1.0
    ) for ty, tx in tiles]
    k3 = float(np.mean(blurred))
    ok_pos = k3 >= 0.15
    print(f"  K3 POS    planted sigma=0.30 px blur  {k3:+.6f} dex  "
          f"bar >=0.15     {'PASS' if ok_pos else 'FAIL'}")
    res["K1_null"] = float(c_id.mean())
    res["K3_positive"] = k3
    if not (ok_null and ok_pos):
        print("\nCONTROL FAILED -- reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    c_ic, _, _ = arm(img, tiles, ident, k, use_cover=True)
    print(f"  K6 COVER  identity warp, coverage on  {c_ic.mean():+.6f} dex  "
          f"(the coverage scale acting alone)")
    res["K6_cover_alone"] = float(c_ic.mean())

    print()
    print("--- THE ARMS ---")
    out_rows = []
    for name, uc, sn, desc in (
        ("NOW", True, False, "coverage scale folded in, output 7032x4688"),
        ("FIX", False, False, "no coverage scale, output ~6548x4366"),
        ("SNAP", False, True, "integer translation, unit scale (floor)"),
    ):
        c, st, ph = arm(img, tiles, warps, k, use_cover=uc, snap=sn)
        sem = float(c.std(ddof=1) / np.sqrt(len(c)))
        out_rows.append((name, c.mean(), sem, len(c), st.mean(), ph.mean(), desc))
        res[name] = {
            "cost_dex": float(c.mean()),
            "sem": sem,
            "n": int(len(c)),
            "mean_step": float(st.mean()),
            "near_int_frac": float(ph.mean()),
        }
    print(f"  {'arm':<5} {'cost (dex)':>11} {'sem':>7} {'n':>5} {'step':>8} "
          f"{'near-int':>9}  what")
    for name, m, s, n, st, ph, desc in out_rows:
        print(f"  {name:<5} {m:>+11.4f} {s:>7.4f} {n:>5} {st:>8.4f} "
              f"{100 * ph:>8.2f}%  {desc}")

    now = res["NOW"]["cost_dex"]
    fix = res["FIX"]["cost_dex"]
    recovery = now - fix
    ships = recovery > 0.10
    dead = recovery < 0.03
    print()
    print("--- B2 (bars registered in M95-coverage/PRE-REGISTRATION.md) ---")
    print(f"  cost(NOW) {now:+.4f}   cost(FIX) {fix:+.4f}")
    print(f"  the crop recovers {recovery:+.4f} dex")
    print(f"  B2-SHIPS  recovery > +0.10 dex  ->  "
          f"{'SHIPS' if ships else 'DOES NOT SHIP'}")
    print(f"  B2-DEAD   recovery < +0.03 dex  ->  "
          f"{'DEAD' if dead else 'not dead'}")
    res["recovery_dex"] = recovery
    res["B2_ships"] = bool(ships)
    res["B2_dead"] = bool(dead)

    p_now = res["NOW"]["near_int_frac"]
    p_fix = res["FIX"]["near_int_frac"]
    p_snap = res["SNAP"]["near_int_frac"]
    ok_p1 = p_snap >= 0.95
    print()
    print("--- P1/P2: does removing the scale restore pass-through? ---")
    print(f"  uniform phase would give                {100 * 2 * NEAR_INT:.2f}%")
    print(f"  P1 POWER  SNAP near-integer   {100 * p_snap:>7.2f}%  bar >=95%  "
          f"{'PASS' if ok_p1 else 'FAIL'}")
    res["P1_power_pass"] = bool(ok_p1)
    if not ok_p1:
        print("  P1 FAILED -- reporting no phase numbers.")
        res["P2"] = "void"
    else:
        print(f"            NOW  near-integer   {100 * p_now:>7.2f}%")
        print(f"            FIX  near-integer   {100 * p_fix:>7.2f}%")
        if p_fix >= 0.50:
            verdict = "SUPPORTED"
        elif p_fix < 0.15:
            verdict = "REFUTED"
        else:
            verdict = "PARTIAL"
        print(f"  P2 CLAIM  'no output pixel is ever a pass-through' -> {verdict}")
        res["P2"] = verdict

    print()
    print("--- R5: is the reference frame a resampling lever? ---")
    p0, r0, _, ref0 = read_map(PIN_REF0, want_ref=0)
    k0 = derive_k(p0, r0)
    w0 = [r0[i] for i in np.linspace(0, len(r0) - 1, NFRAMES).round().astype(int)]
    c0, s0, ph0 = arm(img, tiles, w0, k0, use_cover=True)
    ref149 = res["NOW"]["cost_dex"]
    d = ref149 - float(c0.mean())
    print(f"  reference {reference:>3}  k {k:.6f}  crop {100 * (1 - k):.2f}%  "
          f"cost {ref149:+.4f} dex  step {res['NOW']['mean_step']:.4f}")
    print(f"  reference {ref0:>3}  k {k0:.6f}  crop {100 * (1 - k0):.2f}%  "
          f"cost {c0.mean():+.4f} dex  step {s0.mean():.4f}")
    if d >= 0.03:
        r5 = "LEVER"
    elif abs(d) < 0.03:
        r5 = "NOT A LEVER"
    else:
        r5 = "LEVER, REVERSED (reference 0 is WORSE)"
    print(f"  difference {d:+.4f} dex   bar |x|<0.03 -> not a lever   =>  {r5}")
    print("  scope: this prices the GATHER only. It does not say which")
    print("  reference registers more accurately, which needs its own arm.")
    res["R5"] = {
        "ref149_cost": ref149,
        "ref0_cost": float(c0.mean()),
        "ref0_k": k0,
        "ref0_step": float(s0.mean()),
        "difference_dex": d,
        "verdict": r5,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

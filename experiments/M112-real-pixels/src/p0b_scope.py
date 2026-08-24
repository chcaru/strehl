r"""M112 Phase 0b -- is the no-go specific to the owner's deep bracket, or corpus-wide?

Phase 0 measured the crop's recovery on `bee-3-cpl` and got nothing. That stack
has 6.05 px mean per-frame displacement (M95 `w0_warpstats`), so its gather is
already deeply non-integer and removing `k` cannot make it integer.

A SHALLOW stack is the case that could still clear the bar: if the per-frame
warps were near-identity, removing `k` would leave a near-no-op. M104 P3
measured 97.0% of `flat-on-ruler-cpl`'s deficit to be the coverage resample --
on a stack whose warps barely move -- so the possibility is live and must be
tested rather than argued away.

Same imported arithmetic as Phase 0 (`x8_fix.arm`, `m95cov.band_ratio`), same
40 interior tiles, same band. The only new code is a port of `fit_to_cover`'s
corner bisection, needed because `k` differs per stack and M95 hard-coded it.

GATE ON THE PORT (rule 21 -- gate a computed constant against an independently
predicted value): the port must return `k = 0.9315` for `bee-3-cpl`, which was
measured twice by routes independent of this code -- the tool's own printout
(fact 1400) and a photograph of a millimetre ruler (fact 1289, M98 P10) -- and
`k ~ 0.9708` for `flat-on-ruler-cpl` (M104 P1, `1/k = 1.030078`). If the port
misses those, no scan number is reported.

NOTE ON WHAT IS AND IS NOT TRANSFERRED. `arm()` prices a *mapping*: it gathers
tiles of one base image through each frame's similarity. Applying another
stack's warp geometry to `bee-3-cpl`'s texture therefore prices THAT GEOMETRY,
not that stack's own pixels. That is exactly what M95's committed harness does,
and it is the right isolation here because the question is about the geometry.
Labelled accordingly in the report.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
M95SRC = REPO / "experiments" / "M95-coverage" / "src"
OUT = HERE.parents[1] / "out"

sys.path.insert(0, str(M95SRC))
import m95cov as M          # noqa: E402
import x8_fix as X          # noqa: E402

BASE = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
MARGIN = 3.0                # align_cmd::cover_or_explain passes 3.0

STACKS = {
    "bee-3-cpl":            r"C:\dev\strehl-out\M106\warpmap-corpus-snapshot.txt",
    "flat-on-ruler-cpl":    r"C:\dev\strehl-out\M97\warpmap-ruler.txt",
    "tweezers-cpl":         r"C:\dev\strehl-out\ORCH-quarantine-sidecars\tweezers-cpl--warpmap.txt",
    "leaf-2-cpl":           r"C:\dev\strehl-out\ORCH-quarantine-sidecars\leaf-2-cpl--warpmap.txt",
    "foam":                 r"C:\dev\strehl-out\ORCH-quarantine-sidecars\foam--warpmap.txt",
    "lavendar-cpl":         r"C:\dev\strehl-out\ORCH-quarantine-sidecars\lavendar-cpl--warpmap.txt",
    "flowers-cpl":          r"C:\dev\strehl-out\ORCH-quarantine-sidecars\flowers-cpl--warpmap.txt",
    "lead-1-cpl":           r"C:\dev\strehl-out\ORCH-quarantine-sidecars\lead-1-cpl--warpmap.txt",
    "flower-bud-alone-cpl": r"C:\dev\strehl-out\ORCH-quarantine-sidecars\flower-bud-alone-cpl--warpmap.txt",
}

# k values obtained by routes independent of this file
K_ANCHOR = {"bee-3-cpl": (0.9315, 1e-4, "fact 1289/1400: tool printout + ruler photograph"),
            "flat-on-ruler-cpl": (0.970813, 2e-3, "M104 P1: 1/k = 1.030078")}


def read_map(path):
    """Header fields plus every placed row, as (idx, a_re, a_im, b_re, b_im)."""
    X.MAP = Path(path)
    X.MAP_ALT = Path(path)
    plane, rows, _ = X.read_warps()
    head = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        for key in ("stack-name", "frames", "reference", "stack-digest"):
            if line.startswith(key + " "):
                head[key] = line.split(None, 1)[1].strip()
    return plane, rows, head


def fit_to_cover_k(plane, rows, margin=MARGIN):
    """Port of `align_cmd::fit_to_cover`'s bisection. Returns k.

    `s.then(t)` for a pure scale `s` about the centre gives composed
    `a = k*a_t`, `b = b_t` (align.rs: `then` is `a: self.a*other.a`,
    `b: other.a*self.b + other.b`, and `s.b = 0`). `apply_at` maps
    `p -> a*(p - c) + c + b` with `c = (w/2, h/2)`.
    """
    w, h = float(plane[0]), float(plane[1])
    cx, cy = w * 0.5, h * 0.5
    corners = [(0.0, 0.0), (w - 1.0, 0.0), (0.0, h - 1.0), (w - 1.0, h - 1.0)]
    a = np.array([complex(r[1], r[2]) for r in rows])
    b = np.array([complex(r[3], r[4]) for r in rows])

    def covers(k):
        for (x, y) in corners:
            p = complex(x - cx, y - cy)
            q = (k * a) * p + b
            sx, sy = q.real + cx, q.imag + cy
            if not (np.all(sx >= margin) and np.all(sy >= margin)
                    and np.all(sx <= w - 1.0 - margin)
                    and np.all(sy <= h - 1.0 - margin)):
                return False
        return True

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


def phase_stats(rows):
    """Fraction of frames whose FIX-arm sampling is effectively integer.

    Under FIX the step is |a| and the offset is b (doubled into render px, as
    `arm()` does). 'Effectively integer' = scale within 1e-4 of 1 AND both
    translations within 0.05 px of an integer -- M95 `w0_warpstats`'s criterion.
    """
    n_int = 0
    for _, a_re, a_im, b_re, b_im in rows:
        a = abs(complex(a_re, a_im))
        bx, by = b_re * 2.0, b_im * 2.0
        if (abs(a - 1.0) < 1e-4
                and abs(bx - round(bx)) < 0.05 and abs(by - round(by)) < 0.05):
            n_int += 1
    return n_int / len(rows)


def cost(img, tiles, warps, use_cover):
    c, st = X.arm(img, tiles, warps, use_cover=use_cover)
    return (float(c.mean()), float(c.std(ddof=1) / np.sqrt(len(c))),
            int(len(c)), float(st.mean()))


def main():
    img = M.load_luma(BASE)
    tiles = M.pick_tiles(img)
    res = {"gate": {}, "stacks": {}}

    print("=== GATE: does the fit_to_cover port reproduce independently "
          "measured k? ===")
    ok = True
    for name, (k_exp, tol, src) in K_ANCHOR.items():
        plane, rows, head = read_map(STACKS[name])
        k = fit_to_cover_k(plane, rows)
        good = abs(k - k_exp) <= tol
        ok &= good
        res["gate"][name] = {"k_port": k, "k_expected": k_exp, "tol": tol,
                             "pass": bool(good), "source": src}
        print(f"  {name:<20} port k={k:.6f}  expected {k_exp:.6f} "
              f"+/-{tol:g}  {'PASS' if good else 'FAIL'}   [{src}]")
    if not ok:
        print("\nGATE FAILED -- the port does not reproduce measured k. "
              "No scan numbers reported.")
        (OUT / "p0b.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    print("\n=== crop recovery per stack, 40 interior tiles, 0.30-0.48 cyc/px ===")
    print(f"{'stack':<22} {'N':>4} {'k':>8} {'1/k-1':>7} {'int%':>6} "
          f"{'NOW':>8} {'FIX':>8} {'recovery':>9}  verdict")
    for name, path in STACKS.items():
        if not Path(path).exists():
            print(f"{name:<22} MISSING")
            continue
        plane, rows, head = read_map(path)
        k = fit_to_cover_k(plane, rows)
        X.K_COVER = k
        now = cost(img, tiles, rows, use_cover=True)
        fix = cost(img, tiles, rows, use_cover=False)
        rec = now[0] - fix[0]
        frac_int = phase_stats(rows)
        verdict = ("SHIPS" if rec > 0.10 else "DEAD" if rec < 0.03 else "partial")
        res["stacks"][name] = {
            "sidecar": path, "frames": head.get("frames"),
            "reference": head.get("reference"), "plane": list(plane),
            "k": k, "enlargement_pct": 100.0 * (1.0 / k - 1.0),
            "frac_frames_integer_phase_under_FIX": frac_int,
            "NOW": {"cost_dex": now[0], "sem": now[1], "n": now[2], "step": now[3]},
            "FIX": {"cost_dex": fix[0], "sem": fix[1], "n": fix[2], "step": fix[3]},
            "recovery_dex": rec, "verdict": verdict,
        }
        print(f"{name:<22} {len(rows):>4} {k:>8.5f} {100*(1/k-1):>6.2f}% "
              f"{100*frac_int:>5.1f}% {now[0]:>+8.4f} {fix[0]:>+8.4f} "
              f"{rec:>+9.4f}  {verdict}")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "p0b.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT / 'p0b.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

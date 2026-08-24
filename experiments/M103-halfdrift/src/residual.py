"""B3-TWOSIDED -- an end-to-end residual instrument that works above 1.0.

Why this file exists
--------------------
M97 built the absolute end-to-end check this milestone is judged on, and its
baseline reading (150.2 plane px, 50.2% of the drift removed) reproduces exactly.
But the search inside it is **structurally one-sided**, and M103 measured that:

    best_scale trials a candidate scale s by forming `zoom(b_raw, 1.0/s)`,
    and `zoom(img, t) = gather(img, 1/t)`, so the trial image is
    `gather(b_raw, s)`. For any trial s > 1 that calls `gather` with a > 1.

`gather` samples with `mode="constant", cval=nan`, and `prep` turns those NaNs
into zeros. For a > 1 the sample lattice runs off the input, so every trial above
1.0 is scored with a black rim eating into the frame. Its NCC is depressed by
construction, so the argmax can never land there. M97's own control already
reports this branch as broken -- `GATHER ROUND-TRIP a=1.08 -> 118.1 plane px FAIL`
against `a=0.92 -> 7.3 px OK` -- but the connection to `best_scale`'s own trials
was not drawn, and the instrument's two plant controls (0.940, 0.860) both sit
below 1.0, so nothing in the suite ever exercised the failing side.

MEASURED consequence: sweeping M97's `gain` hook on the baseline sidecar, the
residual falls monotonically to 3.3 plane px at gain 1.909 and then reads
*exactly* 0.99997 / 0.1 px at both gain 2.000 and gain 2.200 -- two materially
different sidecars returning bit-identical residuals, and identical to the SELF
arm. That is a clip, not a measurement. It matters here and nowhere else in the
corpus, because a *correctly* solved sidecar over-shoots slightly and lands above
1.0, which is precisely the side that cannot be seen.

Note this also contaminates the instrument's own plants: `zoom(g0, 0.860)` is
`gather(g0, 1.163)`, on the broken branch. Their reported errors (-0.0015) are
partly the plant, not the estimator.

What this does differently
--------------------------
1. Trials are always formed on the clean branch. To compare content at scale 1
   against content at scale s, either shrink b (gather arg s) or shrink a
   (gather arg 1/s); exactly one of those is <= 1, and this picks it.
2. Plants are built as a *pair*, `gather(img, min(1,s))` against
   `gather(img, min(1,1/s))`, whose content ratio is exactly s with both gather
   arguments <= 1. This also resamples both sides, so the plant does not
   introduce the sharp-against-blurred asymmetry that facts 18/45 describe --
   discipline 615: the control must not perturb the mechanism it measures through.
3. Controls are swept on both sides of 1.0, and the original `best_scale` is run
   beside the corrected one on the same inputs so the clip is visible rather than
   asserted.

Everything geometric is imported from signtest itself, unmodified, so this cannot
drift from the deciding instrument.

    python src/residual.py control  <out.json>
    python src/residual.py sidecar  <sidecar> <out.json> <last> [gain]
"""

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "M97-warped-merge", "src"))

import signtest as S  # noqa: E402

R_PLANE = 0.5 * float(np.hypot(3512.0, 2344.0))


def shrink(img, alpha):
    """`gather` restricted to the branch M97's round-trip control passes."""
    if alpha > 1.0 + 1e-12:
        raise AssertionError(f"refusing gather on the contaminated branch: a={alpha}")
    return S.gather(img, complex(alpha, 0.0), 0j, 1.0)


def trial_pair(a_raw, b_raw, s):
    """Bring `a` and `b` to a common scale under the hypothesis b = s * a."""
    if s <= 1.0:
        return a_raw, shrink(b_raw, s)
    return shrink(a_raw, 1.0 / s), b_raw


def best_scale_2s(a_raw, b_raw, lo=0.70, hi=1.35, n=61, refine=3):
    """Two-sided scale search. Same ladder as `best_scale`, clean trials."""
    railed = False
    best, bestv = 1.0, -1.0
    for it in range(refine):
        grid = np.linspace(lo, hi, n)
        vals = []
        for s in grid:
            pa, pb = trial_pair(a_raw, b_raw, float(s))
            vals.append(S.ncc_peak(S.prep(pa), S.prep(pb)))
        k = int(np.argmax(vals))
        if it == 0 and k in (0, len(grid) - 1):
            railed = True
        best, bestv = float(grid[k]), float(vals[k])
        step = float(grid[1] - grid[0])
        lo, hi, n = best - step, best + step, 21
    return best, bestv, railed


def plant_pair(img, s):
    """A pair whose true content ratio is exactly `s`, both sides resampled."""
    aa = min(1.0, s)
    return shrink(img, aa), shrink(img, aa / s)


def frames(last):
    names = sorted(f for f in os.listdir(S.STACK) if f.lower().endswith(".arw"))
    return (
        S.green_plane(os.path.join(S.STACK, names[0])),
        S.green_plane(os.path.join(S.STACK, names[last])),
    )


def control(out_json):
    """B5 for the instrument: known scales either side of 1.0, both searches."""
    g0, _ = frames(1)
    print(f"working {g0.shape[1]}x{g0.shape[0]}")
    print("plant is gather(img,min(1,s)) vs gather(img,min(1,1/s)): both sides")
    print("resampled, both gather args <= 1, true ratio exactly s.")
    print()
    print(f"{'planted':>8} {'two-sided':>10} {'err':>9} | "
          f"{'M97 best_scale':>15} {'err':>9} {'clipped':>8}")
    rows = []
    for s in [0.80, 0.86, 0.94, 0.98, 1.00, 1.02, 1.06, 1.12, 1.20]:
        A, B = plant_pair(g0, s)
        got2, _, _ = best_scale_2s(A, B)
        got1, _, _ = S.best_scale(S.prep(A), B)
        clip = abs(got1 - 0.99997) < 3e-4 and s > 1.005
        rows.append(dict(planted=s, two_sided=got2, m97=got1, clipped=bool(clip)))
        print(f"{s:>8.3f} {got2:>10.5f} {got2 - s:>+9.5f} | "
              f"{got1:>15.5f} {got1 - s:>+9.5f} {str(clip):>8}")
    worst2 = max(abs(r["two_sided"] - r["planted"]) for r in rows)
    above = [r for r in rows if r["planted"] > 1.005]
    worst1 = max(abs(r["m97"] - r["planted"]) for r in above)
    print()
    print(f"two-sided worst |err| over the whole range : {worst2:.5f} "
          f"({worst2 * R_PLANE:.1f} plane px)")
    print(f"M97 search worst |err| above 1.005         : {worst1:.5f} "
          f"({worst1 * R_PLANE:.1f} plane px)")
    print(f"M97 search clipped on {sum(r['clipped'] for r in rows)} of "
          f"{len(above)} plants above 1.0")
    ok = worst2 < 0.004
    print(f"\nTWO-SIDED INSTRUMENT {'OK' if ok else 'FAIL'} "
          f"(bar: worst |err| < 0.004 over 0.80..1.20)")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(dict(rows=rows, worst_two_sided=worst2, worst_m97_above=worst1,
                       ok=bool(ok)), fh, indent=1)
    return 0 if ok else 1


def sidecar(path, out_json, last, gain=1.0):
    header, rows0 = S.parse(path)
    plane_w = float(header["plane"].split("x")[0])
    g0, gN = frames(last)
    scale_px = plane_w / g0.shape[1]
    if gain != 1.0:
        rows0 = {k: (np.exp(gain * np.log(a)), gain * b) for k, (a, b) in rows0.items()}
    a0, b0 = rows0[0]
    aN, bN = rows0[last]
    print(f"sidecar {os.path.basename(path)}  reference {header['reference']}  "
          f"gain {gain:.4f}")
    print(f"|a_0| = {abs(a0):.6f}  |a_{last}| = {abs(aN):.6f}  "
          f"span = {abs(aN) / abs(a0):.6f}")

    raw, rawv, _ = best_scale_2s(g0, gN)
    drift = abs(raw - 1.0) * R_PLANE
    print(f"RAW      {raw:>9.5f}  {drift:>7.1f} plane px  ncc {rawv:.4f}")
    selfs, _, _ = best_scale_2s(g0, g0)
    print(f"SELF     {selfs:>9.5f}  {abs(selfs - 1.0) * R_PLANE:>7.1f} plane px")

    w0 = S.gather(g0, a0, b0, scale_px)
    wN = S.gather(gN, aN, bN, scale_px)
    asis, v, _ = best_scale_2s(w0, wN)
    px = abs(asis - 1.0) * R_PLANE
    removed = 1.0 - px / drift
    print(f"AS-IS    {asis:>9.5f}  {px:>7.1f} plane px  ncc {v:.4f}")
    print()
    print(f"predicted from the sidecar alone : {raw / (abs(aN) / abs(a0)):.5f}")
    print(f"MEASURED residual                : {asis:.5f}  "
          f"({px:.1f} plane px, {removed * 100:.1f}% of the drift removed)")
    out = dict(sidecar=path, gain=gain, raw=raw, self=selfs, asis=asis,
               plane_px=px, removed=removed,
               span=abs(aN) / abs(a0), drift_px=drift)
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    return 0


def main(argv):
    if argv[1] == "control":
        return control(argv[2])
    if argv[1] == "sidecar":
        g = float(argv[5]) if len(argv) > 5 else 1.0
        return sidecar(argv[2], argv[3], int(argv[4]), g)
    raise SystemExit(f"unknown mode {argv[1]!r}")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

"""M98 S4 -- the D1 ladder, full stack, one alignment solve, noise-subtracted.

WHY THIS INSTRUMENT EXISTS
  The parity-half design (S1) is sound on a shallow bracket and fails on a deep
  one, for a reason worth recording: each half solves its own alignment, so the
  two halves of `bee-3-cpl` came out at reference frames 75 and 74 with
  `fit_to_cover` scales 0.9227 and 0.9360 and a held-out error of 58.4 px on the
  half that could measure one at all.  Their mutual misregistration is a
  spatially varying 10-50 px field, and it annihilated the high-frequency cross
  power the instrument reads: `dsig` returned NaN on 24 of 24 ROIs.  That is a
  property of splitting the bracket, not of the gate.

  Rendering the FULL stack once per gate uses ONE alignment solve -- the sidecar
  that already exists beside the frames, loaded identically at every rung -- so
  the geometry is bit-identical across the ladder and the gate is the only thing
  that varies.  This is also M85's own design, which makes the comparison to
  fact 1196 direct.

HOW THE NOISE IS REMOVED WITHOUT A SECOND RENDER
  Fact 27 pins the optical cutoff at f_sig = 0.2762 cyc/px: above it there is no
  scene signal, so ring power there is the noise floor.  It is estimated over
  f in [0.30, 0.45] and subtracted from every ring.

  Rule 18, stated as a direction and not as a hope.  The warp resampler is a
  low-pass, so the merge's noise is NOT white: its power at 0.30-0.45 is lower
  than at 0.15-0.2762.  The floor therefore UNDER-subtracts in band, and it
  under-subtracts most where there is most noise, which is gate 0.  That
  inflates the gate-0 denominator and pushes A_hf(T)/A_hf(0) DOWN.  The bias
  runs against the conclusion that the gate is cheap, so a cheap-gate result
  measured with it is a floor, not a flattery.

  Both the raw and the noise-subtracted ratio are reported.  The raw one IS
  M85's instrument, so the two columns are a direct measurement of how much of
  fact 1196's 0.985x was noise.

Usage:  python s4_fullstack.py <stack> [ALN,ZOOM]
"""
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m98lib as M98  # noqa: E402
import m57lib as K    # noqa: E402

STACK = sys.argv[1] if len(sys.argv) > 1 else "bee-3-cpl"
ARMS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["ALN", "ZOOM"]

F_FLOOR_LO, F_FLOOR_HI = 0.30, 0.45


class SubRing:
    """`RingStats` with the measured noise floor subtracted from every ring.

    Duck-typed so `m57lib.dsig_db` runs on it unmodified (rule 15: the frozen
    metric is imported, never reimplemented).  The floor is a constant offset,
    so subtracting the same scalar from `c` and from every `c_jack` leaves the
    sector jackknife variance exactly unchanged -- the weight `dsig` uses is not
    touched by the subtraction.
    """

    def __init__(self, rs, floor):
        self._rs = rs
        self.floor = float(floor)
        self.f = rs.f
        self.nsect = rs.nsect

    @property
    def c(self):
        return self._rs.c - self.floor

    def c_jack(self, s):
        return self._rs.c_jack(s) - self.floor

    def c_var(self):
        return self._rs.c_var()


def floor_of(rs):
    idx = np.where((rs.f >= F_FLOOR_LO) & (rs.f <= F_FLOOR_HI))[0]
    return float(rs.c[idx].mean())


def a_band(rs, lo=M98.F_LO_HF, hi=M98.F_HI_HF):
    idx = K.band_index(rs.f, lo, hi)
    return float(np.asarray(rs.c)[idx].mean())


def full_path(stack, arm, gate):
    return os.path.join(M98.RENDERS, f"{stack}-FULL-{arm}-g{gate:g}.tif")


def pred_sigma_gain(stack, arm, gate):
    """The merge's own predicted noise gain, printed by the CLI before any
    analysis existed.  The noise-floor estimator is checked against it."""
    import re
    p = os.path.join(M98.LOGS, f"{stack}-FULL-{arm}-g{gate:g}.log")
    if not os.path.exists(p):
        return None
    txt = open(p, encoding="utf-8", errors="replace").read()
    m = re.search(r"^\s*%s\s+[\d.]+\s+([\d.]+)\s+[\d.]+%%\s+[\d.]+%%\s+([\d.]+)x"
                  % re.escape(f"{gate:.2f}"), txt, re.M)
    return (float(m.group(1)), float(m.group(2))) if m else None


def main():
    t0 = time.time()
    lines = []

    def log(s=""):
        print(s, flush=True)
        lines.append(s)

    log("=" * 78)
    log(f"M98 S4 -- FULL-STACK gate ladder on {STACK}, one alignment solve")
    log("  A_hf raw   = M85's instrument: band auto-power ratio, noise included")
    log("  A_hf clean = the same band with the measured above-cutoff noise floor")
    log("               subtracted.  The difference between the two columns is")
    log("               how much of fact 1196 was noise.")
    log("  dsig       = m57lib K7, unmodified, on the noise-subtracted rings.")
    log("               POSITIVE = gate T is BLURRIER than gate 0.")
    log("=" * 78)

    ref = full_path(STACK, "ALN", 0.0)
    if not os.path.exists(ref):
        log(f"MISSING {ref}")
        return
    g0 = M98.green(ref)
    h, w = g0.shape
    grid = M98.roi_grid(h, w)
    hp = [M98.hp_sd(M98.crop(g0, xy)) for xy in grid]
    ter = M98.terciles(hp)
    log(f"\nrender geometry : {w} x {h}   ROIs: {len(grid)} of {M98.ROI}^2")
    log(f"noise floor band: f in [{F_FLOOR_LO}, {F_FLOOR_HI}] cyc/px "
        f"(above fact 27's cutoff {K.F_SIG:.4f})")

    result = dict(stack=STACK, w=w, h=h, grid=grid, hp_sd=hp, arms={})

    for arm in ARMS:
        log("\n" + "=" * 78)
        log(f"ARM {arm}")
        log("=" * 78)
        rings, subs = {}, {}
        ok = True
        for g in M98.GATES:
            p = full_path(STACK, arm, g)
            if not os.path.exists(p):
                log(f"  MISSING {os.path.basename(p)}; arm skipped")
                ok = False
                break
            a = M98.green(p)
            rr = [K.RingStats(M98.crop(a, xy), M98.crop(a, xy)) for xy in grid]
            rings[g] = rr
            subs[g] = [SubRing(r, floor_of(r)) for r in rr]
        if not ok:
            continue

        # -------- RULE 9 FLAT CONTROL, run FIRST, and it is now a real one ----
        # The noise floor is measured directly, so noise reduction can be read
        # off a single render and checked against the merge's own prediction.
        kflat = int(np.argmin(hp))
        log(f"\n--- RULE 9 FLAT/NOISE CONTROL (run FIRST) --- ROI {kflat} at "
            f"{grid[kflat]}, hp_sd {hp[kflat]:.3f}")
        log(f"  {'gate':>5} {'floor(T)':>12} {'floor ratio':>12} "
            f"{'sigma ratio':>12} {'CLI predicted':>14} {'n_eff(CLI)':>11}")
        f0 = floor_of(rings[0.0][kflat])
        flat = {}
        for g in M98.GATES:
            fl = floor_of(rings[g][kflat])
            pr = pred_sigma_gain(STACK, arm, g)
            flat[f"{g:g}"] = dict(floor=fl, ratio=fl / f0,
                                  sigma=float(np.sqrt(fl / f0)),
                                  cli=pr)
            log(f"  {g:>5g} {fl:>12.5g} {fl/f0:>12.5f} {np.sqrt(fl/f0):>12.5f} "
                f"{(pr[1] if pr else float('nan')):>14.4f} "
                f"{(pr[0] if pr else float('nan')):>11.3f}")
        r4 = flat["4"]["ratio"]
        log(f"  PRE-REGISTERED BAR: noise power at gate 4 <= 0.25 of gate 0 "
            f"(sigma <= 0.5x) -> {r4:.4f}  {'PASS' if r4 <= 0.25 else 'FAIL'}")
        cli4 = flat["4"]["cli"]
        if cli4:
            log(f"  INDEPENDENT CHECK: the merge predicted a sigma gain of "
                f"{cli4[1]:.4f}x from its own")
            log(f"    noise model before any of this was measured; the floor "
                f"gives {np.sqrt(r4):.4f}x.")
            log(f"    Agreement {np.sqrt(r4)/cli4[1]:.4f}x.  These are "
                f"independent instruments.")

        # -------- the ladder --------------------------------------------------
        per_gate = {}
        for g in M98.GATES:
            rows = []
            for k in range(len(grid)):
                raw = a_band(rings[g][k])
                raw0 = a_band(rings[0.0][k])
                cl = a_band(subs[g][k])
                cl0 = a_band(subs[0.0][k])
                d = K.dsig_db(subs[0.0][k], subs[g][k],
                              M98.F_LO_DSIG, M98.F_HI_DSIG)
                rows.append(dict(k=k, hp_sd=hp[k],
                                 raw=raw, raw_ratio=raw / raw0 if raw0 else np.nan,
                                 clean=cl, clean_ratio=cl / cl0 if cl0 else np.nan,
                                 floor=subs[g][k].floor,
                                 floor_ratio=subs[g][k].floor / subs[0.0][k].floor,
                                 dsig=d["px"], gof=d.get("gof", np.nan)))
            per_gate[f"{g:g}"] = rows

        log(f"\n--- LADDER, pooled over all {len(grid)} ROIs ---")
        log(f"  {'gate':>5} {'A_hf raw':>10} {'SE':>8} {'A_hf clean':>11} "
            f"{'SE':>8} {'dsig px':>9} {'SE':>8} {'sig':>6} {'n-':>4} "
            f"{'noise pwr':>10}")
        for g in M98.GATES:
            rows = per_gate[f"{g:g}"]
            sr = M98.stats_across([r["raw_ratio"] for r in rows])
            sc = M98.stats_across([r["clean_ratio"] for r in rows])
            sd_ = M98.stats_across([r["dsig"] for r in rows])
            nf = float(np.median([r["floor_ratio"] for r in rows]))
            log(f"  {g:>5g} {sr['mean']:>10.5f} {sr['se']:>8.5f} "
                f"{sc['mean']:>11.5f} {sc['se']:>8.5f} {sd_['mean']:>+9.5f} "
                f"{sd_['se']:>8.5f} {sd_['sigma']:>6.2f} {sd_['nneg']:>4} "
                f"{nf:>10.5f}")

        log(f"\n--- STRATIFIED by detail tercile (discipline 603) ---")
        strat = {}
        for name in ("low", "mid", "high"):
            idx = ter[name]
            log(f"\n  tercile {name.upper()}  (hp_sd "
                f"{min(hp[i] for i in idx):.1f} - {max(hp[i] for i in idx):.1f})")
            log(f"    {'gate':>5} {'A_hf raw':>10} {'A_hf clean':>11} {'SE':>8} "
                f"{'dsig px':>9} {'SE':>8} {'sig':>6} {'n-':>4} {'gof med':>8}")
            strat[name] = {}
            for g in M98.GATES:
                rows = [per_gate[f"{g:g}"][i] for i in idx]
                sr = M98.stats_across([r["raw_ratio"] for r in rows])
                sc = M98.stats_across([r["clean_ratio"] for r in rows])
                sd_ = M98.stats_across([r["dsig"] for r in rows])
                gg = [r["gof"] for r in rows if np.isfinite(r["gof"])]
                strat[name][f"{g:g}"] = dict(raw=sr, clean=sc, dsig=sd_,
                                             gof=float(np.median(gg)) if gg else np.nan)
                log(f"    {g:>5g} {sr['mean']:>10.5f} {sc['mean']:>11.5f} "
                    f"{sc['se']:>8.5f} {sd_['mean']:>+9.5f} {sd_['se']:>8.5f} "
                    f"{sd_['sigma']:>6.2f} {sd_['nneg']:>4} "
                    f"{(float(np.median(gg)) if gg else float('nan')):>8.4f}")

        result["arms"][arm] = dict(per_gate=per_gate, strat=strat, flat=flat,
                                   flat_roi=kflat)

    log(f"\n({time.time()-t0:.0f}s)")
    with open(os.path.join(M98.OUT, f"s4_{STACK}.json"), "w") as fh:
        json.dump(result, fh, indent=1, default=float)
    with open(os.path.join(M98.OUT, f"s4_{STACK}.log"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()

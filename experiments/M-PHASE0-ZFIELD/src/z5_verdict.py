"""M-PHASE0-ZFIELD -- Z5, the verdict, plus the two analyses the census forced.

Two things the census made necessary, neither of which was in section 5:

Z5a  THE MATCHED LADDER. Section 2 evaluates the partition at four DOF/2 values,
     two from the recommended step and two from corpus density. The eight M66
     cubes ARE corpus-density stacks, so reading a native cube against the
     recommended-step half-widths compares a corpus sigma_z against a
     recommended-step DOF -- a units error. The matched comparison decimates the
     frame axis by m, which IS the step change, and evaluates against
     (1.5, 3.0)/m. Section 5's Z4 registered the ladder; this is how to read it.

Z5b  THE REGULARISATION SENSITIVITY. Preregistration bias B1 recorded that M66's
     27x27 + 17x17 regularisation inflates apparent coherence, and called that a
     bias FAVOURING A5. That is only half of B1 and the census exposed the other
     half: the same smoothing also shrinks sigma_r, which shrinks sigma_z, which
     inflates EASY and therefore works AGAINST A5. B1 as registered is
     incomplete, and the omitted half is the one that drives this lane's verdict.

     The bootstrap can answer it directly. It builds sigma_z by adding noise of a
     stated size to a smoothed truth, so inflating sigma_r by F yields the
     sigma_z a noisier -- that is, less regularised -- operator would have. The
     verdict is therefore reported as a curve in F, and the F at which it flips
     is compared against the range implied by the two operators' window sizes.
"""

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import zflib  # noqa: E402
from z1_census import (CORPUS_HALF, HALF_WIDTHS, M66, N_SAMPLE, OUT, SIGNAL_MIN,
                       WINDOWS, blocked_fields)  # noqa: E402

F_LADDER = [1.0, 2.0, 4.0, 5.4, 6.83, 8.0, 16.0, 32.0, 64.0]

# The M66 cascade averages |sobel| over a 27x27 box and then over a 17x17 box.
# The shipping estimator's fine field is 5x5. Treating box means as averages of
# independent samples, the cascade pools at least 27^2 and at most 27^2 * 17^2
# samples against the 5x5 field's 25, so the response-noise ratio F between the
# two operators lies in [sqrt(729/25), sqrt(210681/25)] = [5.4, 91.8].
F_LO, F_HI = np.sqrt(729.0 / 25.0), np.sqrt(729.0 * 289.0 / 25.0)


def verdict(w):
    return "KILL" if w < 0.02 else ("SURVIVE" if w >= 0.10 else "INCONCLUSIVE")


def best_winnable(boot, half, rho_x, rho_y):
    best = 0.0
    bw = None
    for W in WINDOWS:
        g = np.sqrt(zflib.n_eff(rho_x, rho_y, W))
        _, wn, _, _ = zflib.partition(boot, half, g)
        if wn > best:
            best, bw = wn, W
    return best, bw


def main():
    census = json.loads((OUT / "z1-census.json").read_text(encoding="utf-8"))
    stacks = sorted(p.stem.replace("-d4", "") for p in M66.glob("*-d4.npy"))
    report = {"matched_ladder": {}, "f_sensitivity": {}, "native_corpus": {}}

    # ---- Z5a: native verdict at the corpus half-widths, and the matched ladder.
    for half in HALF_WIDTHS:
        ws = [a["1"]["partition"][str(half)]["winnable_best"]
              for a in census["stacks"].values() if "skipped" not in a.get("1", {})]
        es = [a["1"]["partition"][str(half)]["by_window"][
                  str(a["1"]["partition"][str(half)]["best_window"])]["easy"]
              for a in census["stacks"].values() if "skipped" not in a.get("1", {})]
        report["native_corpus"][str(half)] = {
            "median_winnable": float(np.median(ws)),
            "median_easy": float(np.median(es)),
            "verdict": verdict(float(np.median(ws))),
            "matched": half in CORPUS_HALF,
        }

    for m in ("1", "2", "3"):
        for half_native in CORPUS_HALF:
            h = half_native / float(m)
            ws = []
            for a in census["stacks"].values():
                arm = a.get(m)
                if not arm or "skipped" in arm:
                    continue
                # The census stored only the four registered half-widths, so the
                # matched value is recomputed from the stored quantiles only when
                # it coincides; otherwise it is recomputed in the F pass below.
                key = str(h)
                if key in arm["partition"]:
                    ws.append(arm["partition"][key]["winnable_best"])
            if ws:
                report["matched_ladder"][f"m{m}_half{h}"] = {
                    "n_stacks": len(ws),
                    "median_winnable": float(np.median(ws)),
                    "verdict": verdict(float(np.median(ws))),
                }

    # ---- Z5b: the regularisation sensitivity, recomputed from the cubes.
    print("  F-ladder (inflating sigma_r to simulate a less regularised operator)")
    per_stack = {}
    for i, s in enumerate(stacks):
        cube = np.asarray(np.load(M66 / f"{s}-d4.npy", mmap_mode="r"), dtype=np.float32)
        n, h, w = cube.shape
        sr, D, zh, inter, prom = blocked_fields(cube)
        rng = np.random.default_rng(1000 + 17 * i + 1)
        ys, xs = rng.integers(0, h, N_SAMPLE), rng.integers(0, w, N_SAMPLE)
        curves = np.asarray(cube[:, ys, xs], dtype=np.float64)
        srs = sr[ys, xs]
        rho_x, rho_y = zflib.noise_autocorr(cube)
        rows = {}
        for F in F_LADDER:
            boot = zflib.bootstrap_sigma_z(curves, srs * F)
            rows[str(F)] = {}
            for half in CORPUS_HALF:
                wn, bw = best_winnable(boot, half, rho_x, rho_y)
                e, _, l, _ = zflib.partition(
                    boot, half, np.sqrt(zflib.n_eff(rho_x, rho_y, bw or 33)))
                rows[str(F)][str(half)] = {"winnable": wn, "easy": e, "lost": l,
                                           "best_window": bw}
            print(f"    {s:<15} F={F:<5g} "
                  + "  ".join(f"half={hh}: W {rows[str(F)][str(hh)]['winnable'] * 100:5.2f}% "
                              f"E {rows[str(F)][str(hh)]['easy'] * 100:5.1f}% "
                              f"L {rows[str(F)][str(hh)]['lost'] * 100:5.1f}%"
                              for hh in CORPUS_HALF), flush=True)
        per_stack[s] = rows
        del cube, curves

    report["f_sensitivity"] = {"per_stack": per_stack, "ladder": F_LADDER,
                              "f_range_operator": [float(F_LO), float(F_HI)]}
    summary = {}
    for F in F_LADDER:
        for half in CORPUS_HALF:
            ws = [per_stack[s][str(F)][str(half)]["winnable"] for s in per_stack]
            es = [per_stack[s][str(F)][str(half)]["easy"] for s in per_stack]
            ls = [per_stack[s][str(F)][str(half)]["lost"] for s in per_stack]
            summary[f"F{F}_half{half}"] = {
                "median_winnable": float(np.median(ws)),
                "median_easy": float(np.median(es)),
                "median_lost": float(np.median(ls)),
                "verdict": verdict(float(np.median(ws))),
            }
    report["f_sensitivity"]["summary"] = summary

    (OUT / "z5-verdict.json").write_text(json.dumps(report, indent=1), encoding="utf-8")

    print("\n  Native cubes, corpus-matched half-widths:")
    for half in CORPUS_HALF:
        r = report["native_corpus"][str(half)]
        print(f"    DOF/2={half}: WINNABLE {r['median_winnable'] * 100:.2f}%  "
              f"EASY {r['median_easy'] * 100:.1f}%  -> {r['verdict']}")
    print("\n  F-sensitivity (median over 8 stacks):")
    for F in F_LADDER:
        line = f"    F={F:<5g}"
        for half in CORPUS_HALF:
            r = summary[f"F{F}_half{half}"]
            line += (f"  half={half}: W {r['median_winnable'] * 100:5.2f}% "
                     f"E {r['median_easy'] * 100:5.1f}% "
                     f"L {r['median_lost'] * 100:5.1f}% {r['verdict']:<12}")
        print(line)
    print(f"\n  operator F range implied by window sizes: {F_LO:.1f} to {F_HI:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


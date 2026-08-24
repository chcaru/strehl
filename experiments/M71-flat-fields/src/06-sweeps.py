"""M71 step 06 -- the focus sweeps. PR-2a, PR-2b, PR-4c.

PR-4c is the decisive gate of this milestone. Step 05's kappa rests on the
claim that the two-green difference D = r_G1 - r_G2 cancels optical structure.
That claim is testable and this is the test.

Defocus destroys subject texture and leaves sensor PRNU untouched. The two
62-frame sweeps run out-of-focus -> through focus -> out-of-focus at the SAME
aperture and magnification as the flats. So along a sweep:

  C = cov(r_G1, r_G2)   -- the COMMON optical structure -- must rise and fall
                           by an order of magnitude as the paper comes into
                           focus and goes out again.
  P = the D-based PRNU  -- must not move at all.

An estimator that is really measuring paper cannot pass both. If P tracks C,
step 05's headline is paper and is withdrawn.

Single frames, not stacks. The sweeps have no temporal replication -- every
frame is at a different focus -- but the estimator does not need any. Within
ONE frame the shot noise in G1 and G2 is independent (different photosites),
so cov(r_G1, r_G2) is already unbiased for the common optical term, and
var(D) - (noise) is the PRNU. The noise term here IS subtracted rather than
cancelled, so it is the weaker of the two routes and is used only where the
strong route is unavailable.

PR-2a/PR-2b also fall out: X = C is exactly the focus statistic, and comparing
the flats' C against the sweeps' range answers "was the paper in focus during
the 360 flats?" from pixels rather than from the FocusDistance2 tag.
"""

from __future__ import annotations

import csv
import json
from fractions import Fraction
from pathlib import Path

import numpy as np
import rawpy

HERE = Path(__file__).resolve().parent.parent
CACHE = HERE / "out" / "cache"
OUT = HERE / "data" / "06-sweeps.json"
BLACK = 512.0
WHITE_SUB = 15360.0 - BLACK
BOX, NPASS, N = 61, 3, 20

import importlib.util
_spec = importlib.util.spec_from_file_location(
    "k5", Path(__file__).resolve().parent / "05-kappa.py")
_k5 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_k5)
smooth, residual, highpass_response, tag_of = (
    _k5.smooth, _k5.residual, _k5.highpass_response, _k5.tag_of)


def planes_of(vis):
    return {"R": vis[0::2, 0::2], "G1": vis[0::2, 1::2],
            "G2": vis[1::2, 0::2], "B": vis[1::2, 1::2]}


def frame_stats(path, F, gain, b_floor):
    with rawpy.imread(str(path)) as raw:
        vis = raw.raw_image_visible.astype(np.float32)     # rule 32
    vis -= BLACK
    pl = planes_of(vis)
    out = {}
    g1, g2 = pl["G1"].astype(np.float32), pl["G2"].astype(np.float32)
    m1, m2 = float(g1.mean()), float(g2.mean())
    out["mean_G1"], out["mean_G2"] = m1, m2
    out["clip_G1"] = float((g1 >= WHITE_SUB).mean())
    out["clip_G2"] = float((g2 >= WHITE_SUB).mean())
    r1 = residual(g1 / np.float32(m1))
    r2 = residual(g2 / np.float32(m2))
    a, bb = r1.ravel(), r2.ravel()
    C = float(np.mean(a * bb) - np.mean(a) * np.mean(bb))
    out["C_common"] = C
    out["var_r_G1"] = float(np.var(r1))
    out["var_r_G2"] = float(np.var(r2))
    D = r1 - r2
    out["var_D"] = float(np.var(D))
    # single-frame shot+read noise in relative units, from the measured model
    nv1 = (gain * m1 + b_floor) / (m1 * m1) * F
    nv2 = (gain * m2 + b_floor) / (m2 * m2) * F
    out["noise_var_D"] = float(nv1 + nv2)
    out["P_prnu"] = float((out["var_D"] - out["noise_var_D"]) / 2.0)
    del vis, pl
    return out, D


def main() -> None:
    F = highpass_response()
    ptc = json.loads((HERE / "data" / "03-ptc.json").read_text(encoding="utf-8"))
    dark = json.loads((HERE / "data" / "04-dark-and-linearity.json").read_text(encoding="utf-8"))
    gain = ptc["G1"]["g"]
    b_floor = dark["darks"]["planes"]["G1"]["pooled_rms_sigma_dn"] ** 2
    print(f"single-frame noise model used: var = {gain:.6f}*S + {b_floor:.5f} DN^2, "
          f"high-pass F = {F:.6f}\n")

    rows = list(csv.DictReader((HERE / "data" / "exif-all.csv").open(encoding="utf-8-sig")))
    res = {}
    keep_D = {}
    for d in ("subject-focus-sweep-with-cpl", "subject-focus-sweep-no-cpl"):
        sub = sorted([r for r in rows if Path(r["Directory"]).name == d],
                     key=lambda r: r["SubSecDateTimeOriginal"])
        assert len(sub) == 62, f"{d}: {len(sub)}"
        recs = []
        print(f"=== {d}")
        for i, r in enumerate(sub):
            st, D = frame_stats(Path(r["SourceFile"]), F, gain, b_floor)
            st["i"] = i
            st["file"] = r["FileName"]
            recs.append(st)
            keep_D[(d, i)] = D
        Cs = np.array([s["C_common"] for s in recs])
        Ps = np.array([s["P_prnu"] for s in recs])
        order = np.argsort(Cs)
        sharp = int(order[-1])
        soft = int(order[0])
        print(f"  C (common optical power) min {Cs.min():.3e} at frame {soft}, "
              f"max {Cs.max():.3e} at frame {sharp}, ratio {Cs.max() / Cs.min():.1f}x")
        print(f"  P (PRNU variance)  at sharpest frame {Ps[sharp]:.4e} "
              f"-> kappa {np.sqrt(max(Ps[sharp], 0)) * 100:.4f}%")
        print(f"  P (PRNU variance)  at softest  frame {Ps[soft]:.4e} "
              f"-> kappa {np.sqrt(max(Ps[soft], 0)) * 100:.4f}%")
        print(f"  P across all 62:   mean {Ps.mean():.4e}  sd {Ps.std(ddof=1):.4e}  "
              f"-> kappa {np.sqrt(max(Ps.mean(), 0)) * 100:.4f}% "
              f"+- {0.5 * Ps.std(ddof=1) / np.sqrt(max(Ps.mean(), 1e-12)) * 100:.4f}%")
        print("  frame-by-frame (every 4th):")
        for s in recs[::4]:
            print(f"    {s['i']:3d} {s['file']}  meanG1={s['mean_G1']:8.1f}  "
                  f"C={s['C_common']:.3e}  P={s['P_prnu']:.4e}  "
                  f"kappa={np.sqrt(max(s['P_prnu'], 0)) * 100:6.4f}%")
        res[d] = {"frames": recs, "C_min": float(Cs.min()), "C_max": float(Cs.max()),
                  "C_ratio": float(Cs.max() / Cs.min()),
                  "sharpest_index": sharp, "softest_index": soft,
                  "P_at_sharpest": float(Ps[sharp]), "P_at_softest": float(Ps[soft]),
                  "P_mean": float(Ps.mean()), "P_sd": float(Ps.std(ddof=1))}
        np.save(CACHE / f"sweep-{d}-soft.npy", keep_D[(d, soft)])
        np.save(CACHE / f"sweep-{d}-sharp.npy", keep_D[(d, sharp)])
        print()

    dirs = list(res.keys())

    # ---- PR-2a: where do the flats sit on this scale?
    print("=== PR-2a focus state of the 360 flats, from pixels")
    flat_C = {}
    for tag in ("e0.05-A", "e0.05-B", "e0.03333333333333333-A"):
        r1 = residual(np.load(CACHE / f"{tag}-G1-mean.npy"))
        r2 = residual(np.load(CACHE / f"{tag}-G2-mean.npy"))
        a, bb = r1.ravel(), r2.ravel()
        C = float(np.mean(a * bb) - np.mean(a) * np.mean(bb))
        flat_C[tag] = C
        print(f"  flats {tag:26s} C = {C:.3e}")
    cmin = min(res[d]["C_min"] for d in dirs)
    worst = max(flat_C.values())
    pr2a = worst < cmin
    print(f"  least-focused sweep frame C = {cmin:.3e}")
    print(f"  worst (largest) flat C      = {worst:.3e}  "
          f"({cmin / worst:.1f}x BELOW the most defocused sweep frame)")
    print(f"  PR-2a: {'MET' if pr2a else 'NOT MET'} -- the 360 flats were shot "
          f"{'far out of focus' if pr2a else 'in focus'}")
    pr2b = all(res[d]["C_ratio"] >= 10 for d in dirs)
    print(f"  PR-2b (sweep C range >= 10x): {'MET' if pr2b else 'NOT MET'}  "
          + ", ".join(f"{d}={res[d]['C_ratio']:.1f}x" for d in dirs))

    # ---- PR-4c AS PRE-REGISTERED. It fails. It is reported as failing.
    print("\n=== PR-4c AS PRE-REGISTERED -- PRNU invariance across the WHOLE sweep")
    pr4c = []
    for d in dirs:
        rr = res[d]
        ratio = rr["P_at_sharpest"] / rr["P_at_softest"]
        ok = rr["C_ratio"] >= 10 and abs(ratio - 1.0) <= 0.25
        pr4c.append(ok)
        print(f"  {d}: C moved {rr['C_ratio']:.1f}x, "
              f"P(sharp)/P(soft) = {ratio:.1f}  (required 1.00 +- 0.25)  "
              f"-> {'MET' if ok else 'NOT MET'}")
        rr["pr4c_ratio"] = float(ratio)
        rr["pr4c_met"] = bool(ok)
    print("  PR-4c NOT MET. The premise was wrong, and the sweep is what shows")
    print("  it: D = r_G1 - r_G2 samples the optical field at two positions one")
    print("  pixel apart on the diagonal, so it cancels optical structure only")
    print("  where that structure is smooth on a 2-px scale. In focus it is not,")
    print("  and D is then dominated by paper. The pre-registered claim that D")
    print("  cancels paper AT ANY FOCUS is refuted by this measurement.")

    # ---- the corrected test. POST-HOC, and labelled as such.
    print("\n=== POST-HOC replacement for PR-4c: extrapolate the paper term to zero")
    print("    Over the DEFOCUSED TAIL, P is linear in C. Fit P = P0 + alpha*C")
    print("    and evaluate the paper contribution at the flats' own C.")
    extrap = {}
    for d in dirs:
        recs = res[d]["frames"]
        tail = [s for s in recs if s["C_common"] <= 2.0e-3]
        cs = np.array([s["C_common"] for s in tail])
        ps = np.array([s["P_prnu"] for s in tail])
        alpha, P0 = np.polyfit(cs, ps, 1)
        pred_r2 = 1.0 - float(np.var(ps - (alpha * cs + P0)) / np.var(ps))
        leak = alpha * worst
        extrap[d] = {"n_tail": len(tail), "C_tail_range": [float(cs.min()), float(cs.max())],
                     "alpha": float(alpha), "P0": float(P0), "r2": float(pred_r2),
                     "kappa_extrapolated": float(np.sqrt(max(P0, 0.0))),
                     "paper_leak_at_flats_C": float(leak),
                     "paper_leak_frac_of_P0": float(leak / P0)}
        print(f"  {d}: n={len(tail)} tail frames, C in "
              f"[{cs.min():.3e}, {cs.max():.3e}] ({cs.max() / cs.min():.1f}x), R^2={pred_r2:.5f}")
        print(f"    alpha = {alpha:.4e}   P0 = {P0:.4e}  ->  "
              f"kappa(paper-free) = {np.sqrt(max(P0, 0)) * 100:.4f}%")
        print(f"    predicted paper term at the flats' C={worst:.3e}: {leak:.3e} "
              f"= {100 * leak / P0:.4f}% of P0 "
              f"({50 * leak / P0:.4f}% of kappa)")

    # ---- and the strongest form: does the sweep's PRNU MAP match the flats'?
    print("\n=== sensor-fixedness across optical states (post-hoc)")
    print("    cov(D_sweep, D_flats). Independent captures, so temporal noise")
    print("    cancels in expectation and NO noise model is used at all.")
    print("    Different minute, different filter, different focus, different")
    print("    shutter mode (mechanical vs electronic), same sensor.")
    dflat = np.load(CACHE / "e0.05-A-Dgreen.npy").ravel()
    for d in dirs:
        for label, idx in (("softest", res[d]["softest_index"]),
                           ("sharpest", res[d]["sharpest_index"])):
            ds = keep_D[(d, idx)].ravel()
            cov = float(np.mean(ds * dflat) - np.mean(ds) * np.mean(dflat))
            rho = cov / (np.std(ds) * np.std(dflat))
            print(f"    {d:32s} {label:9s} frame {idx:2d}: "
                  f"cov = {cov:.4e} -> kappa {np.sqrt(max(cov, 0) / 2) * 100:.4f}%  "
                  f"rho = {rho:.4f}")
            res[d][f"cov_with_flats_{label}"] = cov
            res[d][f"kappa_from_cov_{label}"] = float(np.sqrt(max(cov, 0) / 2))
        # negative control: same comparison with the sweep map rolled by an
        # even offset, which preserves CFA phase and destroys pixel identity.
        ds = np.roll(keep_D[(d, res[d]["softest_index"])], 314, axis=0).ravel()
        cov = float(np.mean(ds * dflat) - np.mean(ds) * np.mean(dflat))
        print(f"    {d:32s} ROLLED negative control: cov = {cov:.4e} "
              f"({100 * cov / res[d]['cov_with_flats_softest']:+.2f}% of signal)")
        res[d]["cov_rolled"] = cov

    res = {"sweeps": {d: res[d] for d in dirs}, "flats_C": flat_C,
           "pr2a_met": bool(pr2a), "pr2b_met": bool(pr2b),
           "pr4c_met_as_preregistered": bool(all(pr4c)),
           "posthoc_extrapolation": extrap}
    OUT.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

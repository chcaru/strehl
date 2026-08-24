"""M69 arms B1-B3 -- the FINE field's form.

Pre-registered in PREREGISTRATION-2.md, committed at c545588 before this script
was written.

The fine field is the SAME operator at a smaller radius with no regulariser:
  selection : regularise( box_mean(|grad L|, 13) / sigma(L), 8 )   -> 0.015214
  fine      :             box_mean(|grad L|,  2) / sigma(L)        -> 0.090400

B1  the crate's own calibration plant, 2x2 -- CONTROL (K11-K14).
B2  M69 arm A3's texture plant UNCHANGED, 2x2 -- the result arm.
B3  the corpus, fine field, all 12 stacks.

Observable: rho = SD(field on textured plant) / C, where C is that cell's own
flat-plant constant, so the constant cancels and D = max(rho)/min(rho) over ell
is independent of the constant's value.

Registered E1: TIGHT if D_fine < 1.5; SAME-ORDER if D_fine >= 3.0; otherwise
INTERMEDIATE with no verdict word.
"""

import json
import pathlib
import re
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

a2mod = __import__("importlib").import_module("20-a2-m66-replication")
a3mod = __import__("importlib").import_module("30-a3-transfer")

FINE_WINDOW_RADIUS = int(
    re.search(
        r"pub const FINE_WINDOW_RADIUS: usize = (\d+);",
        (m69.ROOT / "crates" / "strehl-core" / "src" / "focus.rs").read_text(
            encoding="utf-8"
        ),
    ).group(1)
)

# (tag, window radius, regulariser radius or None)
CELLS = [
    ("coarse+reg", m69.WINDOW_RADIUS, m69.REGULARISER_RADIUS),
    ("coarse+bare", m69.WINDOW_RADIUS, None),
    ("fine+reg", FINE_WINDOW_RADIUS, m69.REGULARISER_RADIUS),
    ("fine+bare", FINE_WINDOW_RADIUS, None),
]

# Published anchors, for the controls. Sources quoted in the report.
ANCHORS = {
    "coarse+reg": (m69.FOCUS_NOISE_SD, "FOCUS_NOISE_SD, merge.rs:185"),
    "fine+bare": (m69.FINE_FOCUS_NOISE_SD, "FINE_FOCUS_NOISE_SD, through_focus.rs:153"),
    "fine+reg": (0.027613, "SYNTHESIS fact 500, measured 3x (M43/M52/M54)"),
    "coarse+bare": (0.018847, "SYNTHESIS fact 528, M45 FieldConfig::BARE"),
}

NSEED_B1 = 12
SIZE = a3mod.SIZE


def field(luma, radius, reg, iso=None, sigma=None):
    """box_mean(|grad|, radius) / sigma, optionally regularised. The shipped chain."""
    if sigma is None:
        sigma = m69.green_luma_sigma(luma, iso)
    f = m69.box_clamped(m69.sobel_mag(luma), radius) / np.maximum(sigma, m69.SIGMA_EPS)
    if reg is not None:
        f = m69.box_clamped(f, reg)
    return f


def inset_for(radius, reg):
    return 1 + radius + (reg or 0) + 2


# --------------------------------------------------------------- B1

def b1():
    m69.banner("B1 -- the crate's calibration plant, 2x2  (CONTROL: K11-K14)")
    print("  512x512 iid N(0,1), unit sigma model (sigma == 1), 12 seeds --")
    print("  the configuration merge.rs:1197 and through_focus.rs:1052 calibrate in.\n")
    print(f"  {'cell':<12} {'radius':>7} {'reg':>5} {'measured SD':>14} {'SEM':>10} "
          f"{'anchor':>11} {'delta':>9}")
    print("  " + "-" * 76)
    out = {}
    for tag, radius, reg in CELLS:
        vals = []
        for seed in range(NSEED_B1):
            rng = np.random.default_rng(90210 + seed)
            luma = rng.standard_normal((SIZE, SIZE))
            f = field(luma, radius, reg, sigma=np.ones_like(luma))
            vals.append(float(m69.interior(f, inset_for(radius, reg)).std()))
        mean = float(np.mean(vals))
        sem = float(np.std(vals, ddof=1) / np.sqrt(len(vals)))
        anchor, src = ANCHORS[tag]
        delta = mean / anchor - 1.0
        print(f"  {tag:<12} {radius:>7} {str(reg):>5} {mean:>14.6e} {sem:>10.2e} "
              f"{anchor:>11.6f} {delta:>+8.2%}")
        out[tag] = {
            "radius": radius,
            "reg": reg,
            "sd": mean,
            "sem": sem,
            "anchor": anchor,
            "anchor_source": src,
            "delta": delta,
        }
    print()
    k11 = abs(out["fine+bare"]["delta"]) <= 0.02
    k12 = abs(out["coarse+reg"]["delta"]) <= 0.02
    k13 = abs(out["fine+reg"]["delta"]) <= 0.02
    ratio = out["coarse+bare"]["sd"] / out["coarse+reg"]["sd"]
    m45_ratio = 0.018847 / 0.015211
    k14 = abs(ratio / m45_ratio - 1.0) <= 0.02
    print(f"  K11 fine+bare  vs FINE_FOCUS_NOISE_SD : {out['fine+bare']['delta']:+.2%}"
          f"   bar 2%  -> {'MET' if k11 else 'NOT MET'}")
    print(f"  K12 coarse+reg vs FOCUS_NOISE_SD      : {out['coarse+reg']['delta']:+.2%}"
          f"   bar 2%  -> {'MET' if k12 else 'NOT MET'}")
    print(f"  K13 fine+reg   vs fact 500 (0.027613) : {out['fine+reg']['delta']:+.2%}"
          f"   bar 2%  -> {'MET' if k13 else 'NOT MET'}")
    print(f"  K14 bare/reg ratio {ratio:.4f} vs M45's {m45_ratio:.4f} : "
          f"{ratio / m45_ratio - 1.0:+.2%}   bar 2%  -> {'MET' if k14 else 'NOT MET'}")
    print(f"\n  fine+bare / fine+reg = {out['fine+bare']['sd'] / out['fine+reg']['sd']:.4f}"
          f"   (through_focus.rs:1121 states 3.273)")
    out["_controls"] = {"K11": k11, "K12": k12, "K13": k13, "K14": k14,
                        "bare_over_reg": ratio, "m45_ratio": m45_ratio}
    return out


# --------------------------------------------------------------- B2

def measure_cell(latent, radius, reg, nrep, seed):
    rng = np.random.default_rng(seed)
    acc = None
    for _ in range(nrep):
        luma = latent + rng.standard_normal(latent.shape)
        f = field(luma, radius, reg, sigma=a3mod.unit_sigma(luma))
        if acc is None:
            acc = m69.Welford(f.shape)
        acc.push(f)
    return float(m69.interior(acc.sd(), inset_for(radius, reg)).mean())


def b2(b1out):
    m69.banner("B2 -- M69 arm A3's texture plant, unchanged, at all four cells")
    print(f"  SIZE {SIZE}, NREP {a3mod.NREP}, ELLS {a3mod.ELLS}, the same Z_GRID and the")
    print("  same make_latent normalisation by S_SOBEL, which is radius-independent --")
    print("  so z = nu/s means the same thing in every cell and one latent serves all four.\n")
    rows = []
    for tag, radius, reg in CELLS:
        c = b1out[tag]["sd"]
        print(f"  --- {tag}  (window r={radius}, reg={reg}, C={c:.6e}) ---")
        print(f"  {'ell':>5} " + " ".join(f"{z:>7.1f}" for z in a3mod.Z_GRID))
        for ell in a3mod.ELLS:
            line = []
            for z in a3mod.Z_GRID:
                rng = np.random.default_rng(int(1000 * ell) + int(10 * z))
                latent = a3mod.make_latent(rng, z, ell)
                sd = measure_cell(latent, radius, reg, a3mod.NREP, 4242 + int(10 * z))
                rho = sd / c
                line.append(rho)
                rows.append({"cell": tag, "ell": ell, "z": z, "rho": rho})
            print(f"  {ell:>5.0f} " + " ".join(f"{v:>7.4f}" for v in line))
        print()
    return rows


def b2_dispersion(rows):
    m69.banner("B2 / E1 -- dispersion D = max(rho)/min(rho) over ell, at z = 40")
    zmax = max(a3mod.Z_GRID)
    print(f"  {'cell':<12} " + " ".join(f"{'ell=' + str(int(e)):>9}" for e in a3mod.ELLS)
          + f" {'D':>9}")
    print("  " + "-" * 62)
    disp = {}
    for tag, _, _ in CELLS:
        vals = [r["rho"] for e in a3mod.ELLS
                for r in rows if r["cell"] == tag and r["ell"] == e and r["z"] == zmax]
        d = max(vals) / min(vals)
        disp[tag] = {"rhos": vals, "D": d}
        print(f"  {tag:<12} " + " ".join(f"{v:>9.4f}" for v in vals) + f" {d:>9.3f}x")
    print()
    # full-grid dispersion too, over every (ell, z) with z > 0
    print("  Same statistic over the WHOLE grid (all ell, all z > 0):")
    for tag, _, _ in CELLS:
        vals = [r["rho"] for r in rows if r["cell"] == tag and r["z"] > 0]
        dfull = max(vals) / min(vals)
        disp[tag]["D_fullgrid"] = dfull
        print(f"  {tag:<12} min {min(vals):.4f}  max {max(vals):.4f}  D {dfull:>7.3f}x")
    dfine = disp["fine+bare"]["D"]
    verdict = "TIGHT" if dfine < 1.5 else ("SAME-ORDER" if dfine >= 3.0 else "INTERMEDIATE")
    print(f"\n  E1: D_fine+bare = {dfine:.3f}x   registered bars: TIGHT <1.5, SAME-ORDER >=3.0")
    print(f"  E1 VERDICT: {verdict}")
    print(f"\n  E2 decomposition, at z = {zmax}:")
    print(f"    radius lever, bare  : D {disp['coarse+bare']['D']:.3f}x -> "
          f"{disp['fine+bare']['D']:.3f}x  "
          f"({disp['fine+bare']['D'] / disp['coarse+bare']['D']:.3f}x)")
    print(f"    radius lever, reg   : D {disp['coarse+reg']['D']:.3f}x -> "
          f"{disp['fine+reg']['D']:.3f}x  "
          f"({disp['fine+reg']['D'] / disp['coarse+reg']['D']:.3f}x)")
    print(f"    reg lever, coarse   : D {disp['coarse+reg']['D']:.3f}x -> "
          f"{disp['coarse+bare']['D']:.3f}x  "
          f"({disp['coarse+bare']['D'] / disp['coarse+reg']['D']:.3f}x)")
    print(f"    reg lever, fine     : D {disp['fine+reg']['D']:.3f}x -> "
          f"{disp['fine+bare']['D']:.3f}x  "
          f"({disp['fine+bare']['D'] / disp['fine+reg']['D']:.3f}x)")
    return disp, verdict


# --------------------------------------------------------------- B3

STACKS = ["coffee-bubbles", "109MSDCF", "119MSDCF", "113MSDCF", "112MSDCF", "foam",
          "coffee-bean", "wrapped-text-2", "wrapped-text-1", "bee-1", "bee-2", "bee-3"]


def p1_support(z, radius, reg):
    """P1's shape factor for an arbitrary (window, regulariser) pair.

    SD of a box mean of N samples with per-sample SD s_i is
    sqrt(mean(s_i^2)/N), so the shape is sqrt(box(r(z)^2)); the 1/sqrt(N)
    cancels in every ratio taken against the flat plant.
    """
    v = m69.box_clamped(a3mod.r_of_z(z) ** 2, radius)
    if reg is not None:
        v = m69.box_clamped(v, reg)
    return np.sqrt(v)


def b3(b1out):
    m69.banner("B3 -- the corpus on the fine field, all 12 stacks")
    print("  Method of M69 arm A2 / section 6: one real frame per stack as latent,")
    print("  synthetic replicates at the modelled sensor noise.")
    print("  rho_obs is the raw ratio; rho_true applies M69 fact 14's frozen-eta")
    print("  debias (nu_hat^2 = |grad L|^2 - 2 s^2) through EACH FIELD'S OWN support,")
    print("  which is what makes the fine column comparable to fact 13's 1.186x.\n")
    cs = {"fine": b1out["fine+bare"]["sd"], "coarse": b1out["coarse+reg"]["sd"]}
    geom = {"fine": (FINE_WINDOW_RADIUS, None),
            "coarse": (m69.WINDOW_RADIUS, m69.REGULARISER_RADIUS)}
    print(f"  {'stack':<16} {'ISO':>5} | {'fine obs':>9} {'fine true':>9} {'p95/p05':>8} "
          f"| {'crs obs':>8} {'crs true':>9} {'p95/p05':>8}")
    print("  " + "-" * 84)
    out = {}
    for st in STACKS:
        lat, path, y, x = a2mod.read_latent(st, None, None, None)
        iso = m69.iso_of(path)
        sd_dn = a2mod.raw_noise_sd(lat, iso)
        accs = {}
        rng = np.random.default_rng(777)
        for _ in range(a2mod.NREP_EXTRA):
            frame = lat + sd_dn * rng.standard_normal(lat.shape)
            luma = m69.luma_from_raw(frame)
            sig = m69.green_luma_sigma(luma, iso)
            for tag, (radius, reg) in geom.items():
                f = field(luma, radius, reg, sigma=sig)
                if tag not in accs:
                    accs[tag] = m69.Welford(f.shape)
                accs[tag].push(f)

        clean = m69.luma_from_raw(lat)
        sig_c = m69.green_luma_sigma(clean, iso)
        gx, gy = m69.sobel_components(clean)
        z_obs = np.hypot(gx, gy) / (a3mod.S_SOBEL * sig_c)
        z_true = np.sqrt(np.maximum(z_obs**2 - 2.0, 0.0))

        row = {"iso": iso}
        for tag, (radius, reg) in geom.items():
            ins = inset_for(radius, reg)
            sd = m69.interior(accs[tag].sd(), ins)
            r_obs = float(sd.mean() / cs[tag])
            deb = float(
                m69.interior(p1_support(z_true, radius, reg), ins).mean()
                / m69.interior(p1_support(z_obs, radius, reg), ins).mean()
            )
            p05 = float(np.percentile(sd, 5) / cs[tag])
            p95 = float(np.percentile(sd, 95) / cs[tag])
            row[tag] = {"rho_obs": r_obs, "debias": deb, "rho_true": r_obs * deb,
                        "p05": p05, "p95": p95, "within_stack": p95 / p05}
        print(f"  {st:<16} {iso:>5.0f} | {row['fine']['rho_obs']:>9.4f} "
              f"{row['fine']['rho_true']:>9.4f} {row['fine']['within_stack']:>8.3f} | "
              f"{row['coarse']['rho_obs']:>8.4f} {row['coarse']['rho_true']:>9.4f} "
              f"{row['coarse']['within_stack']:>8.3f}")
        out[st] = row

    print()
    for tag in ("fine", "coarse"):
        for kind in ("rho_obs", "rho_true"):
            v = [out[s][tag][kind] for s in STACKS]
            print(f"  E3 {tag:<7} {kind:<8}: min {min(v):.4f}  max {max(v):.4f}  "
                  f"median {np.median(v):.4f}  span {max(v) / min(v):.3f}x")
        w = [out[s][tag]["within_stack"] for s in STACKS]
        print(f"     {tag:<7} p95/p05 WITHIN one stack: min {min(w):.3f}x  "
              f"max {max(w):.3f}x  median {np.median(w):.3f}x\n")
    print("  M69 fact 13's committed coarse rho_true span, same method: 1.186x")
    return out


def main():
    m69.banner("M69 arms B1-B3 -- the FINE field's form  (pre-registered at c545588)")
    m69.dump_constants()
    print(f"  FINE_WINDOW_RADIUS parsed from focus.rs = {FINE_WINDOW_RADIUS}")
    o1 = b1()
    rows = b2(o1)
    disp, verdict = b2_dispersion(rows)
    o3 = b3(o1)
    (m69.OUT / "97-b-fine-field.json").write_text(
        json.dumps({"b1": o1, "b2": rows, "dispersion": disp, "e1_verdict": verdict,
                    "b3": o3, "fine_window_radius": FINE_WINDOW_RADIUS}, indent=2),
        encoding="utf-8",
    )
    print("\n  wrote out/97-b-fine-field.json")


if __name__ == "__main__":
    main()

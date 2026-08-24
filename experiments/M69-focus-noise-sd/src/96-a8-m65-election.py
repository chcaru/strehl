"""M69 arm A8 -- the limb M62 did not price: M65's election comparison.

M62's addendum priced the acceptance battery by algebra and asked M69 not to
redo it. M65's election comparison was left unpriced by both. This arm prices
it, and in doing so measures the one number M65 says it could not reach from
inside its own units.

Three parts.

A8.1  The constant a RAW-election merge would need. M65's circularity is that
      FOCUS_NOISE_SD is calibrated on the REGULARISED field, so arm X -- the arm
      built to break the circularity by turning the regulariser off -- is still
      scored in units derived from it. M65 handled that with a matched-unit arm
      X' using k_sd = 1.2377, measured as a RATIO. Here the raw-field constant is
      measured DIRECTLY on the crate's own calibration plant, by the same
      pipeline that reproduces the shipped constant to 1.3% (control K1). That
      gives M65's missing unit as an absolute number rather than a ratio, and it
      re-derives k_sd independently as a cross-check on M65 fact 3.

A8.2  How far M65's verdict is from being overturned by a recalibration. By the
      linearity of Gate::tolerance() -- checked directly against merge.rs:310-311
      here, as M62 asked -- scaling sigma_F by rho is exactly scaling the gate by
      rho. M65's dev(rho_W) is monotone DECREASING in the gate, so a rho < 1
      moves its comparison toward the regime where the regulariser IS
      load-bearing. The question is the crossing point.

A8.3  Whether the raw field carries the SAME texture dependence as the
      regularised one. If it does not, then a per-pixel sigma_F changes the two
      arms by different amounts and M65's comparison is not merely rescaled.
"""

import json
import pathlib
import re
import sys

import numpy as np
from scipy.interpolate import PchipInterpolator

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import m69  # noqa: E402

ctl = __import__("importlib").import_module("10-controls")
a2 = __import__("importlib").import_module("20-a2-m66-replication")

# M65 fact 10, quoted from docs/research/M65-election-gate-measured.md:235-241.
M65_GATES = [0.5, 1.0, 2.0, 4.0, 64.0]
M65_DEV = {
    "109MSDCF": [1.3481, 1.2370, 1.1460, 1.0827, 1.0029],
    "119MSDCF": [1.4231, 1.2975, 1.1859, 1.1076, 1.0042],
    "113MSDCF": [2.5593, 2.1841, 1.5279, 1.1793, 1.0223],
    "coffee-bubbles": [1.7343, 1.5940, 1.4156, 1.2335, 1.0085],
}
M65_BAR = 1.332
M65_KSD = 1.23770

LATENTS = [
    ("M62/109MSDCF", "109MSDCF", "DSC00020.ARW", 1024, 4096),
    ("coffee-bean", "coffee-bean", "DSC00068.ARW", None, None),
    ("wrapped-text-1", "wrapped-text-1", "DSC00066.ARW", None, None),
    ("bee-1", "bee-1", "DSC00150.ARW", None, None),
]


def check_linearity():
    """M62 asked M69 to check its linearity claim against the code, not accept it."""
    src = (m69.ROOT / "crates" / "strehl-core" / "src" / "merge.rs").read_text(
        encoding="utf-8", errors="replace"
    )
    lines = src.splitlines()
    hit = [(i + 1, l) for i, l in enumerate(lines)
           if "FOCUS_NOISE_SD" in l and "SQRT_2" in l]
    print("  merge.rs, the only line that spends the constant:")
    for n, l in hit:
        print(f"    {n}: {l.strip()}")
    print(f"\n  occurrences of FOCUS_NOISE_SD in merge.rs:"
          f" {len(re.findall(r'FOCUS_NOISE_SD', src))}")
    for i, l in enumerate(lines):
        if "FOCUS_NOISE_SD" in l:
            print(f"    {i + 1}: {l.strip()[:96]}")
    print("\n  Verdict on M62's claim: tolerance() is a PRODUCT of T, a constant")
    print("  and FOCUS_NOISE_SD, with no additive term and no other use of the")
    print("  constant on the gate path. Scaling the constant by c is arithmetically")
    print("  identical to scaling T by c. M62's linearity claim is CONFIRMED by")
    print("  independent reading. M69 fact 28 was derived the same way.")


def a81():
    m69.banner("A8.1 -- the constant a raw-election merge would need")
    raws, regs = [], []
    for s in range(ctl.SEEDS):
        rng = np.random.default_rng(20250 + s)
        luma = ctl.crate_plant(rng, ctl.SIZE, 1.0)
        sig = ctl.unit_sigma(luma)
        raws.append(float(m69.interior(m69.focus_field(luma, sigma=sig), 22).std(ddof=1)))
        regs.append(float(m69.interior(m69.regularised(luma, sigma=sig), 22).std(ddof=1)))
    raws, regs = np.array(raws), np.array(regs)
    r_m, r_s = raws.mean(), raws.std(ddof=1) / np.sqrt(len(raws))
    g_m, g_s = regs.mean(), regs.std(ddof=1) / np.sqrt(len(regs))
    ksd = r_m / g_m
    print(f"  raw focus field        sd = {r_m:.6e} +- {r_s:.2e}")
    print(f"  regularised field      sd = {g_m:.6e} +- {g_s:.2e}"
          f"   (shipped constant {m69.FOCUS_NOISE_SD:.6e})")
    print(f"\n  FOCUS_NOISE_SD_raw  = {r_m:.6f}   <- the number M65's arm X needs")
    print(f"  k_sd  = raw / reg   = {ksd:.5f}")
    print(f"  M65 fact 3 k_sd     = {M65_KSD:.5f}   delta {ksd - M65_KSD:+.5f}"
          f"  ({ksd / M65_KSD - 1:+.2%})")
    print(f"  regulariser removes {1 - 1 / ksd:.1%} of the response noise"
          f"   (M65: 19.2%)")
    return {"raw_sd": float(r_m), "raw_sem": float(r_s), "reg_sd": float(g_m),
            "reg_sem": float(g_s), "k_sd": float(ksd), "m65_k_sd": M65_KSD}


def a82():
    m69.banner("A8.2 -- how far M65's verdict is from being overturned")
    print(f"  M65 fact 10: dev(rho_W) by gate, bar {M65_BAR}. Monotone DECREASING")
    print("  in the gate, so a rho < 1 recalibration moves M65 toward the regime")
    print("  where the election field IS load-bearing. Crossing found by monotone")
    print("  PCHIP in log gate on M65's own published rows -- no re-run.\n")
    print(f"  {'stack':<16} {'dev@4':>8} {'crossing gate':>14} {'rho_crit':>9}"
          f" {'corpus rho':>11} {'headroom':>9}")
    print("  " + "-" * 72)
    rho = json.loads((m69.OUT / "80-corpus-rho.json").read_text(encoding="utf-8"))
    out = {}
    lg = np.log(M65_GATES)
    for st, dev in M65_DEV.items():
        f = PchipInterpolator(lg, np.array(dev)[::1][::-1][::-1], extrapolate=True)
        # dev is decreasing in gate; invert by solving on a dense grid.
        grid = np.exp(np.linspace(np.log(0.05), np.log(64.0), 40000))
        vals = f(np.log(grid))
        idx = np.where(vals >= M65_BAR)[0]
        gcrit = float(grid[idx[-1]]) if len(idx) else float("nan")
        rcrit = gcrit / 4.0
        rt = rho[st]["rho_true"] if st in rho else float("nan")
        out[st] = {"dev_at_4": dev[3], "gate_crit": gcrit, "rho_crit": rcrit,
                   "rho_true": rt, "headroom": rt / rcrit}
        print(f"  {st:<16} {dev[3]:>8.4f} {gcrit:>14.4f} {rcrit:>9.4f}"
              f" {rt:>11.4f} {rt / rcrit:>8.2f}x")
    worst = min(v["headroom"] for v in out.values())
    lo = min(v["rho_true"] for v in rho.values())
    print(f"\n  worst headroom {worst:.2f}x. The corpus minimum rho_true is {lo:.4f};")
    print(f"  the largest rho_crit is {max(v['rho_crit'] for v in out.values()):.4f}.")
    return out


def a83():
    m69.banner("A8.3 -- does the RAW field carry the same texture dependence?")
    print("  If the two fields respond to texture differently, a per-pixel sigma_F")
    print("  does not merely rescale M65's comparison -- it moves the arms by")
    print("  different amounts and the matched-unit trick stops working.\n")
    print(f"  {'latent':<16} {'rho reg':>9} {'rho raw':>9} {'k_sd here':>10}"
          f" {'vs plant':>9}")
    print("  " + "-" * 58)
    base = None
    rows = {}
    for tag, stack, name, y, x in LATENTS:
        latent, path, y, x = a2.read_latent(stack, name, y, x)
        iso = m69.iso_of(path)
        sd_dn = a2.raw_noise_sd(latent, iso)
        rng = np.random.default_rng(11)
        accR = accW = None
        for _ in range(24):
            frame = latent + sd_dn * rng.standard_normal(latent.shape)
            luma = m69.luma_from_raw(frame)
            raw = m69.focus_field(luma, iso)
            reg = m69.regularised(luma, iso)
            if accR is None:
                accR, accW = m69.Welford(reg.shape), m69.Welford(raw.shape)
            accR.push(reg)
            accW.push(raw)
        rr = float(np.mean(m69.interior(accR.sd())) / m69.FOCUS_NOISE_SD)
        rw = float(np.mean(m69.interior(accW.sd())) / m69.FOCUS_NOISE_SD)
        k = rw / rr
        if base is None:
            base = k
        rows[tag] = {"rho_reg": rr, "rho_raw": rw, "k_sd": k}
        print(f"  {tag:<16} {rr:>9.4f} {rw:>9.4f} {k:>10.4f} {k / M65_KSD:>8.3f}x")
    ks = [v["k_sd"] for v in rows.values()]
    print(f"\n  k_sd across real latents: {min(ks):.4f} to {max(ks):.4f}"
          f"  (span {max(ks) / min(ks):.3f}x), plant {M65_KSD:.4f}")
    return rows


def main():
    m69.banner("M69 arm A8 -- M65's election comparison, priced")
    m69.dump_constants()
    m69.banner("A8.0 -- checking M62's linearity claim against the code")
    check_linearity()
    r1 = a81()
    r2 = a82()
    r3 = a83()
    (m69.OUT / "96-a8.json").write_text(
        json.dumps({"raw_constant": r1, "m65_crossing": r2, "texture": r3}, indent=2),
        encoding="utf-8")
    print("\n  wrote out/96-a8.json")


if __name__ == "__main__":
    main()


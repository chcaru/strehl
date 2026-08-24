"""Integrate the measured rho(d) over a CONTIGUOUS admitted window.

Why this file exists
--------------------
`cmd_rho` reports the all-pairs average of the inter-frame pattern correlation.
That is the right statistic only if the merge averages every pair with equal
weight. It does not. `Estimator::fold` admits the frames whose focus response
is within `gate` sigmas of the winner's, and for a unimodal through-focus curve
that admitted set is an *interval* in frame index. Adjacent frames are exactly
the ones with the smallest relative warp, and therefore the highest residual
pattern correlation, so the all-pairs average understates what the merge sees.

This is a separate program from the Rust instrument on purpose: if the two
disagree, the disagreement surfaces instead of being absorbed.

F(m) = W * [ 1/m + (2/m^2) * sum_{d=1}^{m-1} (m - d) * rho(d) ]

The bracket is the standard variance of the mean of `m` unit-variance samples
with a stationary correlation sequence rho(d); W is the within-frame
attenuation the resampler applies before any averaging happens.
"""

import sys

# Measured by `m90-rho sep`, hp = 8, interior margin, pooled over the lattice.
# experiments/M90-prnu/out/rho2-sep-bee-3-cpl.txt and rho2-sep-coffee-bean-m86.txt
RHO = {
    ("bee-3-cpl", "S3-ba-unit", "Nearest"): (0.9902, {
        1: 0.4940, 2: 0.3248, 3: 0.2214, 4: 0.1613, 6: 0.0933, 8: 0.0587,
        12: 0.0260, 16: 0.0134, 24: 0.0038, 32: 0.0007, 48: 0.0003,
        64: 0.0003, 96: -0.0004, 128: 0.0002}),
    ("bee-3-cpl", "S3-ba-unit", "Bilinear"): (0.4729, {
        1: 0.7124, 2: 0.5302, 3: 0.3886, 4: 0.2955, 6: 0.1809, 8: 0.1173,
        12: 0.0541, 16: 0.0276, 24: 0.0082, 32: 0.0019, 48: 0.0003,
        64: 0.0002, 96: -0.0004, 128: 0.0001}),
    ("bee-3-cpl", "S3-ba-unit", "CatmullRom"): (0.6780, {
        1: 0.6801, 2: 0.4800, 3: 0.3341, 4: 0.2448, 6: 0.1419, 8: 0.0885,
        12: 0.0391, 16: 0.0196, 24: 0.0057, 32: 0.0012, 48: 0.0003,
        64: 0.0001, 96: -0.0004, 128: 0.0000}),
    ("bee-3-cpl", "S4-poly4", "CatmullRom"): (0.6763, {
        1: 0.8370, 2: 0.5586, 3: 0.3763, 4: 0.2765, 6: 0.1748, 8: 0.1223,
        12: 0.0634, 16: 0.0354, 24: 0.0113, 32: 0.0040, 48: 0.0006,
        64: -0.0001, 96: -0.0001, 128: 0.0009}),
    ("coffee-bean", "S3-ba-unit", "CatmullRom"): (0.6789, {
        1: 0.5914, 2: 0.2884, 3: 0.1574, 4: 0.0976, 6: 0.0454, 8: 0.0214,
        12: 0.0032, 16: 0.0007, 24: -0.0002, 32: 0.0008, 48: 0.0002,
        64: 0.0004, 96: -0.0004}),
    ("coffee-bean", "S3-ba-unit", "Nearest"): (0.9882, {
        1: 0.4038, 2: 0.1848, 3: 0.1030, 4: 0.0652, 6: 0.0310, 8: 0.0146,
        12: 0.0023, 16: 0.0009, 24: -0.0002, 32: 0.0008, 48: 0.0002,
        64: 0.0004, 96: -0.0004}),
    ("coffee-bean", "S3-ba-unit", "Bilinear"): (0.4756, {
        1: 0.6324, 2: 0.3493, 3: 0.2071, 4: 0.1339, 6: 0.0636, 8: 0.0301,
        12: 0.0046, 16: 0.0007, 24: -0.0001, 32: 0.0010, 48: -0.0000,
        64: 0.0012, 96: -0.0002}),
    ("109MSDCF", "S3-ba-unit", "CatmullRom"): (0.6980, {
        1: 0.3070, 2: 0.1043, 3: 0.0532, 4: 0.0269, 6: 0.0031, 8: -0.0011,
        12: -0.0006, 16: -0.0000}),
    ("flat-on-ruler-cpl", "S3-ba-unit", "CatmullRom"): (0.6840, {
        1: 0.4656, 2: 0.1846, 3: 0.0974, 4: 0.0598, 6: 0.0227, 8: 0.0072,
        12: -0.0008, 16: -0.0014, 24: -0.0003, 32: -0.0005, 48: 0.0006,
        64: 0.0009}),
    ("foam", "S3-ba-unit", "CatmullRom"): (0.6788, {
        1: 0.3077, 2: 0.1091, 3: 0.0556, 4: 0.0283, 6: 0.0060, 8: 0.0015,
        12: 0.0001, 16: -0.0003, 24: -0.0007, 32: 0.0001, 48: -0.0008,
        64: -0.0004, 96: -0.0004}),
    ("bee-2-cpl", "S3-ba-unit", "CatmullRom"): (0.6763, {
        1: 0.6038, 2: 0.3563, 3: 0.2139, 4: 0.1393, 6: 0.0715, 8: 0.0400,
        12: 0.0129, 16: 0.0042, 24: -0.0002, 32: -0.0001, 48: 0.0002,
        64: -0.0003, 96: 0.0001, 128: 0.0003}),
}

# Round 1's per-stack mean n_eff, docs/research/M90-prnu-noise-model.md section 5.4.
STACK_N_EFF = [
    ("foam", 1.35),
    ("109MSDCF", 4.99),
    ("coffee-bean", 22.89),
    ("bee-3-cpl", 44.19),
]

# Round 1's mean n_eff values, docs/research/M90-prnu-noise-model.md section 5.4.
N_EFF = [1.35, 4.99, 7.26, 10.11, 22.89, 44.19]


def rho_at(table, d):
    """Linear interpolation between measured separations; 0 past the last one."""
    if d <= 0:
        return 1.0
    ks = sorted(table)
    if d in table:
        return table[d]
    if d > ks[-1]:
        return 0.0
    lo = max(k for k in ks if k < d)
    hi = min(k for k in ks if k > d)
    t = (d - lo) / (hi - lo)
    return table[lo] + t * (table[hi] - table[lo])


def f_window(w, table, m):
    """F for a contiguous admitted window of `m` frames."""
    if m <= 1:
        return w
    acc = 0.0
    for d in range(1, int(m)):
        acc += (m - d) * rho_at(table, d)
    return w * (1.0 / m + 2.0 * acc / (m * m))


def f_allpairs(w, rho_bar, m):
    """F under a single scalar rho, which is fact 1194's parameterisation."""
    if m <= 1:
        return w
    return w * (1.0 / m + (m - 1.0) / m * rho_bar)


def main():
    print("F over a CONTIGUOUS admitted window vs the all-pairs scalar")
    print("F = 1 is round 1's assumption (fixed pattern, no averaging at all).")
    print("F = W/m is the temporal bound (pattern behaves like white noise).\n")

    for key in RHO:
        case, solver, res = key
        w, table = RHO[key]
        print(f"--- {case} / {solver} / {res}  (W = {w:.4f}) ---")
        print(f"{'n_eff':>8} {'F_window':>10} {'n_prnu':>9} {'F_temporal':>11}"
              f" {'excess':>8} {'vs round1':>10}")
        for m in N_EFF:
            fw = f_window(w, table, m)
            ft = w / m
            print(f"{m:>8.2f} {fw:>10.5f} {1.0 / fw:>9.2f} {ft:>11.5f}"
                  f" {fw / ft:>7.2f}x {(1.0 / fw) ** 0.5:>9.2f}x")
        print()

    # The headline comparison, at the depth the owner actually shoots.
    w, table = RHO[("bee-3-cpl", "S3-ba-unit", "CatmullRom")]
    print("=== the ruling number: bee-3-cpl, CatmullRom (the merge default) ===")
    print(f"{'n_eff':>8} {'window':>9} {'all-pairs':>10} {'ratio':>8}")
    for m in N_EFF:
        fw = f_window(w, table, m)
        fa = f_allpairs(w, 0.0253, m)
        print(f"{m:>8.2f} {fw:>9.5f} {fa:>10.5f} {fw / fa:>7.2f}x")

    # Per-resampler ranking at the owner's depth, which is what settles M86.
    print("\n=== per-resampler, bee-3-cpl S3, at n_eff = 44.19 ===")
    print(f"{'resampler':>12} {'W':>8} {'F_window':>10} {'n_prnu':>9} {'sigma_prnu rel':>15}")
    base = None
    for res in ("Nearest", "Bilinear", "CatmullRom"):
        k = ("bee-3-cpl", "S3-ba-unit", res)
        if k not in RHO:
            continue
        w, table = RHO[k]
        fw = f_window(w, table, 44.19)
        if base is None:
            base = fw
        print(f"{res:>12} {w:>8.4f} {fw:>10.5f} {1.0 / fw:>9.2f}"
              f" {(fw / base) ** 0.5:>14.4f}x")


    # Per-stack, each at its OWN measured rho(d) and its OWN n_eff. This is the
    # number the blast radius is priced at.
    print("\n=== per-stack rho_eff to feed m90-prnu --rho ===")
    print("rho_eff solves (1-rho)/n_eff + rho = F_window, which is exactly the")
    print("split `predicted_sigma_for` applies. A NEGATIVE rho_eff means round 1's")
    print("one-parameter form cannot represent the measurement at that depth.")
    print(f"{'stack':>20} {'n_eff':>8} {'W':>8} {'F_window':>10} {'n_prnu':>8} {'rho_eff':>9}")
    for case, m in STACK_N_EFF:
        k = (case, "S3-ba-unit", "CatmullRom")
        if k not in RHO:
            continue
        w, table = RHO[k]
        fw = f_window(w, table, m)
        gain = 1.0 / m
        rho_eff = (fw - gain) / (1.0 - gain)
        flag = "  <-- UNREPRESENTABLE" if rho_eff < 0 else ""
        print(f"{case:>20} {m:>8.2f} {w:>8.4f} {fw:>10.5f} {1.0 / fw:>8.2f}"
              f" {rho_eff:>9.4f}{flag}")

    # rho(1) alone, which is what round 1 argued from.
    print("\n=== what round 1 argued vs what adjacent frames actually do ===")
    print("Round 1: 'the merge admits precisely the adjacent frames', so rho ~ 1.")
    print(f"{'stack':>20} {'rho(1)':>9} {'rho(2)':>9} {'rho(4)':>9} {'rho(8)':>9} {'d where <0.01':>14}")
    for case in ("109MSDCF", "flat-on-ruler-cpl", "foam", "coffee-bean",
                 "bee-2-cpl", "bee-3-cpl"):
        k = (case, "S3-ba-unit", "CatmullRom")
        if k not in RHO:
            continue
        _, table = RHO[k]
        d0 = next((d for d in range(1, 200) if rho_at(table, d) < 0.01), None)
        print(f"{case:>20} {rho_at(table, 1):>9.4f} {rho_at(table, 2):>9.4f}"
              f" {rho_at(table, 4):>9.4f} {rho_at(table, 8):>9.4f} {d0:>14}")


if __name__ == "__main__":
    sys.exit(main())

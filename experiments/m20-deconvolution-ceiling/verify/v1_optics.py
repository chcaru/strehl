"""M20 verification -- Gate 1: the optics model, re-derived from first principles.

Independent of the author's optgate.py: the diffraction MTF is obtained BOTH from the
closed form AND from a numerical autocorrelation of a circular pupil, and the defocus
OTF BOTH from the closed form AND from a numerically sampled line-spread function.
"""
import numpy as np

PITCH_UM = 5.12          # A7C II sensor pixel pitch
LAM_UM = 0.550           # design wavelength


def f_cut(n_eff):
    """Incoherent diffraction cutoff, cycles per sensor pixel.

    Cutoff in cyc/mm is 1/(lambda*N).  Multiply by pitch to get cyc/px.
    """
    lam_mm = LAM_UM * 1e-3
    pitch_mm = PITCH_UM * 1e-3
    return (1.0 / (lam_mm * n_eff)) * pitch_mm


def mtf_diff_closed(f, n_eff):
    u = np.clip(np.asarray(f, float) / f_cut(n_eff), 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(u) - u * np.sqrt(np.maximum(0.0, 1.0 - u * u)))


def mtf_diff_numeric(u_vals, ngrid=4096):
    """MTF as the normalised autocorrelation area of a unit-radius disc pupil.

    Purely geometric: overlap area of two unit discs offset by u*2 (u = f/f_c),
    divided by the area of one disc.  No formula reused from the closed form.
    """
    ax = np.linspace(-1.0, 1.0, ngrid)
    X, Y = np.meshgrid(ax, ax, indexing="ij")
    pup = ((X * X + Y * Y) <= 1.0).astype(np.float64)
    cell = (ax[1] - ax[0]) ** 2
    area = pup.sum() * cell
    out = []
    for u in np.atleast_1d(u_vals):
        shift_px = (2.0 * u) / (ax[1] - ax[0])
        s = int(round(shift_px))
        if s >= ngrid:
            out.append(0.0)
            continue
        ov = (pup[s:, :] * pup[: ngrid - s, :]).sum() * cell
        out.append(ov / area)
    return np.array(out)


def otf_disc_closed(f, d_px):
    from scipy.special import j1
    x = np.pi * abs(float(d_px)) * np.asarray(f, float)
    o = np.ones_like(x)
    nz = np.abs(x) > 1e-12
    o[nz] = np.abs(2.0 * j1(x[nz]) / x[nz])
    return o


def otf_disc_numeric(f, d_px, ns=200001, half=200.0):
    """1-D line-spread function of a uniform disc of diameter d, then its FT.

    LSF(x) = (2/(pi a^2)) sqrt(a^2 - x^2), a = d/2.  Integrated numerically.
    """
    a = abs(float(d_px)) / 2.0
    if a < 1e-12:
        return np.ones_like(np.asarray(f, float))
    x = np.linspace(-half, half, ns)
    lsf = np.where(np.abs(x) < a, np.sqrt(np.maximum(a * a - x * x, 0.0)), 0.0)
    lsf /= np.trapezoid(lsf, x)
    f = np.atleast_1d(np.asarray(f, float))
    return np.abs(np.array([np.trapezoid(lsf * np.exp(-2j * np.pi * ff * x), x) for ff in f]))


if __name__ == "__main__":
    print("=" * 78)
    print("GATE 1 -- independent re-derivation of the optics model")
    print("=" * 78)
    print(f"pitch = {PITCH_UM} um   lambda = {LAM_UM} um")
    print(f"cutoff constant pitch/lambda = {PITCH_UM/LAM_UM:.6f}  (f_c = that / N_eff, cyc/px)")
    print()

    print("-- cross-check of the closed-form diffraction MTF against pupil autocorrelation --")
    us = np.array([0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 0.902344])
    a = mtf_diff_closed(us * f_cut(1.0), 1.0)
    b = mtf_diff_numeric(us)
    for u, aa, bb in zip(us, a, b):
        print(f"   u={u:.6f}   closed {aa:.6f}   pupil-autocorr {bb:.6f}   diff {aa-bb:+.2e}")
    print()

    print("-- cross-check of the defocus disc OTF against a numerically integrated LSF --")
    for d in (1.0, 2.0, 4.0):
        for ff in (0.05, 0.15, 0.25):
            c = float(otf_disc_closed(np.array([ff]), d)[0])
            n = float(otf_disc_numeric(np.array([ff]), d)[0])
            print(f"   d={d:.1f}px f={ff:.2f}c/px   closed {c:.6f}   numeric-LSF {n:.6f}   diff {c-n:+.2e}")
    print()

    print("=" * 78)
    print("The six gate rows the report claims")
    print("=" * 78)
    n27 = 33.7
    print(f"[row 1] f_c(N_eff={n27})            = {f_cut(n27):.4f} cyc/px   claimed 0.2762  (fact 27 'measured knee')")
    # exact inverse
    n_from_knee = (PITCH_UM / LAM_UM) / 0.2762
    print(f"        inverse: N_eff from knee 0.2762 = {n_from_knee:.4f}   -> B at marked f/11 = {n_from_knee/11:.4f}")
    n_ext = (PITCH_UM / LAM_UM) / 0.5
    print(f"[row 2] N_eff with f_c = Nyquist    = {n_ext:.4f}          claimed 18.618 (fact 12 says 18.6)")
    B = 3.0
    for marked in (5.6, 8.0, 11.0):
        ne = marked * B
        print(f"[row 3-5] marked f/{marked:<4} -> N_eff {ne:5.2f}  f_c {f_cut(ne):.4f}  MTF@Nyq {mtf_diff_closed(0.5, ne):.4f}")
    print(f"[row 6] critical sampling marked    = {n_ext/B:.4f}          claimed 6.206 (fact 28 says 6.21)")
    print()

    print("=" * 78)
    print("CIRCULARITY AUDIT")
    print("=" * 78)
    print("row 1: f_c(33.7)=0.2762 <-> N_eff(0.2762)=33.71.  Same equation, both directions.")
    print("row 2: pitch/(lambda*0.5) is pure arithmetic; no measurement enters.")
    print("row 6: row2 / B; B itself = 33.706/11 = 3.064 (M5 line 26), rounded to 3.0.")
    print("rows 3-5: MTF at N_eff = marked*B, i.e. the same formula at the same B.")
    print()
    print("The ONE non-circular check available in the corpus, which M20 did NOT run:")
    print("  a-priori B = 1 + m/p with m=2.0, p=1.0 -> B = 3.000 -> N_eff(f/11) = 33.000")
    fc_apriori = f_cut(33.0)
    print(f"  predicted knee = {fc_apriori:.4f} cyc/px   measured knee = 0.2762 cyc/px")
    print(f"  ratio measured/predicted = {0.2762/fc_apriori:.4f}  ({abs(0.2762/fc_apriori-1)*100:.1f}% )")
    print()

    print("=" * 78)
    print("B-SENSITIVITY -- the report fixes B=3.0 and never sweeps it")
    print("fact 27 bounds B in [2.41, 3.06]; point estimate 2.6-2.9")
    print("=" * 78)
    print(f"{'B':>6} | {'N_eff f/11':>10} {'MTF@0.25 f/11':>14} | {'N_eff f/5.6':>11} {'MTF@0.25 f/5.6':>15} | {'ratio 5.6/11':>12}")
    for Bv in (2.41, 2.6, 2.75, 2.9, 3.0, 3.064):
        m11 = float(mtf_diff_closed(0.25, 11.0 * Bv))
        m56 = float(mtf_diff_closed(0.25, 5.6 * Bv))
        r = m56 / m11 if m11 > 1e-9 else np.inf
        print(f"{Bv:>6.3f} | {11*Bv:>10.2f} {m11:>14.4f} | {5.6*Bv:>11.2f} {m56:>15.4f} | {r:>12.2f}")

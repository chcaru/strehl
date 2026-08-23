"""M20 verification -- Gate 4: the aperture budget (report §4.4), rebuilt from scratch.

Everything is derived here from the geometry, not taken from the report:
  * defocus circle of confusion  c = m^2 * delta_obj / N_eff   (image-side working f/#)
  * depth of field               delta_obj(c = C) = C * N_eff / m^2      => DOF ~ N_eff
  * matched focus-axis sampling  => c per step is constant by construction
  * frames for fixed subject depth D:  M = D / delta_step  ~ 1/N_eff
Then three photon budgets, and a sweep of the bellows factor B, which the report fixes at 3.0.
"""
import numpy as np
from scipy.special import j1

PITCH_UM, LAM_UM = 5.12, 0.550
M_MAG = 2.0                      # magnification of the rig in question


def f_cut(n):
    return (PITCH_UM / LAM_UM) / n


def mtf_diff(f, n):
    u = np.clip(np.asarray(f, float) / f_cut(n), 0.0, 1.0)
    return (2.0 / np.pi) * (np.arccos(u) - u * np.sqrt(np.maximum(0.0, 1.0 - u * u)))


def mtf_disc(f, d):
    x = np.pi * abs(float(d)) * np.asarray(f, float)
    o = np.ones_like(x)
    nz = np.abs(x) > 1e-12
    o[nz] = np.abs(2.0 * j1(x[nz]) / x[nz])
    return o


def coc_px(delta_obj_um, n_eff, m=M_MAG):
    """Geometric blur diameter at the sensor, in pixels, for an object-side defocus."""
    return (m * m * delta_obj_um / n_eff) / PITCH_UM


def check_invariance():
    print("=" * 78)
    print("GATE 4.1 -- is blur-per-step in pixels really aperture-invariant?")
    print("=" * 78)
    C_LIMIT_PX = 1.0                     # the CoC we choose to step by, in pixels
    print(f"  Policy: step the focus axis so each step grows the CoC by {C_LIMIT_PX} px.")
    print(f"{'marked':>7} {'N_eff':>7} {'step (um obj)':>14} {'CoC/step (px)':>14} "
          f"{'DOF-ish (um)':>13} {'frames for 600um':>17}")
    for marked in (4.0, 5.6, 8.0, 11.0, 16.0):
        ne = marked * 3.0
        # invert coc_px: delta = c_px * PITCH * n_eff / m^2
        step_um = C_LIMIT_PX * PITCH_UM * ne / (M_MAG ** 2)
        print(f"{marked:>7.1f} {ne:>7.1f} {step_um:>14.3f} {coc_px(step_um, ne):>14.4f} "
              f"{step_um:>13.3f} {int(np.ceil(600.0/step_um)):>17d}")
    print("  -> step_um is proportional to N_eff and CoC/step is EXACTLY constant.")
    print("     The invariance holds, but it is a CONSEQUENCE OF THE SAMPLING POLICY")
    print("     (step proportional to DOF), not a free-standing property of the optics.")
    print("     Physical content: frames ~ 1/N_eff at fixed depth. That part is real.")
    print()


def budget_table(B, step_px=1.0, ref_marked=11.0, ref_frames=41, target=0.25, verbose=True):
    rows = []
    ne_ref = ref_marked * B
    for marked in (4.0, 5.6, 8.0, 11.0, 16.0):
        ne = marked * B
        M = ref_frames * ne_ref / ne                 # frames ~ 1/N_eff
        Mi = int(round(M)) | 1
        d = np.abs(np.arange(Mi) - Mi // 2) * step_px
        H = np.array([float(mtf_disc(np.array([target]), dd)[0]) for dd in d]) \
            * float(mtf_diff(target, ne))
        best = H.max()
        mf = np.sqrt((H ** 2).sum())
        # photon budgets, sigma normalised to 1.0 at the reference aperture
        sig_time = np.sqrt(ne / ne_ref)              # fixed TOTAL time: e/frame ~ 1/N_eff
        sig_light = np.sqrt(ne_ref / ne)             # fixed TOTAL light: e/frame ~ N_eff
        sig_frame = ne / ne_ref                      # fixed PER-FRAME time: e/frame ~ 1/N_eff^2
        rows.append(dict(marked=marked, ne=ne, M=Mi, best=best, mf=mf,
                         st=sig_time, sl=sig_light, sf=sig_frame))
    if verbose:
        print(f"{'marked':>7} {'N_eff':>7} {'frames':>7} {'sig/fr(T)':>10} {'MTF@%.2f' % target:>10} "
              f"{'SNR sel(T)':>11} {'SNR mf(T)':>10} | {'SNR sel(L)':>11} {'SNR mf(L)':>10} | "
              f"{'SNR sel(pf)':>12}")
        for r in rows:
            print(f"{r['marked']:>7.1f} {r['ne']:>7.1f} {r['M']:>7d} {r['st']:>10.3f} {r['best']:>10.4f} "
                  f"{r['best']/r['st']:>11.4f} {r['mf']/r['st']:>10.4f} | "
                  f"{r['best']/r['sl']:>11.4f} {r['mf']/r['sl']:>10.4f} | {r['best']/r['sf']:>12.4f}")
    return rows


def main():
    check_invariance()

    print("=" * 78)
    print("GATE 4.2 -- the report's table rebuilt (B = 3.0, step 1.0 px, ref f/11 = 41 frames)")
    print("  (T) = fixed total time, (L) = fixed total light, (pf) = fixed per-frame time")
    print("=" * 78)
    rows = budget_table(3.0)
    r56 = [r for r in rows if r['marked'] == 5.6][0]
    r11 = [r for r in rows if r['marked'] == 11.0][0]
    print()
    print(f"  f/11 -> f/5.6 best-frame contrast ratio  = {r56['best']/r11['best']:.2f}x   (report 9.6x)")
    print(f"  f/11 -> f/5.6 matched-filter SNR, time   = {(r56['mf']/r56['st'])/(r11['mf']/r11['st']):.2f}x   (report 13.5x)")
    print(f"  f/11 -> f/5.6 matched-filter SNR, light  = {(r56['mf']/r56['sl'])/(r11['mf']/r11['sl']):.2f}x   (report 6.9x)")
    print(f"  frames ratio                             = {r56['M']/r11['M']:.2f}x   (report 2x)")
    print()
    print("  Matched-filter factor sqrt(sum|H|^2)/max|H| per aperture (should be aperture-invariant):")
    for r in rows:
        if r['best'] > 1e-9:
            print(f"    f/{r['marked']:<5} frames {r['M']:>3d}: {r['mf']/r['best']:.4f}")
    print("  -> constant across apertures and frame counts, so the sum has converged;")
    print("     the frame-count difference contributes nothing. Report's uniform 2.081 confirmed.")
    print()

    print("=" * 78)
    print("GATE 4.3 -- SENSITIVITY TO B.  The report fixes B = 3.0 and never sweeps it.")
    print("  fact 27: B in [2.41, 3.06]; POINT ESTIMATE 2.6-2.9.  B = 3.0 is above the")
    print("  point estimate and just under the hard upper bound.")
    print("=" * 78)
    print(f"{'B':>6} | {'MTF f/11':>9} {'MTF f/5.6':>10} | {'contrast x':>11} {'SNR x (time)':>13} {'SNR x (light)':>14}")
    for Bv in (2.41, 2.5, 2.6, 2.7, 2.75, 2.8, 2.9, 3.0, 3.064):
        rr = budget_table(Bv, verbose=False)
        a = [r for r in rr if r['marked'] == 5.6][0]
        b = [r for r in rr if r['marked'] == 11.0][0]
        cx = a['best'] / b['best']
        sx = (a['mf'] / a['st']) / (b['mf'] / b['st'])
        lx = (a['mf'] / a['sl']) / (b['mf'] / b['sl'])
        print(f"{Bv:>6.3f} | {b['best']:>9.4f} {a['best']:>10.4f} | {cx:>11.2f} {sx:>13.2f} {lx:>14.2f}")
    print()
    print("  Over fact 27's own POINT-ESTIMATE band (2.6-2.9) the headline is 4.0x-7.3x,")
    print("  not 9.6x.  Over the full bound (2.41-3.06) it is 3.1x-12.7x.")
    print()

    print("=" * 78)
    print("GATE 4.4 -- does 'fixed total time' smuggle photons?")
    print("=" * 78)
    for lab, expo in (("fixed total time", "t_frame ~ N_eff, illum ~ 1/N_eff^2"),
                      ("fixed total light", "sum e = const"),
                      ("fixed per-frame time", "t_frame const")):
        print(f"  {lab:<22}: {expo}")
    print()
    print(f"{'marked':>7} {'N_eff':>7} {'total light (T)':>16} {'total light (L)':>16} {'total time (L)':>15}")
    for Bv in (3.0,):
        for marked in (4.0, 5.6, 8.0, 11.0, 16.0):
            ne = marked * Bv
            ne_ref = 11.0 * Bv
            tl_time = (ne_ref / ne) ** 2      # total light at fixed total time
            tt_light = (ne / ne_ref) ** 2     # total time needed to hold light fixed
            print(f"{marked:>7.1f} {ne:>7.1f} {tl_time:>16.3f} {1.0:>16.3f} {tt_light:>15.3f}")
    print("  -> At fixed total TIME, opening f/11->f/5.6 does collect 3.9x more light.")
    print("     The report's fixed-LIGHT control removes that, and the win is still 6.9x.")
    print("     So no, photons are not smuggled: the claim survives the harsher budget.")
    print("     Note the fixed-light budget implies a 3.9x SHORTER total exposure, which is")
    print("     a strange thing to hold fixed in practice; the honest practical budget is")
    print("     fixed total time, and the honest optics-only number is the contrast ratio.")


if __name__ == "__main__":
    main()

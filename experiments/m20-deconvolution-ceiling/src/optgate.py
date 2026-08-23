import numpy as np
from scipy.special import j1

PITCH_UM = 5.12
LAM_UM   = 0.550

def f_cutoff_cyc_px(n_eff):
    """Diffraction cutoff in cycles per pixel."""
    return PITCH_UM / (LAM_UM * n_eff)

def mtf_diff(f, n_eff):
    u = np.clip(np.asarray(f, float) / f_cutoff_cyc_px(n_eff), 0.0, 1.0)
    return (2.0/np.pi) * (np.arccos(u) - u*np.sqrt(np.maximum(0.0, 1.0-u*u)))

print("=== GATE: reproduce the project's own facts ===")
print("fact 27  cutoff at N_eff=33.7 :", round(f_cutoff_cyc_px(33.7), 4), " (measured f_sig = 0.2762 cyc/px)")
print("fact 12  extinction N_eff for f_c=0.5:", round(PITCH_UM/(LAM_UM*0.5), 3), " (stated 18.6)")
B = 3.0
for marked, neff in [(5.6, 5.6*3.0), (8.0, 8.0*3.0), (11.0, 11.0*3.0)]:
    print(f"  marked f/{marked:<4} -> N_eff {neff:5.1f}  f_c={f_cutoff_cyc_px(neff):.4f} cyc/px  MTF@Nyq={mtf_diff(0.5, neff):.4f}")
print("  fact 12 states MTF@Nyquist = 0.036 / 0.000 / 0.000 at f/5.6, f/8, f/11 (m=2.0)")
print()
# fact 12 quotes N_eff 16.8 at m=2.0 wide -> that is 5.6*3.0. check the f/5.6 row exactly
print("  f/5.6 row recomputed at the fact-12 N_eff of 16.8:", round(float(mtf_diff(0.5, 16.8)), 4))
print("  fact 28 critical sampling: N_marked such that f_c = 0.5 ->",
      round(PITCH_UM/(LAM_UM*0.5)/B, 3), "(stated f/6.21)")

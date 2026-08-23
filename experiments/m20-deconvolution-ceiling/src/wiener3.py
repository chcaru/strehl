import numpy as np
from scipy.special import j1

PITCH_UM, LAM_UM, B = 5.12, 0.550, 3.0     # fact 27: B in [2.41,3.06], point est 2.6-2.9; use 3.0 then sweep

def f_c(n_eff): return PITCH_UM/(LAM_UM*n_eff)
def mtf_diff(f, n_eff):
    u = np.clip(f/f_c(n_eff), 0, 1)
    return (2/np.pi)*(np.arccos(u) - u*np.sqrt(np.maximum(0,1-u*u)))
def mtf_disc(f, d_px):                      # geometric defocus blur, disc of diameter d px
    d = np.asarray(d_px, float)
    x = np.pi*np.outer(d, f) if d.ndim else np.pi*d*f
    out = np.ones_like(x); nz = np.abs(x) > 1e-12
    out[nz] = 2*j1(x[nz])/x[nz]
    return np.abs(out)

f = np.linspace(0.002, 0.5, 400)            # cycles/pixel, up to Nyquist

def analyse(marked, step_px, K=41, label=""):
    """K frames, blur disc grows by step_px per focus step away from best focus."""
    n_eff = marked*B
    d = np.abs(np.arange(K) - K//2)*step_px
    H = mtf_disc(f, d) * mtf_diff(f, n_eff)[None, :]        # (K, F)
    sumH2 = (H**2).sum(0); maxH = H.max(0)
    gain = np.where(maxH > 1e-9, np.sqrt(sumH2)/np.maximum(maxH,1e-12), 0.0)
    return n_eff, f, H, sumH2, maxH, gain

print("=== 4. Multi-frame gain across frequency, at this rig ===")
print("    gain(f) = sqrt(sum_k |H_k(f)|^2) / max_k |H_k(f)|  -- how much SNR the off-peak frames add")
print()
for marked in (5.6, 8.0, 11.0):
    for step in (0.5, 1.0, 2.0, 4.0):
        n_eff, ff, H, sH2, mH, g = analyse(marked, step)
        band = ff < f_c(n_eff)
        # frequency-averaged gain, weighted by where there is anything to gain (|H_best| above 2%)
        w = band & (mH > 0.02)
        gm = g[w].mean() if w.any() else 0.0
        # gain at half the cutoff -- the mid-band the reviewer is talking about
        fh = 0.5*f_c(n_eff); i = np.argmin(np.abs(ff-fh))
        print(f"  marked f/{marked:<4} N_eff {n_eff:5.1f}  step {step:>4.1f} px blur/frame | "
              f"f_c {f_c(n_eff):.3f} c/px | gain@f_c/2 {g[i]:5.3f} | mean gain in band {gm:5.3f} | "
              f"frames w/ |H|>0.1 at f_c/2: {(H[:,i]>0.1).sum():3d}")
    print()

print("=== 5. THE APERTURE QUESTION: fixed total capture time, cover a fixed subject depth ===")
print("    Standard macro practice is stop down to f/11 for depth. Under a reconstruction merge,")
print("    is that right? Budget: total light is fixed. Opening 1 stop doubles light/unit time but")
print("    halves DOF, so needs 2x the frames -> per-frame exposure halves -> net per-frame light x1.")
print("    Sensor-limited photon noise: sigma_perframe ~ 1/sqrt(exposure).")
print()
base = 11.0
for marked in (4.0, 5.6, 8.0, 11.0, 16.0):
    n_eff = marked*B
    stops_open  = np.log2((base/marked)**2)          # light gain per unit time
    frames_mult = base/marked                        # DOF ~ N, so frames scale inversely with N
    per_frame_light = (base/marked)**2 / frames_mult  # = base/marked
    sigma_rel = 1/np.sqrt(per_frame_light)
    # matched-filter SNR ~ sqrt(sum|H|^2)/sigma ; evaluate at a fixed physical detail scale
    step_px = 1.0*(marked/base)                      # finer aperture -> deeper DOF -> coarser step ok
    K = int(41*frames_mult)
    _,ff,H,sH2,mH,g = analyse(marked, step_px, K=K|1)
    target = 0.25                                    # 4-px detail, the scale fact 28 quotes
    i = np.argmin(np.abs(ff-target))
    snr_rel = np.sqrt(sH2[i])/sigma_rel
    print(f"  marked f/{marked:<4} N_eff {n_eff:5.1f} | frames {K|1:3d} | per-frame light x{per_frame_light:.2f} | "
          f"MTF@0.25c/px best-frame {mH[i]:.4f} | matched-filter SNR at 4-px detail (rel) {snr_rel:8.4f}")
print()
print("    (0.25 cyc/px = 4-pixel detail, the scale fact 28 uses for its 46%/90% contrast-loss numbers)")

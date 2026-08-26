"""Radially-averaged power spectrum: is the blend's added energy DETAIL?

Detail recovered by focus stacking is HIGH-frequency by definition -- sharpening
means restoring power near the MTF cutoff. Noise is flat. A coarse-scale blend
artifact is LOW-frequency. These three are distinguishable by spectrum shape,
which is a different statistic from any correlation.

Four signals, all measured by the same code in the same domain:
  white           synthetic, the commissioning control (must come out flat)
  sensor noise    a single real frame's backdrop -- noise after THIS demosaic
  added energy    (AFTER - BEFORE) in the backdrop, which is defocused in every
                  frame and so contains no recoverable detail
  recovered detail (BEFORE - FRAME102) on SUBJECT tiles where the single frame is
                  defocused and the merge is sharp -- genuine focus recovery
"""
import sys
import numpy as np
import tifffile
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from noisefloor import tiles, sigma_std, immerkaer, BOX
from whiteness import resid, hf_fraction, rho_lag1

def green(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"expected uint16, got {a.dtype}"
    return a[:, :, 1].astype(np.float32)

def coarse(t, ds=8):
    n = t.shape[0]; b = t.shape[1]//ds
    return sigma_std(t.reshape(n, b, ds, b, ds).mean(axis=(2, 4)).astype(np.float32))

def rapsd(t):
    """Radially averaged power spectral density, normalised to unit mean."""
    r = resid(t)
    F = (np.abs(np.fft.fft2(r, axes=(1, 2)))**2).mean(axis=0)
    n = F.shape[0]
    fy = np.fft.fftfreq(n)[:, None]; fx = np.fft.fftfreq(n)[None, :]
    rad = np.sqrt(fy**2+fx**2)
    nb = 24
    edges = np.linspace(0, 0.5, nb+1)
    cen, val = [], []
    for i in range(nb):
        m = (rad >= edges[i]) & (rad < edges[i+1])
        if m.sum() == 0: continue
        cen.append(0.5*(edges[i]+edges[i+1])); val.append(F[m].mean())
    cen = np.array(cen); val = np.array(val)
    return cen, val/val.mean()

if __name__ == "__main__":
    pf, pb, pa = sys.argv[1], sys.argv[2], sys.argv[3]
    Gf, Gb, Ga = green(pf), green(pb), green(pa)
    Tf, Tb, Ta = tiles(Gf), tiles(Gb), tiles(Ga)
    del Gf, Gb, Ga
    msig = (Tf.mean(axis=(1, 2))+Tb.mean(axis=(1, 2))+Ta.mean(axis=(1, 2)))/3.0
    cs = (coarse(Tf)+coarse(Tb)+coarse(Ta))/3.0

    back = np.where((msig >= 16000) & (msig < 32000))[0]
    back = back[cs[back] <= np.percentile(cs[back], 10)]

    hf_f = immerkaer(Tf); hf_b = immerkaer(Tb)
    subj = np.where((msig > 2000) & (msig < 30000) & (hf_b > 3.0*np.maximum(hf_f, 1e-6)))[0]
    print(f"backdrop tiles (no detail available) : {back.size}")
    print(f"subject tiles where merge is >3x sharper than frame 102 : {subj.size}")
    if subj.size < 8:
        subj = np.argsort(-(hf_b/np.maximum(hf_f, 1e-6)))[:200]
        print(f"  fallback: top 200 by sharpness ratio")
    print()

    rng = np.random.default_rng(11)
    sets = [
        ("white (control)", np.asarray(rng.normal(0, 50., (back.size, BOX, BOX)), np.float32)),
        ("sensor noise: 1 frame, backdrop", Tf[back].astype(np.float32)),
        ("added energy: AFTER-BEFORE, backdrop", (Ta[back].astype(np.float32)-Tb[back].astype(np.float32))),
        ("recovered detail: BEFORE-frame102, subject", (Tb[subj].astype(np.float32)-Tf[subj].astype(np.float32))),
    ]
    print(f"  {'signal':<44} {'sigma':>9} {'rho_lag1':>10} {'HF frac':>9}")
    plt.figure(figsize=(9, 5.5))
    for n, t in sets:
        s = float(np.median(sigma_std(t)))
        print(f"  {n:<44} {s:9.3f} {float(np.median(rho_lag1(t))):10.4f} "
              f"{float(np.median(hf_fraction(t))):9.4f}")
        c, v = rapsd(t)
        plt.loglog(c, v, marker="o", ms=3, label=n)
    plt.axhline(1.0, color="k", lw=0.6, ls=":")
    plt.xlabel("spatial frequency (cycles/pixel)   ->  Nyquist = 0.5")
    plt.ylabel("radially averaged power (normalised)")
    plt.title("Is the blend's added energy noise, or detail?\n"
              "white is flat; recovered detail rises to high frequency; the added energy does neither")
    plt.legend(fontsize=8); plt.grid(alpha=0.3, which="both")
    plt.tight_layout()
    out = sys.argv[4] if len(sys.argv) > 4 else r"C:\dev\strehl-out\V-BLEND\pics\spectrum.png"
    import os; os.makedirs(os.path.dirname(out), exist_ok=True)
    plt.savefig(out, dpi=130)
    print(f"\nwrote {out}")

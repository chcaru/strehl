"""Even/odd split-half SNR.  Two INDEPENDENT stacks per arm (disjoint frame sets).
   N = (even - odd)/2   -> a pure noise realisation (variance sigma^2/2)
   S = (even + odd)/2   -> signal + noise (noise variance sigma^2/2)
   P_signal = P(S) - P(N).
Registration between the two halves is INTEGER ONLY (AGENTS.md: no resampling).
"""
import json, os, sys
import numpy as np, tifffile

OUT = r"C:\dev\strehl-out\V-GATHER"
BANDS = [(0.05, 0.15), (0.15, 0.25), (0.25, 0.35), (0.35, 0.50)]

def luma(im):
    return 0.2126*im[:, :, 0] + 0.7152*im[:, :, 1] + 0.0722*im[:, :, 2]

def load(subj, half, arm):
    im = tifffile.imread(os.path.join(OUT, f"sp-{subj}-{half}-g{arm}.tiff"))
    return luma(im[:, :, :3].astype(np.float64))

def centre(y, n):
    h, w = y.shape
    r, c = h//2 - n//2, w//2 - n//2
    return y[r:r+n, c:c+n], r, c

def int_shift(a, b, maxs=48):
    """integer (dy,dx) that best aligns b onto a, by phase correlation on
       high-passed crops.  Returns (dy,dx)."""
    n = 1024
    A, _, _ = centre(a, n); B, _, _ = centre(b, n)
    A = A - A.mean(); B = B - B.mean()
    w = np.outer(np.hanning(n), np.hanning(n))
    FA = np.fft.rfft2(A*w); FB = np.fft.rfft2(B*w)
    R = FA*np.conj(FB)
    m = np.abs(R); m[m == 0] = 1.0
    cc = np.fft.irfft2(R/m, s=(n, n))
    cc = np.fft.fftshift(cc)
    k = n//2
    win = cc[k-maxs:k+maxs+1, k-maxs:k+maxs+1]
    iy, ix = np.unravel_index(np.argmax(win), win.shape)
    return iy-maxs, ix-maxs, float(win.max())

def shift_int(y, dy, dx):
    return np.roll(np.roll(y, dy, axis=0), dx, axis=1)

def radial_band_power(y, bands):
    n = y.shape[0]
    w = np.outer(np.hanning(n), np.hanning(n))
    F = np.fft.fftshift(np.fft.fft2((y - y.mean())*w))
    P = (np.abs(F)**2) / (w**2).sum()
    fy = np.fft.fftshift(np.fft.fftfreq(n))[:, None]
    fx = np.fft.fftshift(np.fft.fftfreq(n))[None, :]
    rr = np.sqrt(fy**2 + fx**2)
    out = []
    for lo, hi in bands:
        m = (rr >= lo) & (rr < hi)
        out.append(float(P[m].mean()))
    return out

def analyse(subj, arm, n=2048):
    e = load(subj, "even", arm)
    o = load(subj, "odd", arm)
    dy, dx, pk = int_shift(e, o)
    o2 = shift_int(o, dy, dx)
    E, _, _ = centre(e, n); O, _, _ = centre(o2, n)
    N = (E - O)/2.0
    S = (E + O)/2.0
    pn = radial_band_power(N, BANDS)
    ps = radial_band_power(S, BANDS)
    return {"arm": arm, "shift": [int(dy), int(dx)], "pcpeak": round(pk, 4),
            "mean_DN": float(S.mean()),
            "P_noise": pn, "P_total": ps,
            "P_signal": [max(a-b, 0.0) for a, b in zip(ps, pn)]}

if __name__ == "__main__":
    res = {}
    for subj in ("foam", "wrapped-text-1"):
        res[subj] = {}
        for arm in ("0", "1"):
            r = analyse(subj, arm)
            res[subj][arm] = r
            print(f"{subj} g{arm} shift={r['shift']} pc={r['pcpeak']} mean={r['mean_DN']:.1f}", flush=True)

    # NULL CONTROL: same file against itself must give exactly zero noise.
    e = load("foam", "even", "0")
    E, _, _ = centre(e, 2048)
    z = radial_band_power((E - E)/2.0, BANDS)
    print("NULL (even-even)/2 band powers:", z)

    # POSITIVE CONTROL: inject known white noise of sd=20 DN into one half.
    rng = np.random.default_rng(7)
    o = load("foam", "odd", "0")
    dy, dx, _ = int_shift(e, o)
    O, _, _ = centre(shift_int(o, dy, dx), 2048)
    base = radial_band_power((E - O)/2.0, BANDS)
    inj = radial_band_power((E - (O + rng.normal(0, 20, O.shape)))/2.0, BANDS)
    print("POSCTL noise band power  base:", [f"{v:.4g}" for v in base])
    print("POSCTL noise band power  +sd20:", [f"{v:.4g}" for v in inj])
    print("POSCTL ratio:", [f"{b/a:.3f}" for a, b in zip(base, inj)])

    print()
    print("BAND".ljust(14), "  ".join(f"{lo:.2f}-{hi:.2f}".rjust(11) for lo, hi in BANDS))
    for subj in res:
        for key in ("P_noise", "P_signal", "P_total"):
            a0 = res[subj]["0"][key]; a1 = res[subj]["1"][key]
            rat = [(b/a if a > 0 else float('nan')) for a, b in zip(a0, a1)]
            print(f"{subj[:12]:12s} {key[2:]:7s} g1/g0 " +
                  "  ".join(f"{v:11.3f}" for v in rat))
        print()
    with open(os.path.join(OUT, "splitsnr.json"), "w") as f:
        json.dump(res, f, indent=1)

"""M41 -- corrected tiled Wiener.  REPLACES m41lib.arm_wiener, which was WRONG.

What was wrong (rule 15: new name, new file, say what broke).  m41lib.arm_wiener
did the overlap-add with the WRONG normalisation:

    acc  += L * win          where L ~= win * latent   (L is the deconvolution
    wacc += win               of the WINDOWED tile)
    out   = acc / wacc

so the signal was windowed twice but normalised once -- `out ~= win*latent`,
a position-dependent amplitude error inside every tile.  The DC term was worse:
the tile mean was added INSIDE L and then multiplied by `win` again, so the
reconstructed mean was `mean*win/sum(win)`, not `mean`.

The planted positive control caught it: arm D lost to arm A by 7.11-7.14 dB
PSNR, and the loss was FLAT across a 64x noise sweep (-7.113, -7.120, -7.132,
-7.135 dB at noise x0.25, x1, x4, x16).  A deficit that does not move with noise
is not an estimator limitation, it is a systematic bias -- which is what a
windowing bug is.  Every arm-D/D'/E number in out/a2_run.log is therefore VOID.

The correct weighted overlap-add for a windowed analysis is to accumulate the
window ONCE MORE in the numerator and the window SQUARED in the denominator:

    acc  += (L + mean*win) * win     ->  win^2 * latent
    wacc += win * win
    out   = acc / wacc               ->  latent
"""
import numpy as np
import m41lib as L


def arm_wiener2(cube, reg, g, rn_e, s, use_diff=True, guarded=True, order=None,
                tile=None, step=None):
    T = tile or L.TILE
    S = step or L.STEP
    n, H, W = cube.shape
    acc = np.zeros((H, W), np.float64)
    wacc = np.zeros((H, W), np.float64)
    win1 = np.hanning(T)
    win = np.outer(win1, win1)
    win2 = win * win
    FY = np.broadcast_to(np.fft.fftfreq(T)[:, None], (T, T // 2 + 1)).copy()
    FX = np.broadcast_to(np.fft.rfftfreq(T)[None, :], (T, T // 2 + 1)).copy()
    f2 = np.maximum(FX * FX + FY * FY, (1.0 / T) ** 2)
    hd = L.otf_diffraction(FX, FY) if use_diff else np.ones_like(FX)
    idx = np.arange(n) if order is None else np.asarray(order)
    ys = list(range(0, H - T + 1, S)) or [0]
    xs = list(range(0, W - T + 1, S)) or [0]
    if ys[-1] != H - T: ys.append(H - T)
    if xs[-1] != W - T: xs.append(W - T)
    Hks = {}
    for y in ys:
        for x in xs:
            tl = cube[:, y:y + T, x:x + T]
            rt = reg[:, y:y + T, x:x + T].reshape(n, -1).mean(1)
            kstar = int(np.argmax(rt))
            mean = float(tl[kstar].mean())
            sig2 = 0.5 * (g * max(mean, 0.0) + (rn_e * g) ** 2)
            var_sig = max(float(tl[kstar].var()) - sig2, 1e-3)
            Sf = (1.0 / f2)
            Sf = Sf * (var_sig / Sf.mean())
            num = np.zeros((T, T // 2 + 1), np.complex128)
            den = np.zeros((T, T // 2 + 1), np.float64)
            for k in range(n):
                dk = abs(int(idx[k]) - int(idx[kstar]))
                Hk = Hks.get(dk)
                if Hk is None:
                    Hk = L.otf_defocus(dk * s, FX, FY) * hd
                    Hks[dk] = Hk
                Y = np.fft.rfft2((tl[k] - mean) * win)
                num += Hk * Y
                den += Hk * Hk
            den = den + (sig2 / Sf if guarded else 1e-9)
            Lt = np.fft.irfft2(num / den, s=(T, T))
            acc[y:y + T, x:x + T] += (Lt + mean * win) * win
            wacc[y:y + T, x:x + T] += win2
    return (acc / np.maximum(wacc, 1e-12)).astype(np.float32)

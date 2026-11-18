"""Q3: closed-form response of interpolation kernels by sub-pixel phase.

  python -X utf8 kernel-table.py

For each kernel and frequency f (cycles per source sample, one axis): the
response of the taps at phase phi relative to an ideal shift,
G(phi, f) = sum_n h(n - phi) exp(-2 pi i f (n - phi)) / sum_n h(n - phi),
summarised over 256 phases as: mean |G| (what a merge of many phases
delivers if the phases add in amplitude), |mean G| (if they add coherently),
rms |G| (power), the worst phase, and the noise power sum(w^2) at phase 0.5
(1.0 at phase 0). Two axes multiply.
"""
import numpy as np


def catmull(t):
    a = np.abs(t)
    return np.where(a < 1, 1.5 * a ** 3 - 2.5 * a ** 2 + 1, np.where(a < 2, -0.5 * a ** 3 + 2.5 * a ** 2 - 4 * a + 2, 0.0))


def lanczos(n):
    def k(t):
        return np.where(np.abs(t) < n, np.sinc(t) * np.sinc(t / n), 0.0)
    return k


def kaiser_sinc(half, beta):
    def k(t):
        a = np.abs(t) / half
        w = np.where(a < 1, np.i0(beta * np.sqrt(np.clip(1 - a * a, 0, 1))) / np.i0(beta), 0.0)
        return np.sinc(t) * w
    return k


KERNELS = [('Catmull-Rom (4 taps, shipped)', catmull, 2), ('Lanczos-3 (6 taps)', lanczos(3), 3), ('Lanczos-4 (8 taps)', lanczos(4), 4),
           ('Kaiser sinc, 12 taps, beta 6', kaiser_sinc(6, 6.0), 6), ('Kaiser sinc, 16 taps, beta 7', kaiser_sinc(8, 7.0), 8)]
FREQS = (0.20, 0.30, 0.35, 0.40, 0.45)
phis = (np.arange(256) + 0.5) / 256
print('per axis; columns f = ' + ', '.join(f'{f:.2f}' for f in FREQS))
for name, k, sup in KERNELS:
    n = np.arange(-sup + 1, sup + 1)[None, :]
    t = n - phis[:, None]
    w = k(t)
    w = w / w.sum(1, keepdims=True)
    rows = {'mean |G|': [], '|mean G|': [], 'rms |G|': [], 'worst |G|': []}
    for f in FREQS:
        G = (w * np.exp(-2j * np.pi * f * t)).sum(1)
        rows['mean |G|'].append(np.abs(G).mean())
        rows['|mean G|'].append(np.abs(G.mean()))
        rows['rms |G|'].append(np.sqrt((np.abs(G) ** 2).mean()))
        rows['worst |G|'].append(np.abs(G).min())
    half = k(np.arange(-sup + 1, sup + 1) - 0.5)
    half = half / half.sum()
    print(f'{name}: noise power at phase 0.5 = {float((half ** 2).sum()):.3f}, phase-mean {float((w ** 2).sum(1).mean()):.3f}')
    for label, v in rows.items():
        print(f'    {label:10s} ' + '  '.join(f'{x:.3f}' for x in v))

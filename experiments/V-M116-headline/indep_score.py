"""V-M116 probe 2: an INDEPENDENT re-derivation of M116's headline number.

Nothing here imports M116 code. The box filter, the structure field, the masks
and the quantiles are written from the prose definition in prereg.txt section 5,
using cumulative sums rather than scipy.ndimage, so that a scipy edge-mode
difference would show up as a disagreement rather than be inherited.

HAZARD: tifffile only. dtype asserted on the line after every load.
"""
import json, sys
from pathlib import Path
import numpy as np
import tifffile

M = Path(r"C:\dev\strehl-out\M116\measure")
OUT = Path(r"C:\dev\strehl-out\V-M116")
OUT.mkdir(parents=True, exist_ok=True)
SUBJECTS = ["bee-3-cpl", "foam", "tweezers-cpl"]


def load_green(p: Path) -> np.ndarray:
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, f"{p} loaded as {a.dtype}, NOT uint16 -- refusing"
    assert a.ndim == 3 and a.shape[2] == 3, f"{p} is {a.shape}"
    return a[:, :, 1].astype(np.float64)


def box(a: np.ndarray, k: int) -> np.ndarray:
    """kxk box mean, edge-replicated. Own implementation, integral images."""
    assert a.ndim == 2
    h = k // 2
    pad = np.pad(a, ((h, k - 1 - h), (h, k - 1 - h)), mode="edge")
    c = pad.cumsum(0).cumsum(1)
    c = np.pad(c, ((1, 0), (1, 0)))
    s = c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    return s / (k * k)


def hp(g):     return g - box(g, 5)


def structure(g):
    hh, ww = g.shape[0] // 4, g.shape[1] // 4
    small = g[:hh * 4, :ww * 4].reshape(hh, 4, ww, 4).mean(axis=(1, 3))
    m1, m2 = box(small, 33), box(small * small, 33)
    sd = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))
    up = np.repeat(np.repeat(sd, 4, 0), 4, 1)
    out = np.zeros(g.shape, np.float64)
    out[:up.shape[0], :up.shape[1]] = up[:g.shape[0], :g.shape[1]]
    if up.shape[0] < g.shape[0]: out[up.shape[0]:, :] = out[up.shape[0] - 1, :]
    if up.shape[1] < g.shape[1]: out[:, up.shape[1]:] = out[:, up.shape[1] - 1][:, None]
    return out


def nd(g, mflat, mdet):
    h = hp(g)
    sf, sd_ = float(h[mflat].std()), float(h[mdet].std())
    return sf, sd_, np.log10(sf), np.log10(sd_)


res = {}
for s in SUBJECTS:
    st = structure(load_green(M / f"{s}__M0u.tif"))
    mflat = st <= np.quantile(st, 0.20)
    mdet = st >= np.quantile(st, 0.80)
    g0, g1 = load_green(M / f"{s}__B0.tif"), load_green(M / f"{s}__B1u.tif")
    f0, d0, N0, D0 = nd(g0, mflat, mdet)
    f1, d1, N1, D1 = nd(g1, mflat, mdet)
    # noise-corrected structure amplitude: sd_det^2 = S^2 + n^2, n from flat mask
    S0 = np.sqrt(max(d0 * d0 - f0 * f0, 0.0))
    S1 = np.sqrt(max(d1 * d1 - f1 * f1, 0.0))
    res[s] = dict(N_B0=N0, D_B0=D0, Q_B0=D0 - N0, N_B1u=N1, D_B1u=D1, Q_B1u=D1 - N1,
                  dN=N1 - N0, dD=D1 - D0, dQ=(D1 - N1) - (D0 - N0),
                  dD_noisecorrected=float(np.log10(S1 / S0)),
                  noise_share_B0=float(f0 * f0 / (d0 * d0)),
                  noise_share_B1u=float(f1 * f1 / (d1 * d1)),
                  n_flat=int(mflat.sum()), n_det=int(mdet.sum()))
    r = res[s]
    print(f"== {s}")
    print(f"   B0 : N {N0:+.5f}  D {D0:+.5f}  Q {D0-N0:+.5f}   sd_flat {f0:9.4f} sd_det {d0:9.4f}")
    print(f"   B1u: N {N1:+.5f}  D {D1:+.5f}  Q {D1-N1:+.5f}   sd_flat {f1:9.4f} sd_det {d1:9.4f}")
    print(f"   dD  = {r['dD']:+.5f} dex   <-- M116's headline statistic")
    print(f"   dN  = {r['dN']:+.5f} dex   (flat-ROI control, AGENTS rule 9)")
    print(f"   dQ  = {r['dQ']:+.5f} dex   (flat-controlled band ratio)")
    print(f"   dD noise-corrected = {r['dD_noisecorrected']:+.5f} dex  "
          f"(noise share B0 {100*r['noise_share_B0']:.1f}%, B1u {100*r['noise_share_B1u']:.1f}%)")

(OUT / "indep_score.json").write_text(json.dumps(res, indent=2))
print(f"\nwrote {OUT/'indep_score.json'}")

"""30 -- render M25's control plant once and freeze it.

Reproduces the `discs` control variant of
`experiments/m25-simulator/src/17-multiscale-occluder.py` -- the variant that
produced the 0.19x / 0.23x wrong-sign result recorded in facts 568 and 603 --
using M25's own simulator at M25's own configuration, and writes the rendered
frames plus the truth planes to disk.

Nothing about the plant is varied here.  The point of freezing it is that every
statistic in `31-swap.py` then reads the SAME arrays, so any difference between
them is the statistic and cannot be the plant.

PRE-REGISTERED in PREREGISTRATION-B.md section 4, committed b28b2e3 before this
script existed.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/M60-bimodality/src/30-render-m25-plant.py
"""

from __future__ import annotations

import glob as glob_mod
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.abspath(os.path.join(HERE, "..", "..", "m25-simulator", "src"))
sys.path.insert(0, SIM)

from strehl_sim import build as B                                # noqa: E402
from strehl_sim import config as C                               # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import scene as SC                               # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.config import Breathing, Capture, Optics         # noqa: E402
from strehl_sim.render import RenderConfig, render_stack         # noqa: E402

OUTDIR = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(OUTDIR, "30-m25-plant.npz")
LOG = os.path.join(OUTDIR, "30-render.txt")

# --- every constant below is copied from 17-multiscale-occluder.py -----------
REAL = r"C:\dev\macro\test\coffee-bean"
CROP = (600, 1624, 900, 1924)
CFA, SUPERSAMPLE, MARGIN, SUB, K = 2048, 2, 40, 5, 21
NEAR, FAR, COC = 4.0, 16.0, 1.0

LINES = []


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


def cfg(coc, margin_px=MARGIN, n=K):
    """17-multiscale-occluder.py's cfg(), verbatim."""
    return RenderConfig(
        sensor=C.A7C2,
        optics=Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=50.0, n_frames=n, coc_px_per_frame=coc),
        breathing=Breathing(total_scale_change=-0.04575,
                            centre_x_px=-22.0, centre_y_px=-113.0),
        margin_px=margin_px, seed=1, channels="green", depth_bands=1)


def main() -> None:
    t0 = time.time()
    os.makedirs(OUTDIR, exist_ok=True)
    say("M60b/30 -- freezing M25's control plant (shape='discs')")
    say("Constants copied from 17-multiscale-occluder.py; nothing varied.")
    say()

    import rawpy
    fs = sorted(glob_mod.glob(os.path.join(REAL, "*.ARW")))[::SUB]
    assert len(fs) == K, f"expected {K} frames after {SUB}x subsample, got {len(fs)}"
    G = []
    for f in fs:
        with rawpy.imread(f) as rr:
            g = rr.raw_image_visible[0::2, 1::2].astype(np.float32) - 512
        G.append(g[CROP[0]:CROP[1], CROP[2]:CROP[3]])
    G = np.stack(G)

    iso = S.iso_of(REAL)
    nm = F.NoiseModel.for_iso(iso)
    lv = G.mean(axis=(1, 2))
    mid = G[len(G) // 2]
    beta = B.fit_beta(mid)
    nv = 0.5 * (nm.gain_dn_per_e * mid.mean()
                + (nm.read_noise_e * nm.gain_dn_per_e) ** 2)
    struct = float(np.sqrt(max(mid.std() ** 2 - nv, 1.0)))
    base_e = float(mid.mean()) / nm.gain_dn_per_e
    ce = struct / nm.gain_dn_per_e
    m13 = [x for x in F.design(False) if x.name == "ring-1-3"][0]
    fr = np.array([m13.compute(np.maximum(G[k], 0), nm)[16:-16, 16:-16].mean()
                   for k in range(len(G))])
    peak = int(np.argmax(fr))

    B.set_supersample(SUPERSAMPLE)
    tf, tp, nvp, clamped = B.target_psd(mid, iso)
    freq, amp, hist = B.calibrate_psd(cfg(COC, margin_px=24), (512, 512),
                                      base_e, ce, beta, 101, tf, tp,
                                      float(peak), iters=4)
    psd = (freq, amp)
    say(f"real: ISO {iso:.0f}  g={nm.gain_dn_per_e:.5f} DN/e-  "
        f"mean {mid.mean():.0f} DN  sd {mid.std():.0f} DN  beta {beta:.3f}  "
        f"peak frame {peak}")
    say("PSD shaping mismatch by iteration: "
        + ", ".join(f"{h:.4f}" for h in hist))
    say(f"defocus: coc {COC} px/frame, fg index {NEAR:.0f}, bg index "
        f"{FAR:.0f} -> {abs(FAR - NEAR) * COC:.0f} px blur separation")
    say()

    gain = lv / lv[len(G) // 2]
    tr = time.time()
    sc = SC.two_layer_occlusion(
        (CFA, CFA), SUPERSAMPLE, base_e, ce, base_e * 1.25, ce * 1.25,
        FAR, NEAR, edge_frac=0.35, beta=beta, seed=7,
        margin=MARGIN, psd=psd, shape="discs")

    al = sc.layers[1].alpha
    gy, gx = np.gradient(al)
    per = float(np.sqrt(gy * gy + gx * gx).sum()) / al.size
    feat = 1.0 / max(per, 1e-9)

    st = render_stack(sc, cfg(COC), gain_series=gain)
    Gs = (st.frames[:, 0::2, 1::2].astype(np.float32) - 512)
    vf = st.truth["visible_focus"][0::2, 1::2]
    af = st.truth["alpha_front"][0::2, 1::2]

    say(f"occluder: coverage {al.mean()*100:.1f}%, mean feature ~{feat:.1f} "
        f"latent px ({feat/SUPERSAMPLE:.1f} sensor px)")
    say(f"render {time.time()-tr:.0f}s -> frames {Gs.shape} "
        f"{Gs.dtype}, truth {vf.shape}")
    say(f"frame DN: min {Gs.min():.0f} max {Gs.max():.0f} mean {Gs.mean():.0f}")
    say(f"alpha_front: {(af>0.02).mean()*100:.1f}% >0.02, "
        f"{((af>0.02)&(af<0.98)).mean()*100:.1f}% partial")

    np.savez_compressed(
        OUT, frames=Gs.astype(np.float32), visible_focus=vf.astype(np.float32),
        alpha_front=af.astype(np.float32), gain=gain.astype(np.float64),
        iso=np.float64(iso), g_dn_per_e=np.float64(nm.gain_dn_per_e),
        rn_e=np.float64(nm.read_noise_e), near=np.float64(NEAR),
        far=np.float64(FAR), coc=np.float64(COC))
    say()
    say(f"wrote {OUT}  ({os.path.getsize(OUT)/1e6:.1f} MB)")
    say(f"total {time.time()-t0:.0f}s")

    with open(LOG, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")


if __name__ == "__main__":
    main()

"""13 -- why does the occlusion cell not enrich?  Vary ONE thing: the defocus rate.

Gate 1c attempt 3 (`12-gate1c-shaped.py`) fixed the subject spectrum -- overall
multi-peak fell 28.5 % -> 17.4 % against a real 4.8 % -- and enrichment moved
0.77x -> 1.03x.  Still a FAIL.  Two candidate causes remain and they have
opposite implications:

  (a) the veiling physics is not reproduced -- the simulator is wrong about the
      thing M21 studies, which would be the worst finding in this milestone;
  (b) the *fitted defocus rate* is the problem.  The fit ran to the grid edge
      at 12.0 px/frame.  With the occluder at focus index 4 and the background
      at 16, that puts a 144 px blur disc across the edge -- far wider than
      both the R=2 bimodality scale and the R=13 depth-step scale.  The
      two-depth signature would then be smeared clean out of the detector's
      reach, and no amount of correct veiling physics would show up.

This probe separates them by varying **only** `coc_px_per_frame`, serving the
same occlusion scene into all three of M21's stack slots at three rates.  Every
other parameter -- radiometry, spectrum, gain series, geometry, noise, seed --
is held identical to attempt 3.

If enrichment rises as `coc` falls, cause (b) is established and the FAIL is a
fitting failure, not a physics failure.  If it stays flat near 1.0x at every
rate, cause (a) is established and that is the headline.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/13-coc-probe.py
"""

from __future__ import annotations

import glob as glob_mod
import os
import runpy
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from strehl_sim import build as B                                # noqa: E402
from strehl_sim import config as C                               # noqa: E402
from strehl_sim import focus as F                                # noqa: E402
from strehl_sim import scene as SC                               # noqa: E402
from strehl_sim import stackio as S                              # noqa: E402
from strehl_sim.config import Breathing, Capture, Optics         # noqa: E402
from strehl_sim.render import RenderConfig, render_stack         # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "coc-probe.txt")
M21 = os.path.join(HERE, "..", "..", "m21-occlusion-bimodality", "src",
                   "03-permutation-placebo.py")
REAL = r"C:\dev\macro\test\coffee-bean"
CROP = (600, 1624, 900, 1924)
CFA = 2048
RAW_OFF = (1200, 1800)
SUPERSAMPLE = 2
MARGIN = 40
SUB = 5
K = 21
NEAR, FAR = 4.0, 16.0
COCS = (1.0, 3.0, 12.0)          # 119MSDCF, 109MSDCF, coffee-bean slots
SLOT = {"119MSDCF": 1.0, "109MSDCF": 3.0, "coffee-bean": 12.0}
LINES = []
_STACKS: dict[str, np.ndarray] = {}
_NPATH = {"109MSDCF": K, "119MSDCF": K, "coffee-bean": K * SUB}


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


class _FakeRaw:
    def __init__(self, cfa):
        a = np.full((C.A7C2.height, C.A7C2.width), C.A7C2.black, np.uint16)
        r0, c0 = RAW_OFF
        a[r0:r0 + cfa.shape[0], c0:c0 + cfa.shape[1]] = cfa
        self.raw_image_visible = a

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.raw_image_visible = None
        return False


def _fake_glob(pattern):
    for name, n in _NPATH.items():
        if os.path.normpath(os.path.dirname(pattern)).endswith(name):
            return [f"sim://{name}/{i:04d}.ARW" for i in range(n)]
    raise AssertionError(f"unexpected glob pattern {pattern!r}")


def _fake_imread(path):
    assert path.startswith("sim://"), path
    name, fn = path[len("sim://"):].split("/")
    i = int(fn.split(".")[0])
    if name == "coffee-bean":
        assert i % SUB == 0, f"frame {i} should never be opened"
        i //= SUB
    return _FakeRaw(_STACKS[name][i])


def cfg_coffee(coc, seed=1, depth_bands=12, margin_px=MARGIN, n=K):
    return RenderConfig(
        sensor=C.A7C2,
        optics=Optics(n_marked=11.0, magnification=2.0, pupil_ratio=1.0),
        capture=Capture(iso=50.0, n_frames=n, coc_px_per_frame=coc),
        breathing=Breathing(total_scale_change=-0.04575,
                            centre_x_px=-22.0, centre_y_px=-113.0),
        margin_px=margin_px, seed=seed, channels="green",
        depth_bands=depth_bands)


def main():
    t0 = time.time()
    say("Probe -- is Gate 1c's FAIL a physics failure or a fitting failure?")
    say("varying ONE parameter: coc_px_per_frame in "
        + ", ".join(f"{c}" for c in COCS))
    say("everything else identical to Gate 1c attempt 3 "
        "(12-gate1c-shaped.py)")
    say()

    fs = sorted(glob_mod.glob(os.path.join(REAL, "*.ARW")))[::SUB]
    import rawpy
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
    say(f"real: ISO {iso:.0f}, mean {mid.mean():.0f} DN, sd {mid.std():.0f} DN,"
        f" beta {beta:.3f}, focus peak frame {peak}")

    B.set_supersample(SUPERSAMPLE)
    tf, tp, nvp, clamped = B.target_psd(mid, iso)
    cpsd = cfg_coffee(1.0, depth_bands=1, margin_px=24)
    freq, amp, hist = B.calibrate_psd(cpsd, (512, 512), base_e, ce, beta, 101,
                                      tf, tp, float(peak), iters=4)
    psd = (freq, amp)
    say("PSD shaping mismatch by iteration: "
        + ", ".join(f"{h:.4f}" for h in hist))
    say()

    hw = (CFA, CFA)
    gain = lv / lv[len(G) // 2]
    for name, coc in SLOT.items():
        tr = time.time()
        sc = SC.two_layer_occlusion(
            hw, SUPERSAMPLE, base_e, ce, base_e * 1.25, ce * 1.25, FAR, NEAR,
            shape="discs", edge_frac=0.35, beta=beta, seed=7, margin=MARGIN,
            psd=psd)
        st = render_stack(sc, cfg_coffee(coc, depth_bands=1),
                          gain_series=gain)
        _STACKS[name] = st.frames
        g = st.frames[K // 2][0::2, 1::2].astype(np.float64) - 512
        say(f"slot {name:<12} coc {coc:>5} px/frame -> edge blur "
            f"{coc * (FAR - NEAR):.0f} px   rendered in "
            f"{time.time() - tr:.0f}s   mid green mean {g.mean():.0f} sd "
            f"{g.std():.0f}")
    say()

    say("=" * 78)
    old_glob, old_imread = glob_mod.glob, rawpy.imread
    captured = []
    real_print = print

    def cap(*a, **kw):
        real_print(*a, **kw)
        captured.append(" ".join(str(x) for x in a))

    glob_mod.glob = _fake_glob
    rawpy.imread = _fake_imread
    try:
        import builtins
        old_print = builtins.print
        builtins.print = cap
        try:
            runpy.run_path(M21, run_name="__main__")
        finally:
            builtins.print = old_print
    finally:
        glob_mod.glob = old_glob
        rawpy.imread = old_imread
    LINES.extend(captured)
    say("=" * 78)

    enrich, overall, cur = {}, {}, None
    for ln in captured:
        s = ln.strip()
        for nm_ in ("109MSDCF", "119MSDCF", "coffee-bean"):
            if s.startswith(nm_ + ":"):
                cur = nm_
        if "multi-peak:" in s and cur:
            tag = "real" if s.startswith("REAL") else "perm"
            enrich[(cur, tag)] = float(s.split("=")[1].split("x")[0])
            overall[(cur, tag)] = float(s.split("overall")[1]
                                        .split("%")[0].strip())

    say("SAME occlusion scene, three defocus rates:")
    say(f"{'coc px/frame':>13} {'edge blur':>10} {'overall':>9} "
        f"{'enrich':>7} {'placebo':>8}")
    rows = []
    for nm_, coc in sorted(SLOT.items(), key=lambda kv: kv[1]):
        e = enrich.get((nm_, "real"), float("nan"))
        rows.append((coc, e))
        say(f"{coc:>13} {coc * (FAR - NEAR):>9.0f}p "
            f"{overall.get((nm_, 'real'), float('nan')):>8.1f}% "
            f"{e:>7.2f} {enrich.get((nm_, 'perm'), float('nan')):>8.2f}")
    say(f"{'REAL coffee-bean (M21)':>24}   {4.8:>8.1f}% {4.38:>7.2f} "
        f"{1.01:>8.2f}")
    rows.sort()
    trend = rows[0][1] - rows[-1][1]
    say()
    if trend > 0.3:
        say(f"VERDICT: enrichment RISES as the defocus rate falls "
            f"({rows[-1][1]:.2f}x -> {rows[0][1]:.2f}x).  The Gate 1c FAIL is "
            f"driven by the fitted defocus rate smearing the edge signature "
            f"out of the detector's reach, not by the veiling physics.")
    elif trend < -0.3:
        say("VERDICT: enrichment FALLS as the defocus rate falls -- opposite "
            "to the smearing hypothesis.  Report as unexplained.")
    else:
        say(f"VERDICT: enrichment is FLAT across a 12x range of defocus rate "
            f"({rows[0][1]:.2f}x .. {rows[-1][1]:.2f}x).  The defocus rate is "
            f"NOT the binding cause; the simulator does not reproduce M21's "
            f"enrichment and that is the honest failure axis.")
    say(f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    real_print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

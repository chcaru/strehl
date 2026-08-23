"""07 -- Gate 1c, second attempt: M21's enrichment at the conditions where it exists.

The first attempt (`04-gate1c-occlusion.py`) rendered the occlusion scene with
109MSDCF's **flat-ROI** radiometry -- 1.4 % contrast, structure-to-noise about
1:1 -- and got 81.4 % multi-peak and 0.98x enrichment.  That looked like a
failure.  It is not: M21's own committed table reports 109MSDCF at **60.7 %**
multi-peak and **0.87x** enrichment, and says why -- at R=2 on that stack
"six pixels in ten are already flagged multi-peaked by noise alone.  There is
no dynamic range left for a real second peak to show up in."  The simulator
reproduced the saturated regime faithfully.  **I compared it against a number
measured in the unsaturated one.**

The 4.38x lives on `coffee-bean`, and `coffee-bean` is a different world.
Measured on the real files, at M21's own crop:

  * ISO 50 (g = 0.1145 DN/e-) rather than ISO 160,
  * mean 1528 DN, sd 616 DN -- **40.3 % contrast**, not 1.4 %,
  * modelled green-luma noise 9.36 DN, so structure:noise is about **66:1**,
  * spectral slope beta = 3.45,
  * every 5th frame of 105, so five times the focus step per used frame.

All five come from the real stack.  None is tuned to the enrichment.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/07-gate1c-coffee.py
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
OUT = os.path.join(HERE, "..", "data", "gate1c-shaped.txt")
TRUTH = os.path.join(HERE, "..", "data", "gate1c-shaped-truth.npz")
M21 = os.path.join(HERE, "..", "..", "m21-occlusion-bimodality", "src",
                   "03-permutation-placebo.py")
REAL = r"C:\dev\macro\test\coffee-bean"
CROP = (600, 1624, 900, 1924)
CFA = 2048
RAW_OFF = (1200, 1800)
SUPERSAMPLE = 2
MARGIN = 40
SUB = 5                       # M21 subsamples coffee-bean by 5
K = 21
NEAR, FAR = 4.0, 16.0
COC_GRID = np.round(np.arange(0.5, 12.1, 0.5), 2)
TARGET_ENRICH = 2.0
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
    """Serve simulated frames.  The `coffee-bean` slot is served 105 paths so
    that M21's `[::5]` subsampling picks 21 of them; only those 21 are ever
    opened, and each maps to a distinct rendered frame.  The other 84 paths
    exist solely so the slice arithmetic is the script's, not mine."""
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
    """A render config matched to `coffee-bean`: ISO 50, marked f/11, every
    5th frame of 105.  Drift is 109/119's rate scaled to the used frame span
    -- a generator convenience, labelled as such, not a measurement."""
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
    say("Gate 1c (third attempt) -- shaped subject spectrum, coffee-bean "
        "conditions")
    say(f"M21 script: {os.path.normpath(M21)} (byte-identical via runpy)")
    say()

    # ---- MEASURE the real stack -----------------------------------------
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
    sd = G.std(axis=(1, 2))
    m13 = [x for x in F.design(False) if x.name == "ring-1-3"][0]
    fr = np.array([m13.compute(np.maximum(G[k], 0), nm)[16:-16, 16:-16].mean()
                   for k in range(len(G))])
    peak = int(np.argmax(fr))
    mid = G[len(G) // 2]
    beta = B.fit_beta(mid)
    nv = 0.5 * (nm.gain_dn_per_e * mid.mean()
                + (nm.read_noise_e * nm.gain_dn_per_e) ** 2)
    struct = float(np.sqrt(max(mid.std() ** 2 - nv, 1.0)))
    say(f"MEASURED on real {os.path.basename(REAL)} at M21's crop "
        f"{CROP}, {len(fs)} frames (every {SUB}th of "
        f"{len(sorted(glob_mod.glob(os.path.join(REAL, '*.ARW'))))}):")
    say(f"  ISO {iso:.0f}, g {nm.gain_dn_per_e:.4f} DN/e-, "
        f"RN {nm.read_noise_e:.2f} e-")
    say(f"  reference frame {len(G) // 2}: mean {mid.mean():.1f} DN, "
        f"sd {mid.std():.1f} DN -> contrast "
        f"{100 * mid.std() / mid.mean():.1f}%")
    say(f"  modelled green-luma noise {np.sqrt(nv):.2f} DN -> "
        f"structure:noise = {struct / np.sqrt(nv):.0f}:1")
    say(f"  spectral slope beta {beta:.3f}; focus peaks at frame {peak}")
    say(f"  per-frame level peak-to-peak "
        f"{100 * (lv.max() - lv.min()) / lv.mean():.2f}% (MEASURED, injected)")
    say()

    # ---- fit the one free parameter to the real through-focus sd curve ----
    B.set_supersample(SUPERSAMPLE)
    base_e = float(mid.mean()) / nm.gain_dn_per_e
    target = sd / sd[peak]
    small = (512, 512)

    # ---- measure the subject's radial power spectrum and shape to it ------
    # Done BEFORE the coc fit, because the fit's through-focus curve depends
    # on which spatial frequencies the subject actually has: a single power
    # law fitted on 0.02-0.20 cyc/px starves the fine detail that defocus
    # destroys first, and the fitted coc then runs away to the grid edge.
    tf, tp, nvp, clamped = B.target_psd(mid, iso)
    say(f"target PSD: {clamped} of {len(tf)} radial bins clamped at the "
        f"modelled noise floor ({nvp:.3g} DN^2/bin)")
    cpsd = cfg_coffee(1.0, depth_bands=1, margin_px=24)
    freq, amp, hist = B.calibrate_psd(cpsd, small, base_e,
                                      struct / nm.gain_dn_per_e, beta, 101,
                                      tf, tp, float(peak), iters=4)
    psd = (freq, amp)
    say("calibrate_psd shape mismatch (median |log ratio|) by iteration: "
        + ", ".join(f"{h:.4f}" for h in hist))
    say("DECLARED: this widens the fitted nuisance set from one number (beta)")
    say("  to a 64-bin radial profile of the subject's second-order")
    say("  statistics.  A radial power spectrum is stationary and isotropic")
    say("  and carries NO information about which pixels sit at a depth")
    say("  discontinuity, which is the only thing this gate scores.")
    say()

    best = None
    for coc in COC_GRID:
        cfg = cfg_coffee(float(coc), depth_bands=1, margin_px=24)
        cfg.shot = cfg.read = cfg.fpn = False
        sc = SC.flat_texture(small, SUPERSAMPLE, base_e,
                             struct / nm.gain_dn_per_e * 2, float(peak),
                             beta=beta, seed=101, margin=24, psd=psd)
        st = render_stack(sc, cfg)
        s2 = np.array([S.green_value(st.frames[k]).std() for k in range(K)])
        curve = s2 / s2[peak]
        err = float(np.sqrt(np.mean((curve - target) ** 2)))
        if best is None or err < best[1]:
            best = (float(coc), err, curve)
    coc, err, curve = best
    say(f"fitted coc = {coc} px/frame (grid {COC_GRID[0]}..{COC_GRID[-1]}), "
        f"RMS shape error {err:.4f}")
    say("  real: " + " ".join(f"{v:4.2f}" for v in target))
    say("  sim : " + " ".join(f"{v:4.2f}" for v in curve))
    say()

    # ---- three cells at those conditions ---------------------------------
    hw = (CFA, CFA)
    ce = struct / nm.gain_dn_per_e
    cells = {
        "109MSDCF": (cfg_coffee(coc, depth_bands=1), SC.two_layer_occlusion(
            hw, SUPERSAMPLE, base_e, ce, base_e * 1.25, ce * 1.25, FAR, NEAR,
            shape="discs", edge_frac=0.35, beta=beta, seed=7, margin=MARGIN,
            psd=psd)),
        "119MSDCF": (cfg_coffee(coc), SC.stepped_plane(
            hw, SUPERSAMPLE, base_e, ce, NEAR, FAR, edge_frac=0.35, beta=beta,
            seed=7, margin=MARGIN, psd=psd)),
        "coffee-bean": (cfg_coffee(coc), SC.tilted_plane(
            hw, SUPERSAMPLE, base_e, ce, NEAR, FAR, beta=beta, seed=7,
            margin=MARGIN, psd=psd)),
    }
    say("cells: 109MSDCF slot = OCCLUSION (depth step WITH alpha edge, the "
        "test);")
    say("       119MSDCF slot = TERRACE  (same depth step, NO alpha edge);")
    say("       coffee-bean   = TILT     (depth variation, NO step).")
    say(f"       occluder at focus index {NEAR}, background at {FAR}.")
    say()
    truth = {}
    gain = lv / lv[len(G) // 2]
    for name, (cfg, sc) in cells.items():
        tr = time.time()
        st = render_stack(sc, cfg, gain_series=gain)
        _STACKS[name] = st.frames
        g = st.frames[K // 2][0::2, 1::2].astype(np.float64) - 512
        say(f"rendered {name:<12} {st.frames.shape} in {time.time() - tr:.0f}s"
            f"   mid green mean {g.mean():.0f} DN sd {g.std():.0f} DN "
            f"(real {mid.mean():.0f} / {mid.std():.0f})")
        truth[name + "/visible_focus"] = st.truth["visible_focus"]
        truth[name + "/best_frame"] = st.truth["best_frame"]
        truth[name + "/alpha_front"] = st.truth["alpha_front"]

    vf = truth["109MSDCF/visible_focus"][0::2, 1::2]
    af = truth["109MSDCF/alpha_front"][0::2, 1::2]
    assert vf.shape == (1024, 1024), vf.shape
    tstep = (np.abs(np.gradient(vf)[0]) + np.abs(np.gradient(vf)[1])) >= 1.0
    say()
    say("ground truth on the occlusion cell's crop (TRUE, not estimated -- "
        "this is the thing the real corpus cannot supply):")
    say(f"  foreground coverage {100 * (af > 0.5).mean():.1f}%")
    say(f"  true depth-step pixels {int(tstep.sum())}")
    say(f"  partial-coverage (0.02 < alpha < 0.98) pixels "
        f"{int(((af > 0.02) & (af < 0.98)).sum())}")
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
    occ, occp = enrich.get(("109MSDCF", "real")), enrich.get(("109MSDCF",
                                                              "perm"))
    say(f"{'cell':<26} {'overall':>8} {'enrich':>7} {'placebo':>8}")
    for nm_, lbl in (("109MSDCF", "occlusion (TEST)"),
                     ("119MSDCF", "terrace (no alpha edge)"),
                     ("coffee-bean", "tilt (no depth step)")):
        say(f"{lbl:<26} {overall.get((nm_, 'real'), float('nan')):>7.1f}% "
            f"{enrich.get((nm_, 'real'), float('nan')):>7.2f} "
            f"{enrich.get((nm_, 'perm'), float('nan')):>8.2f}")
    say(f"{'REAL coffee-bean (M21)':<26} {4.8:>7.1f}% {4.38:>7.2f} "
        f"{1.01:>8.2f}")
    say(f"{'REAL 109MSDCF (M21)':<26} {60.7:>7.1f}% {0.87:>7.2f} "
        f"{1.01:>8.2f}")
    ok = (occ is not None and occ >= TARGET_ENRICH
          and occp is not None and abs(occp - 1.0) <= 0.15)
    say(f"GATE 1c: {'PASS' if ok else 'FAIL'}  (enrichment >= "
        f"{TARGET_ENRICH}x AND placebo 1.00 +/- 0.15)  "
        f"[{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    np.savez_compressed(TRUTH, **truth)
    real_print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

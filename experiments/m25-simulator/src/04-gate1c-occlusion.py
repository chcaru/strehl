"""04 -- Gate 1c: M21's occlusion bimodality, on a scene with ground truth.

M21 measured that through-focus curves are **4.38x enriched** in
multi-peakedness at depth steps versus smooth depth, and that permuting the
frame order collapses this to **1.01x**.  It could not check whether that
enrichment is *caused* by occlusion, because on a real capture there is no
truth behind an occluder.

This runs M21's committed `03-permutation-placebo.py` **byte-identical**, via
`runpy`, against a shim that makes `glob.glob` and `rawpy.imread` serve
simulated frames.  The script is not modified, not re-implemented and not
paraphrased: whatever it measures on real files it measures here.

Its three hard-coded stack slots are repurposed as three cells:

  slot            cell                       what it isolates
  109MSDCF    ->  occlusion                  depth step WITH an alpha edge
  119MSDCF    ->  terrace                    the same depth step, NO alpha edge
  coffee-bean ->  tilt                       depth variation, NO step at all

Cells 2 and 3 are controls that cannot exist on real data.  Cell 1 is the
test.  The permutation placebo inside the script is a fourth control that runs
on all three.

Run:
    $env:PYTHONIOENCODING='utf-8'
    python experiments/m25-simulator/src/04-gate1c-occlusion.py
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
from strehl_sim.render import render_stack                       # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data", "gate1c-occlusion.txt")
TRUTH = os.path.join(HERE, "..", "data", "gate1c-truth.npz")
M21 = os.path.join(HERE, "..", "..", "m21-occlusion-bimodality", "src",
                   "03-permutation-placebo.py")
REAL = r"C:\dev\macro\test\109MSDCF"
REAL_ROI = S.Roi(2272, 1344, 256, 256)

# M21 crops the green plane at [600:1624, 900:1924].  green = raw[0::2,1::2],
# so it needs raw rows 1200..3248 and raw cols 1801..3849.  A 2048x2048 CFA
# block placed at raw offset (1200, 1800) covers exactly that, and preserves
# RGGB parity because both offsets are even.
CFA = 2048
RAW_OFF = (1200, 1800)
SUPERSAMPLE = 2
MARGIN = 40
K = 22
COC = 1.0
NEAR, FAR = 5.0, 16.0
TARGET_ENRICH = 2.0
LINES = []
_STACKS: dict[str, np.ndarray] = {}


def say(s=""):
    print(s, flush=True)
    LINES.append(s)


class _FakeRaw:
    def __init__(self, cfa):
        vh, vw = C.A7C2.height, C.A7C2.width
        a = np.full((vh, vw), C.A7C2.black, np.uint16)
        r0, c0 = RAW_OFF
        a[r0:r0 + cfa.shape[0], c0:c0 + cfa.shape[1]] = cfa
        self.raw_image_visible = a

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.raw_image_visible = None
        return False


def _fake_glob(pattern):
    for name in _STACKS:
        if os.path.normpath(os.path.dirname(pattern)).endswith(name):
            n = _STACKS[name].shape[0]
            return [f"sim://{name}/{i:04d}.ARW" for i in range(n)]
    raise AssertionError(f"unexpected glob pattern {pattern!r}")


def _fake_imread(path):
    assert path.startswith("sim://"), path
    name, fn = path[len("sim://"):].split("/")
    return _FakeRaw(_STACKS[name][int(fn.split(".")[0])])


def build_cells(base_e, contrast_e, beta):
    hw = (CFA, CFA)
    cells = {}
    cfg = B.cfg_109(COC, n_frames=K, seed=1, margin_px=MARGIN,
                    channels="green")
    cells["109MSDCF"] = (cfg, SC.two_layer_occlusion(
        hw, SUPERSAMPLE, base_e, contrast_e, base_e * 1.6, contrast_e * 1.6,
        FAR, NEAR, shape="discs", edge_frac=0.35, beta=beta, seed=7,
        margin=MARGIN))

    cfg2 = B.cfg_109(COC, n_frames=K, seed=1, margin_px=MARGIN,
                     channels="green")
    cfg2.depth_bands = 12
    cells["119MSDCF"] = (cfg2, SC.stepped_plane(
        hw, SUPERSAMPLE, base_e, contrast_e, NEAR, FAR, edge_frac=0.35,
        beta=beta, seed=7, margin=MARGIN))

    cfg3 = B.cfg_109(COC, n_frames=K, seed=1, margin_px=MARGIN,
                     channels="green")
    cfg3.depth_bands = 12
    cells["coffee-bean"] = (cfg3, SC.tilted_plane(
        hw, SUPERSAMPLE, base_e, contrast_e, NEAR, FAR, beta=beta, seed=7,
        margin=MARGIN))
    return cells


def main():
    t0 = time.time()
    say("Gate 1c -- M21's occlusion bimodality on scenes with ground truth")
    say(f"M21 script: {os.path.normpath(M21)} (run byte-identical via runpy)")
    say(f"CFA {CFA}x{CFA} at raw offset {RAW_OFF}; supersample {SUPERSAMPLE}; "
        f"margin {MARGIN}; K={K}; coc {COC} px/frame")
    say(f"foreground/near focus index {NEAR}, background/far {FAR} "
        f"(depth step {FAR - NEAR:.0f} frames)")
    say()

    raw = S.load_real(REAL)
    iso = S.iso_of(REAL)
    _, rval = S.tiles(raw, REAL_ROI, 0)
    ref = rval[raw.shape[0] // 2]
    base_e, contrast_e = B.fit_radiometry(ref, iso)
    beta = B.fit_beta(ref)
    del raw
    say(f"fitted from real 109MSDCF: base {base_e:.1f} e-, "
        f"contrast {contrast_e:.1f} e-, beta {beta:.3f}")

    B.set_supersample(SUPERSAMPLE)
    # Contrast is calibrated on the SAME optics but a small tile, then reused;
    # the attenuation is a property of the PSF and the texture spectrum, not of
    # the tile size, so this is legitimate and much cheaper.
    cal_cfg = B.cfg_109(COC, n_frames=1, seed=1, margin_px=MARGIN,
                        channels="green")
    contrast_e = B.calibrate_contrast(cal_cfg, (512, 512), base_e, contrast_e,
                                      beta, 101,
                                      contrast_e * F.NoiseModel.for_iso(iso).gain_dn_per_e,
                                      iso)
    say(f"calibrated latent contrast {contrast_e:.1f} e- sd")
    say()

    truth = {}
    for name, (cfg, sc) in build_cells(base_e, contrast_e, beta).items():
        tr = time.time()
        st = render_stack(sc, cfg)
        _STACKS[name] = st.frames
        g = st.frames[K // 2][0::2, 1::2].astype(np.float64) - 512
        say(f"rendered {name:<12} {st.frames.shape} in {time.time() - tr:.0f}s"
            f"   mid-frame green mean {g.mean():.1f} DN, sd {g.std():.1f} DN")
        truth[name + "/visible_focus"] = st.truth["visible_focus"]
        truth[name + "/best_frame"] = st.truth["best_frame"]
        truth[name + "/alpha_front"] = st.truth["alpha_front"]
    say()

    # --- ground truth the real corpus cannot supply -----------------------
    # The rendered block is 2048x2048 CFA at raw offset (1200, 1800), and M21
    # crops green[600:1624, 900:1924] -- which is exactly the block's whole
    # green plane, block[0::2, 1::2].  Checked, not assumed: see the offset
    # arithmetic in the module docstring.
    vf = truth["109MSDCF/visible_focus"][0::2, 1::2]
    af = truth["109MSDCF/alpha_front"][0::2, 1::2]
    assert vf.shape == (1024, 1024), vf.shape
    say("ground truth on the occlusion cell's crop (TRUE, not estimated):")
    say(f"  foreground coverage {100 * (af > 0.5).mean():.1f}% of pixels")
    say(f"  true depth-step pixels (|grad true focus| >= 1): "
        f"{int((np.abs(np.gradient(vf)[0]) + np.abs(np.gradient(vf)[1]) >= 1.0).sum())}")
    say(f"  partial-coverage (0.02 < alpha < 0.98) pixels: "
        f"{int(((af > 0.02) & (af < 0.98)).sum())}")
    say()

    say("=" * 78)
    say("M21 03-permutation-placebo.py, verbatim, on the simulated stacks:")
    say("-" * 78)
    import rawpy
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

    say("-" * 78)
    enrich = {}
    cur = None
    for ln in captured:
        s = ln.strip()
        for nm in ("109MSDCF", "119MSDCF", "coffee-bean"):
            if s.startswith(nm + ":"):
                cur = nm
        if "multi-peak:" in s and cur:
            tag = "real" if s.startswith("REAL") else "perm"
            enrich[(cur, tag)] = float(s.split("=")[1].split("x")[0])
    occ = enrich.get(("109MSDCF", "real"))
    occp = enrich.get(("109MSDCF", "perm"))
    ter = enrich.get(("119MSDCF", "real"))
    til = enrich.get(("coffee-bean", "real"))
    say(f"occlusion cell enrichment  = {occ}   (M21 real corpus: 4.38x)")
    say(f"occlusion cell placebo     = {occp}  (M21 real corpus: 1.01x)")
    say(f"terrace  cell enrichment   = {ter}   (control: depth step, no alpha edge)")
    say(f"tilt     cell enrichment   = {til}   (control: no depth step)")
    ok = (occ is not None and occ >= TARGET_ENRICH
          and occp is not None and abs(occp - 1.0) <= 0.15)
    say(f"GATE 1c: {'PASS' if ok else 'FAIL'}  "
        f"(criterion: enrichment >= {TARGET_ENRICH}x AND placebo 1.00 +/- 0.15)"
        f"  [{time.time() - t0:.0f}s]")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(LINES) + "\n")
    np.savez_compressed(TRUTH, **truth)
    real_print(f"wrote {os.path.normpath(OUT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

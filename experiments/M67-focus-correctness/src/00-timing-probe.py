"""00 -- feasibility probe. Timings and shapes ONLY.

Deliberately prints no focus, admission or correctness statistic of any kind.
It exists so that the pre-registration in `PREREGISTRATION.md` can name a plant
size and a frame count that are actually renderable, without any result
existing before the pre-registration is committed.

    $env:PYTHONIOENCODING='utf-8'
    python experiments/M67-focus-correctness/src/00-timing-probe.py
"""

from __future__ import annotations

import os
import sys
import time

import numpy as np

M25 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "..", "..", "m25-simulator", "src")
sys.path.insert(0, os.path.normpath(M25))

from strehl_sim import build as B            # noqa: E402
from strehl_sim import stackio as S          # noqa: E402
from strehl_sim.render import render_stack   # noqa: E402

REAL = r"D:\personal\macro\109MSDCF"


def main() -> int:
    t0 = time.time()
    raw = S.load_real(REAL)
    iso = S.iso_of(REAL)
    print(f"real stack {REAL}: {raw.shape}, ISO {iso}  "
          f"({time.time() - t0:.0f}s)")

    roi = S.Roi(2272, 1344, 256, 256)
    _, rval = S.tiles(raw, roi, 0)
    ref = rval[raw.shape[0] // 2]
    base_e, contrast_e = B.fit_radiometry(ref, iso)
    beta = B.fit_beta(ref)
    del raw
    print(f"fitted: base {base_e:.1f} e-, contrast {contrast_e:.1f} e- sd, "
          f"beta {beta:.3f}; real ROI mean {ref.mean():.2f} DN "
          f"sd {ref.std():.4f} DN")

    for side, K, bands in ((512, 25, 49), (1024, 25, 49)):
        B.set_supersample(2)
        cfg = B.cfg_109(1.0, n_frames=K, seed=1, channels="green",
                        depth_bands=bands)
        cfg.breathing.__class__  # noqa: B018 - keep the import obvious
        sc = B.tilt_scene(cfg, (side, side), base_e, contrast_e, beta,
                          span_frames=float(K - 1), seed=101)
        t = time.time()
        st = render_stack(sc, cfg)
        dt = time.time() - t
        print(f"side {side:4d}  K {K}  bands {bands}: frames "
              f"{st.frames.shape} {st.frames.dtype}, truth keys "
              f"{sorted(st.truth)}, best_frame {st.truth['best_frame'].shape}"
              f"  render {dt:.0f}s  ({dt / K:.1f}s/frame)")
        print(f"           bytes/stack u16 = "
              f"{st.frames.nbytes / 1e6:.1f} MB")
        del st
    print(f"total {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

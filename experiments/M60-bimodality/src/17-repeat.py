"""M60 — the independent replicate.

bee-2 and bee-3 are 299-frame captures of the SAME scene at two ISOs (scene
identity NCC 0.9562, data/03-previews.txt). That gives something this project
rarely has: two independent draws of the same truth. It supports two tests that
need no ground-truth depth at all.

  repeatability   |k1(bee-3) - k1(bee-2)| is the estimator's own error at each
                  pixel. A confidence signal is worth having exactly insofar as
                  it predicts that error. That is the reviewer's claim for
                  posterior entropy, and it is testable here.
  reproducibility does a pixel flagged bimodal in one capture flag in the other?
                  A detector firing on 78% of band pixels but agreeing with
                  itself at chance would be measuring the noise realisation.

Runs bee-3's cell rectangles on bee-2. Same rects are legitimate only because
the scene did not move; the frame-offset between the two stacks is measured, not
assumed.
"""

import os
import sys
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m60lib as L  # noqa: E402
from cells import CELLS, STACK_ISO  # noqa: E402
import importlib
C = importlib.import_module("09-curves")

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "data"))
OUT = os.path.join(DATA, "curves")
REPS = int(os.environ.get("M60_REPS", "12"))


if __name__ == "__main__":
    src_stack, dst_stack = "bee-3", "bee-2"
    cs = [c for c in CELLS if c[0] == src_stack]
    iso = STACK_ISO[dst_stack]
    fs = L.frames(dst_stack)
    n = len(fs)
    print("%s : %d frames, ISO %.0f, %d cells borrowed from %s"
          % (dst_stack, n, iso, len(cs), src_stack), flush=True)

    # reuse the frozen pixel selection from bee-3 so the two captures are
    # compared at exactly the same pixels
    sel = {}
    for (_, name, _, y0, y1, x0, x1) in cs:
        d = np.load(os.path.join(OUT, "%s__%s.npz" % (src_stack, name)))
        sel[name] = (d["sel"], d["lab"])

    F = {name: np.zeros((n, len(sel[name][0])), np.float32) for name in sel}
    S = {name: np.zeros((n, len(sel[name][0])), np.float32) for name in sel}
    rng = np.random.default_rng(1702)
    t0 = time.time()
    for k, f in enumerate(fs):
        P = L.load_green(f).astype(np.float32)
        for (_, name, _, y0, y1, x0, x1) in cs:
            a = P[y0:y1, x0:x1]
            ii = sel[name][0]
            F[name][k] = C.focus(a).ravel()[ii]
            sd = L.sigma_dn(a, iso)
            s1 = np.zeros(len(ii)); s2 = np.zeros(len(ii))
            for _ in range(REPS):
                v = C.focus(a + rng.normal(0, 1, a.shape).astype(np.float32) * sd).ravel()[ii]
                s1 += v; s2 += v.astype(np.float64) ** 2
            S[name][k] = np.sqrt(np.maximum(s2 / REPS - (s1 / REPS) ** 2, 0)
                                 * REPS / (REPS - 1))
        if k % 40 == 0:
            print("   frame %d/%d  %.0fs" % (k, n, time.time() - t0), flush=True)
    for (_, name, cls, y0, y1, x0, x1) in cs:
        np.savez_compressed(os.path.join(OUT, "%s__%s.npz" % (dst_stack, name)),
                            F=F[name], S=S[name], lab=sel[name][1], sel=sel[name][0],
                            cls=np.array([cls]), stack=np.array([dst_stack]),
                            rect=np.array([y0, y1, x0, x1]), reps=np.array([REPS]),
                            Ibar=np.load(os.path.join(
                                OUT, "%s__%s.npz" % (src_stack, name)))["Ibar"])
        print("   wrote %s__%s" % (dst_stack, name), flush=True)

"""M60 control N1 — the noise-only null.

For each cell, one real frame (chosen by INDEX n//2, never by any focus measure)
is replicated n times and given independent draws of the injected noise model.
The scene, the signal level, the texture and the noise model are those of the
real cell; the only thing removed is through-focus variation. The detector is
then run exactly as on real data.

This is what calibrates the threshold z*: the 99th percentile of z here is the
value at which the detector fires on 1% of pixels that CANNOT be bimodal. It is
per cell, so every class is compared at a matched false-positive rate.

The null is built from a real frame, not from the noise constant alone, so it
cannot validate the noise model itself (AGENTS rule 34 / fact 599) -- it
validates the detector's null distribution given that model.
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
OUT = os.path.join(DATA, "null")
REPS = int(os.environ.get("M60_REPS", "12"))
SEED = 9100


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    want = set(sys.argv[1:])
    by_stack = {}
    for c in CELLS:
        if want and c[0] not in want:
            continue
        by_stack.setdefault(c[0], []).append(c)

    for stack, cs in by_stack.items():
        iso = STACK_ISO[stack]
        fs = L.frames(stack)
        n = len(fs)
        base = L.load_green(fs[n // 2]).astype(np.float32)
        rng = np.random.default_rng(SEED)
        t0 = time.time()
        for (_, name, cls, y0, y1, x0, x1) in cs:
            src = os.path.join(DATA, "curves", "%s__%s.npz" % (stack, name))
            if not os.path.exists(src):
                print("   skip %s (no curves yet)" % name, flush=True)
                continue
            sel = np.load(src)["sel"]
            a = base[y0:y1, x0:x1]
            sd = L.sigma_dn(a, iso)
            F = np.zeros((n, len(sel)), np.float32)
            S = np.zeros((n, len(sel)), np.float32)
            for k in range(n):
                obs = a + rng.normal(0, 1, a.shape).astype(np.float32) * sd
                F[k] = C.focus(obs).ravel()[sel]
                s1 = np.zeros(len(sel), np.float64)
                s2 = np.zeros(len(sel), np.float64)
                for _ in range(REPS):
                    v = C.focus(obs + rng.normal(0, 1, a.shape).astype(np.float32) * sd
                                ).ravel()[sel]
                    s1 += v
                    s2 += v.astype(np.float64) ** 2
                S[k] = np.sqrt(np.maximum(s2 / REPS - (s1 / REPS) ** 2, 0.0)
                               * REPS / (REPS - 1))
            np.savez_compressed(os.path.join(OUT, "%s__%s.npz" % (stack, name)),
                                F=F, S=S, cls=np.array([cls]))
            print("   null %s__%s  n=%d P=%d  %.0fs"
                  % (stack, name, n, len(sel), time.time() - t0), flush=True)

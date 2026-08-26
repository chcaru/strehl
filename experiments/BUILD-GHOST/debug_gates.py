#!/usr/bin/env python3
"""Debug: why did measure_pair report not-ok?  Prints the gate census."""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ghostlib as G  # noqa: E402

P = sys.argv[1] if len(sys.argv) > 1 else r"D:\personal\macro\couch-fibers-cpl\DSC00150.ARW"
f = G.decode_plane(P)
ga = f["g"]
print("plane", ga.shape, "mean", ga.mean())


def noise_mod(g):
    s = g[:1024, :1024]
    d = s[:-1, :-1] - s[:-1, 1:] - s[1:, :-1] + s[1:, 1:]
    return float(np.sqrt(np.mean(d * d) / 4.0) / max(float(s.mean()), 1.0))


nm = noise_mod(ga)
print("noise_mod", nm, " hf floor =", G.HF_FLOOR_REL * nm)

oc = G.tile_origins(ga.shape, G.TILE_COARSE, G.STRIDE_COARSE, G.MAX_SHIFT_COARSE)
print("coarse tiles", oc.shape)
A = G.gather_tiles(ga, oc, G.TILE_COARSE)
hf = G.hf_modulation(A)
print("hf percentiles", np.percentile(hf, [1, 10, 50, 90, 99]))
d, rho = G.zncc_shift(A, A.copy(), G.MAX_SHIFT_COARSE)
print("rho percentiles", np.percentile(rho, [1, 10, 50, 90, 99]))
print("d[:5]", d[:5])
print("pass rho", int((rho >= G.RHO_FLOOR).sum()))
print("pass hf ", int((hf >= G.HF_FLOOR_REL * nm).sum()))
r = G.measure_pair(ga, ga.copy())
print("ok", r.ok, "reason", r.reason, "ncoarse", r.n_coarse, "used", r.n_coarse_used,
      "fine kept", r.n_fine_kept, "/", r.n_fine_total)

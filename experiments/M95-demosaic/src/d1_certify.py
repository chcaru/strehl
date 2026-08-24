"""K6 -- certify the Python MHC port against the shipped Rust demosaic.

A Python reimplementation says NOTHING about what strehl ships until it is
shown to agree with what strehl ships. This is that proof, and it gates every
other number in arm 6: if this fails, `d2_ladder.py` refuses to run.

It exercises three inputs on purpose:
  * random      -- no structure, so every stencil tap is loaded independently
  * checkerboard-- maximum CFA-frequency content, where a parity error is loudest
  * ramp        -- MHC's stencils are exact for linear content, so a parity or
                   sign error shows up as a large error rather than a small one

and two sizes, one of them odd, because the mirror border rule
(`reflect()` in demosaic.rs) has different behaviour at an odd extent and a
border bug is invisible on an even one.

Exit 0 = certified. Exit 1 = the port is not the shipped algorithm.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import m95dem  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
EXE = ROOT / "target-m95" / "release" / "examples" / "m95-demosaic.exe"
SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M95-demosaic\scratch")
OUT = pathlib.Path(__file__).resolve().parents[1] / "out"

# tolerance: the Rust accumulates 9-11 f32 terms in a loop, scipy correlates in
# f32 with a different summation order, so bit-equality is not the right bar.
# 1e-6 relative to the input range is ~4 ulp of f32 at unit scale.
TOL = 1e-6


def cases():
    rng = np.random.default_rng(20260824)
    yield "random-256x256", rng.random((256, 256)).astype(np.float32)
    yield "random-129x131", rng.random((129, 131)).astype(np.float32)
    y, x = np.mgrid[0:64, 0:64]
    yield "checker-64x64", ((x + y) % 2).astype(np.float32)
    yield "ramp-64x64", ((x * 3 + y * 7) / 500.0).astype(np.float32)


def run_rust(M, kind):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    h, w = M.shape
    fi = SCRATCH / "cert_in.f32"
    fo = SCRATCH / "cert_out.f32"
    fi.write_bytes(np.ascontiguousarray(M, dtype="<f4").tobytes())
    r = subprocess.run(
        [str(EXE), str(fi), str(w), str(h), str(fo), kind],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"m95-demosaic failed: {r.stderr.strip()}")
    a = np.frombuffer(fo.read_bytes(), dtype="<f4")
    return a.reshape(h, w, 3).astype(np.float32)


def main() -> int:
    if not EXE.exists():
        print(f"FAIL: {EXE} not built")
        return 1
    rows, worst = [], 0.0
    for name, M in cases():
        for kind, fn in (("mhc", m95dem.demosaic_mhc),
                         ("bilinear", m95dem.demosaic_bilinear)):
            rust = run_rust(M, kind)
            py = fn(M)
            d = float(np.abs(rust - py).max())
            worst = max(worst, d)
            rows.append({"case": name, "kind": kind, "max_abs_diff": d,
                         "ok": d <= TOL})
            print(f"  {name:16s} {kind:9s} max|rust-py| = {d:.3e}"
                  f"  {'OK' if d <= TOL else 'MISMATCH'}")

    # A certification that cannot fail certifies nothing. Prove the comparison
    # is live by handing it a port with one stencil tap wrong.
    rng = np.random.default_rng(7)
    M = rng.random((64, 64)).astype(np.float32)
    good = m95dem.demosaic_mhc(M)
    saved = m95dem.F_G.copy()
    try:
        m95dem.F_G = saved.copy()
        m95dem.F_G[2, 2] += 0.125  # one tap, one eighth
        bad = m95dem.demosaic_mhc(M)
    finally:
        m95dem.F_G = saved
    planted = float(np.abs(good - bad).max())
    planted_caught = planted > TOL
    print(f"  {'planted-tap':16s} {'mhc':9s} max|good-bad| = {planted:.3e}"
          f"  {'DETECTED' if planted_caught else 'MISSED'}")

    ok = all(r["ok"] for r in rows) and planted_caught
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "d1_certify.json").write_text(json.dumps({
        "tolerance": TOL, "rows": rows, "worst_max_abs_diff": worst,
        "planted_tap_delta": planted, "planted_caught": planted_caught,
        "certified": ok,
    }, indent=2), encoding="utf-8")

    print()
    print(f"K6 worst disagreement over {len(rows)} cases : {worst:.3e}  (tol {TOL:.0e})")
    print(f"K6 planted one-tap defect detected          : {planted_caught}")
    print("K6 CERTIFIED" if ok else "K6 FAILED -- the port is not the shipped algorithm")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

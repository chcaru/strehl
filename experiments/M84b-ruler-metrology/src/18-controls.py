"""M84b step 18 - the controls that can fail, and are made to fail.

Pre-registration section 8 requires three things and this script does all three,
announcing its test count as rule 36 requires.

  S  a SYNTHETIC POSITIVE control: plant a projective graduation lattice with a
     known tilt and known pitch, run the same fitter, and require it back.
  G1 a BYTE-PLANTED mutation of the physical pitch, 1.0 mm -> 1.1 mm, verified
     by read-back of the file on disk, required to move the reported
     magnification, then restored and asserted byte-for-byte identical.
  G2 a BYTE-PLANTED sign inversion of the projective coefficient C, likewise
     verified, required to break the fit, likewise restored.

Templated on experiments/M81-estimation-merge/unit_mutation_control.py.

The mutations are applied to a PRIVATE COPY of the analysis module under
src/_control_target.py, never to the analysis scripts themselves, so a crash
mid-run cannot leave the measurement pipeline mutated. The copy's byte
equality with its source is asserted before and after.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
OUT = ROOT / "out"

PITCH_MM = 1.0  # G1 mutates this literal on disk
C_SIGN = 1.0  # G2 mutates this literal on disk


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fit_projective(k: np.ndarray, x: np.ndarray, seed_c: float = 0.0) -> dict:
    """The same Huber-IRLS projective fit used in steps 12, 13, 15 and 17."""
    A = B = 0.0
    C = seed_c
    prev = np.array([np.inf, np.inf, np.inf])
    w = np.ones_like(x)
    for _ in range(200):
        v = 1.0 / np.maximum(1.0 + C * k, 1e-6)
        M = np.column_stack([np.ones_like(k), k, -x * k])
        sw = np.sqrt(w * v)
        sol, *_ = np.linalg.lstsq(M * sw[:, None], x * sw, rcond=None)
        A, B, C = sol
        r = x - (A + B * k) / (1.0 + C * k)
        s = 1.4826 * np.median(np.abs(r - np.median(r))) + 1e-12
        c = 1.345 * s
        w = np.where(np.abs(r) <= c, 1.0, c / np.maximum(np.abs(r), 1e-12))
        cur = np.array([A, B, C])
        if np.all(np.abs(cur - prev) <= 1e-10 * np.maximum(np.abs(cur), 1e-12)):
            break
        prev = cur
    r = x - (A + B * k) / (1.0 + C * k)
    return {
        "A": float(A),
        "B": float(B),
        "C": float(C),
        "resid_rms": float(np.sqrt(np.mean(r**2))),
    }


def synthesise(theta_deg: float, m_px_per_mm: float, Z0_mm: float,
               x_pp: float, n: int, pitch_mm: float, noise_px: float,
               seed: int, X0_mm: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Plant a graduation lattice from an exactly known plane."""
    rng = np.random.default_rng(seed)
    th = np.radians(theta_deg)
    f = m_px_per_mm * Z0_mm
    k = np.arange(n, dtype=float)
    Xk = X0_mm + k * pitch_mm * np.cos(th)
    Zk = Z0_mm + k * pitch_mm * np.sin(th)
    xi = f * Xk / Zk
    x = xi + x_pp + rng.normal(0.0, noise_px, n)
    return k, x


# --------------------------------------------------------------------------
# S: synthetic positive control (two-view closure) and its negative twin
# --------------------------------------------------------------------------
QUAD_PITCH_UM = 10.24


def solve_two_view(b_f, c_f, b_a, c_a, P_mm, m_ratio=1.0):
    """Byte-for-byte the closure of src/15-closure.py, re-stated here so the
    control exercises the estimator the measurement actually used."""
    Rb = (b_f / b_a) * m_ratio
    Rc = (c_a / c_f) / m_ratio
    denom = Rb * Rb * Rc * Rc - 1.0
    sf2 = (Rb * Rb - 1.0) / denom
    if not (0.0 <= sf2 < 1.0):
        return None
    sf = np.sqrt(sf2)
    sa = Rc * sf
    if not (0.0 <= sa < 1.0):
        return None
    th_f, th_a = np.arcsin(sf), np.arcsin(sa)
    m_f = b_f / (P_mm * np.cos(th_f))
    f_px = m_f * P_mm * sf / c_f
    return {
        "theta_flat_deg": float(np.degrees(th_f)),
        "theta_ang_deg": float(np.degrees(th_a)),
        "m_quadpx_per_mm": float(m_f),
        "m": float(m_f * QUAD_PITCH_UM / 1000.0),
        "f_mm": float(f_px * QUAD_PITCH_UM / 1000.0),
        "Z0_mm": float(f_px / m_f),
        "dZ_per_grad_ang_um": float(1000.0 * P_mm * sa),
    }


def centred(A, B, C, x_pp):
    return A - x_pp, B - C * x_pp, C


TRUTH = {
    "theta_flat_deg": 3.323,
    "theta_ang_deg": 77.351,
    "m_quadpx_per_mm": 265.605,
    "Z0_mm": 75.566,
    "x_pp": 1757.0,
    "pitch_mm": PITCH_MM,
    "noise_px": 0.27,
}


def _plant_views(seed: int):
    """Plant BOTH views of one exactly known rig: a near-flat target and a
    steeply tilted one, sharing m, f and Z0 exactly as the two stacks are
    assumed to."""
    t = TRUTH
    views = {}
    for tag, th_deg, n, X0 in (
        ("flat", t["theta_flat_deg"], 13, -5.5),
        ("ang", t["theta_ang_deg"], 13, -0.22),
    ):
        k, x = synthesise(
            th_deg, t["m_quadpx_per_mm"], t["Z0_mm"], t["x_pp"], n,
            t["pitch_mm"], t["noise_px"], seed + hash(tag) % 1000, X0
        )
        f = fit_projective(k, x)
        views[tag] = centred(f["A"], f["B"], f["C"], t["x_pp"]) + (f["resid_rms"],)
    return views


def control_S1() -> tuple[bool, dict]:
    """POSITIVE: the two-view closure must return the planted plane."""
    v = _plant_views(0x4D84B018)
    got = solve_two_view(v["flat"][1], v["flat"][2], v["ang"][1], v["ang"][2],
                         TRUTH["pitch_mm"])
    if got is None:
        return False, {"pass": False, "reason": "closure returned None"}
    d_th = abs(got["theta_ang_deg"] - TRUTH["theta_ang_deg"])
    d_m = abs(got["m_quadpx_per_mm"] - TRUTH["m_quadpx_per_mm"]) / TRUTH["m_quadpx_per_mm"]
    dZ_true = 1000.0 * TRUTH["pitch_mm"] * np.sin(np.radians(TRUTH["theta_ang_deg"]))
    d_dZ = abs(got["dZ_per_grad_ang_um"] - dZ_true) / dZ_true
    ok = bool(d_th < 0.5 and d_m < 0.01)
    return ok, {
        "planted": TRUTH,
        "recovered": got,
        "theta_ang_error_deg": float(d_th),
        "m_error_rel": float(d_m),
        "dZ_error_rel": float(d_dZ),
        "resid_rms_px": {t: v[t][3] for t in v},
        "bars": "theta_ang error < 0.5 deg, m error < 1.0 %",
        "pass": ok,
    }


def control_S2() -> tuple[bool, dict]:
    """NEGATIVE, and it is MEANT to fail: the same planted lattice, recovered by
    a SINGLE-view inversion with Z0 assumed known. At theta = 80.5 degrees
    sin(theta) = 0.986 and d(theta)/d(sin theta) = 1/cos(theta) = 6.0 rad, so a
    sub-percent error in the fitted C explodes into degrees of tilt. This
    control exists to show that the single-view route the dispatch's framing
    implies is NOT usable here, and that the two-view closure of step 15 is
    load-bearing rather than decorative."""
    v = _plant_views(0x4D84B018)
    _, b_a, c_a, _ = v["ang"]
    sin_t = c_a * TRUTH["Z0_mm"] / TRUTH["pitch_mm"]
    if abs(sin_t) > 1.0:
        th = float("nan")
        m = float("nan")
    else:
        th = float(np.degrees(np.arcsin(sin_t)))
        m = float(b_a / (TRUTH["pitch_mm"] * np.cos(np.radians(th))))
    d_th = abs(th - TRUTH["theta_ang_deg"]) if np.isfinite(th) else float("inf")
    # The control PASSES when the single-view route demonstrably fails.
    fails_as_predicted = bool(not np.isfinite(th) or d_th > 0.5)
    return fails_as_predicted, {
        "single_view_theta_deg": th,
        "single_view_m_quadpx_per_mm": m,
        "theta_error_deg": d_th,
        "expectation": "single-view inversion must MISS by more than 0.5 deg",
        "conditioning_dtheta_per_dsin_rad": float(
            1.0 / np.cos(np.radians(TRUTH["theta_ang_deg"]))
        ),
        "pass": fails_as_predicted,
    }


# --------------------------------------------------------------------------
# The byte-planted mutations
# --------------------------------------------------------------------------
TARGET = SRC / "_control_target.py"

TARGET_SOURCE = '''"""Private mutation target for M84b step 18. Not part of the measurement path.

Reproduces the step-15 two-view closure from the saved fits, so that a planted
byte error exercises the same dependency structure the real measurement has:
theta comes from the DIMENSIONLESS ratios Rb, Rc and is therefore independent
of the assumed pitch, while m, f, Z0 and the depth scale all scale with it.
"""
import json, pathlib, sys
import numpy as np

PITCH_MM = 1.0
C_SIGN = 1.0

ROOT = pathlib.Path(__file__).resolve().parents[1]
QUAD_PITCH_UM = 10.24
X_PP = 1757.0
X0_ROI = 1100.0


def main():
    clos = json.loads((ROOT / "out" / "15-closure.json").read_text())
    out = {}
    for tag in ("flat", "ang"):
        f = clos["fits_absolute"][tag]
        A, B = f["A"], f["B"]
        C = C_SIGN * f["C"]
        xp = X_PP  # step 15 now writes ABSOLUTE fits for both stacks
        out[tag] = (B - C * xp, C)
    b_f, c_f = out["flat"]
    b_a, c_a = out["ang"]
    Rb = b_f / b_a
    Rc = c_a / c_f
    denom = Rb * Rb * Rc * Rc - 1.0
    sf2 = (Rb * Rb - 1.0) / denom
    if not (0.0 <= sf2 < 1.0):
        print(json.dumps({"error": "sin^2(theta_flat) out of range", "sf2": sf2}))
        return 2
    sf = float(np.sqrt(sf2))
    sa = Rc * sf
    if not (0.0 <= sa < 1.0):
        print(json.dumps({"error": "sin(theta_ang) out of range", "sa": sa}))
        return 2
    th_f = float(np.degrees(np.arcsin(sf)))
    th_a = float(np.degrees(np.arcsin(sa)))
    m_f = b_f / (PITCH_MM * np.cos(np.radians(th_f)))
    f_px = m_f * PITCH_MM * sf / c_f
    if not (m_f > 0.0 and f_px > 0.0):
        print(json.dumps({"error": "non-physical closure: m or f non-positive",
                          "m_f": float(m_f), "f_px": float(f_px)}))
        return 2
    print(json.dumps({
        "PITCH_MM": PITCH_MM, "C_SIGN": C_SIGN,
        "theta_flat_deg": th_f, "theta_ang_deg": th_a,
        "m_quadpx_per_mm": float(m_f),
        "m": float(m_f * QUAD_PITCH_UM / 1000.0),
        "f_mm": float(f_px * QUAD_PITCH_UM / 1000.0),
        "dZ_per_grad_um": float(1000.0 * PITCH_MM * sa),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def run_target() -> dict:
    r = subprocess.run(
        [sys.executable, str(TARGET)], capture_output=True, text=True,
        cwd=str(ROOT),
    )
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": "unparseable", "rc": r.returncode,
                "stdout": r.stdout[-400:], "stderr": r.stderr[-400:]}


def plant(old: str, new: str) -> None:
    text = TARGET.read_text()
    assert old in text, f"plant site {old!r} not present"
    TARGET.write_text(text.replace(old, new, 1))


def mutation(name: str, old: str, new: str, baseline: dict,
             moves: str, expect_broken: bool) -> tuple[bool, dict]:
    before = sha256(TARGET)
    plant(old, new)
    # READ-BACK VERIFICATION: prove the bytes on disk really changed.
    readback = TARGET.read_text()
    planted = new in readback and old not in readback.replace(new, "")
    after_plant = sha256(TARGET)
    changed = after_plant != before
    got = run_target()
    if expect_broken:
        detected = "error" in got
    else:
        b, g = baseline.get(moves), got.get(moves)
        detected = (
            b is not None and g is not None
            and abs(g - b) > 1e-6 * max(abs(b), 1.0)
        )
    # A mutation that changes NOTHING in the output is undetectable whatever the
    # specific bar says, so record that too.
    any_change = got != baseline
    # restore
    TARGET.write_text(TARGET_SOURCE)
    restored = sha256(TARGET)
    byte_equal = restored == before
    post = run_target()
    same_as_baseline = post == baseline
    ok = bool(planted and changed and detected and byte_equal and same_as_baseline)
    return ok, {
        "name": name,
        "plant": f"{old} -> {new}",
        "readback_confirms_plant": bool(planted),
        "hash_changed_on_plant": bool(changed),
        "sha_before": before,
        "sha_planted": after_plant,
        "sha_restored": restored,
        "restored_byte_identical": bool(byte_equal),
        "baseline": baseline,
        "mutated_output": got,
        "post_restore_output": post,
        "post_restore_matches_baseline": bool(same_as_baseline),
        "mutation_detected": bool(detected),
        "any_output_change": bool(any_change),
        "pass": ok,
    }


def main() -> int:
    OUT.mkdir(exist_ok=True)
    tests = []

    ok_s1, det_s1 = control_S1()
    tests.append(("S1 synthetic positive control, two-view closure", ok_s1, det_s1))
    ok_s2, det_s2 = control_S2()
    tests.append(("S2 negative control, single-view inversion must fail",
                  ok_s2, det_s2))

    TARGET.write_text(TARGET_SOURCE)
    baseline = run_target()
    assert "error" not in baseline, f"target broken before any mutation: {baseline}"
    print(f"  target baseline: {json.dumps(baseline)}")

    ok_g1, det_g1 = mutation(
        "G1 wrong physical pitch", "PITCH_MM = 1.0", "PITCH_MM = 1.1",
        baseline, moves="m_quadpx_per_mm", expect_broken=False,
    )
    tests.append(("G1 pitch 1.0 -> 1.1 mm", ok_g1, det_g1))

    ok_g2, det_g2 = mutation(
        "G2 inverted projective coefficient", "C_SIGN = 1.0", "C_SIGN = -1.0",
        baseline, moves="theta_ang_deg", expect_broken=True,
    )
    tests.append(("G2 sign-inverted C", ok_g2, det_g2))

    TARGET.unlink(missing_ok=True)

    n_pass = sum(1 for _, ok, _ in tests if ok)
    print(f"M84b step 18 controls: running {len(tests)} tests")
    for name, ok, det in tests:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
        if name.startswith("S1"):
            print(f"          planted theta_ang {det['planted']['theta_ang_deg']} deg, "
                  f"m {det['planted']['m_quadpx_per_mm']} quad px/mm, "
                  f"noise {det['planted']['noise_px']} px")
            print(f"          recovered theta_ang "
                  f"{det['recovered']['theta_ang_deg']:.4f} deg "
                  f"(err {det['theta_ang_error_deg']:.4f}, bar 0.5), m "
                  f"{det['recovered']['m_quadpx_per_mm']:.3f} quad px/mm "
                  f"(err {det['m_error_rel'] * 100:.4f}%, bar 1.0%), dZ err "
                  f"{det['dZ_error_rel'] * 100:.4f}%")
        elif name.startswith("S2"):
            print(f"          single-view theta {det['single_view_theta_deg']:.4f} deg, "
                  f"error {det['theta_error_deg']:.4f} deg "
                  f"(conditioning dtheta/dsin = "
                  f"{det['conditioning_dtheta_per_dsin_rad']:.2f} rad)")
            print(f"          {det['expectation']} -> "
                  f"{'it did' if det['pass'] else 'it did NOT'}")
        else:
            print(f"          plant {det['plant']}; read-back confirms "
                  f"{det['readback_confirms_plant']}; hash moved "
                  f"{det['hash_changed_on_plant']}")
            print(f"          mutated output {json.dumps(det['mutated_output'])}")
            print(f"          detected {det['mutation_detected']}; restored "
                  f"byte-identical {det['restored_byte_identical']}; "
                  f"post-restore identical to baseline "
                  f"{det['post_restore_matches_baseline']}")
    print(f"M84b step 18 controls: {n_pass}/{len(tests)} passed")

    (OUT / "18-controls.json").write_text(
        json.dumps(
            {"n_tests": len(tests), "n_pass": n_pass,
             "details": [d for _, _, d in tests]},
            indent=1,
        )
    )
    return 0 if n_pass == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())

"""Run the preregistered independent oracle controls, never real CFA emission.

Private files are analytic/control data without a float commission. They are
not outputs of the joint-pupil renderer or an author emitter execution.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import struct
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("independent_cfa_oracle", HERE / "independent-cfa-oracle.py")
O = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(O)


def require(condition, reason):
    if not condition:
        raise AssertionError(reason)


def rational_even(value):
    """Exact rational fixture oracle, distinct from float/fraction decisions."""
    lower, rem = divmod(value.numerator, value.denominator)
    twice = 2 * rem
    if twice > value.denominator or (twice == value.denominator and lower % 2):
        lower += 1
    return lower


def save_float(path, value):
    with path.open("xb") as handle:
        np.save(handle, value, allow_pickle=False)


def raw_bytes(array):
    return struct.pack("<3072H", *(int(v) for v in array.flat))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    require(out.is_relative_to(HERE), "control output must remain in M194e")
    out.mkdir(exist_ok=False)
    sources = [Path(__file__).resolve(), HERE / "independent-cfa-oracle.py", HERE / "independent-emission-design.md"]
    before = {str(p): O.sha256(p) for p in sources}
    records = []
    log = (out / "run.log").open("x", encoding="utf8", newline="\n")

    def check(name, fn, kind="positive"):
        try:
            detail = fn()
            records.append({"name": name, "kind": kind, "pass": True, "detail": detail})
        except Exception:
            records.append({"name": name, "kind": kind, "pass": False, "traceback": traceback.format_exc()})
        log.write(json.dumps(records[-1], allow_nan=False) + "\n")
        log.flush()
        print(name, "PASS" if records[-1]["pass"] else "FAIL", flush=True)

    def refuses(fn):
        try:
            fn()
        except (ValueError, TypeError, OverflowError, EOFError) as exc:
            return {"refusal": type(exc).__name__, "reason": str(exc)}
        raise AssertionError("malformed input or destroyer was accepted")

    def constant(e, electron_tile, code_tile):
        scalar = np.full(O.SHAPE, e, dtype="<f8")
        wanted_e = np.tile(np.array(electron_tile, dtype="<f8"), (24, 32))
        wanted_q = np.tile(np.array(code_tile, dtype="<u2"), (24, 32))
        actual_e, actual_q, summary = O.convert(scalar)
        require(np.array_equal(actual_e, wanted_e), "fixed electron table differs")
        require(np.array_equal(actual_q, wanted_q), "fixed integer table differs")
        return {"electron_tile": electron_tile, "code_tile": code_tile, **summary}

    check("constant20-all-four-parities", lambda: constant(20, [[15, 20], [20, 12]], [[516, 517], [517, 515]]))
    check("constant12000-distinct-high-bytes", lambda: constant(12000, [[9000, 12000], [12000, 7200]], [[2762, 3512], [3512, 2312]]))

    # Independent literal locations, factors and rounded codes; no O.channel call.
    ties = [("red-low", 0, 0, 8, Fraction(3, 4), 514),
            ("red-high", 2, 0, 24, Fraction(3, 4), 516),
            ("green1-low", 1, 0, 2, Fraction(1), 512),
            ("green1-high", 3, 0, 6, Fraction(1), 514),
            ("green2-even", 0, 1, 10, Fraction(1), 514),
            ("blue-low", 1, 1, 10, Fraction(3, 5), 514),
            ("blue-high", 3, 1, 30, Fraction(3, 5), 516)]

    for name, x, y, e, factor, literal in ties:
        def tied(x=x, y=y, e=e, factor=factor, literal=literal):
            observed = []
            wanted = []
            dns = []
            for perturb in [Fraction(-1, 2**20), Fraction(0), Fraction(1, 2**20)]:
                scalar = np.full(O.SHAPE, 20, dtype="<f8")
                scalar[y, x] = float(Fraction(e) + perturb)
                _, actual, _ = O.convert(scalar)
                exact_dn = Fraction(512) + (Fraction(e) + perturb) * factor / 4
                wanted.append(rational_even(exact_dn))
                observed.append(int(actual[y, x]))
                dns.append(float(exact_dn))
            require(wanted[1] == literal, "independent nominal tie table disagrees")
            require(observed == wanted, "explicit tie/side conversion differs")
            require(observed[0] + 1 == observed[2], "perturbation does not exercise rounding boundary")
            return {"native_xy": [x, y], "scalar_e": e, "dn": dns, "codes": observed}
        check("tie-and-sides-" + name, tied)

    def half_up_power():
        even_down = []
        even_up = []
        for name, _, _, e, f, literal in ties:
            dn = Fraction(512) + Fraction(e) * f / 4
            wrong = math.floor(dn + Fraction(1, 2))
            (even_down if wrong != literal else even_up).append(name)
        require(len(even_down) == 4 and len(even_up) == 3, "wrong-rounder occurrence changed")
        require(O.even_integer(513.25) == math.floor(513.25 + 0.5), "non-tie companion differs")
        return {"wrong_half_up_rejected_cases": even_down, "tie_up_inert_cases": even_up, "ordinary_companion": 513.25}
    check("wrong-half-up-power-and-nontie-companion", half_up_power, "destroyer")

    # A nonconstant even-valued field makes row reversal and flatten-transpose live.
    scalar = np.fromfunction(lambda y, x: 12000 + 4*x + 8*y, O.SHAPE, dtype=int).astype("<f8")
    expected = np.empty(O.SHAPE, dtype="<f8")
    codes = np.empty(O.SHAPE, dtype="<u2")
    factor_by_parity = {(0, 0): Fraction(3, 4), (0, 1): Fraction(1),
                        (1, 0): Fraction(1), (1, 1): Fraction(3, 5)}
    # NPY expected electrons reflect explicitly ordered binary f64 multiplication;
    # final integers come separately from exact rational values far from ties.
    for y in range(48):
        for x in range(64):
            factor = factor_by_parity[(y % 2, x % 2)]
            expected[y, x] = float(scalar[y, x]) * float(factor)
            codes[y, x] = rational_even(Fraction(512) + int(scalar[y, x]) * factor / 4)
    scalar_path, expected_path, raw_path = out / "fixture-scalar.npy", out / "fixture-expected.npy", out / "fixture.cfa"
    save_float(scalar_path, scalar)
    save_float(expected_path, expected)
    raw_path.write_bytes(raw_bytes(codes))
    fixture_hashes = {str(p): O.sha256(p) for p in (scalar_path, expected_path, raw_path)}
    check("actual-npy-and-raw-valid", lambda: O.compare_files(scalar_path, expected_path, raw_path))

    def altered_raw(name, changed):
        payload = changed if isinstance(changed, bytes) else raw_bytes(changed)
        require(payload != raw_path.read_bytes(), "destroyer is inert on the chosen fixture")
        path = out / (name + ".cfa")
        path.write_bytes(payload)
        return refuses(lambda: O.compare_files(scalar_path, expected_path, path))

    # Destroyers deliberately use different operation choices from the reader.
    wrong_phase = np.empty_like(codes)
    wrong_factor = codes.copy()
    wrong_gain = np.empty_like(codes)
    wrong_wb = np.empty_like(codes)
    for y in range(48):
        for x in range(64):
            f = factor_by_parity[(y % 2, (x + 1) % 2)]
            wrong_phase[y, x] = rational_even(Fraction(512) + int(scalar[y, x]) * f / 4)
            if y % 2 == 0 and x % 2 == 0:
                wrong_factor[y, x] = rational_even(Fraction(512) + int(scalar[y, x]) * Fraction(4, 5) / 4)
            wrong_gain[y, x] = round(512 + float(expected[y, x]))
            wrong_wb[y, x] = rational_even(Fraction(512) + Fraction(int(scalar[y, x]), 4))
    isolated = codes.copy()
    isolated[31, 42] += 1
    noise = codes.copy()
    noise[::2] += 1
    noise[1::2] -= 1
    payload = raw_path.read_bytes()
    mutations = {
        "wrong-phase": wrong_phase, "wrong-red-factor": wrong_factor,
        "omitted-gain": wrong_gain, "added-wb": wrong_wb,
        "black-offset": codes + 1, "added-balanced-noise": noise,
        "isolated-native-42-31": isolated, "rows-reversed": codes[::-1],
        "transpose-flatten": codes.T.copy().reshape(O.SHAPE),
        "big-endian-payload": codes.astype(">u2").tobytes(),
        "truncated-raw": payload[:-2], "appended-raw": payload + b"\0\0",
    }
    for name, mutation in mutations.items():
        check(name, lambda name=name, mutation=mutation: altered_raw(name, mutation), "destroyer")

    altered_e = expected.copy()
    altered_e[17, 22] += 2**-20
    changed_expected = out / "changed-expected.npy"
    save_float(changed_expected, altered_e)
    check("expected-electron-isolated-change", lambda: refuses(lambda: O.compare_files(scalar_path, changed_expected, raw_path)), "destroyer")

    float_mutants = {
        "float32": scalar.astype("<f4"), "big-endian-float": scalar.astype(">f8"),
        "transposed-shape": scalar.T.copy(), "complex": scalar.astype("<c16"),
        "bool": np.ones(O.SHAPE, dtype=bool),
    }
    for label, value in [("nan", float("nan")), ("infinity", float("inf")), ("negative", -1.0)]:
        mutant = scalar.copy()
        mutant[19, 21] = value
        float_mutants[label] = mutant
    for name, mutant in float_mutants.items():
        path = out / ("bad-" + name + ".npy")
        save_float(path, mutant)
        check("refuse-" + name, lambda path=path: refuses(lambda: O.read_float(path)), "malformed")
    for name, payload in {"npy-trailing": scalar_path.read_bytes() + b"tail", "npy-truncated": scalar_path.read_bytes()[:-8], "bad-container": b"not-an-array"}.items():
        path = out / (name + ".npy")
        path.write_bytes(payload)
        check(name, lambda path=path: refuses(lambda: O.read_float(path)), "malformed")
    check("refuse-bool-coordinate", lambda: refuses(lambda: O.channel(True, 0)), "malformed")
    check("refuse-float-coordinate", lambda: refuses(lambda: O.channel(0.0, 0)), "malformed")
    check("refuse-nonfinite-quantizer", lambda: refuses(lambda: O.even_integer(float("nan"))), "malformed")
    check("zero-electrons-black-valid", lambda: constant(0, [[0, 0], [0, 0]], [[512, 512], [512, 512]]))

    def near_white(e, expected_code=None):
        field = np.full(O.SHAPE, 20, dtype="<f8")
        field[0, 1] = e  # Green, no uncertain channel-factor product.
        if expected_code is None:
            return refuses(lambda: O.convert(field))
        _, q, _ = O.convert(field)
        require(int(q[0, 1]) == expected_code, "near-white valid companion differs")
        return {"green_scalar_e": e, "dn": 512 + e / 4, "code": int(q[0, 1])}

    check("near-white-interior-valid", lambda: near_white(59389, 15359))
    for label, e in [("white-endpoint", 59392), ("white-above", 59393),
                     ("white-rounding-tie", 59390), ("white-rounding-above-tie", 59391),
                     ("white-near-endpoint", 59392 - 2**-20)]:
        check("refuse-" + label, lambda e=e: near_white(e), "malformed")
    check("actual-npy-and-raw-final-reread", lambda: O.compare_files(scalar_path, expected_path, raw_path))

    after = {str(p): O.sha256(p) for p in sources}
    unchanged = before == after and fixture_hashes == {str(p): O.sha256(p) for p in (scalar_path, expected_path, raw_path)}
    result = {
        "schema": "m194e-independent-cfa-oracle-controls-v1",
        "scope": "Independent oracle and private fixture reader controls only; no author emitter execution, no float/model authority, no final CFA commission.",
        "command": [sys.executable, *sys.argv], "python": platform.python_version(), "numpy": np.__version__,
        "environment": {k: v for k, v in os.environ.items() if k.startswith(("OMP_", "MKL_", "OPENBLAS_", "NUMEXPR_"))},
        "sources_before": before, "sources_after": after, "fixture_hashes": fixture_hashes,
        "records": records, "check_count": len(records), "source_and_fixture_unchanged": unchanged,
        "deferred": ["receipt/source/float-commission API", "author observer off/count/placebo execution", "genuine final emitted CFA"],
        "pass": unchanged and all(r["pass"] for r in records),
    }
    (out / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf8", newline="\n")
    log.close()
    print(json.dumps({"pass": result["pass"], "checks": len(records), "result_sha256": O.sha256(out / "result.json")}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

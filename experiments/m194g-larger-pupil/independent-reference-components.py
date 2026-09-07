"""Registered independent spatial reference controls; no execution by import.

The source/command release must precede any actual model or integral call.
Every baseline case gets both independent targets. Refusals are retained rows.
"""
from __future__ import annotations
import os
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.monotonic()
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "2"

import argparse
from contextlib import contextmanager
import copy
from dataclasses import replace
from fractions import Fraction as F
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import traceback

HERE = Path(__file__).resolve().parent


def load_reference(expected):
    path = HERE / "independent-reference.py"
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("externally pinned reference source mismatch")
    spec = importlib.util.spec_from_loader("m194g_reference_under_test", loader=None, origin=str(path))
    ref = importlib.util.module_from_spec(spec)
    ref.__file__ = str(path)
    sys.modules[spec.name] = ref
    exec(compile(raw, str(path), "exec"), ref.__dict__)
    return ref


def disc_series(argument):
    """Exact-rational disc moments, alternating tail once decreasing.

    Computes the characteristic of the spatial unit disc by its even moments.
    No Bessel library or producer factor is used. The interval encloses the
    exact series at the supplied finite argument, not earlier norm roundoff.
    """
    x = F(argument)
    z = x * x / 4
    term = total = F(1)
    for j in range(1, 256):
        term *= -z / (j * (j + 1))
        total += term
        following = term * -z / ((j + 1) * (j + 2))
        if z < (j + 1) * (j + 2) and abs(following) < F(1, 10 ** 18):
            return min(total, total + following), max(total, total + following), j
    raise ValueError("fixed moment-series ceiling")


def square_formula(k):
    return 1. if k == 0 else math.sin(k / 2) / (k / 2)


def layer_oracle(p, xy, layer):
    """Separately assembled moment-series + elementary cell-integral oracle."""
    rad = p.scene.foreground if layer == "foreground" else p.scene.background
    depth = p.scene.foreground_depth if layer == "foreground" else p.scene.background_depth
    d = p.frame.K * (p.frame.inverse_focus - 1 / depth)
    # Exact finite affine coefficients, one final conversion for each coordinate.
    q = tuple(float(sum(p.exact_M[i][j] * F(xy[j]) for j in range(2)) + p.exact_b[i]) for i in range(2))
    terms = [rad.constant, rad.affine[0] * q[0], rad.affine[1] * q[1]]
    evidence = []
    for amplitude, fx, fy, phase in rad.waves:
        omega = (2 * math.pi * fx, 2 * math.pi * fy)
        k = tuple(sum(p.frame.M[i][j] * omega[i] for i in range(2)) for j in range(2))
        argument = abs(d) * math.sqrt(k[0] * k[0] + k[1] * k[1])
        lo, hi, count = disc_series(argument)
        disc = float((lo + hi) / 2)
        sx, sy = square_formula(k[0]), square_formula(k[1])
        terms.append(amplitude * math.cos(2 * math.pi * (fx * q[0] + fy * q[1]) + phase) * disc * sx * sy)
        evidence.append(dict(argument=argument, disc_interval=[str(lo), str(hi)],
                             disc_interval_float=[float(lo), float(hi)], terms=count,
                             square=[sx, sy], scope="exact rational series tail; preceding finite-coordinate/norm arithmetic remains engineering scope"))
    return math.fsum(terms), evidence


@contextmanager
def patched(obj, attr, value):
    original = getattr(obj, attr)
    setattr(obj, attr, value)
    try:
        yield
    finally:
        setattr(obj, attr, original)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--reference-sha256", required=True)
    ap.add_argument("--execution-release", type=Path, required=True)
    ap.add_argument("--execution-release-sha256", required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    # Loading definitions is not authority to call them. Gate precedes prepare/render.
    r = load_reference(args.reference_sha256)
    budget = r.Budget(start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
    result = dict(schema="m194g-independent-reference-components-v1", status="RUNNING",
                  ref_root="repository", repository_provenance=str(r.ROOT),
                  runtime=r.runtime(), sources_before=r.source_map(), sources_after=None,
                  sources_unchanged=False, execution_release=None, catalog=None, inputs=[],
                  baseline=[], refinement=[], oracles=[], faults=[], checks=[],
                  budget=None, exception=None, traceback=None, finalization_errors=[])

    def persist():
        result["budget"] = budget.receipt()
        r.write_json(args.output / "partial.json", result)

    def check(name, passed, evidence):
        result["checks"].append(dict(name=name, passed=bool(passed), evidence=evidence))
        persist()

    def row(case, arm, engine, phase="baseline", fault_id=None):
        item = dict(case_id=case["id"], arm=arm, method=r.METHOD, phase=phase,
                    fault_id=fault_id, call=case["call"], scene=None, frame=None,
                    native_xy=case["native_xy"], status="REFUSED", value_e=None,
                    branch=None, receipt=None, work_before=budget.receipt(), work_after=None,
                    engine_before=engine.receipt(), engine_after=None, error=None)
        try:
            budget.check()
            p = r.case_input(catalog, case)
            item["scene"], item["frame"] = p.scene_record, p.frame_record
            value, receipt = engine.render(p, tuple(case["native_xy"]), cell=case["call"] == "cell")
            item.update(status="VALUE", value_e=value, branch=receipt["branch"], receipt=receipt)
        except Exception as exc:
            item["error"] = repr(exc)
        item["work_after"], item["engine_after"] = budget.receipt(), engine.receipt()
        return item

    def ordinary(case, phase="restored", fault_id=None):
        return row(case, "refined", r.Engine(budget, r.TARGETS["refined"]), phase, fault_id)

    try:
        r.snapshot(result["sources_before"], args.output)
        result["execution_release"] = r.execution_gate(args.execution_release, args.execution_release_sha256,
                                                       "components", result["sources_before"])
        catalog = r.read_json(HERE / "component-population.json", r.CATALOG_SHA)
        r.validate_population(catalog)
        result["catalog"] = r.file_ref(HERE / "component-population.json")
        r.write_json(args.output / "reopened-catalog.json", catalog)
        reopened = r.read_json(args.output / "reopened-catalog.json")
        r.require_input(reopened, catalog)
        check("literal-reopened-catalog", True, dict(equal=True))
        r.validate_population(reopened)
        changed_input = copy.deepcopy(reopened)
        changed_input["fields"]["fg-15000"]["constant"] += 1.
        changed_refused = False
        try:
            r.require_input(changed_input, catalog)
        except r.Refusal:
            changed_refused = True
        check("changed-normalized-field-refused", changed_refused,
              dict(field="fields.fg-15000.constant", added_e=1.))
        cases = catalog["cases"]
        by_id = {case["id"]: case for case in cases}
        # Bound historical arrays/check records are input lineage, never re-generated.
        seen_refs = set()
        def verify_refs(value):
            if isinstance(value, dict):
                if "path" in value and "sha256" in value:
                    path = r.checked_ref(value)
                    if str(path) not in seen_refs:
                        seen_refs.add(str(path))
                        result["inputs"].append(r.file_ref(path))
                for child in value.values():
                    verify_refs(child)
            elif isinstance(value, list):
                for child in value:
                    verify_refs(child)
        verify_refs(catalog)
        interval_controls_path = HERE / "independent-normalized-interval-controls.py"
        interval_controls_key = interval_controls_path.relative_to(r.ROOT).as_posix()
        interval_controls = r.load_source(interval_controls_path, "m194g_independent_interval_controls",
                                         result["sources_before"][interval_controls_key]["sha256"])
        interval_result = interval_controls.run(r, budget, catalog, args.output, check)
        if interval_result["status"] != "PASS_NORMALIZED_INTERVAL_CONTROLS_ONLY":
            raise r.Refusal("additive normalized-interval controls did not pass")
        engines = {name: r.Engine(budget, target) for name, target in r.TARGETS.items()}
        # All150 registered cases, both targets: exactly300 baseline calls, no subset.
        for case in cases:
            for arm in ("primary", "refined"):
                result["baseline"].append(row(case, arm, engines[arm]))
                persist()
        budget.check()
        baseline = {(x["case_id"], x["arm"]): x for x in result["baseline"]}
        for case in cases:
            a, b = (baseline[case["id"], arm] for arm in ("primary", "refined"))
            delta = abs(a["value_e"] - b["value_e"]) if a["status"] == b["status"] == "VALUE" else None
            result["refinement"].append(dict(case_id=case["id"], maximum_e=delta,
                                            limit_e=.0005, passed=delta is not None and delta <= .0005))

        # Literal point/cell and full-layer oracles, independent of the spatial cache.
        oracle_errors = []
        for case in cases:
            p = r.case_input(catalog, case)
            xy = tuple(case["native_xy"])
            expected = details = None
            if case["group"] in ("transfer", "coordinate"):
                layer = "foreground" if p.mask_state == "full" else "background"
                expected, details = layer_oracle(p, xy, layer)
            elif case["id"] == "joint-relative-sign-point":
                expected, details = 11000 + 400 / math.pi, {"expression": "11000+400/pi"}
            elif case["id"] == "joint-zero-pupil-cell":
                expected, details = 13816., {"expression": ".7*16000+.3*(9000-280)", "finite-offset-convention": "actual binary64-.2 differs only at finite arithmetic scale"}
            elif case["group"] == "visibility-fault-power" and p.scene.foreground == p.scene.background:
                expected, details = 12000., {"scope": "equal-field scalar null, not branch proof"}
            elif case["group"] == "preserved-whole-cell":
                ref = case["retained_reference"]
                meta_ref = ref["reference_result"]
                metadata = r.read_json(r.ROOT / meta_ref["path"], meta_ref["sha256"])
                wanted_index = p.frame_record["index"]
                entries = [v for v in metadata["frames"] if v["arm"] == "refined" and v["index"] == wanted_index]
                if metadata["status"] != "PASS_COMPLETE_REFERENCE_ONLY" or len(entries) != 1:
                    raise r.Refusal("retained reference metadata scope")
                entry = entries[0]
                if entry["array"]["sha256"] != ref["array"]["sha256"] or entry["shape"] != [48, 64] or entry["dtype"] != "<f8":
                    raise r.Refusal("retained reference array binding")
                array = r.read_array(dict(ref["array"], bytes=entry["array"]["bytes"]), entry["shape"], entry["dtype"], budget)
                expected = float(array[tuple(ref["index_yx"])])
                details = {"retained_reference": ref}
                del array
            if expected is not None:
                for arm in ("primary", "refined"):
                    actual = baseline[case["id"], arm]
                    error = abs(actual["value_e"] - expected) if actual["status"] == "VALUE" else None
                    passed = error is not None and error <= .004
                    result["oracles"].append(dict(case_id=case["id"], arm=arm, expected_e=expected,
                                                 actual_e=actual["value_e"], absolute_error_e=error,
                                                 limit_e=.004, passed=passed, evidence=details))
                    if error is not None and case["group"] in ("transfer", "coordinate", "preserved-whole-cell"):
                        oracle_errors.append(error)
            if case["group"] == "transfer":
                rad = p.scene.foreground if p.mask_state == "full" else p.scene.background
                expected_sign = -1 if "negative" in case["id"] else 1
                _, records = layer_oracle(p, xy, "foreground" if p.mask_state == "full" else "background")
                lo, hi = records[0]["disc_interval_float"]
                check("moment-series-sign-" + case["id"], hi < 0 if expected_sign < 0 else lo > 0,
                      dict(interval=[lo, hi], expected_sign=expected_sign, nonzero_amplitude=rad.waves[0][0]))
                for arm in ("primary", "refined"):
                    entry = baseline[case["id"], arm]
                    if entry["status"] == "VALUE":
                        factor = entry["receipt"]["factors"][0]
                        consumed = factor["disc"]
                        check("consumed-transfer-sign-" + case["id"] + "-" + arm,
                              consumed < 0 if expected_sign < 0 else consumed > 0,
                              dict(consumed_disc=consumed, expected_sign=expected_sign))
                        if "-zero-" in case["id"]:
                            target = factor["quadrature"][0]["absolute_request"]
                            check("consumed-zero-limit-" + case["id"] + "-" + arm,
                                  abs(consumed - 1.) <= target and factor["quadrature"][0]["argument"] == 0,
                                  dict(consumed_disc=consumed, absolute_target=target,
                                       actual_factor_evaluations=entry["work_after"]["factor_evaluations"] - entry["work_before"]["factor_evaluations"]))
        rms = math.sqrt(sum(x * x for x in oracle_errors) / len(oracle_errors)) if oracle_errors else None
        check("textured-component-oracle-rms", rms is not None and rms <= .0008,
              dict(rms_e=rms, limit_e=.0008, compared=len(oracle_errors)))

        # All14 named faults run through actual reference consumption, with fixed targets.
        for fault in catalog["active_fault_targets"]:
            name, case = fault["id"], by_id[fault["target_case"]]
            engine = r.Engine(budget, r.TARGETS["refined"])
            prime = None
            original_factors = r.Engine.factors
            original_full_layer = r.Engine.full_layer
            original_render = r.m.render
            if name in ("stale-frequency-cache", "cached-phase-zero"):
                prime_case = by_id["transfer-negative-one-full" if name == "stale-frequency-cache" else "coordinate-centre-phase-zero"]
                prime = row(prime_case, "refined", engine, "cache-prime", name)
                prime_entry = copy.deepcopy(engine.last_entry)

            def changed_factors(self, prepared, layer, cell=True):
                entry = copy.deepcopy(original_factors(self, prepared, layer, cell))
                for i, wave in enumerate(entry["waves"]):
                    if name == "abs-disc-transfer":
                        wave["disc"] = abs(wave["disc"])
                    elif name == "clamp-disc-transfer":
                        wave["disc"] = max(0., wave["disc"])
                    elif name == "omit-square-factor":
                        wave["sx"] = wave["sy"] = 1.
                    elif name == "always-unit-disc":
                        wave["disc"] = 1.
                    elif name == "stale-frequency-cache":
                        for k in ("disc", "sx", "sy", "quadrature"):
                            wave[k] = copy.deepcopy(prime_entry["waves"][i][k])
                    elif name == "cached-phase-zero":
                        wave["phase"] = prime_entry["waves"][i]["phase"]
                return entry

            def wrong_selector(prepared, xy):
                h, n, df = r.exact_support(prepared, xy)
                d = F(prepared.frame.K * (prepared.frame.inverse_focus - 1 / prepared.scene.background_depth)) if name == "wrong-background-visibility-radius" else df
                half = (abs(n[0]) + abs(n[1])) / 2 if name == "wrong-background-visibility-radius" else F(0)
                radius2 = d * d * (n[0] * n[0] + n[1] * n[1])
                if h > half and (h - half) ** 2 > radius2:
                    return "foreground"
                if -h > half and (-h - half) ** 2 > radius2:
                    return "background"
                return "numerical"

            if name in ("abs-disc-transfer", "clamp-disc-transfer", "omit-square-factor", "always-unit-disc", "stale-frequency-cache", "cached-phase-zero"):
                mutation = patched(r.Engine, "factors", changed_factors)
            elif name == "omit-pupil-normalization":
                def unnormalized(self, prepared, xy, layer, cell=True):
                    value, receipt = original_full_layer(self, prepared, xy, layer, cell)
                    return math.pi * value, dict(receipt, mutation="omit1/pi from whole disc average, including DC")
                mutation = patched(r.Engine, "full_layer", unnormalized)
            elif name == "transpose-native-frequency":
                def wrong_wave(frame, fx, fy):
                    omega = (2 * math.pi * fx, 2 * math.pi * fy)
                    return tuple(sum(frame.M[i][j] * omega[j] for j in range(2)) for i in range(2))
                mutation = patched(r, "wave_vector", wrong_wave)
            elif name == "chief-ray-native-as-canonical":
                mutation = patched(r, "chief_ray", lambda frame, xy: xy)
            elif name in ("wrong-background-visibility-radius", "missing-cell-visibility-support"):
                mutation = patched(r, "select", wrong_selector)
            elif name == "relative-sign":
                def unsigned_render(*pos, **kw):
                    return original_render(*pos, **kw, unsigned=True)
                mutation = patched(r.m, "render", unsigned_render)
            elif name == "separate-cell-means":
                def separate(scene, frame, xy, **kw):
                    mean = scene.background.value(frame.transform(xy))
                    changed = replace(scene, background=r.m.Radiance(mean))
                    return original_render(changed, frame, xy, **kw)
                mutation = patched(r.m, "render", separate)
            elif name == "swapped-field":
                def swapped(self, prepared, xy, layer, cell=True):
                    return original_full_layer(self, prepared, xy, "foreground", cell)
                mutation = patched(r.Engine, "full_layer", swapped)
            else:
                raise r.Refusal("unimplemented registered fault: " + name)
            with mutation:
                mutated = row(case, "refined", engine, "fault", name)
            restored = ordinary(case, "restored", name)
            before = baseline[case["id"], "refined"]
            complete = before["status"] == mutated["status"] == restored["status"] == "VALUE"
            delta = abs(mutated["value_e"] - before["value_e"]) if complete else None
            equal = complete and struct.pack("<d", restored["value_e"]) == struct.pack("<d", before["value_e"])
            passed = complete and equal and delta > fault["required_abs_value_discrepancy_gt_e"]
            result["faults"].append(dict(fault_id=name, target_case=case["id"], before=before,
                                          prime=prime, mutated=mutated, restored=restored,
                                          difference_e=delta, minimum_exclusive_e=.004,
                                          restored_scalar_bytes_equal=equal, passed=passed))
            persist()

        # Zero must be actually integrated, finite and1; 0/0 must reach value refusal.
        zero = by_id["transfer-zero-full"]
        original_factor = r.integrate_factor
        def zero_over_zero(kind, argument, eps, meter):
            if kind == "disc" and argument == 0:
                return float("nan"), dict(kind=kind, argument=argument, value="NaN fault", absolute_indicator=0., absolute_request=eps)
            return original_factor(kind, argument, eps, meter)
        with patched(r, "integrate_factor", zero_over_zero):
            bad_zero = ordinary(zero, "fault", "zero-over-zero")
        good_zero = ordinary(zero, "restored", "zero-over-zero")
        check("zero-over-zero-refused", bad_zero["status"] == "REFUSED" and good_zero["status"] == "VALUE",
              dict(mutated=bad_zero, restored=good_zero))
        removed_id, repeated_id = catalog["cases"][1]["id"], catalog["cases"][0]["id"]
        dup = copy.deepcopy(catalog)
        dup["cases"][1] = copy.deepcopy(dup["cases"][0])
        refused = False
        try:
            r.validate_population(dup)
        except r.Refusal:
            refused = True
        check("duplicate-case-refused", refused, dict(replaced_id=removed_id, duplicate_id=repeated_id))
        mutant_path = args.output / "bound-byte-mutant.bin"
        raw = bytearray(r.OLD.read_bytes())
        raw[len(raw) // 2] ^= 1
        mutant_path.write_bytes(raw)
        refused = False
        try:
            r.checked_ref(dict(path=mutant_path.resolve().relative_to(r.ROOT).as_posix(), sha256=r.OLD_SHA, bytes=len(raw)))
        except r.Refusal:
            refused = True
        check("source-byte-mismatch-refused", refused,
              dict(mutant=r.file_ref(mutant_path), retained_expected=r.OLD_SHA))

        # A changed target must consume a distinct entry and request, not just relabel it.
        target_case = by_id["transfer-negative-one-full"]
        target_engine = r.Engine(budget, r.TARGETS["primary"])
        first = row(target_case, "primary", target_engine, "cache-prime", "target-consumption")
        old_entry = copy.deepcopy(target_engine.last_entry)
        target_engine.target = r.TARGETS["refined"]
        second = row(target_case, "refined", target_engine, "restored", "target-consumption")
        check("changed-target-consumed", first["status"] == second["status"] == "VALUE" and
              second["work_after"]["factor_evaluations"] > first["work_after"]["factor_evaluations"] and
              target_engine.last_entry["factor_target"] == old_entry["factor_target"] / 16,
              dict(primary=first, refined=second))
        with patched(r.Engine, "factors", lambda *pos, **kw: old_entry):
            stale_target = ordinary(target_case, "fault", "stale-target")
        check("stale-target-refused", stale_target["status"] == "REFUSED", stale_target)

        # All actual baseline values remain necessary, even if earlier controls fail.
        check("complete-300-reference-values", len(result["baseline"]) == 300 and all(x["status"] == "VALUE" for x in result["baseline"]),
              dict(rows=len(result["baseline"]), values=sum(x["status"] == "VALUE" for x in result["baseline"])))
        budget.check()
        all_ok = (all(x["passed"] for x in result["checks"]) and all(x["passed"] for x in result["refinement"])
                  and all(x["passed"] for x in result["oracles"]) and len(result["faults"]) == 14
                  and all(x["passed"] for x in result["faults"]))
        result["status"] = "PASS_REFERENCE_COMPONENTS_ONLY" if all_ok else "UNCOMMISSIONED_REFERENCE_COMPONENTS"
    except Exception as exc:
        result["status"] = "UNCOMMISSIONED_REFERENCE_COMPONENTS"
        result["exception"], result["traceback"] = repr(exc), traceback.format_exc()
    finally:
        r.finalize(result, args.output, budget, "UNCOMMISSIONED_REFERENCE_COMPONENTS")
        print(json.dumps(dict(status=result["status"], baseline=len(result["baseline"]),
                              checks=len(result["checks"]), faults=len(result["faults"]), budget=budget.receipt())))
    return 0 if result["status"] == "PASS_REFERENCE_COMPONENTS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())

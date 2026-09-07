"""Private fixture-only emitter controls. NO optical or genuine float authority.

The synthetic PASS records below exercise an externally trusted API condition;
they are deliberately not scientific evidence and cannot admit final CFA data.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import sys
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model as M
import render as R
import schema as S


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


E = load("m194e_independent_actual_emitter", HERE / "emit-cfa.py")
O = load("m194e_independent_scalar_oracle", HERE / "independent-cfa-oracle.py")
PINS = {
    "schema.py": "b3aee835d7bec9206ebff2401e3af5beb63fc66bf2aca3a32b272b69398edc54",
    "emit-cfa.py": "fbcdfa2c716f638e9aa8f9cf13ba3024a575feca0ad15d1a67012f51176c82fd",
    "emission-contract.md": "a8cbf1107004bdc61058e544f1efe88ebed83b7e6eac2381429ae4d150de1c40",
}
SCOPE = "FIXTURE ONLY: invented float arrays and gate; genuine author component control copied; no scientific float/CFA authority"
AUTHOR_CONTROL = HERE / "author-controls-8/result.json"
AUTHOR_CONTROL_SHA = "169e098024d80d23ca8f8166d12eb89c6dfb356f57caef6d7451cac67ab745c4"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def plain(value):
    return json.loads(json.dumps(value, allow_nan=False))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def ref(path, root, array=False):
    path, root = Path(path).resolve(), Path(root).resolve()
    value = dict(path=path.relative_to(root).as_posix(), sha256=sha(path), bytes=path.stat().st_size)
    if array:
        value.update(dtype="<f8", shape=[48, 64])
    return value


def snap():
    names = set(S.AUTHOR_SOURCES + S.DESIGNS + (Path(__file__).name, "independent-cfa-oracle.py", "independent-emission-design.md"))
    return {name: sha(HERE / name) for name in sorted(names)}


def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob("*")) if p.is_file()}


def authority(folder, bundle):
    """A private API fixture trust anchor, NEVER an independent scientific PASS."""
    write(folder / "float-bundle.json", bundle)
    gate = dict(schema="m194e-float-commission-v1", status="PASS",
                author_root=folder.relative_to(S.REPOSITORY).as_posix(),
                author_bundle=ref(folder / "float-bundle.json", folder),
                producer_sources=deepcopy(bundle["producer"]["sources"]),
                author_controls=deepcopy(bundle["producer"]["author_controls"]),
                expected_scalars={str(i): deepcopy(f["expected_scalar"]) for i, f in enumerate(bundle["frames"])},
                numerical_receipts={str(i): deepcopy(f["numerical_receipt"]) for i, f in enumerate(bundle["frames"])},
                independent_evidence={k: ref(folder / f"fixture-only-{k}.json", S.REPOSITORY)
                                      for k in ("controls", "author_api", "reference", "comparison")})
    gate.update({k: deepcopy(bundle[k]) for k in ("scene", "ray_model", "numerical_contract")})
    path = folder / "fixture-only-no-scientific-authority.json"
    write(path, gate)
    return path


def make_fixture(folder):
    folder.mkdir(parents=True)
    (folder / "README.md").write_text("# Private API fixture\n\n" + SCOPE + ".\n", encoding="utf-8")
    bindings = {name: sha(HERE / name) for name in S.AUTHOR_SOURCES}
    assert sha(AUTHOR_CONTROL) == AUTHOR_CONTROL_SHA
    controls = read(AUTHOR_CONTROL)
    assert controls["status"] == "PASS" and len(controls["checks"]) == 172
    assert all(c["pass_"] is True for c in controls["checks"])
    assert all(controls[k][name] == h for k in ("sources_before", "sources_after") for name, h in bindings.items())
    shutil.copyfile(AUTHOR_CONTROL, folder / "fixture-only-author-controls.json")
    for k in ("controls", "author_api", "reference", "comparison"):
        write(folder / f"fixture-only-{k}.json", dict(scope=SCOPE, kind=k))
    records = {}
    y, x = np.indices((48, 64))
    for arm in S.ARMS:
        records[arm] = []
        destination = folder / arm
        destination.mkdir()
        for i, f in enumerate(M.primary_frames()):
            scalar = np.asarray(12000 + 4 * x + 8 * y + 16 * i, dtype="<f8")
            scalar_path = destination / f"frame-{i}-scalar.npy"
            error_path = destination / f"frame-{i}-indicator.npy"
            np.save(scalar_path, scalar, allow_pickle=False)
            np.save(error_path, np.zeros((48, 64), dtype="<f8"), allow_pickle=False)
            work = dict(point_calls=100, angular_nodes=4096, peak_node_pairs=32,
                        tracked_peak_ndarray_bytes=49152, tracked_peak_ndarrays=2,
                        peak_live_scalar_frames=1, observer="off", observer_events=0,
                        optional_hook_calls=0, cpu_seconds=.01, wall_seconds=.02)
            receipt = dict(schema="m194e-float-frame-v1", status="uncommissioned", frame=plain(asdict(f)),
                           expected_scalar=ref(scalar_path, destination, True), error_indicator=ref(error_path, destination, True),
                           max_error_indicator_e=0.0, integrator=plain(asdict(R.integrator_for(arm))), tile=8, work=work)
            numerical_path = destination / f"frame-{i}-numerical.json"
            write(numerical_path, receipt)
            records[arm].append(dict(**plain(asdict(f)), expected_scalar=ref(scalar_path, folder, True),
                                     numerical_receipt=ref(numerical_path, folder)))
    bundle = dict(schema="m194e-float-bundle-v1", status="uncommissioned", sensor=M.sensor_record(),
                  scene=plain(M.scene_record(M.primary_scene())), ray_model=M.RAY_MODEL,
                  numerical_contract=S.numerical_contract(), frames=records["primary"],
                  refinements={arm: records[arm] for arm in S.ARMS[1:]},
                  producer=dict(source_base="repository", sources=S.source_bindings(), designs=S.design_bindings(),
                                command=["FIXTURE_ONLY", "no-optical-model-run"],
                                author_controls=ref(folder / "fixture-only-author-controls.json", S.REPOSITORY)))
    gate = authority(folder, bundle)
    return folder / "float-bundle.json", gate


def set_at(obj, keys, value):
    for k in keys[:-1]:
        obj = obj[k]
    obj[keys[-1]] = value


def mutate_numerical(folder, bundle, fn, arm="primary", index=0):
    frame = (bundle["frames"] if arm == "primary" else bundle["refinements"][arm])[index]
    path = folder / frame["numerical_receipt"]["path"]
    receipt = read(path)
    fn(receipt)
    write(path, receipt)
    frame["numerical_receipt"] = ref(path, folder)


def mutate_scalar(folder, bundle, fn, *, trailing=None):
    frame = bundle["frames"][0]
    path = folder / frame["expected_scalar"]["path"]
    value = np.load(path, allow_pickle=False)
    new = fn(value)
    np.save(path, new, allow_pickle=False)
    if trailing is not None:
        with path.open("ab") as stream:
            stream.write(trailing)
    frame["expected_scalar"] = ref(path, folder, True)
    mutate_numerical(folder, bundle, lambda r: r.update(expected_scalar=ref(path, (folder / frame["numerical_receipt"]["path"]).parent, True)))


def actual_output(manifest_path, original_bundle):
    """Independent strict reads of actual file bytes, values and archived lineage."""
    root = manifest_path.parent
    m = read(manifest_path)
    b = read(original_bundle)
    assert set(m) == {"schema", "status", "producer", "sensor", "scene", "ray_model", "numerical_contract", "frames"}
    assert m["schema"] == "m194e-joint-pupil-v1" and m["status"] == "float-commissioned-cfa-unverified"
    assert len(m["frames"]) == 5
    for key in ("sensor", "scene", "ray_model", "numerical_contract"):
        assert m[key] == b[key]
    assert set(m["producer"]) == set(b["producer"]) | {"emission_receipt"}
    assert all(m["producer"][k] == v for k, v in b["producer"].items())
    er = m["producer"]["emission_receipt"]
    assert ref(root / er["path"], root) == er
    run = read(root / er["path"])
    assert run["status"] == "CFA_COMPLETE_AWAITING_INDEPENDENT_REVIEW" and run["frames"] == m["frames"]
    assert run["sources_before"] == run["sources_after"] == S.source_bindings()
    result = []
    for i, f in enumerate(m["frames"]):
        original = b["frames"][i]
        assert set(f) == {"index", "inverse_focus", "K", "forward_similarity", "expected_scalar", "numerical_receipt", "expected_cfa", "cfa"}
        for key in ("index", "inverse_focus", "K", "forward_similarity"):
            assert f[key] == original[key]
        for key in ("expected_scalar", "expected_cfa", "cfa", "numerical_receipt"):
            expected = ref(root / f[key]["path"], root, key != "numerical_receipt")
            if key == "cfa":
                expected["dtype"] = "<u2"
            assert f[key] == expected
        for key in ("expected_scalar", "numerical_receipt"):
            assert f[key]["path"] == "input/" + original[key]["path"]
            assert (root / f[key]["path"]).read_bytes() == (original_bundle.parent / original[key]["path"]).read_bytes()
        nr = read(root / f["numerical_receipt"]["path"])
        nr_parent = (root / f["numerical_receipt"]["path"]).parent
        old_parent = (original_bundle.parent / original["numerical_receipt"]["path"]).parent
        for key in ("expected_scalar", "error_indicator"):
            assert (nr_parent / nr[key]["path"]).read_bytes() == (old_parent / nr[key]["path"]).read_bytes()
        result.append(O.compare_files(root / f["expected_scalar"]["path"], root / f["expected_cfa"]["path"], root / f["cfa"]["path"]))
    assert len({r["scalar_sha256"] for r in result}) == 5, "distinct frame occurrence"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    before = snap()
    assert all(before[k] == v for k, v in PINS.items()), "root source pin mismatch"
    (output / "sources").mkdir()
    for name in before:
        shutil.copyfile(HERE / name, output / "sources" / name)
    (output / "README.md").write_text("# Independent API controls\n\n" + SCOPE + ".\n", encoding="utf-8")
    checks = []

    def check(name, fn, refuse=False, boundary="conversion"):
        try:
            detail = fn()
            passed = not refuse
            if refuse:
                detail = "WRONG: accepted a declared invalid input"
        except Exception as exc:
            # A failed assertion is a test defect or observed failed expectation,
            # not an API refusal. All other exceptions are preserved by type.
            passed = refuse and not isinstance(exc, AssertionError)
            detail = dict(error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
        record = dict(name=name, boundary=boundary, expected="refuse" if refuse else "pass", passed=passed, detail=detail)
        checks.append(record)
        print(("PASS " if passed else "FAIL ") + name, flush=True)
        write(output / "progress.json", dict(scope=SCOPE, checks=checks))

    def conversion(value):
        original = value.tobytes()
        expected, codes, info = O.convert(value)
        actual_e, actual_u = E.convert_cfa(value)
        assert value.tobytes() == original
        assert actual_e.dtype.str == "<f8" and actual_u.dtype.str == "<u2"
        assert actual_e.flags.c_contiguous and actual_u.flags.c_contiguous
        assert np.array_equal(actual_e.view("<u8"), expected.view("<u8")) and np.array_equal(actual_u, codes)
        return info

    for value in (0., 20., 12000.):
        check(f"actual-conversion-constant-{value}", lambda value=value: conversion(np.full((48, 64), value, dtype="<f8")))
    ties = [(0, 0, 8.), (2, 0, 24.), (1, 0, 2.), (3, 0, 6.), (5, 0, 10.), (1, 1, 10.), (3, 1, 30.)]
    for delta in (-(2 ** -20), 0., 2 ** -20):
        value = np.full((48, 64), 20., dtype="<f8")
        for x, y, e in ties:
            value[y, x] = e + delta
        check(f"actual-seven-parity-ties-{delta}", lambda value=value: conversion(value))
    y, x = np.indices((48, 64))
    patterned = np.asarray(12000 + 4 * x + 8 * y, dtype="<f8")
    check("actual-spatial-phase-field", lambda: conversion(patterned))
    check("actual-strided-conversion-snapshot", lambda: conversion(patterned[:, ::-1]))
    for name, value in (("f32", patterned.astype("<f4")), ("big-endian", patterned.astype(">f8")),
                        ("bool", patterned.astype(bool)), ("complex", patterned.astype(complex)),
                        ("shape", patterned.T), ("list", patterned.tolist())):
        check("actual-conversion-refuse-" + name, lambda value=value: E.convert_cfa(value), True)
    for v in (-1., float("nan"), float("inf"), 59390., 59391., 59392., 59393., 59392. - 2 ** -20):
        value = patterned.copy()
        value[0, 1] = v
        check("actual-conversion-rail-" + str(v), lambda value=value: E.convert_cfa(value), True)
    value = patterned.copy()
    value[0, 1] = 59389.
    check("actual-valid-near-white-companion", lambda: conversion(value))
    for key, wrong in (("noise", True), ("channel_factors", [.8, 1, .6]), ("black", 513), ("gain_dn_per_e", 1.),
                       ("cfa", "BGGR"), ("active_origin", [1, 0]), ("rounding", "half-up"), ("width", 64.0),
                       ("white", True), ("unknown", None)):
        sensor = M.sensor_record()
        sensor[key] = wrong
        check("actual-sensor-refuse-" + key, lambda sensor=sensor: E.convert_cfa(patterned, sensor), True)

    base = output / "fixture-only-no-optical-authority"
    bundle_path, gate_path = make_fixture(base)
    baseline_tree = tree(base)
    emitted = output / "emitted-private-valid"

    def valid():
        path = E.emit_cfa_bundle(bundle_path, gate_path, sha(gate_path), emitted)
        return actual_output(path, bundle_path)

    check("complete-five-actual-cfa-and-archived-lineage", valid, boundary="fixture-only-complete-api")
    relocated = output / "relocated-identical-package"
    shutil.copytree(base, relocated)

    def relocation():
        assert tree(base) == tree(relocated), "byte-identical input package required"
        relocated_bundle = relocated / bundle_path.name
        p = E.emit_cfa_bundle(relocated_bundle, gate_path, sha(gate_path), output / "emitted-relocation")
        values = actual_output(p, relocated_bundle)
        assert [v["cfa_sha256"] for v in values] == [v["cfa_sha256"] for v in actual_output(emitted / "manifest.json", bundle_path)]
        return values

    check("actual-identical-package-relocation", relocation, boundary="fixture-only-complete-api")

    def api_mutant(name, mutation, *, external_fixed=False, gate_mutation=None):
        folder = output / ("mutant-" + name)
        shutil.copytree(base, folder)
        bundle = read(folder / bundle_path.name)
        mutation(folder, bundle)
        if external_fixed:
            write(folder / bundle_path.name, bundle)
            gate, trusted = gate_path, sha(gate_path)
        else:
            gate = authority(folder, bundle)
            if gate_mutation:
                g = read(gate)
                gate_mutation(g)
                write(gate, g)
            trusted = sha(gate)
        dest = folder / "emission-must-refuse"
        try:
            E.emit_cfa_bundle(folder / bundle_path.name, gate, trusted, dest)
        finally:
            # If conversion happened before rejection, a complete manifest is forbidden.
            if dest.exists() and not (dest / "manifest.json").exists():
                assert read(dest / "emission-run.json")["status"] == "EMISSION_REFUSED"

    def change_scalar(folder, bundle):
        def change(a):
            a[31, 42] += 4
            return a
        mutate_scalar(folder, bundle, change)

    check("rehash-finite-scalar-fixed-external-authority", lambda: api_mutant("finite-fixed-anchor", change_scalar, external_fixed=True), True, "fixed-external-authority")
    check("rehash-foreign-distinct-frame-fixed-authority", lambda: api_mutant("foreign-frame", lambda d, b: mutate_scalar(d, b, lambda a: a + 16), external_fixed=True), True, "fixed-external-authority")

    simple_mutants = [
        ("unknown-top-key", ["unknown"], True), ("wrong-schema", ["schema"], "m194b-scene-v1"),
        ("self-cfa-pass", ["status"], "PASS"), ("bool-index", ["frames", 0, "index"], False),
        ("float-index", ["frames", 0, "index"], 0.), ("focus", ["frames", 0, "inverse_focus"], .6),
        ("wrong-curvature", ["frames", 2, "forward_similarity", "translation"], [.125, 0.]),
        ("bool-bytes", ["frames", 0, "expected_scalar", "bytes"], True),
        ("float-dimension", ["frames", 0, "expected_scalar", "shape"], [48., 64]),
        ("unknown-array-key", ["frames", 0, "expected_scalar", "container"], "npy"),
        ("uppercase-hash", ["frames", 0, "expected_scalar", "sha256"], read(bundle_path)["frames"][0]["expected_scalar"]["sha256"].upper()),
        ("ray-sign", ["ray_model", "defocus"], "K*(1/depth-inverse_focus)"),
        ("ray-order", ["ray_model", "visibility"], "background-first-same-ray"),
        ("ray-pupil", ["ray_model", "pupil"], "unit-radius-boundary"),
        ("cell-law", ["sensor", "cell"], "point-sample"),
        ("phase", ["scene", "background", "waves", 0, "phase"], .3),
        ("relaxed-tolerance", ["numerical_contract", "max_discrepancy_e"], .04),
        ("noise", ["sensor", "noise"], True), ("factor", ["sensor", "channel_factors"], [.75, 1, .7]),
        ("source-base", ["producer", "source_base"], "bundle"),
    ]
    for name, keys, value in simple_mutants:
        check("closed-" + name, lambda name=name, keys=keys, value=value: api_mutant(name, lambda d, b: set_at(b, keys, value)), True, "private-authority-semantic")

    for name, transform in (("nan", lambda a: np.where(np.indices(a.shape)[0] == 0, np.nan, a)),
                            ("negative", lambda a: -a), ("f32", lambda a: a.astype("<f4")),
                            ("big-endian", lambda a: a.astype(">f8")), ("transpose", lambda a: a.T),
                            ("fortran-storage", lambda a: np.asfortranarray(a))):
        check("actual-npy-" + name, lambda name=name, transform=transform: api_mutant("array-" + name, lambda d, b: mutate_scalar(d, b, transform)), True, "private-authority-semantic")
    check("actual-npy-trailing-rehashed", lambda: api_mutant("array-trailing", lambda d, b: mutate_scalar(d, b, lambda a: a, trailing=b"x")), True, "private-authority-semantic")

    numerical_mutants = [
        ("receipt-false-dtype", ["expected_scalar", "dtype"], "<u2"),
        ("receipt-frame-index", ["frame", "index"], True),
        ("receipt-integrator", ["integrator", "angle_high"], 64),
        ("receipt-status", ["status"], "PASS"), ("receipt-unknown", ["unknown"], True),
        ("receipt-indicator-max", ["max_error_indicator_e"], .0001),
        ("receipt-tile-bool", ["tile"], True), ("receipt-work-bool", ["work", "point_calls"], True),
        ("receipt-work-overlimit", ["work", "angular_nodes"], 600_000_001),
        ("receipt-time-overlimit", ["work", "cpu_seconds"], 600.01),
        ("receipt-live-frame-zero", ["work", "peak_live_scalar_frames"], 0),
        ("receipt-inert-count", ["work", "observer"], "count"),
        ("receipt-off-hooks", ["work", "optional_hook_calls"], 1),
    ]
    for name, keys, value in numerical_mutants:
        check(name, lambda name=name, keys=keys, value=value: api_mutant(name, lambda d, b: mutate_numerical(d, b, lambda r: set_at(r, keys, value))), True, "private-authority-semantic")

    for name, path in (("traverse", "../" + base.name + "/primary/frame-0-scalar.npy"),
                       ("backslash", "primary\\frame-0-scalar.npy"), ("absolute", str(base / "primary/frame-0-scalar.npy")),
                       ("drive-relative", "C:primary/frame-0-scalar.npy"), ("unc", "//localhost/invalid/frame.npy"),
                       ("dot", "./primary/frame-0-scalar.npy"), ("empty-segment", "primary//frame-0-scalar.npy")):
        check("path-" + name, lambda name=name, path=path: api_mutant("path-" + name, lambda d, b: set_at(b, ["frames", 0, "expected_scalar", "path"], path)), True, "private-authority-semantic")

    for name, mutation in (("missing-source", lambda d, b: b["producer"]["sources"].pop(next(iter(b["producer"]["sources"])))),
                           ("extra-source", lambda d, b: b["producer"]["sources"].update({"fake.py": {"sha256": "0" * 64, "bytes": 0}})),
                           ("duplicate-frame", lambda d, b: b["frames"].__setitem__(1, deepcopy(b["frames"][0]))),
                           ("missing-refinement", lambda d, b: b["refinements"]["cell-refined"].pop())):
        check(name, lambda name=name, mutation=mutation: api_mutant(name, mutation), True, "private-authority-semantic")

    def controls_change(folder, bundle):
        path = folder / "fixture-only-author-controls.json"
        control = read(path)
        control["checks"][0]["pass_"] = False
        write(path, control)
        bundle["producer"]["author_controls"] = ref(path, S.REPOSITORY)
    check("actual-rehashed-failed-author-control", lambda: api_mutant("control-failed", controls_change), True, "private-authority-semantic")

    # These are content substitutions with fresh lengths/hashes, not stale digests.
    def source_substitution(folder, bundle):
        original = HERE / "render.py"
        foreign = folder / "foreign-render.py"
        foreign.write_bytes(original.read_bytes() + b"\n# private changed source payload\n")
        old = original.relative_to(S.REPOSITORY).as_posix()
        new = foreign.relative_to(S.REPOSITORY).as_posix()
        bundle["producer"]["sources"].pop(old)
        bundle["producer"]["sources"][new] = {k: v for k, v in ref(foreign, S.REPOSITORY).items() if k != "path"}
    check("actual-rehashed-foreign-source-substitution", lambda: api_mutant("foreign-source-content", source_substitution), True, "private-authority-semantic")

    def changed_control_anchor(folder, bundle):
        path = folder / "fixture-only-author-controls.json"
        control = read(path)
        control["checks"][0]["name"] += " PRIVATE COHERENT CHANGE"
        write(path, control)
        bundle["producer"]["author_controls"] = ref(path, S.REPOSITORY)
    check("rehashed-pass-control-fixed-external-authority", lambda: api_mutant("pass-control-fixed-anchor", changed_control_anchor, external_fixed=True), True, "fixed-external-authority")
    for name, keys, value in (("gate-schema", ["schema"], "wrong"), ("gate-fail", ["status"], "FAIL"),
                              ("gate-unknown", ["unknown"], True), ("gate-scalar", ["expected_scalars", "0", "bytes"], 1),
                              ("gate-bool-length", ["author_bundle", "bytes"], True)):
        check(name, lambda name=name, keys=keys, value=value: api_mutant(name, lambda d, b: None, gate_mutation=lambda g: set_at(g, keys, value)), True, "private-authority-semantic")

    # Strict JSON uses actual authored entry points and complete unchanged companions.
    for name, content in (("duplicate", '{"a":1,"a":2}'), ("nan", '{"a":NaN}'),
                          ("infinity", '{"a":Infinity}'), ("malformed", '{')):
        check("strict-json-" + name, lambda content=content: S.strict_json_loads(content), True, "strict-json")
    check("strict-json-valid-companion", lambda: S.strict_json_loads('{"a":1,"b":[0.5,false]}'), boundary="strict-json")

    # Corrupt actual outputs and recompute their descriptors: metadata cannot mask value errors.
    def wrong_output(name, field, fn):
        destination = output / ("post-emission-" + name)
        shutil.copytree(emitted, destination)
        manifest = read(destination / "manifest.json")
        f = manifest["frames"][0]
        path = destination / f[field]["path"]
        if field == "cfa":
            a = O.read_raw(path)
            a = fn(a)
            path.write_bytes(a.tobytes())
        else:
            a = np.load(path, allow_pickle=False)
            np.save(path, fn(a), allow_pickle=False)
        f[field] = ref(path, destination, True)
        if field == "cfa":
            f[field]["dtype"] = "<u2"
        write(destination / "manifest.json", manifest)
        # Direct value reader deliberately bypasses stale run receipt metadata.
        return O.compare_files(destination / f["expected_scalar"]["path"], destination / f["expected_cfa"]["path"], path if field == "cfa" else destination / f["cfa"]["path"])

    def isolated(a):
        a[31, 42] += 1
        return a
    for name, field, fn in (("isolated-u16", "cfa", isolated), ("reverse-rows", "cfa", lambda a: a[::-1]),
                            ("byte-order", "cfa", lambda a: a.byteswap()), ("expected-electron", "expected_cfa", isolated)):
        check("actual-rehashed-output-" + name, lambda name=name, field=field, fn=fn: wrong_output(name, field, fn), True, "independent-post-emission-values")

    # Mid-read mutation is limited to this private clone and must never publish completion.
    def mid_read():
        folder = output / "mutation-during-emission"
        shutil.copytree(base, folder)
        bp = folder / bundle_path.name
        gp = authority(folder, read(bp))
        original_read = E.read_bound_bytes
        fired = []
        target = folder / "primary/frame-4-scalar.npy"
        def hook(r, root, **kwargs):
            data = original_read(r, root, **kwargs)
            if not fired:
                target.write_bytes(target.read_bytes() + b"changed during emission")
                fired.append(True)
            return data
        E.read_bound_bytes = hook
        dest = folder / "emitted"
        try:
            E.emit_cfa_bundle(bp, gp, sha(gp), dest)
        finally:
            E.read_bound_bytes = original_read
            assert fired and not (dest / "manifest.json").exists()
            assert read(dest / "emission-run.json")["status"] == "EMISSION_REFUSED"
    check("live-private-input-change-refuses-completion", mid_read, True, "during-emission")

    # Re-chosen non-square small actual renderer input. No full scientific frame claim.
    def observer():
        scene = M.Scene(M.Field(30., (.3, -.1)), M.Field(20., (-.2, .15)), (1., 2.), (1., .2), .8)
        frame = M.Frame(0, .7, 2.)
        arrays, indicators, counters = [], [], []
        for mode in ("off", "count", "placebo"):
            destination = output / ("actual-renderer-" + mode)
            meter = R.Meter(R.Integrator(), mode)
            record = R.render_frame(scene, frame, dict(width=2, height=3), R.Integrator(), destination, meter=meter)
            p = destination / record["expected_scalar"]["path"]
            receipt = read(destination / record["numerical_receipt"]["path"])
            arrays.append(sha(p))
            indicators.append(sha(destination / receipt["error_indicator"]["path"]))
            counters.append(meter.receipt())
        assert len(set(arrays)) == len(set(indicators)) == 1
        assert counters[0]["optional_hook_calls"] == counters[0]["observer_events"] == 0
        assert counters[1]["optional_hook_calls"] > 0 and counters[1]["observer_events"] > 0
        assert counters[2]["optional_hook_calls"] > 0 and counters[2]["observer_events"] == 0
        return dict(shape=[3, 2], scalar_sha256=arrays, indicator_sha256=indicators, measured_work=counters)
    check("actual-renderer-off-count-placebo-byte-invariance", observer, boundary="bounded-renderer-observer")
    check("unchanged-final-five-frame-companion", lambda: actual_output(emitted / "manifest.json", bundle_path), boundary="fixture-only-complete-api")
    def invariance_check():
        assert before == snap() and baseline_tree == tree(base)
        return dict(source_unchanged=True, fixture_unchanged=True)
    check("unchanged-source-and-original-fixture", invariance_check, boundary="invariance")
    after = snap()
    invariant = before == after and baseline_tree == tree(base)
    result = dict(schema="m194e-independent-emission-api-controls-v1", scope=SCOPE, command=sys.argv,
                  interpreter_argv=sys.orig_argv, executable=sys.executable, cwd=os.getcwd(), xoptions=sys._xoptions,
                  environment={k: os.environ.get(k) for k in ("PYTHONHASHSEED", "PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX")},
                  python=platform.python_version(), numpy=np.__version__, source_before=before, source_after=after,
                  root_pins=PINS, author_control=dict(path=str(AUTHOR_CONTROL), sha256=AUTHOR_CONTROL_SHA),
                  original_fixture_before=baseline_tree, original_fixture_after=tree(base),
                  genuine_float_admission=False, final_scientific_cfa_commission=False,
                  checks=checks, passed=sum(c["passed"] for c in checks), total=len(checks),
                  invariance=invariant, pass_=invariant and all(c["passed"] for c in checks))
    write(output / "result.json", result)
    print(json.dumps({k: result[k] for k in ("pass_", "passed", "total", "invariance")}), flush=True)
    return 0 if result["pass_"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

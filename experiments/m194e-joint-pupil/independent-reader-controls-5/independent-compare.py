"""Complete fixed-array numerical adjudication; emit authority only after every arm passes."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import traceback

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ARMS = ("primary", "angle-refined", "cell-refined")
PINS = {
    "controls": ("independent-controls-1/result.json", "e122c38565184a0d1798a6e03cfdf3dd2fae9aab2ede6e7a0dae82b8f7cb10ab"),
    "author_api": ("independent-author-api-5/result.json", "72304b090ab0eb39c56583146c59e4fbcfefd272ef7adb951283121e5f1e244f"),
    "reference": ("independent-reference-1/result.json", "8791700cdc969847ff75f9fbd9205739ee2135ac4bbbdbe445d00b6664c7eccc"),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def file_ref(path, root=REPO):
    path = Path(path).resolve()
    return dict(path=path.relative_to(root.resolve()).as_posix(), bytes=path.stat().st_size, sha256=sha(path))


def pairs(items):
    result = {}
    for k, v in items:
        if k in result:
            raise ValueError("duplicate JSON key: " + k)
        result[k] = v
    return result


def read_json(path, digest=None):
    if digest is not None and sha(path) != digest:
        raise ValueError("external digest differs: " + str(path))
    return json.loads(Path(path).read_text(encoding="utf8"), object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError("nonfinite JSON: " + v)))


def bound_path(ref, root):
    if not isinstance(ref, dict) or not {"path", "bytes", "sha256"}.issubset(ref):
        raise ValueError("missing file binding")
    value = ref["path"]
    if not isinstance(value, str) or not value or "\\" in value or ":" in value or any(v in ("", ".", "..") for v in value.split("/")):
        raise ValueError("noncanonical relative path")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or type(ref["bytes"]) is not int or path.stat().st_size != ref["bytes"] or sha(path) != ref["sha256"]:
        raise ValueError("file binding failed: " + value)
    return path


def array(ref, root):
    path = bound_path(ref, root)
    if path.stat().st_size > 48 * 64 * 8 + 4096:
        raise ValueError("oversized array")
    with path.open("rb") as stream:
        version = np.lib.format.read_magic(stream)
        if version == (1, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
        elif version == (2, 0):
            shape, fortran, dtype = np.lib.format.read_array_header_2_0(stream)
        else:
            raise ValueError("unregistered NPY version")
        if shape != (48, 64) or fortran or dtype.str != "<f8":
            raise ValueError("fixed bounded NPY header required before allocation")
        payload = stream.read()
        if len(payload) != 48 * 64 * 8:
            raise ValueError("incomplete or trailing array payload")
        value = np.frombuffer(payload, dtype="<f8").reshape((48, 64))
    if value.shape != (48, 64) or value.dtype.str != "<f8" or not value.flags.c_contiguous or not np.isfinite(value).all() or np.any(value < 0):
        raise ValueError("finite nonnegative complete64x48 float64 array required")
    return value


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bundle", type=Path, required=True)
    ap.add_argument("--bundle-sha256", required=True)
    ap.add_argument("--author-run", type=Path, required=True)
    ap.add_argument("--author-run-sha256", required=True)
    ap.add_argument("--schema-sha256", required=True)
    ap.add_argument("--reader-controls", type=Path, required=True)
    ap.add_argument("--reader-controls-sha256", required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    args.bundle = args.bundle.resolve()
    args.author_run = args.author_run.resolve()
    started, cpu = time.perf_counter(), time.process_time()
    result = dict(schema="m194e-independent-comparison-v1", status="RUNNING", command=sys.argv,
                  python=sys.version, numpy=np.__version__, numerical_threads=2,
                  inputs={}, sources={}, frames=[], author_refinement=[], independent_refinement=[])
    try:
        if sha(HERE / "schema.py") != args.schema_sha256:
            raise ValueError("externally pinned final schema changed")
        reader_controls = read_json(args.reader_controls, args.reader_controls_sha256)
        if (reader_controls["status"] != "PASS_READER_CONTROLS_ONLY" or reader_controls["source_unchanged"] is not True
                or len(reader_controls["checks"]) != 9 or not all(c["passed"] for c in reader_controls["checks"])):
            raise ValueError("final-array reader controls did not pass")
        for name, digest in reader_controls["sources"].items():
            if sha(HERE / name) != digest:
                raise ValueError("controlled file reader changed")
        result["inputs"]["reader_controls"] = file_ref(args.reader_controls)
        observer_path = HERE / "independent-observer-3/result.json"
        observer = read_json(observer_path, "29e7312d20bd2a46033c1ce5fc982749a52f95ef6ad533f87f1960d902b507fd")
        if (observer["status"] != "PASS_OBSERVER_TRAVERSAL_ONLY" or observer["source_unchanged"] is not True
                or len(observer["checks"]) != 32 or not all(c["passed"] for c in observer["checks"])):
            raise ValueError("independent powered tile/observer controls did not pass")
        for name, digest in observer["sources"].items():
            if sha(HERE / name) != digest:
                raise ValueError("observer-controlled numerical source changed")
        result["inputs"]["observer"] = file_ref(observer_path)
        map_path = HERE / "independent-map-controls-2/result.json"
        map_controls = read_json(map_path, "3c4eae49bd5097d1f7ae2cca0d8e1981f2eb8985e87873bbad8a4b3b629b4d68")
        if (map_controls["status"] != "PASS_MAP_COMPONENTS_ONLY" or map_controls["source_unchanged"] is not True
                or len(map_controls["checks"]) != 400 or not all(c["passed"] for c in map_controls["checks"])):
            raise ValueError("independent tangent-map controls did not pass")
        for name, digest in map_controls["sources"].items():
            if sha(HERE / name) != digest:
                raise ValueError("map-controlled numerical source changed")
        result["inputs"]["map_controls"] = file_ref(map_path)
        allocation_path = HERE / "independent-allocation-controls-3/result.json"
        allocation = read_json(allocation_path, "358905a23abbe77453b2eb6c8ff04f8d9153a8aaa798d72546f71250300754f6")
        if (allocation["status"] != "PASS_ALLOCATION_COMPONENTS_ONLY" or allocation["source_unchanged"] is not True
                or len(allocation["checks"]) != 62 or not all(c["passed"] for c in allocation["checks"])):
            raise ValueError("independent actual allocator controls did not pass")
        for name, digest in allocation["sources"].items():
            if sha(HERE / name) != digest:
                raise ValueError("allocation-controlled numerical source changed")
        result["inputs"]["allocation_controls"] = file_ref(allocation_path)
        # Root's closed structural reader is supplemental. The pixel reader,
        # numerical reference and complete-array comparisons are independent.
        structural = load_module("m194e_bound_schema", HERE / "schema.py")
        math_controls_path = HERE / "independent-comparison-controls-1/result.json"
        math_controls = read_json(math_controls_path, "690801fc7cd1b01ecc7e78be29328868584c582f133ad0188574b36a7978d53e")
        if math_controls["status"] != "PASS_MATH_READER_ONLY" or len(math_controls["checks"]) != 7 or not all(c["passed"] for c in math_controls["checks"]):
            raise ValueError("comparison power controls did not pass")
        for name, digest in math_controls["sources"].items():
            if sha(HERE / name) != digest:
                raise ValueError("commissioned comparison source changed")
        maths = load_module("m194e_independent_comparison_math", HERE / "independent-comparison-math.py")
        evidence = {}
        for key, (name, digest) in PINS.items():
            evidence[key] = read_json(HERE / name, digest)
            result["inputs"][key] = file_ref(HERE / name)
        controls, api, reference = (evidence[k] for k in ("controls", "author_api", "reference"))
        for record, status in ((controls, "PASS_REFERENCE_INSTRUMENT_ONLY"), (api, "PASS_AUTHOR_API_ONLY"), (reference, "PASS_COMPLETE_REFERENCE_ONLY")):
            if record["status"] != status or record["source_unchanged"] is not True:
                raise ValueError("independent predecessor did not pass")
            for name, digest in record["sources"].items():
                if sha(HERE / name) != digest:
                    raise ValueError("independent predecessor source changed: " + name)
        if len(controls["checks"]) != 55 or not all(c["passed"] for c in controls["checks"]):
            raise ValueError("reference instrument controls incomplete")
        for budget in [controls["budget"], api["budget"], *reference["budgets"].values()]:
            if (budget["limits"] != dict(evaluations=30_000_000, cpu_seconds=600., wall_seconds=1200.)
                    or not 0 <= budget["evaluations"] <= 30_000_000
                    or not 0 <= budget["cpu_seconds"] <= 600
                    or not 0 <= budget["wall_seconds"] <= 1200):
                raise ValueError("independent recorded resource ceiling exceeded")
        if len(api["checks"]) != 31 or not all(c["passed"] for c in api["checks"]) or len(api["texture_checks"]) != 336:
            raise ValueError("complete independently chosen API population required")
        errors = np.array([c["error_e"] for c in api["texture_checks"]])
        if not np.isfinite(errors).all() or np.max(np.abs(errors)) > .004 or np.sqrt(np.mean(errors * errors)) > .0008:
            raise ValueError("independent API discrepancy exceeded")
        bundle = read_json(args.bundle, args.bundle_sha256)
        run = read_json(args.author_run, args.author_run_sha256)
        structural.validate_bundle(args.bundle)
        result["inputs"].update(bundle=file_ref(args.bundle), author_run=file_ref(args.author_run), math_controls=file_ref(math_controls_path))
        if run["status"] != "FLOATS_COMPLETE_UNCOMMISSIONED" or run["sources_before"] != bundle["producer"]["sources"] or run["sources_after"] != run["sources_before"]:
            raise ValueError("author run incomplete or source changed")
        if run["designs_before"] != bundle["producer"]["designs"] or run["designs_after"] != run["designs_before"]:
            raise ValueError("author design binding changed or was not fixed before rendering")
        if bound_path(run["bundle"], args.author_run.parent) != args.bundle or run["command"] != bundle["producer"]["command"] or set(run["arms"]) != set(ARMS):
            raise ValueError("author run/bundle binding differs")
        source_paths = [HERE / n for n in ("independent-compare.py", "independent-comparison-math.py", "independent-comparison-controls.py", "independent-model.py", "independent-design.md")]
        for predecessor in (reader_controls, observer, map_controls, allocation, controls, api, reference, math_controls):
            source_paths += [HERE / name for name in predecessor["sources"]]
        source_paths += [REPO / name for name in bundle["producer"]["sources"]]
        source_paths += [HERE / name for name in bundle["producer"]["designs"]]
        snapshot = args.output / "source"
        snapshot.mkdir()
        for path in dict.fromkeys(source_paths):
            shutil.copyfile(path, snapshot / path.name)
            result["sources"][path.relative_to(REPO).as_posix()] = sha(path)
        for name in ("model.py", "render.py"):
            if api["sources"][name] != bundle["producer"]["sources"][(HERE / name).relative_to(REPO).as_posix()]["sha256"]:
                raise ValueError("complete API check used another numerical implementation")
        ref_records = {(r["arm"], r["index"]): r for r in reference["frames"]}
        if len(reference["frames"]) != 10 or set(ref_records) != {(a, i) for a in ("primary", "refined") for i in range(5)}:
            raise ValueError("complete independent primary/refined references required")
        for arm in ARMS:
            records = bundle["frames"] if arm == "primary" else bundle["refinements"][arm]
            if run["arms"][arm]["status"] != "complete" or run["arms"][arm]["frames"] != records:
                raise ValueError("author arm completion differs")
            for i, frame in enumerate(records):
                reference_path = (HERE / PINS["reference"][0]).parent
                ref = array(ref_records[("refined", i)]["array"], reference_path)
                actual = array(frame["expected_scalar"], args.bundle.parent)
                stats = maths.compare(actual, ref)
                result["frames"].append(dict(arm=arm, index=i, statistics=stats, actual=frame["expected_scalar"], reference=ref_records[("refined", i)]["array"]))
                # Do not stop at a failed frame or report only passing pixels.
                del actual, ref
            write(args.output / "partial.json", result)
        for i in range(5):
            reference_path = (HERE / PINS["reference"][0]).parent
            primary = array(ref_records[("primary", i)]["array"], reference_path)
            refined = array(ref_records[("refined", i)]["array"], reference_path)
            maximum = float(np.max(np.abs(primary - refined)))
            result["independent_refinement"].append(dict(index=i, maximum_e=maximum, passed=maximum <= .0005))
            for a, limit in (("primary", .000125), ("refined", .0000078125)):
                indicator = array(ref_records[(a, i)]["indicators"], reference_path)
                if float(indicator.max()) > limit:
                    raise ValueError("independent numerical indicator exceeded")
                del indicator
            del primary, refined
            primary = array(bundle["frames"][i]["expected_scalar"], args.bundle.parent)
            for arm in ("angle-refined", "cell-refined"):
                refined = array(bundle["refinements"][arm][i]["expected_scalar"], args.bundle.parent)
                maximum = float(np.max(np.abs(primary - refined)))
                result["author_refinement"].append(dict(arm=arm, index=i, maximum_e=maximum, passed=maximum <= .001))
                del refined
            del primary
        if len(result["frames"]) != 15 or not all(r["statistics"]["pass"] for r in result["frames"]) or not all(r["passed"] for r in result["independent_refinement"] + result["author_refinement"]):
            raise ValueError("complete fixed-array discrepancy/refinement failed")
        for name, digest in result["sources"].items():
            if sha(REPO / name) != digest:
                raise ValueError("source changed during comparison")
        structural.validate_bundle(args.bundle)
        result["source_unchanged"] = True
        result["status"] = "PASS_FLOAT_MODEL"
    except Exception as exc:
        result["status"] = "UNCOMMISSIONED"
        result["error"] = repr(exc)
        result["traceback"] = traceback.format_exc()
    result["cpu_seconds"] = time.process_time() - cpu
    result["wall_seconds"] = time.perf_counter() - started
    write(args.output / "result.json", result)
    if result["status"] == "PASS_FLOAT_MODEL":
        evidence_refs = {key: file_ref(HERE / path) for key, (path, _) in PINS.items()}
        evidence_refs["comparison"] = file_ref(args.output / "result.json")
        commission = dict(schema="m194e-float-commission-v1", status="PASS",
                          author_root=args.bundle.parent.relative_to(REPO).as_posix(),
                          author_bundle=file_ref(args.bundle, args.bundle.parent),
                          producer_sources=bundle["producer"]["sources"],
                          scene=bundle["scene"], ray_model=bundle["ray_model"], numerical_contract=bundle["numerical_contract"],
                          expected_scalars={str(i): f["expected_scalar"] for i, f in enumerate(bundle["frames"])},
                          numerical_receipts={str(i): f["numerical_receipt"] for i, f in enumerate(bundle["frames"])},
                          author_controls=bundle["producer"]["author_controls"], independent_evidence=evidence_refs)
        write(args.output / "float-commission.json", commission)
    print(json.dumps(dict(status=result["status"], frames=len(result["frames"]), error=result.get("error"))))
    return 0 if result["status"] == "PASS_FLOAT_MODEL" else 1


if __name__ == "__main__":
    raise SystemExit(main())

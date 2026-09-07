"""Independent intended12 read and integrated adapter controls; no producer imports."""
import time
ENTRY_CPU, ENTRY_WALL = time.process_time(), time.perf_counter()
import argparse
import importlib.util
from pathlib import Path
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ARTIFACTS = ("plan", "plan_launch", "receipt", "tiff", "log", "launch")


def population():
    rows = []
    for scene in ("flat", "textured"):
        for seed in (None, 701):
            for mode in ("hard-floor", "floor-pedestal-v1"):
                rows.append(dict(ordinal=len(rows), scene=scene, noise_enabled=seed is not None, seed=seed,
                                 admission=mode, subset="all-five", original_indices=[0,1,2,3,4], observer="off"))
    for observer in ("count", "placebo"):
        rows.append(dict(ordinal=len(rows), scene="textured", noise_enabled=True, seed=701,
                         admission="hard-floor", subset="all-five", original_indices=[0,1,2,3,4], observer=observer))
    for index in (0, 4):
        rows.append(dict(ordinal=len(rows), scene="textured", noise_enabled=False, seed=None,
                         admission="hard-floor", subset="endpoint-"+str(index), original_indices=[index], observer="off"))
    return rows


def context_and_rows(matrix_ref, build_ref, private_ref, *, io, reads, private_reader, adapter):
    """Expose only the real externally bound12 companions to private instruments."""
    p = private_reader
    p.IO = io
    built = p.build_record(build_ref, reads)
    private, _ = reads.json(private_ref)
    io.need(private["schema"] == "m194g-independent-private-bridge-read-v1"
            and private["status"] == "PASS_PRIVATE_PRODUCTION_BRIDGE_READ"
            and private["error"] is None and private["finalization_errors"] == [], "genuine independent private bridge read")
    io.need(private["sources_before"] == private["sources_after"] and private["inputs_before"] == private["inputs_after"], "private read closure")
    p.mapped(private["sources_before"], reads); p.mapped(private["inputs_before"], reads)
    io.need(private["build"] == build_ref and len(private["outputs"]) == 6 and len(private["controls"]) == 9
            and all(v["passed"] is True for v in private["controls"]), "private admitted population/build")
    matrix, matrix_path = reads.json(matrix_ref)
    adapter.keys(matrix, "schema status ref_root build noise_admission execution_release invocation sources_before sources_after inputs_before inputs_after entries work error finalization_errors", "intended12 index")
    io.need(matrix["schema"] == "m194g-production-commission-matrix-v1"
            and matrix["status"] == "COMPLETE_12_RGB_OUTPUTS_UNSCORED" and matrix["ref_root"] == "repository"
            and matrix["error"] is None and matrix["finalization_errors"] == [], "complete actual twelve output index")
    adapter.exact(matrix["build"], build_ref, "same intended build")
    for stem in ("sources", "inputs"):
        io.need(matrix[stem+"_before"] == matrix[stem+"_after"], "intended index stable closure")
        p.mapped(matrix[stem+"_before"], reads)
    released, _ = reads.json(matrix["execution_release"])
    io.need(released["schema"] == "m194g-numerical-execution-release-v1" and released["scope"] == "production-commission-matrix", "actual intended release")
    adapter.exact(released["source_bindings"], matrix["sources_before"], "intended released sources")
    choices = [[matrix["execution_release"]["sha256"] if v == "ACTUAL_EXECUTION_RELEASE_SHA256" else v for v in row] for row in released["commands"]]
    io.need(matrix["invocation"] in choices, "actual intended command")
    io.need(build_ref in released["inputs"] and matrix["noise_admission"] in released["inputs"] and private_ref in released["inputs"], "released genuine prerequisites")
    for ref in released["inputs"]: p.bind(ref, reads)
    noise, _ = reads.json(matrix["noise_admission"])
    adapter.keys(noise, "schema status ref_root manifest generation_result independent_read float_commission noise_commission", "noise admission")
    io.need(noise["schema"] == "m194g-software-noise-admission-v1" and noise["status"] == "PASS_SOFTWARE_NOISE_FILES_ONLY" and noise["ref_root"] == "repository", "genuine noise files admission")
    children = {name: reads.json(noise[name])[0] for name in ("manifest", "generation_result", "independent_read", "float_commission", "noise_commission")}
    admission = children["independent_read"]
    io.need(admission["schema"] == "m194g-independent-noise-files-read-v1" and admission["status"] == "PASS_SOFTWARE_NOISE_FILES_ONLY"
            and admission["file_count"] == 90 and admission["noise_off_count"] == 10 and admission["noisy_count"] == 80
            and admission["controls"]["check_count"] == 37 and len(admission["controls"]["checks"]) == 37
            and all(v["pass"] is True for v in admission["controls"]["checks"])
            and admission["error"] is None and admission["finalization_errors"] == [], "independent complete ninety-file admission")
    for name in ("manifest", "generation_result", "float_commission", "noise_commission"):
        adapter.exact(admission[name], noise[name], "noise actual child association")
    for stem in ("sources", "inputs"):
        io.need(admission[stem+"_before"] == admission[stem+"_after"], "noise file read closure")
        p.mapped(admission[stem+"_before"], reads)
    manifest = children["manifest"]
    io.need(manifest["schema"] == "m194g-software-noise-manifest-v1" and len(manifest["bundles"]) == 18, "actual eighteen noise bundles")
    context = dict(executable=built["test_executable"], noise_admission=matrix["noise_admission"], authority=noise,
                   bundles=manifest["bundles"], manifest_root=reads.ref(noise["manifest"]).parent)
    io.need(type(matrix["entries"]) is list and len(matrix["entries"]) == 12, "exact intended12 population")
    subjects, seen = [], set()
    for expected, row in zip(population(), matrix["entries"], strict=True):
        io.need(type(row) is dict and set(row) == set(expected) | set(ARTIFACTS), "closed intended entry")
        adapter.exact({k: row[k] for k in expected}, expected, "ordered intended identity")
        for name in ARTIFACTS:
            path = p.bind(row[name], reads); stat = path.stat()
            identity = (stat.st_dev, stat.st_ino)
            io.need(stat.st_ino != 0 and identity not in seen, "distinct actual twelve artifacts")
            seen.add(identity)
        subjects.append(dict(row={k: v for k, v in row.items() if k != "observer"}, observer=row["observer"]))
    completed = matrix["work"]["completed_plans"]
    io.need(len(completed) == 12 and matrix["work"]["failed_launch"] is None, "complete plan rehearsal")
    for item, subject in zip(completed, subjects, strict=True):
        adapter.exact(item, dict(plan=subject["row"]["plan"], launch=subject["row"]["plan_launch"]), "completed plan association")
    return context, subjects, private, matrix


def main():
    spec = importlib.util.spec_from_file_location("m194g_intended_io", HERE/"independent-quality-io.py")
    io = importlib.util.module_from_spec(spec); spec.loader.exec_module(io)
    parser = argparse.ArgumentParser()
    for name in ("release", "matrix", "build", "private-read"):
        parser.add_argument("--"+name, type=Path, required=True); parser.add_argument("--"+name+"-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sources = (Path(__file__).name, "independent-quality-io.py", "independent-quality-metrics.py", "independent-rgb-tiff.py",
               "independent-private-bridge-read.py", "independent-quality-adapter.py", "independent-quality-adapter-controls.py", "independent-quality-readout.py")
    names = {(HERE/n).relative_to(ROOT).as_posix() for n in sources}
    required = [args.matrix.resolve(), args.build.resolve(), args.private_read.resolve()]
    required += [(HERE/n).resolve() for n in ("next-intended-bridge-reader-design.md", "next-quality-adapter-control-interface.md", "next-quality-score-adapter.md")]
    release, reads = io.verify_release(args.release, args.release_sha256, "intended-bridge-read", names, required)
    bound = release["source_bindings"]
    modules = {name: io.load_bound(HERE/filename, "m194g_intended_"+name, bound) for name, filename in (
        ("metrics", "independent-quality-metrics.py"), ("private", "independent-private-bridge-read.py"),
        ("adapter", "independent-quality-adapter.py"), ("controls", "independent-quality-adapter-controls.py"),
        ("readout", "independent-quality-readout.py"), ("tiff", "independent-rgb-tiff.py"))}
    io.np = modules["metrics"].np
    budget = modules["metrics"].Budget("instruments", start_cpu=ENTRY_CPU, start_wall=ENTRY_WALL)
    reads.budget = budget
    store = io.Store(args.output, budget)
    result = dict(schema="m194g-independent-production-bridge-read-v1", status="UNCOMMISSIONED_PRODUCTION_BRIDGE_READ", ref_root="repository",
                  build=io.file_ref(args.build), intended_outputs=io.file_ref(args.matrix), private_read=io.file_ref(args.private_read),
                  execution_release=io.file_ref(args.release), invocation=io.invocation(), sources_before=bound, sources_after=None,
                  inputs_before=None, inputs_after=None, adapter_controls=None, outputs=[], observer_identity=None, work=None, error=None, finalization_errors=[])
    private = None
    def check_inputs():
        current = {Path(k).relative_to(ROOT).as_posix(): v for k, v in reads.finish().items()}
        result["inputs_after"] = current
        io.need(result["inputs_before"] is None or result["inputs_before"] == current, "intended read input closure")
        result["sources_after"] = {name: io.file_binding(ROOT/name) for name in bound}
        io.need(bound == result["sources_after"], "intended read source closure")
    try:
        store.snapshots(bound)
        for key, attr in (("build", "build"), ("intended_outputs", "matrix"), ("private_read", "private_read")):
            io.need(result[key]["sha256"] == getattr(args, attr+"_sha256"), "external intended read pin")
        context, subjects, private, matrix = context_and_rows(result["intended_outputs"], result["build"], result["private_read"],
            io=io, reads=reads, private_reader=modules["private"], adapter=modules["adapter"])
        child = modules["controls"].initial_result()
        result["adapter_controls"] = child
        modules["controls"].run_controls(subjects, context, io=io, reads=reads, adapter=modules["adapter"], metrics=modules["metrics"],
                                         readout=modules["readout"], budget=budget, result=child)
        child_ref = store.json("adapter-controls.json", child)
        result["adapter_controls"] = dict(path=(store.root/child_ref["path"]).relative_to(ROOT).as_posix(), sha256=child_ref["sha256"], bytes=child_ref["bytes"])
        io.need(child["status"] == "PASS_QUALITY_MATRIX_ADAPTER_INSTRUMENTS" and child["error"] is None
                and len(child["checks"]) == 59 and all(v["passed"] is True for v in child["checks"]), "complete independent adapter instruments")
        for subject in subjects:
            checked = modules["adapter"].read_entry(subject["row"], io=io, reads=reads, context=context,
                                                    observer=subject["observer"], decode=True, tiff_reader=modules["tiff"])
            if context.get("common_geometry") is None: context["common_geometry"] = checked["geometry"]
            result["outputs"].append(checked)
        hashes = [result["outputs"][i]["row"]["tiff"]["sha256"] for i in (6,8,9)]
        pixel_hashes = [result["outputs"][i]["decoded"]["pixel_sha256"] for i in (6,8,9)]
        io.need(len(set(hashes)) == len(set(pixel_hashes)) == 1, "intended actual off/count/placebo byte identity")
        result["observer_identity"] = dict(ordinals=[6,8,9], file_sha256=hashes[0], pixel_sha256=pixel_hashes[0])
        io.need(len(result["outputs"]) == 12 and budget.tiff_decodes == 12, "complete twelve actual TIFF reads")
        result["status"] = "PASS_PRODUCTION_BRIDGE_ONLY"
    except Exception:
        result["error"] = traceback.format_exc()
    result["inputs_before"] = {Path(k).relative_to(ROOT).as_posix(): v for k, v in reads.observed.items()}
    ok = io.finish_terminal(store, "result.json", result, "PASS_PRODUCTION_BRIDGE_ONLY", check_inputs)
    if ok:
        gate = dict(schema="m194g-production-bridge-commission-v1", status="PASS_PRODUCTION_BRIDGE_ONLY", ref_root="repository",
                    build=result["build"], private_tests=private["private_tests"], private_outputs=private["private_outputs"],
                    intended_outputs=result["intended_outputs"], independent_read=io.file_ref(store.root/"result.json"),
                    execution_release=result["execution_release"], sources_before=bound, sources_after=result["sources_after"],
                    inputs_before=result["inputs_before"], inputs_after=result["inputs_after"], error=None, finalization_errors=[])
        try:
            check_inputs(); store.check(); store.json("bridge-commission.json", gate); check_inputs(); store.check(); budget.check()
        except Exception:
            # A final failure revokes the authoritative fixed path and the read.
            result["status"] = "UNCOMMISSIONED_PRODUCTION_BRIDGE_READ"
            result["finalization_errors"].append(traceback.format_exc())
            gate["status"] = "UNCOMMISSIONED_PRODUCTION_BRIDGE_READ"
            gate["finalization_errors"] = list(result["finalization_errors"])
            path = store.root/"bridge-commission.json"
            try:
                if path.exists(): path.rename(path.with_suffix(".rejected.json"))
            except Exception:
                result["finalization_errors"].append("retain rejected gate: " + traceback.format_exc())
                gate["finalization_errors"] = list(result["finalization_errors"])
                try:
                    # This invocation created the path. If retention failed,
                    # replace its known-invalid success with an explicit refusal.
                    path.write_bytes(io.canonical_bytes(gate))
                except Exception:
                    result["finalization_errors"].append("revoke gate: " + traceback.format_exc())
            io.finish_terminal(store, "result.json", result, "PASS_PRODUCTION_BRIDGE_ONLY", check_inputs)
            ok = False
    print(io.canonical_bytes(dict(status=result["status"], error=result["error"], finalization_errors=result["finalization_errors"])).decode(), flush=True)
    return 0 if ok else 1


if __name__ == "__main__": raise SystemExit(main())

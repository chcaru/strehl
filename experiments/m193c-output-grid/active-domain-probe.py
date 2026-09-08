"""One saved first-frame decoder-domain diagnosis; never imports on module load."""
import time
START = time.monotonic()
CPU_START = time.process_time()
import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "active-domain-probe-1"
MIB = 1 << 20
NATIVE_SHA = "94fe31fbd80854fac80114e0b16b150d9d70ed8899ced727dd8c052b74d0244a"
HELPER_SHA = "47b9f8d848759eba61f055b9fdca1f8ac400f134dcd7636f0e0eaaa955704e0b"


def need(ok, message):
    if not ok:
        raise ValueError(message)


def load(path, expected, name):
    raw = path.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == expected, "held executed source")
    spec = importlib.util.spec_from_loader(name, loader=None, origin=str(path))
    module = importlib.util.module_from_spec(spec)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def worker(release, budget, files, core):
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "2"
    runtime = files.read(release["runtime"])
    extra = files.read(release["adjacent"])
    for ref in [runtime["python_executable"], *runtime["module_files"], *extra["files"]]:
        files.verify(ref, 128 * MIB, True)
    import numpy as np
    import rawpy
    need(Path(sys.executable).resolve() == Path(runtime["python_executable"]["path"]).resolve(),
         "actual pinned interpreter")
    recorded_modules = {Path(ref["path"]).resolve(): ref for ref in runtime["module_files"]}
    for module in (np, np._core._multiarray_umath, rawpy, rawpy._rawpy):
        actual_path = Path(module.__file__).resolve()
        need(actual_path in recorded_modules, "actual imported module path in runtime")
        files.verify(recorded_modules[actual_path], 128 * MIB, True)
    need(np.__version__ == runtime["numpy_version"] and rawpy.__version__ == runtime["rawpy_version"] and
         list(rawpy.libraw_version) == runtime["libraw_version"], "recorded numerical versions")
    primary = files.read(release["primary"])
    source = primary["source"]
    need(primary["selected"] == 0 and source["active"] == dict(x=0, y=0, width=7032, height=4688),
         "exact previously observed first-frame domain")
    snapshot = files.verify(release["snapshot"], 64 * MIB)
    raw_bytes = snapshot.read_bytes()
    need(len(raw_bytes) == release["snapshot"]["bytes"] and
         hashlib.sha256(raw_bytes).hexdigest() == release["snapshot"]["sha256"], "same consumed snapshot bytes")
    visible_digest, subset_digest = hashlib.sha256(), hashlib.sha256()
    with rawpy.imread(io.BytesIO(raw_bytes)) as raw:
        sizes = {k: int(getattr(raw.sizes, k)) for k in
                 ("raw_height", "raw_width", "height", "width", "top_margin", "left_margin", "flip")}
        need(sizes == dict(raw_height=5120, raw_width=7168, height=4688, width=7028,
                           top_margin=0, left_margin=0, flip=0), "same observed independent domain")
        view = raw.raw_image
        need(view.dtype == np.dtype("uint16") and view.shape == (5120, 7168), "bounded raw buffer geometry")
        # Copy only the explicit candidate domain, while the owner is alive.
        candidate = view[:4688, :7032].copy(order="C")
        need(candidate.nbytes == 65932032 and candidate.flags.owndata, "owned bounded candidate ROI")
        visible = raw.raw_image_visible
        need(visible.shape == (4688, 7028), "visible metadata association")
        for y in range(4688):
            visible_digest.update(visible[y].tobytes(order="C"))
            subset_digest.update(candidate[y, :7028].tobytes(order="C"))
            budget.check()
        del visible, view
    del raw_bytes
    need(visible_digest.digest() == subset_digest.digest(), "visible view differs from candidate's common subset")
    full, rows = hashlib.sha256(), []
    for row in candidate:
        payload = row.astype("<u2", copy=False).tobytes(order="C")
        full.update(payload)
        rows.append(hashlib.sha256(payload).hexdigest())
        budget.check()
    expected_rows = source["active_row_sha256_u16_le"]
    need(len(rows) == len(expected_rows) == 4688, "complete row population")
    # A one-code change must disagree on the same complete row hashing path.
    old = int(candidate[2344, 7029])
    candidate[2344, 7029] = old ^ 1
    changed = hashlib.sha256(candidate[2344].astype("<u2", copy=False).tobytes()).hexdigest()
    need(changed != rows[2344], "changed disputed-column code is detectable")
    candidate[2344, 7029] = old
    need(hashlib.sha256(candidate[2344].astype("<u2", copy=False).tobytes()).hexdigest() == rows[2344],
         "restored disputed-column code")
    columns = []
    for x in range(7028, 7032):
        column = candidate[:, x]
        columns.append(dict(x=x, samples=int(column.size), zero_count=int(np.count_nonzero(column == 0)),
                            minimum=int(column.min()), maximum=int(column.max()),
                            sha256_u16_le=hashlib.sha256(column.astype("<u2", copy=False).tobytes()).hexdigest()))
    evidence = dict(schema="m193c-active-domain-evidence-v1", status="COMPLETE_DIAGNOSTIC_ONLY",
        original_index=0, primary=release["primary"], snapshot=release["snapshot"],
        candidate_domain=source["active"], independent_sizes=sizes,
        copied_inside_context=True, owned_array_bytes=int(candidate.nbytes), postprocess_calls=0,
        common_visible_sha256=visible_digest.hexdigest(), candidate_common_sha256=subset_digest.hexdigest(),
        candidate_sha256_u16_le=full.hexdigest(), primary_sha256_u16_le=source["active_sha256_u16_le"],
        whole_domain_matches=full.hexdigest() == source["active_sha256_u16_le"],
        row_sha256_u16_le=rows, mismatch_rows=[i for i, (a, b) in enumerate(zip(rows, expected_rows)) if a != b],
        disputed_columns=columns, changed_code_detected=True, restored_code_matches=True,
        interpretation="Decoder byte agreement only; declared visible domains remain different; physical sensor validity unproved")
    del candidate
    files.recheck()
    return evidence


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--release-sha256", required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    need(Path.cwd().resolve() == ROOT and os.name == "nt" and sys.dont_write_bytecode, "Windows ROOT/-B")
    with args.release.open("rb") as stream:
        raw = stream.read(MIB + 1)
    need(len(raw) < MIB and hashlib.sha256(raw).hexdigest() == args.release_sha256, "external release pin")
    core = load(HERE / "native-derivative-run.py", NATIVE_SHA, "m193c_probe_core")
    release = core.strict(raw)
    core.closed(release, ("schema", "sources", "inputs", "runtime", "adjacent", "primary", "snapshot",
                         "prior_work", "commands"), "probe release")
    need(release["schema"] == "m193c-active-domain-probe-release-v1", "diagnostic scope")
    command = release["commands"]["worker" if args.worker else "parent"]
    need(list(sys.orig_argv) == [args.release_sha256 if x == "ACTUAL_RELEASE_SHA256" else x for x in command],
         "released exact actual argv")
    if not args.worker:
        need(not OUTPUT.exists(), "fresh fixed diagnostic output")
        OUTPUT.mkdir()
    else:
        need(OUTPUT.is_dir() and not (OUTPUT / "worker.json").exists(), "one worker under released parent")
    budget = core.Budget(OUTPUT, release["prior_work"], START, CPU_START)
    files = core.Files(budget)
    result = dict(schema="m193c-active-domain-probe-run-v1", status="REFUSED", command=list(sys.orig_argv),
                  execution_release=None, observation=None, evidence=None, error=None, finalization_errors=[], work=None)
    cpu_complete = True
    try:
        result["execution_release"] = files.bind(args.release, MIB)
        core.binding_map(release["sources"], files)
        for ref in release["inputs"]:
            files.verify(ref, 64 * MIB)
        need(release["snapshot"]["path"] == "experiments/m193c-output-grid/native-derivative-1/frame-00/DSC00016.ARW",
             "only already-retained first snapshot")
        if args.worker:
            result["evidence"] = worker(release, budget, files, core)
        else:
            helper = load(HERE / "bounded-process.py", HELPER_SHA, "m193c_domain_process")
            api = helper.load_job_api(release["sources"]["experiments/m12-scorecard/m12-harness.py"])
            env, _ = helper.clean_environment()
            for name in list(env):
                if name.upper().startswith("PYTHON"):
                    del env[name]
            actual_command = [args.release_sha256 if x == "ACTUAL_RELEASE_SHA256" else x
                              for x in release["commands"]["worker"]]
            limits = budget.limits(MIB)
            limits.update(cpu_seconds=min(30, limits["cpu_seconds"]),
                          wall_seconds=min(60, limits["wall_seconds"]), committed_bytes=2 << 30)
            cpu_complete = False
            observation = helper.run(actual_command, env, ROOT, OUTPUT / "worker.log", api=api,
                                     **limits, check=budget.check)
            result["observation"] = observation
            accounting = observation.get("job_accounting")
            cpu_complete = (observation.get("terminal_job_accounting") is True and type(accounting) is dict and
                            type(accounting.get("active_processes")) is int and accounting["active_processes"] == 0 and
                            type(accounting.get("total_cpu_100ns")) is int and accounting["total_cpu_100ns"] >= 0)
            budget.child(observation)
            core.successful_process(observation, actual_command)
            child_ref = files.bind(OUTPUT / "worker.json", 4 * MIB)
            child = files.read(child_ref)
            need(child["status"] == "COMPLETE_DIAGNOSTIC_ONLY" and child["error"] is None and
                 child["finalization_errors"] == [], "actual diagnostic worker completion")
            need(child["execution_release"] == result["execution_release"] and child["command"] == actual_command,
                 "actual worker release/command association")
            result["evidence"] = child_ref
        files.recheck()
        budget.check(True)
        result["status"] = "COMPLETE_DIAGNOSTIC_ONLY"
    except Exception:
        result["error"] = traceback.format_exc()
    destination = OUTPUT / ("worker.json" if args.worker else "result.json")

    def fail(label):
        message = label + ": " + traceback.format_exc()
        result["status"] = "REFUSED"
        if result["error"] is None:
            result["error"] = message
        else:
            result["finalization_errors"].append(message)

    def persist_refusal():
        try:
            if destination.exists():
                retained = next((destination.with_suffix(suffix) for suffix in
                    (".first.json", ".refused-2.json", ".refused-3.json")
                    if not destination.with_suffix(suffix).exists()), None)
                need(retained is not None, "bounded failed-publication retention")
                destination.rename(retained)
            refused_bytes = core.json_bytes(result)
            need(len(refused_bytes) <= 4 * MIB, "bounded refusal receipt")
            with destination.open("xb") as stream:
                need(stream.write(refused_bytes) == len(refused_bytes), "complete refusal write")
                stream.flush()
                os.fsync(stream.fileno())
        except Exception:
            fail("refusal persistence")
            try:
                print(json.dumps(dict(error=result["error"], finalization_errors=result["finalization_errors"])),
                      file=sys.stderr, flush=True)
            except Exception:
                fail("refusal stderr")

    result["work"] = budget.work()
    result["cpu_accounting_complete"] = cpu_complete
    if not cpu_complete:
        result["work"]["cpu_seconds"] = None
    try:
        budget.save(destination, result)
        files.bind(destination, 4 * MIB)
        files.recheck()
        budget.check(True)
    except Exception:
        fail("terminal publication/check")
        persist_refusal()
    summary = dict(status=result["status"], result=str(destination), work_through_final_checks=budget.work(),
                   cpu_accounting_complete=cpu_complete, error=result["error"], finalization_errors=result["finalization_errors"])
    if not cpu_complete:
        summary["work_through_final_checks"]["cpu_seconds"] = None
    try:
        print(json.dumps(summary, allow_nan=False), flush=True)
        budget.check(True)
    except Exception:
        fail("terminal stdout/budget")
        persist_refusal()
    return 0 if result["status"] == "COMPLETE_DIAGNOSTIC_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())

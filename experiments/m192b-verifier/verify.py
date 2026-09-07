"""Prospective semantic bindings layered on the unchanged M192 verifier.

This reads recorded evidence, never executes recorded commands or opens captures.
The original bar reductions remain authoritative. See preregistration.md.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
import math
import ntpath
import re
from pathlib import Path, PurePosixPath
import statistics
import sys
from uuid import UUID

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT / "experiments/M192-m12-certify/verify.py"
TERMINAL_MEMBERS = {
    "protocol.json", "records.jsonl", "sweeps.json", "inputs-before.json",
    "inputs-after.json", "commission.json", "sidecars.json", "builds.json",
    "logs-manifest.json", "commission-logs-manifest.json", "verifier-self-test.json",
    "certificate.json",
}
ACTIVE_ENV = {"STREHL_PYRAMID_WORKERS", "STREHL_WARPMAP", "STREHL_CACHE_DIR", "TEMP", "TMP"}
THREAD_ENV = {"MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "RAYON_NUM_THREADS"}
SCHEMAS = {
    "builds.json": "m192-builds-v1", "campaign-complete.json": "m192-campaign-complete-v1",
    "certificate.json": "m192-m12-certificate-v1", "commission-logs-manifest.json": "m192-commission-logs-v1",
    "commission.json": "m192-commission-v1", "inputs-after.json": "m192-input-manifest-v1",
    "inputs-before.json": "m192-input-manifest-v1", "logs-manifest.json": "m192-logs-v1",
    "sidecars.json": "m192-sidecars-v1", "verification.json": "m192-verification-v1",
    "verifier-self-test.json": "m192-verifier-self-test-v1",
}


class VerificationError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise VerificationError(message)


def sha(payload):
    return hashlib.sha256(payload).hexdigest().upper()


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    def bad_constant(value):
        raise VerificationError(f"nonfinite JSON constant: {value}")
    return json.loads(path.read_bytes(), object_pairs_hook=pairs, parse_constant=bad_constant)


def positive_int(value, label, allow_zero=False):
    require(type(value) is int and value >= (0 if allow_zero else 1), f"invalid integer: {label}")
    return value


def finite(value, label, low=0.0, high=None):
    require(type(value) in (int, float) and math.isfinite(value) and value >= low
            and (high is None or value <= high), f"invalid number: {label}")
    return value


def close(actual, expected, label):
    finite(actual, label)
    require(math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-10), f"inconsistent {label}")


def timestamp(value):
    require(isinstance(value, str), "timestamp must be a string")
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "timestamp must include its time zone")
    return result


def digest_string(value):
    require(isinstance(value, str) and len(value) == 64
            and all(c in "0123456789ABCDEF" for c in value), "invalid SHA-256")
    return value


def artifact_file(root, relative):
    require(isinstance(relative, str) and relative and "\\" not in relative,
            "invalid artifact path")
    p = PurePosixPath(relative)
    require(not p.is_absolute() and ":" not in relative and ".." not in p.parts
            and p.as_posix() == relative, "artifact path is not canonical relative")
    resolved = (root / relative).resolve()
    require(resolved.is_relative_to(root.resolve()) and resolved.is_file(),
            f"artifact absent or escaping package: {relative}")
    return resolved


def bound_file(root, row, path_key="path"):
    p = artifact_file(root, row[path_key])
    require(p.stat().st_size == positive_int(row["bytes"], "artifact bytes", True), "artifact byte count")
    require(sha(p.read_bytes()) == digest_string(row["sha256"]), f"artifact hash: {row[path_key]}")
    return p


def windows_path(value):
    require(isinstance(value, str) and ntpath.isabs(value), "recorded path must be absolute")
    return ntpath.normcase(ntpath.normpath(value))


def load_legacy():
    # Pin the exact source tracked before this prospective continuation, portable
    # across Git newline settings. Do not silently inherit edits to its bars.
    import subprocess
    pinned = subprocess.check_output(["git", "-C", str(ROOT), "show", "4e6b4572:experiments/M192-m12-certify/verify.py"])
    require(LEGACY.read_bytes().replace(b"\r\n", b"\n") == pinned.replace(b"\r\n", b"\n"), "frozen verifier changed")
    spec = importlib.util.spec_from_file_location("m192b_original_verifier", LEGACY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    defaults = subprocess.check_output(["git", "-C", str(ROOT), "show", "4e6b4572:scripts/check-defaults.py"]).decode("utf-8")
    module.m192b_required_environment = set(re.findall(r'"(STREHL_[A-Z0-9_]+)"\s*:\s*Declared\(', defaults)) | THREAD_ENV | ACTIVE_ENV
    return module


def validate_invocation(row, spec, build, required_environment, campaign_path):
    """Shared product invocation contract for scored and commissioning runs."""
    n, w, rid = row["limit"], row["workers"], row["run_id"]
    positive_int(n, "frame count"); positive_int(w, "workers")
    require(row["schema"] == "m192-run-v1" and row["stack"] == spec["inputs"][str(n)], "record stack/schema")
    require(row["binary"] == {"bytes": build["binary_bytes"], "path": build["binary_path"], "sha256": build["binary_sha256"]}, "record binary binding")
    output = ntpath.join(campaign_path, "work", "outputs", rid + ".tiff")
    argv = row["argv"]
    require(argv[:6] == [build["binary_path"], "stack", spec["inputs"][str(n)], "--limit", str(n), "--out"]
            and windows_path(argv[6]) == windows_path(output)
            and argv[7:] == spec["configuration"]["arguments_after_output"], f"record command: {rid}")
    env = row["environment"]
    require(isinstance(env, dict) and required_environment <= set(env), "missing environment record")
    require(env["STREHL_PYRAMID_WORKERS"] == str(w), "worker environment mismatch")
    for name, suffix in {
        "STREHL_WARPMAP": ("sidecars", f"n{n}.warpmap.txt"),
        "STREHL_CACHE_DIR": ("cache", row["phase"], f"n{n}"),
        "TEMP": ("temp", rid), "TMP": ("temp", rid),
    }.items():
        require(windows_path(env[name]) == windows_path(ntpath.join(campaign_path, "work", *suffix)), f"environment path: {name}")
    require(all(v is None for k, v in env.items() if k not in ACTIVE_ENV), "uncleared environment")
    witness_keys = {"frames", "alignment", "worker", "repair_banner", "folded_all", "wrote_exact_path", "total_terminal", "all"}
    require(row["valid"] is True and type(row["returncode"]) is int and row["returncode"] == 0
            and row["invalid_reasons"] == [] and set(row["terminal_witness"]) == witness_keys
            and all(v is True for v in row["terminal_witness"].values()), "invalid terminal flags")
    for stream in ("stdout", "stderr"):
        require(windows_path(row[stream + "_log"]) == windows_path(output + f".{stream}.log"), "record absolute log path")


def validate_bindings(root, original):
    spec = original.protocol()
    for name, schema in SCHEMAS.items():
        require(load(artifact_file(root, name)).get("schema") == schema, f"artifact schema: {name}")
    require(artifact_file(root, "protocol.json").read_bytes() == original.PROTOCOL_PATH.read_bytes(), "protocol drift")
    records = original.strict_records(artifact_file(root, "records.jsonl"))
    expected = original.expected_runs(spec)
    require(len(records) == len(expected), "record count")
    for row, wanted in zip(records, expected, strict=True):
        require(all(type(row.get(k)) is type(v) and row.get(k) == v for k, v in wanted.items()), "run schedule/type drift")
    certificate = load(artifact_file(root, "certificate.json"))
    complete = load(artifact_file(root, "campaign-complete.json"))
    builds = load(artifact_file(root, "builds.json"))
    campaign_id = complete.get("campaign_id")
    require(isinstance(campaign_id, str) and str(UUID(campaign_id)) == campaign_id, "noncanonical/missing campaign ID")
    require(certificate.get("campaign_id") == campaign_id
            and all(r.get("campaign_id") == campaign_id for r in records), "campaign ID disagreement")
    require(complete.get("interrupted_or_resumed") is False, "interrupted campaign")
    require(set(complete["artifact_sha256"]) == TERMINAL_MEMBERS, "terminal manifest membership")
    for name, digest in complete["artifact_sha256"].items():
        require(sha(artifact_file(root, name).read_bytes()) == digest_string(digest), "terminal digest drift")
    require(certificate["records"]["count"] == len(records), "certificate record count")
    require(certificate["records"]["sha256"] == sha((root / "records.jsonl").read_bytes()), "certificate records binding")
    require(certificate["records"]["last_record_sha256"] == records[-1]["record_sha256"], "certificate chain binding")
    require(certificate["configuration"] == spec["configuration"], "certificate configuration")
    require(certificate["protocol_sha256_checkout"] == sha((root / "protocol.json").read_bytes()), "certificate protocol binding")
    measured = builds["measured"]
    require(certificate["lineage"]["binary_sha256"] == measured["binary_sha256"]
            and certificate["lineage"]["binary_bytes"] == measured["binary_bytes"], "certificate binary binding")
    campaign_path = ntpath.dirname(ntpath.dirname(ntpath.dirname(ntpath.dirname(measured["binary_path"]))))
    # binary_path is campaign/work/builds/measured/bin/strehl.exe.
    campaign_path = ntpath.dirname(campaign_path)
    expected_paths = set(TERMINAL_MEMBERS) | {"campaign-complete.json", "verification.json"}
    log_paths = set()
    previous_end = None
    parents = set()
    for row in records:
        n, w, rid = row["limit"], row["workers"], row["run_id"]
        validate_invocation(row, spec, measured, original.m192b_required_environment, campaign_path)
        argv = row["argv"]
        start, end = timestamp(row["started_utc"]), timestamp(row["completed_utc"])
        require(end > start and (previous_end is None or start >= previous_end), "overlapping/reversed run times")
        previous_end = end
        finite(row["wall_seconds"], "wall seconds", low=1e-9)
        memory = row["memory"]
        positive_int(memory["sample_count"], "sample count")
        positive_int(memory["missed_intervals"], "missed samples", True)
        for field in ("max_gap_ms", "median_gap_ms", "max_lateness_ms"):
            finite(memory[field], field)
        require(memory["max_gap_ms"] >= memory["median_gap_ms"], "gap aggregate order")
        require(memory["sample_interval_ms"] == spec["governing_sources"]["inherited_monitor"]["sample_interval_ms"], "sample interval")
        close(row["sampling_coverage"], original.coverage(row), "sampling coverage")
        require(memory["kernel_job_accounting"]["total_terminated_processes"] == 0, "terminated product process")
        require(memory["process_lifetimes"], "missing process lifetime")
        parents.update(positive_int(p["parent_pid"], "parent PID") for p in memory["process_lifetimes"])
        for stream in ("stdout", "stderr"):
            binding = row["log_artifacts"][stream]
            require(binding["path"] == f"logs/{rid}.tiff.{stream}.log", "record log path")
            bound_file(root, binding)
            log_paths.add(binding["path"])
        text = (root / row["log_artifacts"]["stderr"]["path"]).read_text(encoding="utf-8")
        markers = (f"frames          : {n} from {row['stack']}", "coverage mode   : scale -- as asked, --cover",
                   "alignment       : ON (sidecar-override)", f"{n} placed / 0 refused",
                   f"folded          : {n} / {n} frames", f"{w} execution threads",
                   "memory plan     : 4 canonical chunks, 1 reusable frame worker, 1 retained + 1 scratch accumulator",
                   "camera RGB -> LINEAR sRGB", "Malvar-He-Cutler demosaic", "wrote           : " + argv[6], "total           :")
        require(all(marker in text for marker in markers), f"terminal evidence mismatch: {rid}")
        host = row["host_load_during_run"]
        total = finite(host["system_total_cpu_seconds"], "system CPU total", low=1e-9)
        busy = finite(host["system_busy_cpu_seconds"], "system CPU busy", high=total)
        close(row["whole_host_cpu_mean_percent"], busy / total * 100, "record CPU mean")
    require(len(parents) == 1, "multiple campaign parents")
    require(timestamp(complete["completed_utc"]) >= previous_end, "premature completion")
    for manifest_name, subdir, count in (("logs-manifest.json", "logs", 266), ("commission-logs-manifest.json", "commission-logs", 11)):
        manifest = load(artifact_file(root, manifest_name))
        require(type(manifest["count"]) is int and manifest["count"] == len(manifest["logs"]) == count, "log count")
        names = [r["path"] for r in manifest["logs"]]
        require(len(set(names)) == count and all(PurePosixPath(n).parent.as_posix() == subdir for n in names), "log membership")
        for row in manifest["logs"]:
            bound_file(root, row)
        if subdir == "logs":
            require(set(names) == log_paths, "record/log manifest disagreement")
        expected_paths.update(names)
    before, after = (load(artifact_file(root, f"inputs-{phase}.json")) for phase in ("before", "after"))
    require(before["files"] == after["files"], "input before/after mismatch")
    files = before["files"]
    require(len(files) == len({windows_path(f["path"]) for f in files}) == 404, "input file membership")
    expected_groups = Counter()
    for n in spec["registered_matrix"]["native"]["frame_counts"]:
        directory = windows_path(spec["inputs"][str(n)])
        expected_groups[directory] = max(expected_groups[directory], n)
    require(Counter(windows_path(ntpath.dirname(f["path"])) for f in files) == expected_groups, "input groups")
    for f in files:
        positive_int(f["bytes"], "input bytes"); positive_int(f["mtime_ns"], "input mtime")
        digest_string(f["sha256"])
        require(f["path"].lower().endswith(".arw"), "input format")
    for phase, manifest in (("before", before), ("after", after)):
        require(manifest["phase"] == phase and type(manifest["selected_file_count"]) is int
                and manifest["selected_file_count"] == len(files)
                and manifest["selected_bytes"] == sum(f["bytes"] for f in files), "input aggregates")
        require(timestamp(manifest["started_utc"]) <= timestamp(manifest["completed_utc"]), "input manifest time")
    require(timestamp(before["completed_utc"]) < timestamp(records[0]["started_utc"])
            and timestamp(after["started_utc"]) > previous_end, "input bracketing")
    sidecars = load(artifact_file(root, "sidecars.json"))["sidecars"]
    counts = set(spec["registered_matrix"]["native"]["frame_counts"] + spec["registered_matrix"]["modulo"]["frame_counts"])
    require(len(sidecars) == len(counts) and {r["n"] for r in sidecars} == counts, "sidecar membership")
    for row in sidecars:
        n = positive_int(row["n"], "sidecar frame count")
        require(row["artifact_path"] == f"sidecars/n{n}.warpmap.txt" and row["sha256"] == spec["sidecars"][str(n)]["sha256"], "sidecar protocol binding")
        p = bound_file(root, row, "artifact_path")
        placed = [line.split() for line in p.read_text().splitlines() if line and line[0].isdigit()]
        require([int(x[0]) for x in placed] == list(range(n)) and all(x[1] == "placed" for x in placed), "sidecar placed indices")
        expected_paths.add(row["artifact_path"])
    for label in ("measured", "unrepaired"):
        row = builds[label]
        require(row["build_log"] == f"build-logs/{label}.log", "build log path")
        p = artifact_file(root, row["build_log"])
        require(sha(p.read_bytes()) == row["build_log_sha256"], "build log digest")
        expected_paths.add(row["build_log"])
    actual_paths = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    require(actual_paths == expected_paths, "package file membership")
    validate_commission(root, spec, builds, original.m192b_required_environment, campaign_path, campaign_id)
    validate_cpu(root, records)
    return {"campaign_id": campaign_id, "record_count": len(records), "artifact_files": len(actual_paths),
            "recorded_parent_pid": next(iter(parents)), "input_files": len(files)}


def validate_commission(root, spec, builds, required_environment, campaign_path, campaign_id):
    c = load(root / "commission.json")
    u = c["unrepaired"]
    require(u["commit"] == spec["lineage"]["unrepaired_control_commit"]
            and u["binary_sha256"] == builds["unrepaired"]["binary_sha256"], "commission lineage")
    def peak(record):
        m = record["memory"]
        require(record["returncode"] == 0 and m["kernel_job_accounting"]["active_processes"] == 0, "commission process failed")
        return max(positive_int(m["peak_process_tree_private_committed_bytes"], "commission sampled peak"),
                   positive_int(m["kernel_job_peak_memory"]["peak_job_memory_used_bytes"], "commission Job peak"))
    p = c["memory_plant"]
    close(p["null_peak_bytes"], peak(p["null"]), "null peak")
    close(p["plant_peak_bytes"], peak(p["plant"]), "plant peak")
    require(all(p[k]["memory"]["peak_process_count"] >= 2 for k in ("null", "plant")), "child memory commission not exercised")
    lsb = c["lsb_plant"]
    require(type(lsb["before"]) is int and type(lsb["after"]) is int and lsb["before"] ^ lsb["after"] == 1, "one-LSB plant")
    v = load(root / "verifier-self-test.json")
    names = {"missing-terminal-record", "broken-hash-chain", "worker-hash-divergence", "memory-overrun", "ratio-overrun", "sampling-undercoverage", "timing-overrun", "timing-contention-ambiguity", "missing-sweep-cpu"}
    require({r["name"] for r in v["controls"]} == names, "verifier control membership")
    require(c["verifier_self_test"] == v and v["caught"] == v["total"] == len(v["controls"])
            and v["total"] == 9 and all(x["caught"] is True for x in v["controls"])
            and v["inert_label_survived"] is True, "verifier commissioning details")
    derived = {
        "unrepaired_worker_gate_red": u["n33_w1"]["output_sha256"] != u["n33_w2"]["output_sha256"] and u["n33_w1"]["pixel_sha256"] != u["n33_w2"]["pixel_sha256"],
        "unrepaired_memory_gate_red": peak(u["n33_w4"]) > spec["bars"]["warm_peak_process_tree_bytes_max"],
        "memory_null_green": peak(p["null"]) < 2**30,
        "memory_plant_red": peak(p["plant"]) > spec["bars"]["warm_peak_process_tree_bytes_max"],
        "file_lsb_red": lsb["baseline_file_sha256"] != lsb["planted_file_sha256"],
        "pixel_lsb_red": lsb["baseline_pixel_sha256"] != lsb["planted_pixel_sha256"],
        "verifier_self_test_green": v["status"] == "COMMISSIONED",
    }
    require(c["gates"] == derived and all(derived.values()), "commission labels unsupported by observations")
    logs = load(root / "commission-logs-manifest.json")["logs"]
    expected_names = [f"commission-pre-n33-w{w}.tiff.{stream}.log" for w in (1, 2, 4) for stream in ("stderr", "stdout")]
    expected_names += [f"{stem}.{stream}.log" for stem in ("null-64mib", "plant-7gib") for stream in ("stderr", "stdout")]
    expected_names += ["verifier-self-test.log"]
    require([r["path"] for r in logs] == [f"commission-logs/{i:02d}-{name}" for i, name in enumerate(expected_names)], "commission log membership")
    test_logs = [r for r in logs if r["path"].endswith("-verifier-self-test.log")]
    require(len(test_logs) == 1 and test_logs[0]["sha256"] == c["verifier_self_test_log_sha256"], "commission self-test log binding")
    self_text = artifact_file(root, test_logs[0]["path"]).read_text(encoding="utf-8")
    require(json.loads(self_text[self_text.index("{"):]) == v, "commission self-test log observations")
    for index, key, amount in ((7, "null", 64 * 2**20), (9, "plant", 7 * 2**30)):
        text = artifact_file(root, logs[index]["path"]).read_text(encoding="utf-8")
        require(f"allocated={amount}\n" in text and f"measured_commit={spec['lineage']['measured_commit']}" in text, "allocation log evidence")
    for i, w in enumerate((1, 2, 4)):
        record = u[f"n33_w{w}"]
        peak(record)  # Every commissioning invocation must actually complete.
        validate_invocation(record, spec, builds["unrepaired"], required_environment, campaign_path)
        wanted = {"phase":"commission", "kind":"commission", "sweep":"commission",
                  "limit":33, "workers":w, "repetition":None, "order_index":w,
                  "run_id":f"commission-pre-n33-w{w}", "campaign_id":campaign_id,
                  "measured_commit":spec["lineage"]["unrepaired_control_commit"]}
        require(all(type(record[k]) is type(v) and record[k] == v for k,v in wanted.items()), "commission run identity")
        for offset, stream in enumerate(("stderr", "stdout")):
            embedded, archived = record["log_artifacts"][stream], logs[i * 2 + offset]
            require(embedded["path"] == f"logs/commission-pre-n33-w{w}.tiff.{stream}.log"
                    and all(embedded[k] == archived[k] for k in ("bytes", "sha256")),
                    "commission embedded log binding")
        text = artifact_file(root, logs[i * 2]["path"]).read_text(encoding="utf-8")
        require(f"{w} workers)" in text and "folded          : 33 / 33 frames" in text
                and "wrote           : " + record["argv"][6] in text
                and spec["lineage"]["unrepaired_control_commit"] in text, "unrepaired commission log evidence")
        for field in ("output_sha256", "pixel_sha256"):
            digest_string(record[field])


def validate_cpu(root, records):
    sweeps = load(root / "sweeps.json")
    require(len(sweeps) == 7 and [s["repetition"] for s in sweeps] == [None, 1, 2, 3, 4, 5, 6], "CPU sweep membership")
    for s in sweeps:
        require(s.get("schema") == "m192-sweep-cpu-v1", "CPU sweep schema")
        require(s["repetition"] is None or type(s["repetition"]) is int, "CPU sweep repetition type")
        rows = [r for r in records if r["phase"] == "modulo" and r["repetition"] == s["repetition"]]
        require(s["run_ids"] == [r["run_id"] for r in rows] and s["order"] == [r["limit"] for r in rows], "CPU sweep/run binding")
        require(s["sample_interval_seconds"] == 1.0, "CPU sample interval")
        trace = s["trace"]
        require(isinstance(trace, list) and trace, "missing CPU trace")
        elapsed = finite(s["elapsed_seconds"], "CPU trace duration", low=1e-9)
        require(elapsed >= sum(r["wall_seconds"] for r in rows), "CPU sweep shorter than its runs")
        last = 0.0
        for point in trace:
            t = finite(point["elapsed_seconds"], "CPU time", high=elapsed)
            finite(point["whole_host_cpu_percent"], "CPU percent", high=100)
            require(.75 <= t - last <= 1.25, "CPU trace gap/order")
            last = t
        require(0 <= elapsed - last <= 1.25, "CPU trace missing tail")
        require(s["trace_valid"] is True and s["trace_error"] is None, "CPU trace validity flags")
        close(s["whole_host_cpu_trace_mean_percent"], statistics.mean(p["whole_host_cpu_percent"] for p in trace), "CPU trace mean")
        mean = finite(s["whole_host_cpu_mean_percent"], "boundary CPU mean", high=100)
        # The interval counters start at the same counter as the boundary pair.
        # Any busy/idle interval rules out an all-idle/all-busy enclosing span.
        # Raw boundary counters were not retained, so their exact mean cannot
        # be reconstructed from the arithmetic mean of interval percentages.
        require(not (mean == 0 and any(p["whole_host_cpu_percent"] > 0 for p in trace))
                and not (mean == 100 and any(p["whole_host_cpu_percent"] < 100 for p in trace)),
                "boundary CPU mean contradicts trace")
        close(s["whole_host_cpu_peak_percent"], max(s["whole_host_cpu_mean_percent"], *(p["whole_host_cpu_percent"] for p in trace)), "CPU peak")
        for field, record_field in (("per_run_host_cpu_mean_percent", "whole_host_cpu_mean_percent"),):
            require(s[field] == {r["run_id"]: r[record_field] for r in rows}, "CPU per-run summaries")
        require(s["per_run_external_busy_fraction"] == {r["run_id"]: r["host_load_during_run"]["external_busy_fraction_of_wall_capacity"] for r in rows}, "external CPU summaries")


def verify_artifact(path):
    root = Path(path).resolve()
    original = load_legacy()
    bindings = validate_bindings(root, original)
    result = original.verify_artifact(root)
    recomputed = original.recompute_bars(original.strict_records(root / "records.jsonl"), load(root / "sweeps.json"), original.protocol())
    require(load(root / "certificate.json")["sampling_quality"] == recomputed["sampling_quality"], "certificate sampling quality")
    return {**result, "schema": "m192b-semantic-verification-v1", "semantic_bindings": bindings,
            "scope": "Recorded artifact consistency; unchanged M192 product-bar dispositions."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = verify_artifact(args.artifact)
    except Exception as error:
        print(f"VERIFY ERROR: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    if args.output:
        require(not args.output.resolve().is_relative_to(args.artifact.resolve()), "verification output must be outside frozen artifact")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only independent M192 terminal audit; consumes evidence, never RAW files.

Predeclared rejection cases: missing/duplicate/out-of-order run; broken/resealed
configuration mismatch; absent or mismatched log; changed input manifest; wrong
sidecar; absent completion; unbacked commissioning boolean. The verifier probes
below deliberately change configuration while preserving its record hash chain.
No imported production/verifier formula computes the independent conclusions.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import math
import ntpath
import statistics
import sys
from collections import Counter
from datetime import datetime
from fractions import Fraction
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CAMPAIGN = REPO / "experiments/M192-m12-certify/recovery-20260906-163253"
RESULTS = CAMPAIGN / "results"
VERIFIER = REPO / "experiments/M192-m12-certify/verify.py"


def digest(data):
    return hashlib.sha256(data).hexdigest().upper()


def load(path):
    def pairs(items):
        result = {}
        for k, v in items:
            assert k not in result, (path, "duplicate key", k)
            result[k] = v
        return result
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def seal(record):
    value = {k: v for k, v in record.items() if k != "record_sha256"}
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode())


def inventory():
    return {p.relative_to(RESULTS).as_posix(): {"bytes": p.stat().st_size, "sha256": digest(p.read_bytes())}
            for p in sorted(RESULTS.rglob("*")) if p.is_file()}


def time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def span(values):
    return max(values) / min(values) - 1.0


def main():
    before_inventory = inventory()
    protocol = load(RESULTS / "protocol.json")
    certificate = load(RESULTS / "certificate.json")
    complete = load(RESULTS / "campaign-complete.json")
    start = load(CAMPAIGN / "work/campaign-start.json")
    launch = load(CAMPAIGN / "launch-receipt.json")
    builds = load(RESULTS / "builds.json")
    record_bytes = (RESULTS / "records.jsonl").read_bytes()
    assert record_bytes.endswith(b"\n") and not record_bytes.endswith(b"\n\n")
    records = [json.loads(row) for row in record_bytes.splitlines()]
    expected = []
    for n in (33, 105, 299):
        expected += [(f"native-n{n}-w{w}-warmup", "native", "warmup", n, w, None) for w in (1, 2, 4, 8, 16)]
        for rep in range(1, 7):
            expected += [(f"native-n{n}-w{w}-r{rep}", "native", "scored", n, w, rep)
                         for w in ((1, 2, 4, 8, 16) if rep % 2 else (16, 8, 4, 2, 1))]
    expected += [(f"modulo-n{n}-warmup", "modulo", "warmup", n, 16, None) for n in (96, 97, 98, 99)]
    for rep in range(1, 7):
        expected += [(f"modulo-n{n}-r{rep}", "modulo", "scored", n, 16, rep)
                     for n in ((96, 97, 98, 99) if rep % 2 else (99, 98, 97, 96))]
    assert len(expected) == len(records) == 133
    actual = [tuple(r[k] for k in ("run_id", "phase", "kind", "limit", "workers", "repetition")) for r in records]
    assert actual == expected
    assert len({r["run_id"] for r in records}) == 133
    assert {r["campaign_id"] for r in records} == {start["campaign_id"]} == {complete["campaign_id"]} == {certificate["campaign_id"]}
    assert start["pid"] == launch["pid"] == 22556 and start["resume_allowed"] is False
    assert complete["interrupted_or_resumed"] is False
    assert not (CAMPAIGN / "work/campaign-aborted.json").exists()
    assert not (CAMPAIGN / "work/campaign-failed.json").exists()
    previous = "0" * 64
    prior_end = time(start["started_utc"])
    log_paths = set()
    normalized_flags = set()
    process_parents = set()
    wall_timestamp_error = []
    for index, r in enumerate(records):
        assert r["sequence_index"] == index and r["previous_record_sha256"] == previous
        assert seal(r) == r["record_sha256"]
        previous = r["record_sha256"]
        assert r["valid"] and not r["invalid_reasons"] and r["returncode"] == 0
        assert all(r["terminal_witness"].values())
        assert time(r["started_utc"]) >= prior_end
        assert time(r["completed_utc"]) > time(r["started_utc"])
        prior_end = time(r["completed_utc"])
        wall_timestamp_error.append(abs((prior_end - time(r["started_utc"])).total_seconds() - r["wall_seconds"]))
        n, w = r["limit"], r["workers"]
        assert r["argv"][0] == r["binary"]["path"] == builds["measured"]["binary_path"]
        assert r["binary"]["bytes"] == builds["measured"]["binary_bytes"]
        assert r["argv"][1:3] == ["stack", protocol["inputs"][str(n)]]
        assert r["argv"][3:6] == ["--limit", str(n), "--out"]
        assert r["argv"][7:] == protocol["configuration"]["arguments_after_output"]
        normalized_flags.add(tuple(r["argv"][7:]))
        env = r["environment"]
        assert env["STREHL_PYRAMID_WORKERS"] == str(w)
        assert ntpath.basename(env["STREHL_WARPMAP"]) == f"n{n}.warpmap.txt"
        assert Path(env["STREHL_WARPMAP"]) == CAMPAIGN / "work/sidecars" / f"n{n}.warpmap.txt"
        for name, value in env.items():
            if name not in {"STREHL_PYRAMID_WORKERS", "STREHL_WARPMAP", "STREHL_CACHE_DIR", "TEMP", "TMP"}:
                assert value is None, (r["run_id"], name, value)
        for stream, binding in r["log_artifacts"].items():
            path = RESULTS / binding["path"]
            assert path.resolve().is_relative_to(RESULTS.resolve())
            log_paths.add(binding["path"])
            assert path.stat().st_size == binding["bytes"]
            assert digest(path.read_bytes()) == binding["sha256"]
        text = (RESULTS / r["log_artifacts"]["stderr"]["path"]).read_text(encoding="utf-8")
        for marker in (f"frames          : {n} from {r['stack']}",
                       "coverage mode   : scale -- as asked, --cover",
                       "alignment       : ON (sidecar-override)", f"{n} placed / 0 refused",
                       f"folded          : {n} / {n} frames", f"{w} execution threads",
                       "memory plan     : 4 canonical chunks, 1 reusable frame worker, 1 retained + 1 scratch accumulator",
                       "camera RGB -> LINEAR sRGB", "Malvar-He-Cutler demosaic",
                       "wrote           : " + r["argv"][6], "total           :"):
            assert marker in text, (r["run_id"], marker)
        account = r["memory"]["kernel_job_accounting"]
        assert account["active_processes"] == 0 and account["total_terminated_processes"] == 0
        for p in r["memory"]["process_lifetimes"]:
            process_parents.add(p["parent_pid"])
        assert r["shape"] == [4688, 7032, 3] and r["dtype"] == "uint16"
        assert r["output_bytes"] == 197798956
    assert process_parents == {start["pid"]}
    assert previous == complete["last_record_sha256"] == certificate["records"]["last_record_sha256"]
    assert digest(record_bytes) == certificate["records"]["sha256"]
    assert time(complete["completed_utc"]) >= prior_end
    required = {"protocol.json", "records.jsonl", "sweeps.json", "inputs-before.json", "inputs-after.json", "commission.json", "sidecars.json", "builds.json", "logs-manifest.json", "commission-logs-manifest.json", "verifier-self-test.json", "certificate.json"}
    assert set(complete["artifact_sha256"]) == required
    for name, sha in complete["artifact_sha256"].items():
        assert digest((RESULTS / name).read_bytes()) == sha
    manifests = {}
    for manifest_name, subdir, expected_count in (("logs-manifest.json", "logs", 266), ("commission-logs-manifest.json", "commission-logs", 11)):
        manifest = load(RESULTS / manifest_name)
        assert manifest["count"] == len(manifest["logs"]) == expected_count
        names = {row["path"] for row in manifest["logs"]}
        assert len(names) == expected_count
        assert names == {p.relative_to(RESULTS).as_posix() for p in (RESULTS / subdir).iterdir() if p.is_file()}
        for row in manifest["logs"]:
            assert before_inventory[row["path"]] == {"bytes": row["bytes"], "sha256": row["sha256"]}
        manifests[manifest_name] = expected_count
    assert log_paths == {row["path"] for row in load(RESULTS / "logs-manifest.json")["logs"]}
    inputs_a, inputs_b = load(RESULTS / "inputs-before.json"), load(RESULTS / "inputs-after.json")
    assert inputs_a["files"] == inputs_b["files"]
    file_rows = inputs_a["files"]
    assert len(file_rows) == len({r["path"] for r in file_rows}) == inputs_a["selected_file_count"] == 404
    assert sum(r["bytes"] for r in file_rows) == inputs_a["selected_bytes"] == inputs_b["selected_bytes"]
    groups = Counter(ntpath.basename(ntpath.dirname(r["path"])) for r in file_rows)
    assert groups == {"bee-1-cpl": 299, "coffee-bean": 105}
    for r in file_rows:
        assert r["path"].lower().endswith(".arw") and len(r["sha256"]) == 64 and r["bytes"] > 0
    assert time(inputs_a["completed_utc"]) < time(records[0]["started_utc"])
    assert time(inputs_b["started_utc"]) > time(records[-1]["completed_utc"])
    sidecars = load(RESULTS / "sidecars.json")["sidecars"]
    assert {r["n"] for r in sidecars} == {33, 105, 299, 96, 97, 98, 99}
    for r in sidecars:
        assert r["sha256"] == protocol["sidecars"][str(r["n"])]["sha256"]
        path = RESULTS / r["artifact_path"]
        assert digest(path.read_bytes()) == r["sha256"] and path.stat().st_size == r["bytes"]
        assert digest((CAMPAIGN / "work/sidecars" / path.name).read_bytes()) == r["sha256"]
        rows = [line for line in path.read_text().splitlines() if line and line[0].isdigit()]
        assert len(rows) == r["n"] and [int(line.split()[0]) for line in rows] == list(range(r["n"]))
        assert all(line.split()[1] == "placed" for line in rows)
    for label in ("measured", "unrepaired"):
        b = builds[label]
        path = Path(b["binary_path"])
        assert path.is_relative_to(CAMPAIGN)
        assert path.stat().st_size == b["binary_bytes"] and digest(path.read_bytes()) == b["binary_sha256"]
        log = RESULTS / b["build_log"]
        assert digest(log.read_bytes()) == b["build_log_sha256"]
        assert "Compiling strehl-cli" in log.read_text(encoding="utf-8")
    assert {r["binary"]["sha256"] for r in records} == {builds["measured"]["binary_sha256"]}
    commissioned = load(RESULTS / "commission.json")
    u = commissioned["unrepaired"]
    assert u["commit"] == protocol["lineage"]["unrepaired_control_commit"]
    assert u["n33_w1"]["output_sha256"] != u["n33_w2"]["output_sha256"]
    assert u["n33_w1"]["pixel_sha256"] != u["n33_w2"]["pixel_sha256"]
    assert u["n33_w4"]["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"] > 6 * 2**30
    memory_plant = commissioned["memory_plant"]
    assert memory_plant["null"]["memory"]["peak_process_count"] >= 2
    assert memory_plant["plant"]["memory"]["peak_process_count"] >= 2
    assert memory_plant["null_peak_bytes"] < 2**30 < 6*2**30 < memory_plant["plant_peak_bytes"]
    lsb = commissioned["lsb_plant"]
    assert lsb["before"] ^ lsb["after"] == 1
    assert lsb["baseline_file_sha256"] != lsb["planted_file_sha256"]
    assert lsb["baseline_pixel_sha256"] != lsb["planted_pixel_sha256"]
    # Independent grouping/reduction; no verifier formulas are imported here.
    native = [r for r in records if r["phase"] == "native" and r["kind"] == "scored"]
    assert len(native) == 90
    cells = {(n, w): [r for r in native if (r["limit"], r["workers"]) == (n, w)] for n in (33,105,299) for w in (1,2,4,8,16)}
    identities = {}
    for n in (33,105,299):
        subset = [r for r in native if r["limit"] == n]
        assert len(subset) == 30
        assert all(len(cells[n,w]) == 6 for w in (1,2,4,8,16))
        identities[n] = {"file_hashes": sorted({r["output_sha256"] for r in subset}), "pixel_hashes": sorted({r["pixel_sha256"] for r in subset})}
        assert all(len(v) == 1 for v in identities[n].values())
    field = lambda r, kind: r["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"] if kind == "job" else r["memory"]["peak_process_tree_private_committed_bytes"]
    peaks = {kind: max(field(r,kind) for r in native) for kind in ("job", "sampled")}
    ratios = {kind: {w: str(Fraction(max(field(r,kind) for r in cells[299,w]), max(field(r,kind) for r in cells[33,w]))) for w in (1,2,4,8,16)} for kind in ("job", "sampled")}
    max_ratios = {kind: float(max(Fraction(v) for v in values.values())) for kind, values in ratios.items()}
    gaps = [{"run_id": r["run_id"], "coverage": r["memory"]["sample_count"]/(r["memory"]["sample_count"]+r["memory"]["missed_intervals"]), "max_gap_ms": r["memory"]["max_gap_ms"]} for r in native]
    failed = [r for r in gaps if r["coverage"] < .90 or r["max_gap_ms"] > 100]
    modulo = {(r["repetition"],r["limit"]): r["wall_seconds"]/r["limit"] for r in records if r["phase"] == "modulo" and r["kind"] == "scored"}
    raw_spread = span([min(modulo[rep,n] for rep in range(1,7)) for n in (96,97,98,99)])
    pair_spreads = []
    for rep in (1,3,5):
        arithmetic = [(modulo[rep,n]+modulo[rep+1,n])/2 for n in (96,97,98,99)]
        geometric = [math.exp((math.log(modulo[rep,n])+math.log(modulo[rep+1,n]))/2) for n in (96,97,98,99)]
        pair_spreads.append(max(span(arithmetic), span(geometric)))
    sweeps = load(RESULTS / "sweeps.json")
    assert len(sweeps) == 7
    for s in sweeps:
        expected_ids = [r["run_id"] for r in records if r["phase"] == "modulo" and r["repetition"] == s["repetition"]]
        assert s["run_ids"] == expected_ids
        trace = s["trace"]
        assert trace and all(0 <= point["whole_host_cpu_percent"] <= 100 for point in trace)
        assert all(a["elapsed_seconds"] < b["elapsed_seconds"] for a,b in zip(trace,trace[1:]))
        assert abs(statistics.mean(p["whole_host_cpu_percent"] for p in trace)-s["whole_host_cpu_trace_mean_percent"]) < 1e-10
        assert max(s["whole_host_cpu_mean_percent"], *(p["whole_host_cpu_percent"] for p in trace)) == s["whole_host_cpu_peak_percent"]
        assert all(.75 <= p["elapsed_seconds"] - (trace[i-1]["elapsed_seconds"] if i else 0) <= 1.25 for i,p in enumerate(trace))
        assert 0 <= s["elapsed_seconds"] - trace[-1]["elapsed_seconds"] <= 1.25
    # Challenge what the official validator fails to inspect, in-memory only.
    module_spec = importlib.util.spec_from_file_location("m192_original_verifier", VERIFIER)
    official = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(official)
    mutations = []
    scored_index = next(i for i,r in enumerate(records) if r["kind"] == "scored")
    for name in ("wrong_pyramid_gate", "wrong_worker_environment", "missing_campaign_ids"):
        altered = copy.deepcopy(records)
        if name == "wrong_pyramid_gate": altered[scored_index]["argv"][10] = "999"
        if name == "wrong_worker_environment": altered[scored_index]["environment"]["STREHL_PYRAMID_WORKERS"] = "999"
        if name == "missing_campaign_ids":
            for r in altered: del r["campaign_id"]
        prev = "0"*64
        for r in altered:
            r["previous_record_sha256"] = prev
            r["record_sha256"] = seal(r)
            prev = r["record_sha256"]
        try:
            official.validate_record_structure(altered, protocol, RESULTS)
            accepted = True
        except Exception:
            accepted = False
        mutations.append({"name": name, "record_validator_accepted": accepted})
    assert inventory() == before_inventory
    result = {
        "status": "VERIFIED_COMPLETE_WITH_SCOPED_PASS_AND_ADMISSION_REFUSALS",
        "scope": "artifact verification and independent reductions; no new product render or RAW access",
        "source_hashes": {"independent_audit": digest(Path(__file__).read_bytes()), "official_verifier": digest(VERIFIER.read_bytes()), "protocol": digest((RESULTS/'protocol.json').read_bytes()), "records": digest(record_bytes), "certificate": digest((RESULTS/'certificate.json').read_bytes())},
        "record_count": len(records), "native_scored_count": len(native), "schedule_counts": dict(Counter(r["phase"]+"/"+r["kind"] for r in records)),
        "campaign_id": start["campaign_id"], "parent_pids": sorted(process_parents), "last_chain_hash": previous,
        "input_files": len(file_rows), "input_groups": dict(groups), "input_bytes": inputs_a["selected_bytes"], "input_manifests_equal": True,
        "verified_log_manifest_counts": manifests, "result_artifact_files": len(before_inventory), "original_artifacts_unchanged": True,
        "all_record_configurations_and_stderr_witnesses_checked": True, "wall_vs_timestamp_max_delta_seconds": max(wall_timestamp_error),
        "binary_sha256": builds["measured"]["binary_sha256"], "identities": identities,
        "memory_peaks_bytes": peaks, "peak_ratios_exact": ratios, "peak_ratios_maximum": max_ratios, "sampling_failures": failed,
        "minimum_sampling_coverage": min(r["coverage"] for r in gaps), "maximum_sampling_gap_ms": max(r["max_gap_ms"] for r in gaps),
        "timing_raw_spread": raw_spread, "timing_reversal_pair_spreads": pair_spreads,
        "bar_verdicts": {"byte_identity": "PASS", "memory": "UNMEASURED_SAMPLING_COVERAGE", "peak_ratio": "UNMEASURED_SAMPLING_COVERAGE", "modulo": "UNMEASURED_HOST_CONTENTION"},
        "record_validator_challenges": mutations,
        "commission_memory": {"null_peak_bytes": memory_plant["null_peak_bytes"], "plant_peak_bytes": memory_plant["plant_peak_bytes"], "unrepaired_n33_w4_job_peak_bytes": u["n33_w4"]["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"]},
        "preservation_inventory": before_inventory,
    }
    (HERE / "independent-audit.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    result.pop("preservation_inventory")
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()

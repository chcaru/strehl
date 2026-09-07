"""Exercise full public artifact verification with re-sealed corruptions.

Original campaign files are never written. Every control reaches verify_artifact;
ordinary metadata checksums are repaired before invocation.
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
from uuid import uuid4

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ORIGINAL = ROOT / "experiments/M192-m12-certify/recovery-20260906-163253/results"
module_spec = importlib.util.spec_from_file_location("m192b_verify", HERE / "verify.py")
V = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(V)


def inventory(path):
    return {p.relative_to(path).as_posix(): V.sha(p.read_bytes()) for p in path.rglob("*") if p.is_file()}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def reseal(root, rows, documents):
    previous = "0" * 64
    for row in rows:
        row["previous_record_sha256"] = previous
        value = {k: v for k, v in row.items() if k != "record_sha256"}
        row["record_sha256"] = V.sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode())
        previous = row["record_sha256"]
    (root / "records.jsonl").write_text("".join(json.dumps(r, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n" for r in rows), encoding="utf-8", newline="\n")
    certificate = documents["certificate.json"]
    certificate["records"]["last_record_sha256"] = previous
    certificate["records"]["sha256"] = V.sha((root / "records.jsonl").read_bytes())
    complete = documents["campaign-complete.json"]
    complete["last_record_sha256"] = previous
    for name, value in documents.items():
        if name != "campaign-complete.json":
            write_json(root / name, value)
    for name in complete["artifact_sha256"]:
        complete["artifact_sha256"][name] = V.sha((root / name).read_bytes())
    write_json(root / "campaign-complete.json", complete)


def mutate(name, root, rows, docs):
    row = rows[5]
    if name == "wrong-gate": row["argv"][10] = "999"
    elif name == "wrong-worker": row["environment"]["STREHL_PYRAMID_WORKERS"] = "999"
    elif name == "uncleared-environment": row["environment"]["STREHL_ALIGN"] = "0"
    elif name == "missing-environment-key": del row["environment"]["STREHL_ALIGN"]
    elif name == "missing-campaign-id":
        for r in rows: r.pop("campaign_id")
    elif name == "foreign-campaign-id": docs["campaign-complete.json"]["campaign_id"] = "5fc6cdd7-bff0-42f9-bf5e-b99f5ff063b3"
    elif name == "missing-terminal-key": del docs["campaign-complete.json"]["artifact_sha256"]["commission-logs-manifest.json"]
    elif name == "duplicate-input":
        for key in ("inputs-before.json", "inputs-after.json"): docs[key]["files"][-1] = copy.deepcopy(docs[key]["files"][0])
    elif name == "input-total":
        for key in ("inputs-before.json", "inputs-after.json"): docs[key]["selected_bytes"] += 1
    elif name == "unknown-schema": docs["inputs-before.json"]["schema"] = "m192-unknown-v999"
    elif name == "binary-drift": row["binary"]["bytes"] += 1
    elif name == "worker-cache-alias": row["environment"]["STREHL_CACHE_DIR"] = rows[35]["environment"]["STREHL_CACHE_DIR"]
    elif name == "sidecar-alias": row["environment"]["STREHL_WARPMAP"] = rows[35]["environment"]["STREHL_WARPMAP"]
    elif name == "commission-log-corrupt":
        p = root / docs["commission-logs-manifest.json"]["logs"][0]["path"]
        p.write_bytes(p.read_bytes() + b"\nCORRUPT\n")
    elif name == "commission-log-omitted": docs["commission-logs-manifest.json"]["logs"].pop()
    elif name == "commission-label-lie":
        u = docs["commission.json"]["unrepaired"]
        u["n33_w2"]["output_sha256"] = u["n33_w1"]["output_sha256"]
        u["n33_w2"]["pixel_sha256"] = u["n33_w1"]["pixel_sha256"]
    elif name == "commission-allocation-lie":
        b = docs["commission-logs-manifest.json"]["logs"][9]
        p = root / b["path"]
        p.write_bytes(p.read_bytes().replace(b"allocated=7516192768", b"allocated=67108864"))
        b.update(bytes=p.stat().st_size, sha256=V.sha(p.read_bytes()))
    elif name == "truncated-cpu": docs["sweeps.json"][1]["trace"].pop(100)
    elif name == "duplicate-cpu": docs["sweeps.json"][1]["trace"].insert(100, copy.deepcopy(docs["sweeps.json"][1]["trace"][100]))
    elif name == "cpu-summary-drift": docs["sweeps.json"][1]["whole_host_cpu_trace_mean_percent"] += 1
    elif name == "cpu-run-drift": docs["sweeps.json"][1]["run_ids"][0] = "other"
    elif name == "sampling-summary-lie": docs["certificate.json"]["sampling_quality"]["pass"] = True
    elif name == "extra-artifact": (root / "extra.txt").write_text("unbound data")
    elif name == "path-escape": row["log_artifacts"]["stderr"]["path"] = "../outside.log"
    elif name == "inert-label": row["inert_label"] = "placebo"
    elif name == "valid-product-failure":
        row["memory"]["kernel_job_peak_memory"]["peak_job_memory_used_bytes"] = 7 * 2**30
        row["memory"]["peak_process_tree_private_committed_bytes"] = 7 * 2**30
        original = V.load_legacy()
        calculated = original.recompute_bars(rows, docs["sweeps.json"], original.protocol())
        for field in ("bars", "partition", "sampling_quality", "overall_verdict"):
            docs["certificate.json"][field] = calculated[field]
    else: raise AssertionError(name)


def main():
    before = inventory(ORIGINAL)
    baseline = V.verify_artifact(ORIGINAL)
    assert baseline["overall_verdict"] == "UNMEASURED" and baseline["partition"] == {"pass": 1, "fail": 0, "unmeasured": 3, "total": 4}
    work = HERE / "work"
    work.mkdir(exist_ok=True)
    negatives = {
        "wrong-gate": "record command", "wrong-worker": "worker environment", "uncleared-environment": "uncleared environment",
        "missing-environment-key": "missing environment", "missing-campaign-id": "campaign ID disagreement", "foreign-campaign-id": "campaign ID disagreement",
        "missing-terminal-key": "terminal manifest membership", "duplicate-input": "input file membership", "input-total": "input aggregates",
        "unknown-schema": "artifact schema", "binary-drift": "record binary", "worker-cache-alias": "environment path", "sidecar-alias": "environment path",
        "commission-log-corrupt": "artifact byte count", "commission-log-omitted": "log count", "commission-label-lie": "commission labels",
        "commission-allocation-lie": "allocation log evidence", "truncated-cpu": "CPU trace gap/order", "duplicate-cpu": "CPU trace gap/order",
        "cpu-summary-drift": "CPU trace mean", "cpu-run-drift": "CPU sweep/run binding", "sampling-summary-lie": "certificate sampling quality",
        "extra-artifact": "package file membership", "path-escape": "record log path",
    }
    outputs = []
    for name in [*negatives, "inert-label", "valid-product-failure"]:
        # The resolved temporary target is checked before recursive cleanup.
        directory = (work / ("case-" + uuid4().hex)).resolve()
        directory.mkdir()
        assert directory.is_relative_to(work.resolve())
        try:
            shutil.copytree(ORIGINAL, directory, dirs_exist_ok=True)
            rows = [json.loads(l) for l in (directory / "records.jsonl").read_bytes().splitlines()]
            docs = {p.name: V.load(p) for p in directory.glob("*.json") if p.name != "protocol.json"}
            mutate(name, directory, rows, docs)
            reseal(directory, rows, docs)
            try:
                result = V.verify_artifact(directory)
            except Exception as error:
                assert name in negatives, (name, str(error))
                assert negatives[name] in str(error), (name, "wrong rejection", str(error))
                outputs.append({"name": name, "rejected": True, "reason": str(error)})
            else:
                assert name not in negatives, (name, "accepted corruption")
                expected = "FAIL" if name == "valid-product-failure" else "UNMEASURED"
                assert result["overall_verdict"] == expected
                outputs.append({"name": name, "accepted": True, "overall_verdict": expected})
        finally:
            assert directory.is_relative_to(work.resolve()) and directory != work.resolve()
            shutil.rmtree(directory)
    assert before == inventory(ORIGINAL), "original artifact changed"
    result = {"status": "COMMISSIONED", "public_entry_point": "verify_artifact", "negative_controls": len(negatives),
              "controls": outputs, "original_artifact_files_unchanged": len(before), "baseline_partition": baseline["partition"],
              "source_sha256": {p.name: V.sha(p.read_bytes()) for p in (HERE / "verify.py", Path(__file__))}}
    write_json(HERE / "commission.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__": main()

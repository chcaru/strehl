"""Produce one explicitly named M194d mode on all fixed twenty M194b inputs."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXED = ROOT / "experiments/m194b-known-scene"
SEEDS = [None, 701, 709, 719, 727, 733, 739, 743, 751]
EXPECTED = [(scene, seed) for scene in ("flat", "plane") for seed in SEEDS]
EXPECTED += [("color", None), ("color-null", None)]


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1048576), b""):
            h.update(b)
    return h.hexdigest()


def read(path, expected):
    if sha(path) != expected:
        raise ValueError(f"trusted input changed: {path}")
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, data):
    with Path(path).open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def now():
    return datetime.now(timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("build-record", "producer-result", "producer-commission"):
        parser.add_argument(f"--{name}", type=Path, required=True)
        parser.add_argument(f"--{name}-sha", required=True)
    parser.add_argument("--admission", choices=["hard-floor", "floor-pedestal-v1"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out = args.out.resolve()
    build = read(args.build_record, args.build_record_sha)
    producer = read(args.producer_result, args.producer_result_sha)
    commission = read(args.producer_commission, args.producer_commission_sha)
    if not build["pass"] or producer["status"] != "complete":
        raise ValueError("build or producer incomplete")
    if producer["commission_sha256"] != args.producer_commission_sha:
        raise ValueError("producer commission mismatch")
    if any(v["status"] != "pass" for v in commission["groups"].values()):
        raise ValueError("full first-scope matrix has an uncommissioned producer part")
    manifests = {}
    for ref in producer["manifests"]:
        path = (args.producer_result.resolve().parent / ref["path"]).resolve()
        data = read(path, ref["sha256"])
        key = (data["scene"], data["repeat"])
        if key in manifests:
            raise ValueError("duplicate producer case")
        manifests[key] = (path, ref["sha256"], data)
    if set(manifests) != set(EXPECTED) or len(manifests) != 20:
        raise ValueError("producer matrix differs from fixed twenty input cases")
    source_map = dict(build["sources_after"])
    source_map.update(producer["sources_after"])
    for name in ("run-baseline.py", "consumer-run.py", "commission-forward.py", "score.py", "score-benchmark.py",
                 "preregister.md", "scorer-preregister.md", "producer-preregister.json"):
        p = FIXED / name
        source_map[p.relative_to(ROOT).as_posix()] = sha(p)
    for name in ("consumer-run.py", "run-matrix.py", "score-benchmark.py",
                 "run-experiment.py", "compare-experiment.py", "sparse-error.py"):
        p = HERE / name
        source_map[p.relative_to(ROOT).as_posix()] = sha(p)
    for name in ("comparison-preregister.md", "implementation-preregister.md", "adapter-lineage.json"):
        p = HERE / name
        source_map[p.relative_to(ROOT).as_posix()] = sha(p)
    if any(sha(ROOT / p) != h for p, h in source_map.items()):
        raise ValueError("compiled/generator/controller source changed before run")
    args.out.mkdir(parents=True, exist_ok=False)
    for name in ("plans", "receipts", "tiffs", "logs", "sources"):
        (args.out / name).mkdir()
    snapshots = []
    for relative, digest in sorted(source_map.items()):
        destination = args.out / "sources" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
        if sha(destination) != digest:
            raise ValueError("source changed while snapshotting")
        snapshots.append({"original_path": relative,
                          "path": destination.relative_to(args.out).as_posix(), "sha256": digest})
    index_path = args.out / "run-index.json"
    index = {"schema": "m194d-benchmark-run-v1", "admission": args.admission, "status": "planning",
             "started_utc": now(), "command": sys.argv, "sources_before": source_map,
             "source_snapshots": snapshots, "cases": [], "commands": [],
             "build_record": {"path": str(args.build_record.resolve()), "sha256": args.build_record_sha},
             "producer_result": {"path": str(args.producer_result.resolve()), "sha256": args.producer_result_sha},
             "producer_commission": {"path": str(args.producer_commission.resolve()), "sha256": args.producer_commission_sha}}
    write(index_path, index)
    driver = [sys.executable, "-X", "utf8", str(HERE / "consumer-run.py")]
    bindings = ["--admission", args.admission, "--build-record", str(args.build_record.resolve()),
                "--build-sha256", args.build_record_sha]
    def check_sources():
        if any(sha(ROOT / path) != digest for path, digest in source_map.items()):
            raise ValueError("frozen compiled/producer/adapter source changed")

    def invoke(command, label):
        check_sources()
        log = args.out / "logs" / f"{label}.controller.log"
        with log.open("xb") as f:
            p = subprocess.run(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        entry = {"command": command, "exit_code": p.returncode,
                                  "log": log.relative_to(args.out).as_posix(),
                                  "log_sha256": sha(log), "completed_utc": now()}
        evidence_path = Path(command[command.index("--log") + 1]).with_suffix(".json")
        if evidence_path.exists():
            entry["consumer_evidence"] = {"path": evidence_path.relative_to(args.out).as_posix(),
                                          "sha256": sha(evidence_path)}
        index["commands"].append(entry)
        write(index_path, index)
        check_sources()
        if p.returncode:
            raise RuntimeError(f"{label} failed: exit {p.returncode}; preserved {log}")
    try:
        # All domains and their hashes are fixed before the first production TIFF.
        for scene, repeat in EXPECTED:
            path, digest, data = manifests[(scene, repeat)]
            label = f"{scene}-" + ("noise-off" if repeat is None else f"seed-{repeat}")
            plan_path = args.out / "plans" / f"{label}.json"
            invoke(driver + ["plan"] + bindings + ["--manifest", str(path),
                "--manifest-sha256", digest, "--plan", str(plan_path),
                "--log", str(args.out / "logs" / f"{label}-plan.command.log")], f"{label}-plan")
            case = {"label": label, "scene": scene, "repeat": repeat,
                    "noise_enabled": data["noise_enabled"], "manifest_path": str(path),
                    "manifest_sha256": digest, "plan_path": plan_path.relative_to(args.out).as_posix(),
                    "plan_sha256": sha(plan_path), "arms": []}
            index["cases"].append(case)
            write(index_path, index)
        index["all_plans_frozen_utc"] = now()
        index["status"] = "rendering"
        write(index_path, index)
        print("All 20 plans frozen before production TIFFs", flush=True)
        for case in index["cases"]:
            for arm, subset in (("full9", "all"), ("single4", "best")):
                label = f"{case['label']}-{arm}"
                receipt = args.out / "receipts" / f"{label}.json"
                output = args.out / "tiffs" / f"{label}.tif"
                invoke(driver + ["render"] + bindings + ["--manifest", case["manifest_path"],
                    "--manifest-sha256", case["manifest_sha256"], "--plan", str(args.out / case["plan_path"]),
                    "--plan-sha256", case["plan_sha256"], "--subset", subset,
                    "--output", str(output), "--receipt", str(receipt),
                    "--log", str(args.out / "logs" / f"{label}.command.log")], label)
                case["arms"].append({"name": arm, "receipt_path": receipt.relative_to(args.out).as_posix(),
                                     "receipt_sha256": sha(receipt)})
                write(index_path, index)
            print(f"Rendered {case['label']}: full9 and single4", flush=True)
        index["sources_after"] = {p: sha(ROOT / p) for p in source_map}
        if index["sources_after"] != index["sources_before"]:
            raise ValueError("source changed during production baseline")
        if sha(Path(build["test_executable"]["path"])) != build["test_executable"]["sha256"]:
            raise ValueError("pinned binary changed during production baseline")
        index["status"] = "complete"
        index["completed_utc"] = now()
        write(index_path, index)
        print(json.dumps({"status": "complete", "outputs": 40,
                          "index": str(index_path), "index_sha256": sha(index_path)}), flush=True)
    except Exception as exc:
        index["status"] = "failed"
        index["failure"] = f"{type(exc).__name__}: {exc}"
        index["completed_utc"] = now()
        write(index_path, index)
        raise


if __name__ == "__main__":
    main()

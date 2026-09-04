#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import multiprocessing
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Any


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def encode(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def write(path: Path, value: Any) -> None:
    path.write_bytes(encode(value))


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def load_module(source: Path):
    spec = importlib.util.spec_from_file_location("m138_adjudicate_race", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load adjudicator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def replace_from(path: Path, source: Path, serial: int) -> None:
    temporary = path.with_name(f".{path.name}.race-{os.getpid()}-{serial}")
    try:
        os.link(source, temporary)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def toggle(path: Path, first: Path, second: Path, stop: threading.Event) -> None:
    serial = 0
    while not stop.is_set():
        for source in (first, second):
            if stop.is_set():
                return
            try:
                replace_from(path, source, serial)
                serial += 1
            except PermissionError:
                time.sleep(0.001)
            time.sleep(0)


def summary(verdict: dict[str, Any]) -> dict[str, Any]:
    result = {"verdict": verdict.get("verdict")}
    if "reason" in verdict:
        result["reason"] = verdict["reason"]
    if (
        isinstance(verdict.get("achieved_effect"), dict)
        and "holdout" in verdict["achieved_effect"]
    ):
        result["holdout_max_upper"] = verdict["achieved_effect"]["holdout"][
            "maximum_simultaneous_one_sided_upper"
        ]
        result["holdout_r"] = verdict["achieved_effect"]["holdout"][
            "by_capture_and_plane"
        ]["noise-holdout"]["R"]["estimated_power_ratio"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("fixture", type=Path)
    parser.add_argument("scratch", type=Path)
    parser.add_argument("--attempts", type=int, default=32)
    parser.add_argument("--padding-bytes", type=int, default=1048576)
    args = parser.parse_args()
    source = args.source.resolve()
    fixture = args.fixture.resolve()
    root = args.scratch.resolve()
    if root.exists():
        shutil.rmtree(root)
    shutil.copytree(fixture, root)
    module = load_module(source)

    contract = load(root / "contract.json")
    registered_request = module.make_noise_evidence(
        contract,
        contract["capture_ledgers"]["holdout"]["noise"],
        root,
        "race-output-fail-holdout",
        1.50,
    )
    replacement_request = load(root / "noise-pass-holdout.json")
    registered_ref = registered_request["captures"]["noise-holdout"][
        "candidate_outputs"
    ][1]
    replacement_ref = replacement_request["captures"]["noise-holdout"][
        "candidate_outputs"
    ][1]
    target = root / registered_ref["path"]
    registered_bytes = target.read_bytes()
    replacement_bytes = (root / replacement_ref["path"]).read_bytes()
    registered_file = root / "registered-noise-output.bin"
    replacement_file = root / "replacement-noise-output.bin"
    registered_file.write_bytes(registered_bytes)
    replacement_file.write_bytes(replacement_bytes)
    write(root / "noise-race-request.json", registered_request)

    holdout = load(root / "holdout.json")
    holdout["arm"]["noise_evidence"] = {
        "path": "noise-race-request.json",
        "sha256": sha(root / "noise-race-request.json"),
    }
    write(root / "holdout-race.json", holdout)
    result = load(root / "result.json")
    result["holdout"] = {
        "path": "holdout-race.json",
        "sha256": sha(root / "holdout-race.json"),
    }
    write(root / "result-race.json", result)

    def invoke() -> dict[str, Any]:
        return module.adjudicate_result(
            root / "result-race.json",
            root / "contract.json",
            verify_sources=False,
            test_mode=True,
        )

    stable_registered = invoke()
    target.write_bytes(replacement_bytes)
    stable_replaced = invoke()
    target.write_bytes(registered_bytes)

    original_sha256 = module.sha256
    hash_complete = threading.Event()
    replacement_complete = threading.Event()
    barrier_used = False

    def barrier_sha256(path: Path) -> str:
        nonlocal barrier_used
        digest = original_sha256(path)
        if (
            not barrier_used
            and Path(path).resolve() == target.resolve()
            and digest == sha_bytes(registered_bytes)
        ):
            barrier_used = True
            hash_complete.set()
            if not replacement_complete.wait(timeout=10):
                raise RuntimeError("replacement did not complete")
        return digest

    def replace_after_hash() -> None:
        if not hash_complete.wait(timeout=30):
            return
        replace_from(target, replacement_file, 999999)
        replacement_complete.set()

    barrier_worker = threading.Thread(target=replace_after_hash, daemon=True)
    module.sha256 = barrier_sha256
    barrier_worker.start()
    try:
        deterministic_race = invoke()
    finally:
        module.sha256 = original_sha256
        barrier_worker.join(timeout=5)
        target.write_bytes(registered_bytes)

    stop = multiprocessing.Event()
    worker = multiprocessing.Process(
        target=toggle,
        args=(target, registered_file, replacement_file, stop),
        daemon=True,
    )
    counts: dict[str, int] = {}
    unsafe: list[dict[str, Any]] = []
    worker.start()
    try:
        for attempt in range(1, args.attempts + 1):
            verdict = invoke()
            name = str(verdict.get("verdict"))
            counts[name] = counts.get(name, 0) + 1
            if name == "PHASE1_GO":
                unsafe.append({"attempt": attempt, "output": summary(verdict)})
                break
    finally:
        stop.set()
        worker.join(timeout=5)
        target.write_bytes(registered_bytes)

    output = {
        "registered_sha256": sha_bytes(registered_bytes),
        "replacement_sha256": sha_bytes(replacement_bytes),
        "stable_registered": summary(stable_registered),
        "stable_replacement": summary(stable_replaced),
        "deterministic_interleaving": summary(deterministic_race),
        "barrier_used": barrier_used,
        "replacement_completed": replacement_complete.is_set(),
        "race_attempts_requested": args.attempts,
        "race_counts": counts,
        "unsafe": unsafe,
    }
    print(json.dumps(output, sort_keys=True))
    return 1 if unsafe or deterministic_race.get("verdict") == "PHASE1_GO" else 0


if __name__ == "__main__":
    raise SystemExit(main())

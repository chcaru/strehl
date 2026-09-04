from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE / "fixtures" / "vulnerable-bound-runtime"
EXPECTED_VULNERABLE_ADAPTER_SHA256 = (
    "6d4366533b2b12fc1e03c44d96faa1af3d7e89e6c6f35ed5420dd33b8e5e6290"
)
EXPECTED_VULNERABLE_CORE_SHA256 = (
    "a8f92dbfc436e7a0ffab0fd0cc8bbc9d6708cc829f0435a5bdda510e2a30af5b"
)
ORIGINAL_CAPTURE_IDS = [
    "pass",
    "fail",
    "invalid",
    "flat-roi",
    "null-state",
    "missing-state",
    "invalid-plus-bool",
    "bool-only",
    "pass-false",
    "fail-true",
    "null",
    "blur",
    "improvement",
    "missing-flat",
]


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_core(path: Path) -> Any:
    module = types.ModuleType("m149_review_core")
    module.__file__ = str(path)
    module.__package__ = ""
    code = compile(path.read_bytes(), str(path), "exec", dont_inherit=True)
    exec(code, module.__dict__)
    return module


def rebuild_bundle(runtime: Path) -> Path:
    path = runtime / "m138-checker-bundle.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for row in manifest["files"]:
        row["sha256"] = sha256_file(runtime / row["path"])
    write_json(path, manifest)
    return path


def copy_registered_runtime(source: Path, runtime: Path) -> None:
    source = source.resolve()
    if runtime.exists():
        shutil.rmtree(runtime)
    runtime.mkdir(parents=True)
    manifest_path = source / "m138-checker-bundle.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for row in manifest["files"]:
        src = source / row["path"]
        dst = runtime / row["path"]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    shutil.copy2(manifest_path, runtime / manifest_path.name)


def add_capture(
    binding: dict[str, Any],
    contract: dict[str, Any],
    capture_id: str,
) -> None:
    binding["applicable_captures"][capture_id] = {
        "site_count": 64,
        **{
            field: hashlib.sha256(
                f"{capture_id}:{field}".encode("utf-8")
            ).hexdigest()
            for field in contract["required_capture_hashes"]
        },
    }


def prepare_bound_runtime(source: Path, runtime: Path) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    copy_registered_runtime(source, runtime)
    core = load_core(runtime / "comparison_checker.py")
    contract = json.loads(
        (runtime / "comparison-contract.json").read_text(encoding="utf-8")
    )
    binding = core.synthetic_binding(contract)
    for capture_id in ORIGINAL_CAPTURE_IDS:
        add_capture(binding, contract, capture_id)
    write_json(runtime / "comparison-binding.json", binding)
    rebuild_bundle(runtime)
    return core, contract, binding


def payload_for(
    core: Any,
    contract: dict[str, Any],
    binding: dict[str, Any],
    capture_id: str,
    *,
    information: float = 1.0,
    transfer: float = 1.0,
    unexplained: float = 0.0,
) -> dict[str, Any]:
    value = core.synthetic_payload(
        contract,
        binding,
        information=information,
        transfer=transfer,
        unexplained=unexplained,
    )
    value["capture_id"] = capture_id
    capture_binding = binding["applicable_captures"][capture_id]
    for field in contract["required_capture_hashes"]:
        value["lineage"][field] = capture_binding[field]
    return value


def invalid_and_fail_payloads(
    core: Any,
    contract: dict[str, Any],
    binding: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    invalid = payload_for(core, contract, binding, "invalid")
    del invalid["modes"]["candidate"]["flat_control"]
    passing = payload_for(core, contract, binding, "pass")
    fail = copy.deepcopy(invalid)
    fail["modes"]["candidate"]["flat_control"] = copy.deepcopy(
        passing["modes"]["candidate"]["flat_control"]
    )
    fail["modes"]["candidate"]["information_bits_per_site"] = 1.05
    fail["bootstrap"]["information_ratio"] = [
        0.70
    ] * fail["bootstrap"]["replicates"]
    return invalid, fail


def binding_hashes(runtime: Path, binding: dict[str, Any]) -> dict[str, str]:
    return {
        "checker_bundle_manifest_sha256": sha256_file(
            runtime / "m138-checker-bundle.json"
        ),
        "environment_manifest_sha256": sha256_file(
            runtime / "m138-adapter-environment.json"
        ),
        "physical_preregistration_sha256": binding[
            "physical_preregistration_sha256"
        ],
        "comparison_rule_sha256": sha256_file(
            runtime / "comparison-contract.json"
        ),
    }


def invoke_adapter(
    runtime: Path,
    mode: str,
    request_path: Path,
    *,
    timeout: int = 120,
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [
            sys.executable,
            "-I",
            str(runtime / "m138_adapter.py"),
            f"--m138-{mode}",
            str(request_path),
        ],
        cwd=runtime,
        capture_output=True,
        check=False,
        timeout=timeout,
    )


def completed_record(completed: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8"),
        "stderr": completed.stderr.decode("utf-8"),
    }

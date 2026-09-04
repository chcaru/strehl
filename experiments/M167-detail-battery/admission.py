"""Commission M167's arm-blinded admission rule with a cheating canary.

The canary is executed only after a committed freeze manifest exists.  Each
blinded observation is sent through a fresh child process with no arm label.
Candidate outputs are sealed and hashed before this process maps opaque tokens
back to the original P1--P6 semantics.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import io
import json
import os
import platform
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import scipy
from scipy.ndimage import gaussian_filter

from commission import adjudicate


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PREREG_PATH = HERE / "ADMISSION-PREREGISTRATION.md"
RUNNER_PATH = HERE / "admission.py"
WORKER_PATH = HERE / "admission_worker.py"
CANDIDATE_PATH = HERE / "cheating_canary.py"
COMMISSION_PATH = HERE / "commission.py"
FREEZE_PATH = HERE / "admission-freeze.json"
SEALED_PATH = HERE / "admission-sealed.json"
RESULT_PATH = HERE / "admission-results.json"

SIDE = 256
OVERSAMPLE = 4
NOISE_SD = 0.003
FPN_SD = 0.04
BASE_SIGMA = 1.0
IMPROVED_SIGMA = 0.55
DEGRADED_SIGMA = 1.65
BLUR_SIGMAS = (0.0, 0.5, 1.0, 1.5)
USM_SIGMA = 1.0
USM_AMOUNT = 0.75
INSTANCE_COUNT = 3
DUPLICATE_SEMANTICS = ("flat_detail", "base", "improved")
ARM_TERMS = (
    "flat_detail",
    "wrong_shape",
    "nonfinite",
    "improved",
    "degraded",
    "blur_0p5",
    "blur_1p5",
    "blur_0",
    "blur_1",
    "base",
    "flat",
    "usm",
)
DANGEROUS_NAMES = {
    "__builtins__",
    "__cached__",
    "__file__",
    "__import__",
    "__loader__",
    "__name__",
    "__package__",
    "__spec__",
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "getattr",
    "globals",
    "locals",
    "open",
    "setattr",
    "vars",
}
DANGEROUS_ATTRIBUTES = {
    "DataSource",
    "Path",
    "Popen",
    "call",
    "chdir",
    "check_call",
    "check_output",
    "ctypeslib",
    "datetime64",
    "default_rng",
    "distutils",
    "dump",
    "dumps",
    "environ",
    "fork",
    "forkpty",
    "fromfile",
    "fromregex",
    "f2py",
    "genfromtxt",
    "getcwd",
    "getenv",
    "getpid",
    "getppid",
    "kill",
    "listdir",
    "load",
    "load_library",
    "loadtxt",
    "lstat",
    "makedirs",
    "memmap",
    "monotonic",
    "NpzFile",
    "open",
    "open_memmap",
    "os",
    "pathlib",
    "perf_counter",
    "popen",
    "process_time",
    "putenv",
    "random",
    "RandomState",
    "readlink",
    "recfromcsv",
    "recfromtxt",
    "remove",
    "rename",
    "replace",
    "request",
    "rmdir",
    "run",
    "save",
    "savetxt",
    "savez",
    "savez_compressed",
    "scandir",
    "sleep",
    "socket",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
    "stat",
    "subprocess",
    "symlink",
    "sys",
    "time",
    "tofile",
    "unlink",
    "urlopen",
    "walk",
}


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git_bytes(*arguments: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def verify_freeze() -> dict[str, object]:
    manifest = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    files = manifest.get("files")
    if not isinstance(files, dict):
        raise RuntimeError("freeze manifest has no file map")
    required_files = {
        PREREG_PATH.name,
        RUNNER_PATH.name,
        WORKER_PATH.name,
        CANDIDATE_PATH.name,
        COMMISSION_PATH.name,
    }
    artifact_commit = str(manifest.get("artifact_commit", ""))
    preregistration_commit = str(
        manifest.get("preregistration_commit", "")
    )
    expected_worktree_hashes = {
        name: record.get("worktree_sha256")
        if isinstance(record, dict)
        else None
        for name, record in files.items()
    }
    expected_commit_hashes = {
        name: record.get("commit_sha256")
        if isinstance(record, dict)
        else None
        for name, record in files.items()
    }
    actual = {
        name: sha256_file(HERE / name)
        for name in files
    }
    hash_match = actual == expected_worktree_hashes
    paths = [str((HERE / name).relative_to(ROOT)) for name in files]
    committed_hashes = {}
    committed_reads_ok = True
    for name, relative_path in zip(files, paths):
        process = git_bytes(
            "show", f"{artifact_commit}:{relative_path.replace(os.sep, '/')}"
        )
        if process.returncode != 0:
            committed_reads_ok = False
            committed_hashes[name] = None
        else:
            committed_hashes[name] = sha256_bytes(process.stdout)
    artifact_paths_unstaged = git(
        "diff", "--quiet", "HEAD", "--", *paths
    )
    artifact_paths_staged = git(
        "diff", "--cached", "--quiet", "HEAD", "--", *paths
    )
    manifest_relative = str(FREEZE_PATH.relative_to(ROOT))
    manifest_unstaged = git(
        "diff", "--quiet", "HEAD", "--", manifest_relative
    )
    manifest_staged = git(
        "diff", "--cached", "--quiet", "HEAD", "--", manifest_relative
    )
    ancestor = git(
        "merge-base",
        "--is-ancestor",
        artifact_commit,
        "HEAD",
    )
    preregistration_ancestor = git(
        "merge-base",
        "--is-ancestor",
        preregistration_commit,
        artifact_commit,
    )
    committed_drift = git(
        "diff",
        "--quiet",
        artifact_commit,
        "HEAD",
        "--",
        *paths,
    )
    latest_change = git(
        "log",
        "-1",
        "--format=%H",
        "HEAD",
        "--",
        *paths,
    )
    checks = {
        "manifest_schema": manifest.get("schema") == 2,
        "manifest_file_set_exact": set(files) == required_files,
        "preregistration_commit_pinned": (
            manifest.get("preregistration_commit")
            == "20ef67e822c4bd08dd5792989694c8982b9e0308"
        ),
        "preregistration_precedes_artifacts": (
            preregistration_ancestor.returncode == 0
        ),
        "artifact_hashes_match": hash_match,
        "artifact_commit_objects_readable": committed_reads_ok,
        "manifest_hashes_match_artifact_commit": (
            committed_hashes == expected_commit_hashes
        ),
        "no_committed_artifact_drift": committed_drift.returncode == 0,
        "artifact_commit_is_last_pinned_change": (
            latest_change.returncode == 0
            and latest_change.stdout.strip() == artifact_commit
        ),
        "artifact_paths_unstaged_clean": (
            artifact_paths_unstaged.returncode == 0
        ),
        "artifact_paths_staged_clean": (
            artifact_paths_staged.returncode == 0
        ),
        "freeze_manifest_unstaged_clean": (
            manifest_unstaged.returncode == 0
        ),
        "freeze_manifest_staged_clean": manifest_staged.returncode == 0,
        "artifact_commit_is_ancestor": ancestor.returncode == 0,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "manifest": manifest,
        "actual_hashes": actual,
        "artifact_commit_hashes": committed_hashes,
    }


def audit_candidate_source() -> dict[str, object]:
    source = CANDIDATE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    mutable_module_declarations = []

    def statically_immutable(node: ast.AST | None) -> bool:
        if node is None:
            return True
        if isinstance(node, ast.Constant):
            return True
        if isinstance(node, ast.Tuple):
            return all(statically_immutable(item) for item in node.elts)
        if isinstance(node, ast.UnaryOp):
            return statically_immutable(node.operand)
        if isinstance(node, ast.BinOp):
            return statically_immutable(
                node.left
            ) and statically_immutable(node.right)
        return False

    for statement in tree.body:
        if isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = (
                statement.targets
                if isinstance(statement, ast.Assign)
                else [statement.target]
            )
            value = statement.value
            for target in targets:
                if isinstance(target, ast.Name):
                    if not statically_immutable(value):
                        mutable_module_declarations.append(target.id)
                else:
                    mutable_module_declarations.append(ast.unparse(target))
        elif isinstance(statement, ast.AugAssign):
            mutable_module_declarations.append(
                ast.unparse(statement.target)
            )
        elif isinstance(statement, ast.ClassDef):
            mutable_module_declarations.append(
                f"class:{statement.name}"
            )

    def root_name(node: ast.AST) -> str | None:
        while isinstance(node, (ast.Attribute, ast.Subscript)):
            node = node.value
        return node.id if isinstance(node, ast.Name) else None

    imports = []
    strings = []
    called_names = []
    sensitive_name_uses = []
    dangerous_attributes = []
    dangerous_imports = []
    mutable_state_hits = []
    score_signature = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append((node.module or "").split(".", 1)[0])
            dangerous_imports.extend(
                alias.name
                for alias in node.names
                if (
                    alias.name == "*"
                    or alias.name.startswith("__")
                    or alias.name in DANGEROUS_ATTRIBUTES
                )
            )
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            lowered = node.value.lower()
            strings.extend(term for term in ARM_TERMS if term in lowered)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            called_names.append(node.func.id)
        elif isinstance(node, ast.Name) and node.id in DANGEROUS_NAMES:
            sensitive_name_uses.append(node.id)
        elif isinstance(node, ast.Attribute) and (
            node.attr in DANGEROUS_ATTRIBUTES
            or node.attr.startswith("__")
        ):
            dangerous_attributes.append(node.attr)
        elif isinstance(node, ast.Global):
            mutable_state_hits.extend(node.names)
        elif isinstance(node, ast.Nonlocal):
            mutable_state_hits.extend(node.names)
        elif isinstance(node, ast.AugAssign):
            target_root = root_name(node.target)
            mutable_state_hits.append(
                target_root or ast.unparse(node.target)
            )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
            )
            for target in targets:
                target_root = root_name(target)
                if not isinstance(target, ast.Name):
                    mutable_state_hits.append(
                        target_root or ast.unparse(target)
                    )
        elif (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr
            in {
                "__setitem__",
                "add",
                "append",
                "clear",
                "discard",
                "extend",
                "insert",
                "pop",
                "remove",
                "reverse",
                "setdefault",
                "sort",
                "update",
            }
        ):
            target_root = root_name(node.func.value)
            mutable_state_hits.append(
                target_root or ast.unparse(node.func.value)
            )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == "score":
                score_signature = {
                    "positional_only": [
                        arg.arg for arg in node.args.posonlyargs
                    ],
                    "positional": [arg.arg for arg in node.args.args],
                    "defaults": len(node.args.defaults),
                    "keyword_only": [
                        arg.arg for arg in node.args.kwonlyargs
                    ],
                    "keyword_defaults": sum(
                        value is not None
                        for value in node.args.kw_defaults
                    ),
                    "vararg": (
                        node.args.vararg.arg if node.args.vararg else None
                    ),
                    "kwarg": (
                        node.args.kwarg.arg if node.args.kwarg else None
                    ),
                }

    allowed_imports = {"__future__", "math", "numpy"}
    import_violations = sorted(
        {name for name in imports if name not in allowed_imports}
    )
    dangerous_calls = sorted(set(called_names) & DANGEROUS_NAMES)
    exact_signature = score_signature == {
        "positional_only": [],
        "positional": ["image"],
        "defaults": 0,
        "keyword_only": [],
        "keyword_defaults": 0,
        "vararg": None,
        "kwarg": None,
    }
    checks = {
        "only_declared_imports": not import_violations,
        "score_accepts_only_observation": exact_signature,
        "no_arm_vocabulary": not strings,
        "no_dynamic_or_reflective_calls": (
            not dangerous_calls
            and not sensitive_name_uses
            and not dangerous_attributes
            and not dangerous_imports
        ),
        "no_mutable_global_state": (
            not mutable_state_hits and not mutable_module_declarations
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "imports": sorted(set(imports)),
        "import_violations": import_violations,
        "score_signature": score_signature,
        "arm_vocabulary_hits": sorted(set(strings)),
        "dangerous_calls": dangerous_calls,
        "sensitive_name_uses": sorted(set(sensitive_name_uses)),
        "dangerous_attributes": sorted(set(dangerous_attributes)),
        "dangerous_imports": sorted(set(dangerous_imports)),
        "mutable_state_hits": sorted(set(mutable_state_hits)),
        "mutable_module_declarations": sorted(
            set(mutable_module_declarations)
        ),
    }


def derive_seed(nonce: bytes, instance: int, domain: str) -> int:
    digest = hashlib.sha256()
    digest.update(b"M167-ADMISSION-V1\0")
    digest.update(nonce)
    digest.update(instance.to_bytes(4, "big"))
    digest.update(domain.encode("ascii"))
    return int.from_bytes(digest.digest()[:8], "big")


def normalise(array: np.ndarray) -> np.ndarray:
    value = np.asarray(array, dtype=np.float64)
    return (value - float(np.mean(value))) / float(np.std(value))


def render(latent: np.ndarray, sigma_output_px: float) -> np.ndarray:
    blurred = gaussian_filter(
        latent,
        sigma_output_px * OVERSAMPLE,
        mode="reflect",
        truncate=6.0,
    )
    return blurred.reshape(
        SIDE, OVERSAMPLE, SIDE, OVERSAMPLE
    ).mean(axis=(1, 3))


def packet_bytes(image: np.ndarray) -> bytes:
    stream = io.BytesIO()
    np.save(stream, np.asarray(image, dtype=np.float64), allow_pickle=False)
    return stream.getvalue()


def build_instance(nonce: bytes, instance: int) -> dict[str, object]:
    high_side = SIDE * OVERSAMPLE
    latent = np.random.default_rng(
        derive_seed(nonce, instance, "latent")
    ).standard_normal((high_side, high_side))
    latent = gaussian_filter(
        latent, 1.0, mode="reflect", truncate=6.0
    )
    latent = 0.5 + 0.12 * normalise(latent)

    noise_a = NOISE_SD * np.random.default_rng(
        derive_seed(nonce, instance, "noise-a")
    ).standard_normal((SIDE, SIDE))
    fixed_pattern = FPN_SD * normalise(
        np.random.default_rng(
            derive_seed(nonce, instance, "fixed-pattern")
        ).standard_normal((SIDE, SIDE))
    )

    base = render(latent, BASE_SIGMA) + noise_a
    improved = render(latent, IMPROVED_SIGMA) + noise_a
    degraded = render(latent, DEGRADED_SIGMA) + noise_a
    flat_detail = render(latent, BASE_SIGMA) + fixed_pattern + noise_a
    flat = (
        np.full((SIDE, SIDE), 0.5, dtype=np.float64)
        + fixed_pattern
        + noise_a
    )

    arrays = {
        "flat_detail": flat_detail,
        "flat": flat,
        "base": base,
        "improved": improved,
        "degraded": degraded,
        "blur_0": base.copy(),
        "blur_0p5": gaussian_filter(
            base, 0.5, mode="reflect", truncate=6.0
        ),
        "blur_1": gaussian_filter(
            base, 1.0, mode="reflect", truncate=6.0
        ),
        "blur_1p5": gaussian_filter(
            base, 1.5, mode="reflect", truncate=6.0
        ),
    }
    low = gaussian_filter(
        base, USM_SIGMA, mode="reflect", truncate=6.0
    )
    arrays["usm"] = base + USM_AMOUNT * (base - low)
    nonfinite = base.copy()
    nonfinite[0, 0] = np.nan
    arrays["nonfinite"] = nonfinite
    arrays["wrong_shape"] = base[0].copy()

    roster = [
        {"semantic": semantic, "duplicate_of": None, "image": image}
        for semantic, image in arrays.items()
    ]
    roster.extend(
        {
            "semantic": f"{semantic}__duplicate",
            "duplicate_of": semantic,
            "image": arrays[semantic].copy(),
        }
        for semantic in DUPLICATE_SEMANTICS
    )
    order = np.random.default_rng(
        derive_seed(nonce, instance, "permutation")
    ).permutation(len(roster))
    ordered = [roster[int(index)] for index in order]
    for ordinal, item in enumerate(ordered):
        digest = hashlib.sha256()
        digest.update(b"M167-OPAQUE-TOKEN-V1\0")
        digest.update(nonce)
        digest.update(instance.to_bytes(4, "big"))
        digest.update(str(item["semantic"]).encode("ascii"))
        digest.update(ordinal.to_bytes(4, "big"))
        item["token"] = digest.hexdigest()[:32].upper()
        encoded = packet_bytes(item["image"])
        item["packet_bytes"] = encoded
        item["packet_sha256"] = sha256_bytes(encoded)

    commitment = hashlib.sha256(
        b"M167-INSTANCE-COMMITMENT-V1\0"
        + nonce
        + instance.to_bytes(4, "big")
    ).hexdigest().upper()
    return {
        "index": instance,
        "commitment": commitment,
        "packets": ordered,
    }


def load_canary():
    spec = importlib.util.spec_from_file_location(
        "m167_cheating_canary_legacy", CANDIDATE_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load cheating canary")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def result_from_records(
    records: dict[str, dict[str, object]],
    name: str,
) -> dict[str, object]:
    return {
        "schema": 1,
        "candidate": {
            "name": name,
            "kind": "INELIGIBLE_CHEATING_CANARY",
            "input_mode": "single_image",
            "score_orientation": "higher_is_more_resolved",
        },
        "arms": {
            "flat_roi": {
                "detail": records["flat_detail"],
                "flat": records["flat"],
            },
            "planted_improvement": {
                "base": records["base"],
                "improved": records["improved"],
            },
            "planted_degradation": {
                "base": records["base"],
                "degraded": records["degraded"],
            },
            "blur_monotonicity": [
                {
                    "added_sigma_px": sigma,
                    "measurement": records[semantic],
                }
                for sigma, semantic in zip(
                    BLUR_SIGMAS,
                    ("blur_0", "blur_0p5", "blur_1", "blur_1p5"),
                )
            ],
            "sharpening_discrimination": {
                "base": records["base"],
                "usm": records["usm"],
                "improved": records["improved"],
            },
            "fail_closed": {
                "nonfinite": records["nonfinite"],
                "wrong_shape": records["wrong_shape"],
            },
        },
    }


def legacy_labeled_result(instance: dict[str, object]) -> dict[str, object]:
    canary = load_canary()
    images = {
        str(item["semantic"]): item["image"]
        for item in instance["packets"]
        if item["duplicate_of"] is None
    }
    records = {
        semantic: canary.score(image, semantic)
        for semantic, image in images.items()
    }
    return result_from_records(records, "cheating-canary-legacy-labeled")


def normalized_child_environment() -> dict[str, str]:
    result = {
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "BLIS_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
    }
    for name in ("SYSTEMROOT", "WINDIR"):
        if name in os.environ:
            result[name] = os.environ[name]
    return result


def run_packet(encoded: bytes, root: Path) -> dict[str, object]:
    environment = normalized_child_environment()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    try:
        worker = root / "worker.py"
        candidate = root / "candidate.py"
        shutil.copy2(WORKER_PATH, worker)
        shutil.copy2(CANDIDATE_PATH, candidate)
        command = [
            sys.executable,
            "-I",
            "-B",
            str(worker),
            str(candidate),
        ]
        visible_blob = "\n".join(
            [
                *command,
                *(f"{key}={value}" for key, value in sorted(environment.items())),
                str(root),
            ]
        ).lower().replace("-", "_").replace(".", "p")
        leaked_terms = sorted(
            {term for term in ARM_TERMS if term in visible_blob}
        )
        process = subprocess.run(
            command,
            cwd=root,
            env=environment,
            input=encoded,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        parse_status = "NOT_PARSED"
        if process.returncode == 0:
            try:
                record = json.loads(process.stdout.decode("utf-8"))
                if not isinstance(record, dict):
                    raise TypeError("candidate result is not an object")
                parse_status = "OK"
            except Exception as error:
                record = {
                    "status": "ERROR",
                    "code": "INVALID_RESULT_JSON",
                    "reason": f"{type(error).__name__}: {error}",
                }
                parse_status = "INVALID_JSON"
        else:
            record = {
                "status": "ERROR",
                "code": "CANDIDATE_PROCESS_ERROR",
                "reason": process.stderr.decode("utf-8", errors="replace"),
            }
            parse_status = "PROCESS_ERROR"
        return {
            "record": record,
            "returncode": process.returncode,
            "parse_status": parse_status,
            "stderr": process.stderr.decode("utf-8", errors="replace"),
            "channel_audit": {
                "constant_argv_shape": [
                    "PYTHON",
                    "-I",
                    "-B",
                    "worker.py",
                    "candidate.py",
                ],
                "environment": environment,
                "cwd_shape": "fresh-opaque-temp/one-packet",
                "private_term_leaks": leaked_terms,
                "token_supplied": False,
                "packet_index_supplied": False,
            },
        }
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_blinded(
    instances: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, object]]:
    sealed_instances = []
    channel_audits = []
    run_number = int(str(instances[0]["commitment"])[:16], 16)
    packet_root = (
        Path(tempfile.gettempdir())
        / f"m167_blind_worker_{run_number}"
    )
    for instance in instances:
        packets = []
        for item in instance["packets"]:
            child = run_packet(item["packet_bytes"], packet_root)
            item["child"] = child
            channel_audits.append(child["channel_audit"])
            packets.append(
                {
                    "token": item["token"],
                    "packet_sha256": item["packet_sha256"],
                    "result": child["record"],
                    "returncode": child["returncode"],
                    "parse_status": child["parse_status"],
                    "stderr": child["stderr"],
                }
            )
        sealed_instances.append(
            {
                "instance_commitment": instance["commitment"],
                "packets": packets,
            }
        )

    transcript = {
        "schema": 1,
        "candidate_artifact_sha256": sha256_file(CANDIDATE_PATH),
        "candidate_kind": "INELIGIBLE_CHEATING_CANARY",
        "input_mode": "single_image",
        "instances": sealed_instances,
    }
    channels = {
        "calls": len(channel_audits),
        "all_private_term_leaks_empty": all(
            not item["private_term_leaks"] for item in channel_audits
        ),
        "all_tokens_withheld": all(
            item["token_supplied"] is False for item in channel_audits
        ),
        "all_indices_withheld": all(
            item["packet_index_supplied"] is False
            for item in channel_audits
        ),
        "argv_shapes": sorted(
            {
                tuple(item["constant_argv_shape"])
                for item in channel_audits
            }
        ),
        "environment_variants": len(
            {
                canonical_bytes(item["environment"])
                for item in channel_audits
            }
        ),
        "cwd_shapes": sorted(
            {item["cwd_shape"] for item in channel_audits}
        ),
    }
    return transcript, channels


def unblind(
    sealed_bytes: bytes,
    instances: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    sealed = json.loads(sealed_bytes)
    sealed_by_token = {
        packet["token"]: packet
        for instance in sealed["instances"]
        for packet in instance["packets"]
    }
    verdicts = []
    mappings = []
    for instance in instances:
        records = {}
        duplicate_records = {}
        mapping = []
        for item in instance["packets"]:
            sealed_packet = sealed_by_token[item["token"]]
            if sealed_packet["packet_sha256"] != item["packet_sha256"]:
                raise RuntimeError("sealed packet hash changed before unblinding")
            semantic = str(item["semantic"])
            record = sealed_packet["result"]
            mapping.append(
                {
                    "token": item["token"],
                    "semantic": semantic,
                    "duplicate_of": item["duplicate_of"],
                    "packet_sha256": item["packet_sha256"],
                }
            )
            if item["duplicate_of"] is None:
                records[semantic] = record
            else:
                duplicate_records[str(item["duplicate_of"])] = record

        candidate = result_from_records(
            records, f"cheating-canary-blinded-{instance['index']}"
        )
        base_verdict = adjudicate(candidate)
        duplicate_checks = {
            semantic: (
                canonical_bytes(records[semantic])
                == canonical_bytes(duplicate_records[semantic])
            )
            for semantic in DUPLICATE_SEMANTICS
        }
        p7 = all(duplicate_checks.values())
        verdicts.append(
            {
                "instance": instance["index"],
                "P1_to_P6": base_verdict,
                "P7": p7,
                "P7_duplicate_checks": duplicate_checks,
                "candidate_result": candidate,
            }
        )
        mappings.append(
            {
                "instance": instance["index"],
                "instance_commitment": instance["commitment"],
                "packets": mapping,
            }
        )
    return verdicts, mappings


def validate_sealed_transcript(
    sealed_bytes: bytes,
    instances: list[dict[str, object]],
) -> dict[str, object]:
    checks = {
        "json_object": False,
        "top_level_fields_exact": False,
        "fixed_metadata_exact": False,
        "instance_count_exact": False,
        "instance_fields_exact": False,
        "instance_commitments_exact": False,
        "packet_count_exact": False,
        "packet_fields_exact": False,
        "packet_tokens_unique": False,
        "packet_tokens_exact": False,
        "packet_hashes_exact": False,
        "packet_instance_membership_exact": False,
        "packet_order_exact": False,
    }
    errors = []
    try:
        sealed = json.loads(sealed_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        errors.append(f"{type(error).__name__}: {error}")
        return {"passed": False, "checks": checks, "errors": errors}

    checks["json_object"] = isinstance(sealed, dict)
    if not checks["json_object"]:
        errors.append("sealed transcript is not a JSON object")
        return {"passed": False, "checks": checks, "errors": errors}

    expected_top_fields = {
        "schema",
        "candidate_artifact_sha256",
        "candidate_kind",
        "input_mode",
        "instances",
    }
    checks["top_level_fields_exact"] = set(sealed) == expected_top_fields
    checks["fixed_metadata_exact"] = (
        sealed.get("schema") == 1
        and sealed.get("candidate_artifact_sha256")
        == sha256_file(CANDIDATE_PATH)
        and sealed.get("candidate_kind")
        == "INELIGIBLE_CHEATING_CANARY"
        and sealed.get("input_mode") == "single_image"
    )

    sealed_instances = sealed.get("instances")
    checks["instance_count_exact"] = (
        isinstance(sealed_instances, list)
        and len(sealed_instances) == len(instances) == INSTANCE_COUNT
    )
    if not isinstance(sealed_instances, list):
        errors.append("sealed instances is not a list")
        return {"passed": False, "checks": checks, "errors": errors}

    expected_packet_fields = {
        "token",
        "packet_sha256",
        "result",
        "returncode",
        "parse_status",
        "stderr",
    }
    actual_tokens = []
    expected_tokens = []
    token_hashes = {}
    expected_token_hashes = {}
    instance_fields_exact = True
    instance_commitments_exact = (
        len(sealed_instances) == len(instances)
    )
    packet_count_exact = len(sealed_instances) == len(instances)
    packet_fields_exact = True
    packet_instance_membership_exact = (
        len(sealed_instances) == len(instances)
    )
    packet_order_exact = len(sealed_instances) == len(instances)

    for index, sealed_instance in enumerate(sealed_instances):
        if not isinstance(sealed_instance, dict):
            instance_fields_exact = False
            instance_commitments_exact = False
            packet_count_exact = False
            packet_fields_exact = False
            continue
        instance_fields_exact &= (
            set(sealed_instance) == {"instance_commitment", "packets"}
        )
        packets = sealed_instance.get("packets")
        if index >= len(instances):
            instance_commitments_exact = False
            packet_count_exact = False
            expected_packets = []
        else:
            expected_instance = instances[index]
            instance_commitments_exact &= (
                sealed_instance.get("instance_commitment")
                == expected_instance["commitment"]
            )
            expected_packets = expected_instance["packets"]
            expected_tokens.extend(
                str(packet["token"]) for packet in expected_packets
            )
            expected_token_hashes.update(
                {
                    str(packet["token"]): str(packet["packet_sha256"])
                    for packet in expected_packets
                }
            )
        if not isinstance(packets, list):
            packet_count_exact = False
            packet_fields_exact = False
            packet_instance_membership_exact = False
            continue
        packet_count_exact &= len(packets) == len(expected_packets)
        actual_instance_token_hashes = {}
        actual_instance_tokens = []
        for packet in packets:
            if not isinstance(packet, dict):
                packet_fields_exact = False
                packet_instance_membership_exact = False
                continue
            packet_fields_exact &= set(packet) == expected_packet_fields
            token = packet.get("token")
            packet_hash = packet.get("packet_sha256")
            if isinstance(token, str):
                actual_tokens.append(token)
                actual_instance_tokens.append(token)
                token_hashes[token] = packet_hash
                actual_instance_token_hashes[token] = packet_hash
        expected_instance_token_hashes = {
            str(packet["token"]): str(packet["packet_sha256"])
            for packet in expected_packets
        }
        packet_instance_membership_exact &= (
            actual_instance_token_hashes
            == expected_instance_token_hashes
        )
        packet_order_exact &= actual_instance_tokens == [
            str(packet["token"]) for packet in expected_packets
        ]

    checks["instance_fields_exact"] = bool(instance_fields_exact)
    checks["instance_commitments_exact"] = bool(
        instance_commitments_exact
    )
    checks["packet_count_exact"] = bool(packet_count_exact)
    checks["packet_fields_exact"] = bool(packet_fields_exact)
    checks["packet_tokens_unique"] = (
        len(actual_tokens) == len(set(actual_tokens))
    )
    checks["packet_tokens_exact"] = (
        len(actual_tokens) == len(expected_tokens)
        and set(actual_tokens) == set(expected_tokens)
    )
    checks["packet_hashes_exact"] = (
        checks["packet_tokens_exact"]
        and token_hashes == expected_token_hashes
    )
    checks["packet_instance_membership_exact"] = bool(
        packet_instance_membership_exact
    )
    checks["packet_order_exact"] = bool(packet_order_exact)
    if not all(checks.values()):
        errors.append("sealed transcript does not exactly match challenge")
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--nonce",
        help="64-hex disclosed nonce; reproduction only",
    )
    parser.add_argument("--sealed", type=Path, default=SEALED_PATH)
    parser.add_argument("--output", type=Path, default=RESULT_PATH)
    args = parser.parse_args()

    freeze = verify_freeze()
    if not freeze["passed"]:
        raise SystemExit(
            "artifact freeze failed before nonce generation: "
            + json.dumps(freeze["checks"], sort_keys=True)
        )
    source_audit = audit_candidate_source()

    if args.nonce is None:
        if args.sealed.exists() or args.output.exists():
            raise SystemExit(
                "initial outputs already exist; use their disclosed nonce "
                "only for an explicit reproduction"
            )
        nonce = secrets.token_bytes(32)
    else:
        try:
            nonce = bytes.fromhex(args.nonce)
        except ValueError as error:
            raise SystemExit(f"invalid nonce: {error}") from error
        if len(nonce) != 32:
            raise SystemExit("nonce must encode exactly 256 bits")

    instances = [
        build_instance(nonce, index) for index in range(INSTANCE_COUNT)
    ]
    legacy_result = legacy_labeled_result(instances[0])
    legacy_verdict = adjudicate(legacy_result)

    transcript, channel_audit = run_blinded(instances)
    sealed_bytes = canonical_bytes(transcript)
    args.sealed.write_bytes(sealed_bytes)
    readback = args.sealed.read_bytes()
    sealed_sha256 = sha256_bytes(readback)
    seal_readback_exact = readback == sealed_bytes

    sealed_validation = validate_sealed_transcript(readback, instances)
    unblind_error = None
    if sealed_validation["passed"]:
        try:
            blinded_verdicts, mappings = unblind(readback, instances)
        except (
            KeyError,
            TypeError,
            ValueError,
            RuntimeError,
        ) as error:
            blinded_verdicts, mappings = [], []
            unblind_error = f"{type(error).__name__}: {error}"
    else:
        blinded_verdicts, mappings = [], []
        unblind_error = "; ".join(sealed_validation["errors"])
    expected_blinded_pattern = (
        len(blinded_verdicts) == INSTANCE_COUNT
        and all(
            item["P1_to_P6"]["gates"]
            == {
                "P1": False,
                "P2": False,
                "P3": False,
                "P4": False,
                "P5": False,
                "P6": True,
            }
            and item["P7"] is True
            for item in blinded_verdicts
        )
    )
    legacy_all_green = all(legacy_verdict["gates"].values())
    packet_blinding = (
        channel_audit["all_private_term_leaks_empty"]
        and channel_audit["all_tokens_withheld"]
        and channel_audit["all_indices_withheld"]
        and len(channel_audit["argv_shapes"]) == 1
        and channel_audit["environment_variants"] == 1
        and len(channel_audit["cwd_shapes"]) == 1
    )
    canary_rejected = (
        len(blinded_verdicts) == INSTANCE_COUNT
        and all(
            item["P1_to_P6"]["verdict"]
            == "REJECTED_BY_SYNTHETIC_BATTERY"
            for item in blinded_verdicts
        )
    )
    sealed_packets = [
        packet
        for instance in transcript["instances"]
        for packet in instance["packets"]
    ]
    all_children_succeeded = (
        len(sealed_packets)
        == INSTANCE_COUNT * (12 + len(DUPLICATE_SEMANTICS))
        and channel_audit["calls"]
        == INSTANCE_COUNT * (12 + len(DUPLICATE_SEMANTICS))
        and all(
            packet["returncode"] == 0
            and packet["parse_status"] == "OK"
            and packet["stderr"] == ""
            for packet in sealed_packets
        )
    )

    def fallback_exact(item: dict[str, object]) -> bool:
        arms = item["candidate_result"]["arms"]
        valid = [
            arms["flat_roi"]["detail"],
            arms["flat_roi"]["flat"],
            arms["planted_improvement"]["base"],
            arms["planted_improvement"]["improved"],
            arms["planted_degradation"]["degraded"],
            *(
                rung["measurement"]
                for rung in arms["blur_monotonicity"]
            ),
            arms["sharpening_discrimination"]["usm"],
        ]
        malformed = arms["fail_closed"]
        expected_value = {
            "status": "VALUE",
            "score": 1.0,
            "canary_identity_source": "CALL_INDEX_GUESS",
            "canary_identity_guess": "flat_detail",
        }
        expected_nonfinite = {
            "status": "REFUSED",
            "code": "NONFINITE_INPUT",
            "reason": "canary saw a non-finite observation",
        }
        expected_wrong_shape = {
            "status": "ERROR",
            "code": "INVALID_SHAPE",
            "reason": "canary saw a non-2-D observation",
        }
        return (
            all(
                canonical_bytes(record) == canonical_bytes(expected_value)
                for record in valid
            )
            and canonical_bytes(malformed["nonfinite"])
            == canonical_bytes(expected_nonfinite)
            and canonical_bytes(malformed["wrong_shape"])
            == canonical_bytes(expected_wrong_shape)
        )

    blinded_fallback_exact = (
        len(blinded_verdicts) == INSTANCE_COUNT
        and all(fallback_exact(item) for item in blinded_verdicts)
    )
    commissioning_checks = {
        "freeze_passed_before_nonce": freeze["passed"],
        "legacy_labeled_canary_passes_P1_to_P6": legacy_all_green,
        "source_audit_detects_cheat": not source_audit["passed"],
        "blinded_channels_withhold_identity": packet_blinding,
        "all_blinded_children_succeeded": all_children_succeeded,
        "sealed_transcript_readback_exact": (
            seal_readback_exact
            and sealed_validation["passed"]
            and unblind_error is None
        ),
        "blinded_canary_fallback_exact": blinded_fallback_exact,
        "blinded_gate_pattern_matches_preregistration": (
            expected_blinded_pattern
        ),
        "cheating_canary_rejected_on_all_instances": canary_rejected,
    }
    admission_gates = {
        "A1_artifact_freeze": freeze["passed"],
        "A2_source_provenance": source_audit["passed"],
        "A3_packet_blinding": packet_blinding,
        "A4_fresh_process_per_packet": (
            channel_audit["calls"]
            == INSTANCE_COUNT * (12 + len(DUPLICATE_SEMANTICS))
        ),
        "A5_seal_before_unblind": (
            seal_readback_exact
            and sealed_validation["passed"]
            and unblind_error is None
        ),
        "A6_capability_sandbox": False,
    }
    p_gates = (
        len(blinded_verdicts) == INSTANCE_COUNT
        and all(
            all(item["P1_to_P6"]["gates"].values()) and item["P7"]
            for item in blinded_verdicts
        )
    )
    admitted = p_gates and all(admission_gates.values())
    commissioned = all(commissioning_checks.values())
    result = {
        "schema": 1,
        "status": (
            "COMMISSIONED_CANARY_REJECTION"
            if commissioned
            else "NOT_COMMISSIONED"
        ),
        "admission_verdict": (
            "ADMITTED_BY_BLINDED_BATTERY"
            if admitted
            else "REJECTED_BY_BLINDED_ADMISSION"
        ),
        "candidate": {
            "name": "cheating-arm-identity-canary",
            "kind": "INELIGIBLE_CHEATING_CANARY",
            "sha256": sha256_file(CANDIDATE_PATH),
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "absolute_timing_measured": False,
        },
        "freeze": freeze,
        "source_audit": source_audit,
        "nonce_hex_disclosed_after_seal": nonce.hex().upper(),
        "sealed_transcript": {
            "path": str(args.sealed.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sealed_sha256,
            "bytes": len(readback),
            "contains_semantic_mapping": False,
            "validation": sealed_validation,
            "unblind_error": unblind_error,
        },
        "channel_audit": channel_audit,
        "legacy_labeled_control": {
            "candidate_result": legacy_result,
            "verdict": legacy_verdict,
        },
        "blinded_instances": blinded_verdicts,
        "unblinded_mapping": mappings,
        "admission_gates": admission_gates,
        "commissioning_checks": commissioning_checks,
        "sandbox_note": (
            "Local Windows subprocess commissioning proves API blinding and "
            "fresh-process behavior only. A6 is false; real candidate "
            "admission remains fail-closed until an independently audited "
            "capability sandbox is available."
        ),
    }
    args.output.write_bytes(
        json.dumps(
            result,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )
    summary = {
        "status": result["status"],
        "admission_verdict": result["admission_verdict"],
        "legacy_gates": legacy_verdict["gates"],
        "blinded_gates": [
            {
                **item["P1_to_P6"]["gates"],
                "P7": item["P7"],
            }
            for item in blinded_verdicts
        ],
        "source_audit_passed": source_audit["passed"],
        "sandbox_attested": admission_gates["A6_capability_sandbox"],
        "sealed_sha256": sealed_sha256,
        "nonce_hex_disclosed_after_seal": (
            result["nonce_hex_disclosed_after_seal"]
        ),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if commissioned and not admitted else 1


if __name__ == "__main__":
    raise SystemExit(main())

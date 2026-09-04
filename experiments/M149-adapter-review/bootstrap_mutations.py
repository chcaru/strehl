from __future__ import annotations

import argparse
import importlib._bootstrap_external
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True

from review_common import (
    HERE,
    completed_record,
    copy_registered_runtime,
    rebuild_bundle,
    sha256_file,
)

DEFAULT_SOURCE = HERE / "fixtures" / "vulnerable-unbound-runtime"
DIRECT_ANCHOR = '''        code = compile(path.read_bytes(), str(path), "exec", dont_inherit=True)
        module = types.ModuleType("m135_comparison_checker")
        module.__file__ = str(path)
        module.__package__ = ""
        exec(code, module.__dict__)'''
DIRECT_REPLACEMENT = '''        import importlib.util
        spec = importlib.util.spec_from_file_location("m135_comparison_checker", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not create standard source loader")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)'''
BUNDLE_ANCHOR = "        verify_artifact_ref(ref, base=HERE, root=HERE, label=label)"
BUNDLE_REPLACEMENT = "        pass  # M149 neutered bundle member hash verification"


def replace_exact(path: Path, anchor: str, replacement: str) -> int:
    text = path.read_text(encoding="utf-8")
    count = text.count(anchor)
    if count != 1:
        raise RuntimeError(f"{path.name}: anchor count {count}, expected 1")
    path.write_bytes(text.replace(anchor, replacement).encode("utf-8"))
    return count


def run_describe(runtime: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [sys.executable, "-I", str(runtime / "m138_adapter.py"), "--describe"],
        cwd=runtime,
        capture_output=True,
        check=False,
        timeout=120,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-run M149's direct-source and bundle-member bootstrap mutations."
    )
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path(tempfile.gettempdir()) / "strehl-M149-bootstrap-mutation-run",
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    work = args.work_dir.resolve()
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)

    pyc_runtime = work / "direct-loader"
    copy_registered_runtime(args.source_dir.resolve(), pyc_runtime)
    core = pyc_runtime / "comparison_checker.py"
    marker = work / "POISONED_PYC_EXECUTED"
    cache = Path(importlib.util.cache_from_source(str(core)))
    cache.parent.mkdir(exist_ok=True)
    poison_source = (
        "from pathlib import Path\n"
        + "Path(r'"
        + str(marker).replace("\\", "\\\\")
        + "').write_text('EXECUTED', encoding='utf-8')\n"
    )
    code = compile(poison_source, str(core), "exec")
    stat = core.stat()
    cache.write_bytes(
        importlib._bootstrap_external._code_to_timestamp_pyc(
            code, int(stat.st_mtime), stat.st_size
        )
    )

    if marker.exists():
        marker.unlink()
    spec = importlib.util.spec_from_file_location("m149_standard_loader_probe", core)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not construct conventional loader probe")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    conventional_executed = marker.exists()

    if marker.exists():
        marker.unlink()
    original_direct = run_describe(pyc_runtime)
    original_ignored = not marker.exists()

    adapter = pyc_runtime / "m138_adapter.py"
    direct_anchor_count = replace_exact(adapter, DIRECT_ANCHOR, DIRECT_REPLACEMENT)
    rebuild_bundle(pyc_runtime)
    if marker.exists():
        marker.unlink()
    direct_mutant = run_describe(pyc_runtime)
    direct_mutant_executed = marker.exists()

    static_runtime = work / "static-tamper-original"
    copy_registered_runtime(args.source_dir.resolve(), static_runtime)
    static_marker = work / "STATIC_TAMPER_EXECUTED"
    static_core = static_runtime / "comparison_checker.py"
    static_core.write_bytes(
        static_core.read_bytes()
        + (
            "\nPath(r'"
            + str(static_marker).replace("\\", "\\\\")
            + "').write_text('EXECUTED', encoding='utf-8')\n"
        ).encode("utf-8")
    )
    static_original = run_describe(static_runtime)
    static_original_blocked = bool(
        static_original.returncode != 0 and not static_marker.exists()
    )

    bundle_runtime = work / "bundle-member-mutant"
    copy_registered_runtime(args.source_dir.resolve(), bundle_runtime)
    bundle_adapter = bundle_runtime / "m138_adapter.py"
    bundle_anchor_count = replace_exact(
        bundle_adapter, BUNDLE_ANCHOR, BUNDLE_REPLACEMENT
    )
    rebuild_bundle(bundle_runtime)
    bundle_marker = work / "BUNDLE_GUARD_MUTANT_EXECUTED"
    bundle_core = bundle_runtime / "comparison_checker.py"
    bundle_core.write_bytes(
        bundle_core.read_bytes()
        + (
            "\nPath(r'"
            + str(bundle_marker).replace("\\", "\\\\")
            + "').write_text('EXECUTED', encoding='utf-8')\n"
        ).encode("utf-8")
    )
    bundle_mutant = run_describe(bundle_runtime)
    bundle_mutant_executed = bundle_marker.exists()

    checks = {
        "poisoned_bytecode_exists": cache.is_file(),
        "standard_source_loader_executes_poisoned_bytecode": conventional_executed,
        "registered_adapter_ignores_poisoned_bytecode": bool(
            original_direct.returncode == 0 and original_ignored
        ),
        "direct_loader_mutant_executes_poisoned_bytecode": direct_mutant_executed,
        "static_tamper_original_refuses_before_execution": static_original_blocked,
        "bundle_guard_mutant_executes_tampered_core": bundle_mutant_executed,
    }
    report = {
        "schema": "m149-adapter-bootstrap-mutations-v1",
        "status": "PASS" if set(checks.values()) == {True} else "FAIL",
        "source_dir": str(args.source_dir.resolve()),
        "work_dir": str(work),
        "checks": checks,
        "direct_anchor_count": direct_anchor_count,
        "bundle_anchor_count": bundle_anchor_count,
        "direct_mutant_adapter_sha256": sha256_file(adapter),
        "bundle_mutant_adapter_sha256": sha256_file(bundle_adapter),
        "original_direct": completed_record(original_direct),
        "direct_mutant": completed_record(direct_mutant),
        "static_original": completed_record(static_original),
        "bundle_mutant": completed_record(bundle_mutant),
    }
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n"
    print(encoded, end="")
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8", newline="\n")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

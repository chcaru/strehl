"""Build and pin separate M194d core/CLI controls; no scored image campaign."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = runpy.run_path(str(ROOT / "experiments/m194b-known-scene/consumer-run.py"))
TARGET = "target/m194d-band-admission"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    result = BASE["sources"]()
    for path in HERE.glob("*.rs"):
        result[path.relative_to(ROOT).as_posix()] = sha(path)
    relative = "crates/strehl-cli/src/merge_cmd/band-admission-benchmark.rs"
    result[relative] = sha(ROOT / relative)
    return result


def write(path, value):
    BASE["write_new"](path, value)


def invoke(command, directory, label):
    env = BASE["controlled_env"]()
    started = datetime.now(timezone.utc).isoformat()
    process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    ended = datetime.now(timezone.utc).isoformat()
    log = directory / (label + ".log")
    log.write_bytes(process.stdout + process.stderr)
    record = dict(command=command, started_utc=started, ended_utc=ended,
                  exit_code=process.returncode, log=str(log), log_sha256=sha(log),
                  environment={k: v for k, v in env.items() if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"})
    write(directory / (label + ".json"), record)
    return process, record


def build(directory, package, target_args, name):
    before = sources()
    touched = "crates/strehl-core/src/pyramid.rs" if package == "strehl-core" else "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs"
    (ROOT / touched).touch()
    command = ["cargo", "test", "-p", package, *target_args, "--target-dir", TARGET,
               "--no-run", "--message-format=json-render-diagnostics"]
    process, record = invoke(command, directory, name + "-build-command")
    artifacts = []
    for line in process.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("{"):
            item = json.loads(line)
            if item.get("reason") == "compiler-artifact" and item.get("executable") and item.get("profile", {}).get("test"):
                artifacts.append(item)
    after = sources()
    record.update(schema="m194b-consumer-build-v1", purpose="M194d " + name + " component controls",
                  sources_before=before, sources_after=after,
                  rebuilt_cli=b"Compiling strehl-cli" in process.stderr,
                  rebuilt_core=b"Compiling strehl-core" in process.stderr,
                  driver_sha256=sha(__file__))
    expected = record["rebuilt_core"] if package == "strehl-core" else record["rebuilt_cli"]
    record["pass"] = process.returncode == 0 and expected and len(artifacts) == 1 and before == after
    if record["pass"]:
        artifact = artifacts[0]
        original = Path(artifact["executable"])
        copied = directory / (name + "-tests.exe")
        original_binding = dict(path=str(original.resolve()), sha256=sha(original), bytes=original.stat().st_size)
        shutil.copyfile(original, copied)
        record["compiler_artifact_message"] = artifact
        record["compiler_artifact"] = original_binding
        record["test_executable"] = dict(path=str(copied), sha256=sha(copied), bytes=copied.stat().st_size)
        record["copy_matches_compiler_artifact"] = sha(original) == sha(copied) == original_binding["sha256"]
        record["pass"] = record["copy_matches_compiler_artifact"]
    path = directory / (name + "-build.json")
    write(path, record)
    print(process.stderr.decode("utf-8", "replace")[-5000:], flush=True)
    if not record["pass"]:
        raise RuntimeError("build failed: " + str(path))
    return path, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    snapshot = directory / "edited-source-snapshot"
    paths = [ROOT / p for p in ["crates/strehl-core/src/pyramid.rs", "crates/strehl-cli/src/merge_cmd.rs",
             "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs", "crates/strehl-cli/src/merge_cmd/band-admission-benchmark.rs"]]
    paths += list(HERE.glob("*.rs")) + [Path(__file__)]
    for path in paths:
        destination = snapshot / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)
    core_path, core = build(directory, "strehl-core", ["--lib"], "core")
    cli_path, cli = build(directory, "strehl-cli", ["--bin", "strehl"], "cli")
    checks = []
    for name, record, prefix, count in [
        ("core", core, "pyramid::m194d_author_tests::", 4),
        ("cli", cli, "merge_cmd::known_scene_benchmark::band_admission_benchmark::m194d_defaults_and_explicit_option", 1),
    ]:
        command = [record["test_executable"]["path"], prefix, "--test-threads=1", "--nocapture"]
        process, check = invoke(command, directory, name + "-author-tests")
        check["pass"] = process.returncode == 0 and f"{count} passed; 0 failed".encode() in process.stdout
        checks.append(check)
        print(process.stdout.decode("utf-8", "replace")[-2500:], flush=True)
        if process.returncode:
            print(process.stderr.decode("utf-8", "replace")[-3500:], flush=True)
    result = dict(schema="m194d-author-controls-v1", core_build=str(core_path), core_build_sha256=sha(core_path),
                  cli_build=str(cli_path), cli_build_sha256=sha(cli_path), checks=checks,
                  sources_unchanged=core["sources_after"] == cli["sources_after"] == sources())
    result["pass"] = result["sources_unchanged"] and all(c["pass"] for c in checks)
    write(directory / "result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}), flush=True)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

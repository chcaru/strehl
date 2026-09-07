"""Build and run M194c sampler/probe controls in isolated gather processes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
GATEFLOOR = ROOT / "crates/strehl-cli/src/merge_cmd/gatefloor.rs"
BASE = runpy.run_path(str(ROOT / "experiments/m194b-known-scene/consumer-run.py"))
PREFIX = "merge_cmd::gatefloor::m194c_author_tests::"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def extra_sources():
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(HERE.glob("*.rs"))}


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def run(command, env, directory, label):
    started = datetime.now(timezone.utc).isoformat()
    p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    ended = datetime.now(timezone.utc).isoformat()
    raw = p.stdout + p.stderr
    log = directory / (label + ".log")
    with log.open("xb") as f:
        f.write(raw)
    record = dict(command=command, started_utc=started, ended_utc=ended,
                  exit_code=p.returncode, log=str(log), log_sha256=sha(log),
                  environment={k: v for k, v in env.items()
                               if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"})
    write_new(directory / (label + ".json"), record)
    return p, raw, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    directory = args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    before = BASE["sources"]()
    extra_before = extra_sources()
    env = BASE["controlled_env"]()
    GATEFLOOR.touch()
    command = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--target-dir",
               "target/m194c-probe-layout", "--no-run", "--message-format=json-render-diagnostics"]
    p, raw, record = run(command, env, directory, "build-command")
    artifacts = []
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        if not line.startswith("{"):
            continue
        v = json.loads(line)
        if (v.get("reason") == "compiler-artifact" and v.get("executable")
                and v.get("target", {}).get("name") == "strehl"
                and v.get("profile", {}).get("test")):
            artifacts.append(Path(v["executable"]))
    after = BASE["sources"]()
    extra_after = extra_sources()
    record.update(schema="m194b-consumer-build-v1", purpose="M194c candidate and sampler commissioning",
                  sources_before=before, sources_after=after,
                  included_test_sources_before=extra_before, included_test_sources_after=extra_after,
                  rebuilt_cli=b"Compiling strehl-cli" in raw)
    record["pass"] = (p.returncode == 0 and record["rebuilt_cli"] and len(artifacts) == 1
                      and before == after and extra_before == extra_after)
    if record["pass"]:
        original = dict(path=str(artifacts[0].resolve()), sha256=sha(artifacts[0]),
                        bytes=artifacts[0].stat().st_size)
        pinned = directory / "known-scene-tests.exe"
        shutil.copyfile(artifacts[0], pinned)
        record["compiler_artifact"] = original
        record["test_executable"] = dict(path=str(pinned), sha256=sha(pinned), bytes=pinned.stat().st_size)
        record["copy_matches_compiler_artifact"] = (
            sha(pinned) == original["sha256"] == sha(artifacts[0])
            and pinned.stat().st_size == original["bytes"])
        record["pass"] = record["copy_matches_compiler_artifact"]
    build_path = directory / "build.json"
    write_new(build_path, record)
    if not record["pass"]:
        print("Build failed; full evidence:", directory / "build-command.log")
        print(p.stderr.decode("utf-8", "replace")[-6000:])
        return 1
    checks = []
    for gather in ["0", "1"]:
        env = BASE["controlled_env"]()
        env.update(STREHL_FULLRES_GATHER=gather, STREHL_M194C="1")
        command = [str(pinned), PREFIX, "--include-ignored", "--test-threads=1", "--nocapture"]
        p, raw, result = run(command, env, directory, "gather-" + gather)
        result["pass"] = p.returncode == 0 and b"4 passed; 0 failed" in raw
        checks.append(result)
    result = dict(schema="m194c-author-controls-v1", build_record=str(build_path),
                  build_sha256=sha(build_path), checks=checks,
                  sources_unchanged=after == BASE["sources"]() and extra_after == extra_sources())
    result["pass"] = result["sources_unchanged"] and all(c["pass"] for c in checks)
    write_new(directory / "result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "checks"}))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

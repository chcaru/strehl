"""Retain M194d broader unit/lint checks before handing out final test pins."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import runpy
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DRIVER = runpy.run_path(str(HERE / "run-author-controls.py"))
BASE = DRIVER["BASE"]
TARGET = DRIVER["TARGET"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--lint-only", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    before = DRIVER["sources"]()
    checks = []
    jobs = [
        ("core-unit", "Compiling strehl-core", ["cargo", "test", "-p", "strehl-core", "--lib", "--target-dir", TARGET, "--", "--test-threads=1"], "crates/strehl-core/src/pyramid.rs"),
        ("cli-unit", "Compiling strehl-cli", ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--target-dir", TARGET, "--", "--test-threads=1"], "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs"),
        ("clippy", "Checking strehl-core", ["cargo", "clippy", "-p", "strehl-core", "-p", "strehl-cli", "--lib", "--bins", "--tests", "--target-dir", TARGET], "crates/strehl-core/src/pyramid.rs"),
    ]
    if args.lint_only:
        jobs = [job for job in jobs if job[0] == "clippy"]
    for label, proof, command, touched in jobs:
        (ROOT / touched).touch()
        if label == "clippy":
            (ROOT / "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs").touch()
        env = BASE["controlled_env"]()
        if label == "clippy":
            env["STREHL_BUILD_ID"] = "m194d-lint-only"
        started = datetime.now(timezone.utc).isoformat()
        p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
        ended = datetime.now(timezone.utc).isoformat()
        log = out / (label + ".log")
        raw = p.stdout + p.stderr
        log.write_bytes(raw)
        record = dict(command=command, started_utc=started, ended_utc=ended,
                      exit_code=p.returncode, log=str(log), log_sha256=DRIVER["sha"](log),
                      rebuilt=proof.encode() in raw,
                      environment={k: v for k, v in env.items() if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"})
        if label == "clippy":
            record["checked_cli"] = b"Checking strehl-cli" in raw
        record["pass"] = p.returncode == 0 and record["rebuilt"]
        if label == "clippy":
            record["pass"] = record["pass"] and record["checked_cli"]
        BASE["write_new"](out / (label + ".json"), record)
        checks.append(record)
        print(raw.decode("utf-8", "replace")[-4500:], flush=True)
    result = dict(schema="m194d-broader-checks-v1", checks=checks, sources_unchanged=before == DRIVER["sources"]())
    result["pass"] = all(c["pass"] for c in checks) and result["sources_unchanged"]
    BASE["write_new"](out / "result.json", result)
    print(json.dumps({"pass": result["pass"], "record": str(out / "result.json")}), flush=True)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

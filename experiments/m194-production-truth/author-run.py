"""Author regression checks of the shared source path; not independent verification."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCES = [
    ROOT / "crates/strehl-cli/src/merge_cmd.rs",
    ROOT / "crates/strehl-cli/src/merge_cmd/production-truth.rs",
    HERE / "independent-controls.rs",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if sys.argv[1:] not in ([], ["--focused"]):
        raise SystemExit("usage: author-run.py [--focused]")
    focused = bool(sys.argv[1:])
    started = datetime.now(timezone.utc).isoformat()
    sources_before = {str(p.relative_to(ROOT)): sha(p) for p in SOURCES}
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("STREHL_")}
    env.pop("RUSTFLAGS", None)
    env.pop("CARGO_ENCODED_RUSTFLAGS", None)
    env.update(STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
    # Source content is unchanged. Force compiler proof after the final edits,
    # including a source restored/renamed with an older timestamp.
    os.utime(SOURCES[1], None)
    command = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl",
               "--target-dir", "target/m194-production-truth"]
    if focused:
        command.append("m194_actual_source_gather_fold_writer_controls")
    command += ["--", "--test-threads=1"]
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    output = completed.stdout + completed.stderr
    log = HERE / ("author-focused-test.log" if focused else "author-final-test.log")
    log.write_bytes(output)
    decoded = output.decode("utf-8", errors="replace")
    evidence = {
        "schema": "m194-author-regression-v1",
        "started_utc": started,
        "command": command,
        "cleared_environment_policy": "all inherited STREHL_* (case insensitive), RUSTFLAGS and CARGO_ENCODED_RUSTFLAGS",
        "environment": {k: v for k, v in env.items()
                        if k.upper().startswith("STREHL_") or k == "RAYON_NUM_THREADS"},
        "exit_code": completed.returncode,
        "rebuilt_cli": "Compiling strehl-cli" in decoded,
        "summary": re.findall(r"test result:.*", decoded),
        "log": log.name,
        "log_sha256": sha(log),
        "sources_before": sources_before,
        "sources_after": {str(p.relative_to(ROOT)): sha(p) for p in SOURCES},
    }
    evidence["pass"] = (
        completed.returncode == 0
        and evidence["rebuilt_cli"]
        and bool(evidence["summary"])
        and evidence["sources_before"] == evidence["sources_after"]
    )
    (HERE / ("author-focused-verification.json" if focused else "author-verification.json")).write_text(
        json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

"""Isolated M194 independent synthetic commissioning, no RAW access."""
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


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def controlled_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("STREHL_")}
    env.update(STREHL_PYRAMID_WORKERS="2", STREHL_DEFECT="off", RAYON_NUM_THREADS="2")
    env.pop("RUSTFLAGS", None)
    env.pop("CARGO_ENCODED_RUSTFLAGS", None)
    return env


def main():
    started = datetime.now(timezone.utc).isoformat()
    paths = [ROOT / "crates/strehl-cli/src/merge_cmd.rs",
             ROOT / "crates/strehl-cli/src/merge_cmd/production-truth.rs",
             HERE / "independent-controls.rs"]
    sources = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    # No source-content changes; mtime forces Cargo to rebuild the included
    # controls even if a sibling build fingerprinted an earlier file version.
    os.utime(HERE / "independent-controls.rs", None)
    results = []
    for debug in [False, True]:
        env = controlled_env()
        label = "debug" if debug else "normal"
        if debug:
            debug_dir = HERE / "work/independent-debug-maps"
            debug_dir.mkdir(parents=True, exist_ok=True)
            env["STREHL_CONFIDENCE_DEBUG"] = str(debug_dir)
        cmd = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl",
               "--target-dir", "target/m194-production-truth", "independent_m194_",
               "--", "--test-threads", "1", "--nocapture"]
        p = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True)
        text = (p.stdout + p.stderr).decode("utf-8", errors="replace")
        log = HERE / f"independent-{label}-test.log"
        log.write_bytes(p.stdout + p.stderr)
        summary = re.findall(r"test result:.*", text)
        record = dict(label=label, command=cmd, exit_code=p.returncode,
                      log=log.name, log_sha256=sha(log), test_summary=summary,
                      rebuilt_cli="Compiling strehl-cli" in text,
                      environment={k: v for k, v in env.items()
                                   if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"},
                      cleared_environment_policy="all inherited STREHL_*; RUSTFLAGS; CARGO_ENCODED_RUSTFLAGS")
        results.append(record)
        print(json.dumps(record), flush=True)
        if p.returncode or not any("5 passed; 0 failed" in s for s in summary):
            break
    evidence = dict(schema="m194-independent-synthetic-v1", started_utc=started,
                    sources_before=sources,
                    sources_after={str(p.relative_to(ROOT)): sha(p) for p in paths},
                    runs=results)
    evidence["pass"] = (len(results) == 2 and all(r["exit_code"] == 0 for r in results)
                        and results[0]["rebuilt_cli"]
                        and evidence["sources_before"] == evidence["sources_after"])
    (HERE / "independent-verification.json").write_text(json.dumps(evidence, indent=2) + "\n")
    return 0 if evidence["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

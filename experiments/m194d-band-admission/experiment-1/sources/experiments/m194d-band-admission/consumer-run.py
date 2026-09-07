"""M194d explicit-mode adapter derived from the frozen M194b consumer driver."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FIXED = ROOT / "experiments/m194b-known-scene"
SOURCE = ROOT / "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs"
TEST = "merge_cmd::known_scene_benchmark::band_admission_benchmark::m194d_known_scene_consumer"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def controlled_env():
    env = {k: v for k, v in os.environ.items() if not k.upper().startswith("STREHL_")}
    for key in ["RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RAYON_NUM_THREADS", "CARGO_TARGET_DIR"]:
        env.pop(key, None)
    env.update(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1",
               STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
    return env


def sources():
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z", "crates", "Cargo.toml", "Cargo.lock"], cwd=ROOT
    ).decode("utf-8").split("\0")
    paths = {ROOT / p for p in tracked if p and (ROOT / p).is_file()}
    paths.update([SOURCE, ROOT / "experiments/m194-production-truth/independent-controls.rs"])
    paths.update((ROOT / "experiments/m194c-probe-layout").glob("*.rs"))
    paths.update(HERE.glob("*.rs"))
    paths.add(SOURCE.parent / "band-admission-benchmark.rs")
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def build(args):
    record_path = args.build_record.resolve()
    if record_path.exists():
        raise ValueError("build record already exists; preserve it and choose another path")
    before = sources()
    os.utime(SOURCE, None)
    command = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl",
               "--target-dir", "target/m194d-band-admission", TEST, "--no-run",
               "--message-format=json-render-diagnostics"]
    env = controlled_env()
    started_utc = datetime.now(timezone.utc).isoformat()
    p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    ended_utc = datetime.now(timezone.utc).isoformat()
    raw_log = p.stdout + p.stderr
    log = record_path.with_suffix(".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("xb") as f:
        f.write(raw_log)
    artifacts = []
    for line in p.stdout.decode("utf-8", "replace").splitlines():
        if not line.startswith("{"):
            continue
        value = json.loads(line)
        if (value.get("reason") == "compiler-artifact" and value.get("executable")
                and value.get("target", {}).get("name") == "strehl"
                and value.get("profile", {}).get("test")):
            artifacts.append(Path(value["executable"]))
    after = sources()
    record = dict(schema="m194d-consumer-build-v1", command=command,
                  started_utc=started_utc, ended_utc=ended_utc,
                  exit_code=p.returncode, log=str(log), log_sha256=sha(log),
                  rebuilt_cli=b"Compiling strehl-cli" in raw_log,
                  sources_before=before, sources_after=after,
                  environment={k: v for k, v in env.items()
                               if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"})
    record["pass"] = (p.returncode == 0 and record["rebuilt_cli"]
                      and before == after and len(artifacts) == 1)
    if record["pass"]:
        original = dict(path=str(artifacts[0].resolve()), sha256=sha(artifacts[0]),
                        bytes=artifacts[0].stat().st_size)
        directory = HERE / "work/consumer-binaries" / uuid.uuid4().hex
        directory.mkdir(parents=True, exist_ok=False)
        pinned = directory / "known-scene-tests.exe"
        shutil.copyfile(artifacts[0], pinned)
        record["test_executable"] = dict(path=str(pinned), sha256=sha(pinned),
                                         bytes=pinned.stat().st_size)
        record["compiler_artifact"] = original
        record["copy_matches_compiler_artifact"] = (
            record["test_executable"]["sha256"] == original["sha256"]
            and record["test_executable"]["bytes"] == original["bytes"]
            and sha(artifacts[0]) == original["sha256"]
        )
        record["pass"] = record["copy_matches_compiler_artifact"]
    write_new(record_path, record)
    print(json.dumps({"build_record": str(record_path), "sha256": sha(record_path),
                      "pass": record["pass"]}))
    if not record["pass"]:
        sys.stderr.write(raw_log.decode("utf-8", "replace"))
    return 0 if record["pass"] else 1


def invoke(args):
    record_path = args.build_record.resolve()
    if sha(record_path) != args.build_sha256:
        raise ValueError("trusted build record SHA-256 mismatch")
    record = load(record_path)
    if record["schema"] != "m194d-consumer-build-v1" or not record["pass"]:
        raise ValueError("build is not commissioned")
    if sources() != record["sources_after"]:
        raise ValueError("compiled source binding changed")
    executable = Path(record["test_executable"]["path"])
    if sha(executable) != record["test_executable"]["sha256"]:
        raise ValueError("pinned test executable changed")
    env = controlled_env()
    env.update(STREHL_M194D_ADMISSION=args.admission,
               STREHL_M194B_MODE=args.mode,
               STREHL_M194B_MANIFEST=str(args.manifest.resolve()),
               STREHL_M194B_MANIFEST_SHA256=args.manifest_sha256,
               STREHL_M194B_PLAN=str(args.plan.resolve()))
    if args.diagnostic_white_floor:
        env.update(STREHL_M194B_DIAGNOSTIC="white-floor-isolation",
                   STREHL_GATE_FLOOR="white")
    target = args.plan if args.mode == "plan" else args.receipt
    if args.mode == "render":
        env.update(STREHL_M194B_PLAN_SHA256=args.plan_sha256,
                   STREHL_M194B_SUBSET=args.subset,
                   STREHL_M194B_OUTPUT=str(args.output.resolve()),
                   STREHL_M194B_RECEIPT=str(args.receipt.resolve()))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.confidence:
            env["STREHL_M194B_CONFIDENCE"] = str(args.confidence.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    log = args.log or target.with_suffix(".command.log")
    if log.exists():
        raise ValueError("command log already exists; choose a fresh evidence path")
    command = [str(executable), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
    p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True)
    raw = p.stdout + p.stderr
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("xb") as f:
        f.write(raw)
    success = p.returncode == 0 and b"1 passed; 0 failed" in raw and target.exists()
    evidence = dict(schema="m194d-consumer-command-v1", command=command,
                    exit_code=p.returncode, pass_=success, log=str(log.resolve()),
                    log_sha256=sha(log), build_sha256=args.build_sha256,
                    environment={k: v for k, v in env.items()
                                 if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"})
    if success:
        evidence.update(result=str(target.resolve()), result_sha256=sha(target))
    write_new(log.with_suffix(".json"), evidence)
    print(json.dumps(evidence))
    if not success:
        sys.stderr.write(raw.decode("utf-8", "replace"))
    return 0 if success else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    b = modes.add_parser("build")
    b.add_argument("--build-record", type=Path, required=True)
    for name in ["plan", "render"]:
        p = modes.add_parser(name)
        p.add_argument("--admission", choices=["hard-floor", "floor-pedestal-v1"], required=True)
        p.add_argument("--build-record", type=Path, required=True)
        p.add_argument("--build-sha256", required=True)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--manifest-sha256", required=True)
        p.add_argument("--plan", type=Path, required=True)
        p.add_argument("--log", type=Path)
        p.add_argument("--diagnostic-white-floor", action="store_true",
                       help="isolation control only; excluded from the registered baseline")
        if name == "render":
            p.add_argument("--plan-sha256", required=True)
            p.add_argument("--subset", choices=["all", "best"], required=True)
            p.add_argument("--output", type=Path, required=True)
            p.add_argument("--receipt", type=Path, required=True)
            p.add_argument("--confidence", type=Path)
    args = parser.parse_args()
    return build(args) if args.mode == "build" else invoke(args)


if __name__ == "__main__":
    sys.exit(main())

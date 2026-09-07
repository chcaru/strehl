"""M194f bounded production bridge driver; no model or merge arithmetic."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / "crates/strehl-cli/src/merge_cmd/joint-pupil-bridge.rs"
PARENT = SOURCE.with_name("known-scene-benchmark.rs")
TEST = "merge_cmd::known_scene_benchmark::joint_pupil_bridge::m194f_production_bridge"
TARGET = "target/m194f-production-bridge"
PREFIX = "STREHL_M194F_"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def unique(items):
    out = {}
    for key, value in items:
        if key in out:
            raise ValueError("duplicate JSON key " + key)
        out[key] = value
    return out


def load(path):
    with Path(path).open("rb") as f:
        raw = f.read(1_048_577)
    if len(raw) > 1_048_576:
        raise ValueError("JSON exceeds registered1MiB limit")
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def controlled_env():
    env = {k: v for k, v in os.environ.items()
           if not k.upper().startswith("STREHL_") and k.upper() not in
           {"RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "RAYON_NUM_THREADS", "CARGO_TARGET_DIR"}}
    env.update(STREHL_DEFECT="off", STREHL_FIX_CA="off", STREHL_FULLRES_GATHER="1",
               STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2")
    return env


def sources():
    """Bind tracked crates plus this tree's explicit external Rust include forms.

    As in M194d, this is not a general Rust/cfg parser. Both test crates' sources
    are bound even when a dependency build omits their cfg(test) modules.
    """
    tracked = subprocess.check_output(["git", "--no-optional-locks", "ls-files", "-z",
                                       "crates", "Cargo.toml", "Cargo.lock"], cwd=ROOT)
    paths = {ROOT / p for p in tracked.decode("utf-8").split("\0") if p and (ROOT / p).is_file()}
    paths.add(SOURCE)
    pending = [(p, ROOT / "crates" / p.relative_to(ROOT).parts[1])
               for p in paths if p.suffix == ".rs"]
    seen = set()
    while pending:
        source, crate = pending.pop()
        if (source, crate) in seen:
            continue
        seen.add((source, crate))
        text = source.read_text(encoding="utf-8")
        targets = [(crate / relative.lstrip("/")).resolve() for relative in re.findall(
            r'^\s*include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)', text, re.M)]
        targets += [(source.parent / relative).resolve() for relative in
                    re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]', text, re.M)]
        for target in targets:
            if not target.is_relative_to(ROOT) or not target.is_file():
                raise ValueError("invalid external Rust include " + str(target))
            paths.add(target)
            pending.append((target, crate))
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def relevant_env(env):
    return {k: v for k, v in env.items() if k.startswith("STREHL_") or k == "RAYON_NUM_THREADS"}


def build(args):
    target = args.build_record.resolve()
    if target.exists() or target.with_suffix(".log").exists():
        raise ValueError("new build record/log required")
    before = sources()
    driver_sha = sha(__file__)
    SOURCE.touch()
    PARENT.touch()
    command = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--target-dir", TARGET,
               "--no-run", "--message-format=json-render-diagnostics"]
    env = controlled_env()
    started = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, check=False)
    ended = datetime.now(timezone.utc).isoformat()
    raw = proc.stdout + proc.stderr
    log = target.with_suffix(".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("xb") as f:
        f.write(raw)
    artifacts = []
    for line in proc.stdout.decode("utf-8", "replace").splitlines():
        if line.startswith("{"):
            value = json.loads(line)
            if (value.get("reason") == "compiler-artifact" and value.get("executable")
                    and value.get("target", {}).get("name") == "strehl"
                    and value.get("profile", {}).get("test")):
                artifacts.append(value)
    after = sources()
    record = dict(schema="m194f-consumer-build-v1", command=command, interpreter_argv=sys.orig_argv,
                  started_utc=started, ended_utc=ended, exit_code=proc.returncode,
                  log=str(log), log_sha256=sha(log), rebuilt_cli=b"Compiling strehl-cli" in raw,
                  sources_before=before, sources_after=after, driver_sha256=driver_sha,
                  environment=relevant_env(env), xoptions=sys._xoptions, python=sys.version)
    record["pass"] = (proc.returncode == 0 and record["rebuilt_cli"] and before == after
                      and len(artifacts) == 1 and sha(__file__) == driver_sha)
    if record["pass"]:
        original = Path(artifacts[0]["executable"]).resolve()
        directory = HERE / "work/consumer-binaries" / uuid.uuid4().hex
        directory.mkdir(parents=True, exist_ok=False)
        copied = directory / "joint-pupil-bridge-tests.exe"
        original_ref = dict(path=str(original), sha256=sha(original), bytes=original.stat().st_size)
        shutil.copyfile(original, copied)
        record.update(compiler_artifact_message=artifacts[0], compiler_artifact=original_ref,
                      test_executable=dict(path=str(copied), sha256=sha(copied), bytes=copied.stat().st_size))
        record["copy_matches_compiler_artifact"] = (
            sha(original) == sha(copied) == original_ref["sha256"] and copied.stat().st_size == original_ref["bytes"])
        record["pass"] = record["copy_matches_compiler_artifact"]
    write_new(target, record)
    print(proc.stderr.decode("utf-8", "replace"), flush=True)
    print(json.dumps(dict(build_record=str(target), sha256=sha(target), passed=record["pass"])))
    return 0 if record["pass"] else 1


def invoke(args):
    record_path = args.build_record.resolve()
    if sha(record_path) != args.build_sha256:
        raise ValueError("external build SHA differs")
    build_record = load(record_path)
    if (build_record["schema"] != "m194f-consumer-build-v1" or build_record["pass"] is not True
            or build_record["driver_sha256"] != sha(__file__)
            or build_record["sources_before"] != build_record["sources_after"]):
        raise ValueError("build or driver not commissioned")
    if sources() != build_record["sources_after"]:
        raise ValueError("compiled sources changed")
    exe = Path(build_record["test_executable"]["path"])
    if sha(exe) != build_record["test_executable"]["sha256"]:
        raise ValueError("pinned executable changed")
    env = controlled_env()
    fields = dict(MODE=args.mode, MANIFEST=str(args.manifest.resolve()), MANIFEST_SHA256=args.manifest_sha256,
                  CFA_COMMISSION=str(args.cfa_commission.resolve()), CFA_COMMISSION_SHA256=args.cfa_commission_sha256,
                  PLAN=str(args.plan.resolve()), OBSERVER=args.observer, CONFIDENCE=str(int(args.confidence)),
                  EXPOSURE=str(args.exposure))
    target = args.plan if args.mode == "plan" else args.receipt
    if args.mode == "render":
        if bool(args.confidence_output) != args.confidence:
            raise ValueError("confidence output required exactly when confidence is enabled")
        fields.update(PLAN_SHA256=args.plan_sha256, OUTPUT=str(args.output.resolve()), RECEIPT=str(args.receipt.resolve()))
        if args.confidence:
            fields["CONFIDENCE_OUTPUT"] = str(args.confidence_output.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
    env.update({PREFIX + k: v for k, v in fields.items()})
    log = (args.log or target.with_suffix(".command.log")).resolve()
    command_record = log.with_suffix(".json")
    if any(p.exists() for p in (log, command_record, target)):
        raise ValueError("new log, command record and result required")
    log.parent.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    command = [str(exe), "--exact", TEST, "--ignored", "--test-threads=1", "--nocapture"]
    started = datetime.now(timezone.utc).isoformat()
    proc = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, check=False)
    raw = proc.stdout + proc.stderr
    with log.open("xb") as f:
        f.write(raw)
    unchanged = (sources() == build_record["sources_after"]
                 and sha(exe) == build_record["test_executable"]["sha256"]
                 and sha(__file__) == build_record["driver_sha256"])
    success = proc.returncode == 0 and b"1 passed; 0 failed" in raw and target.is_file() and unchanged
    evidence = dict(schema="m194f-consumer-command-v1", command=command, interpreter_argv=sys.orig_argv,
                    started_utc=started, ended_utc=datetime.now(timezone.utc).isoformat(),
                    exit_code=proc.returncode, passed=success, log=str(log), log_sha256=sha(log),
                    build_sha256=args.build_sha256, driver_sha256=sha(__file__), sources_unchanged=unchanged,
                    environment=relevant_env(env), xoptions=sys._xoptions, python=sys.version)
    if target.is_file():
        evidence.update(result=str(target.resolve()), result_sha256=sha(target))
    write_new(command_record, evidence)
    print(json.dumps(evidence))
    if not success:
        print(raw.decode("utf-8", "replace"))
    return 0 if success else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    modes = ap.add_subparsers(dest="mode", required=True)
    modes.add_parser("build").add_argument("--build-record", type=Path, required=True)
    for name in ("plan", "render"):
        p = modes.add_parser(name)
        p.add_argument("--build-record", type=Path, required=True)
        p.add_argument("--build-sha256", required=True)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--manifest-sha256", required=True)
        p.add_argument("--cfa-commission", type=Path, required=True)
        p.add_argument("--cfa-commission-sha256", required=True)
        p.add_argument("--plan", type=Path, required=True)
        p.add_argument("--observer", choices=("off", "count", "placebo"), required=True)
        p.add_argument("--confidence", action="store_true")
        p.add_argument("--exposure", type=int, choices=(0, 1), default=0)
        p.add_argument("--log", type=Path)
        if name == "render":
            p.add_argument("--plan-sha256", required=True)
            p.add_argument("--output", type=Path, required=True)
            p.add_argument("--receipt", type=Path, required=True)
            p.add_argument("--confidence-output", type=Path)
    args = ap.parse_args()
    return build(args) if args.mode == "build" else invoke(args)


if __name__ == "__main__":
    raise SystemExit(main())

"""Record exact invocation around the frozen full reader; grants no authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
READER_SHA = "e9745149a30f2754240c2970ce5d1855849679636488efecd125202831432f42"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value, exclusive=False):
    with path.open("x" if exclusive else "w", encoding="utf8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)


def main():
    ap = argparse.ArgumentParser()
    for name in ("bundle", "author-run", "reader-controls", "output", "cache-prefix"):
        ap.add_argument("--" + name, type=Path, required=True)
    for name in ("bundle-sha256", "author-run-sha256", "schema-sha256", "reader-controls-sha256"):
        ap.add_argument("--" + name, required=True)
    args = ap.parse_args()
    reader = HERE / "independent-compare.py"
    args.output = args.output.resolve()
    cache = args.cache_prefix.resolve()
    receipt_path = args.output.with_name(args.output.name + "-invocation.json")
    stdout_path = args.output.with_name(args.output.name + "-stdout.log")
    stderr_path = args.output.with_name(args.output.name + "-stderr.log")
    if any(p.exists() for p in (args.output, cache, receipt_path, stdout_path, stderr_path)):
        raise ValueError("fresh result/cache/log/receipt paths are required")
    if sha(reader) != READER_SHA:
        raise ValueError("externally frozen full reader source differs")
    bindings = {}
    for name, path, digest in (("bundle", args.bundle, args.bundle_sha256),
                               ("author_run", args.author_run, args.author_run_sha256),
                               ("reader_controls", args.reader_controls, args.reader_controls_sha256),
                               ("schema", HERE / "schema.py", args.schema_sha256)):
        if sha(path) != digest:
            raise ValueError("external " + name + " source binding differs before launch")
        bindings[name] = dict(path=str(path.resolve()), sha256=digest, bytes=path.stat().st_size)
    command = [sys.executable, "-X", "utf8", "-X", "pycache_prefix=" + str(cache), str(reader),
               "--bundle", str(args.bundle.resolve()), "--bundle-sha256", args.bundle_sha256,
               "--author-run", str(args.author_run.resolve()), "--author-run-sha256", args.author_run_sha256,
               "--schema-sha256", args.schema_sha256,
               "--reader-controls", str(args.reader_controls.resolve()), "--reader-controls-sha256", args.reader_controls_sha256,
               "--output", str(args.output)]
    env = os.environ.copy()
    thread_env = {k: "2" for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS")}
    env.update(thread_env)
    receipt = dict(schema="m194e-independent-reader-launch-v1", status="LAUNCH_STARTED", launcher_orig_argv=sys.orig_argv,
                   launcher_xoptions=sys._xoptions, executable=sys.executable, python=sys.version, platform=platform.platform(),
                   launcher_sha256=sha(Path(__file__)), reader_sha256=READER_SHA, child_argv=command, cwd=str(REPO),
                   cache_absent_before=True, numerical_thread_environment=thread_env, bindings_before=bindings,
                   started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    write(receipt_path, receipt, exclusive=True)
    started = time.perf_counter()
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            completed = subprocess.run(command, cwd=REPO, env=env, stdout=stdout, stderr=stderr, check=False)
        receipt["exit_code"] = completed.returncode
        receipt["status"] = "CHILD_COMPLETED"
    except Exception as exc:
        receipt["status"] = "LAUNCH_FAILED"
        receipt["error"] = repr(exc)
        receipt["traceback"] = traceback.format_exc()
    receipt["wall_seconds"] = time.perf_counter()-started
    receipt["ended_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    receipt["reader_unchanged"] = sha(reader) == READER_SHA
    receipt["bindings_unchanged"] = all(sha(Path(v["path"])) == v["sha256"] for v in bindings.values())
    receipt["logs"] = {key: dict(path=str(path), bytes=path.stat().st_size, sha256=sha(path))
                       for key, path in (("stdout", stdout_path), ("stderr", stderr_path)) if path.exists()}
    result_path = args.output / "result.json"
    if result_path.exists():
        receipt["child_result"] = dict(path=str(result_path), bytes=result_path.stat().st_size, sha256=sha(result_path),
                                       status=json.loads(result_path.read_text(encoding="utf8"))["status"])
    write(receipt_path, receipt)
    print(json.dumps(dict(status=receipt["status"], exit_code=receipt.get("exit_code"), child_result=receipt.get("child_result"))))
    # Only the unchanged frozen child can create scientific authority.
    return int(receipt.get("exit_code", 1)) if receipt["reader_unchanged"] and receipt["bindings_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Record the exact genuine emitter invocation without changing its frozen source."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
EMITTER_SHA = "fbcdfa2c716f638e9aa8f9cf13ba3024a575feca0ad15d1a67012f51176c82fd"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ("bundle", "float-commission", "output", "cache-prefix"):
        ap.add_argument("--" + key, type=Path, required=True)
    for key in ("bundle-sha256", "trusted-float-sha256"):
        ap.add_argument("--" + key, required=True)
    args = ap.parse_args()
    output, cache = args.output.resolve(), args.cache_prefix.resolve()
    receipt = output.with_name(output.name + "-invocation.json")
    stdout, stderr = (output.with_name(output.name + suffix) for suffix in ("-stdout.log", "-stderr.log"))
    if any(p.exists() for p in (output, cache, receipt, stdout, stderr)):
        raise ValueError("new output, cache, receipt and log paths required")
    emitter = HERE / "emit-cfa.py"
    bindings = {
        "emitter": (emitter, EMITTER_SHA),
        "bundle": (args.bundle.resolve(), args.bundle_sha256),
        "float_commission": (args.float_commission.resolve(), args.trusted_float_sha256),
    }
    for name, (path, digest) in bindings.items():
        if sha(path) != digest:
            raise ValueError("external input changed: " + name)
    command = [sys.executable, "-X", "utf8", "-X", "pycache_prefix=" + str(cache), str(emitter),
               "--bundle", str(args.bundle.resolve()), "--float-commission", str(args.float_commission.resolve()),
               "--trusted-float-sha256", args.trusted_float_sha256, "--output", str(output)]
    record = dict(schema="m194e-emission-launch-v1", status="STARTED", launcher_argv=sys.orig_argv,
                  launcher_sha256=sha(__file__), executable=sys.executable, python=sys.version,
                  xoptions=sys._xoptions, cwd=str(ROOT), child_argv=command, cache_absent_before=True,
                  started_utc=datetime.now(timezone.utc).isoformat(),
                  inputs={k: dict(path=str(p), sha256=h, bytes=p.stat().st_size) for k, (p, h) in bindings.items()})
    with receipt.open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    try:
        with stdout.open("xb") as out, stderr.open("xb") as err:
            proc = subprocess.run(command, cwd=ROOT, stdout=out, stderr=err, check=False)
        record.update(status="CHILD_COMPLETED", exit_code=proc.returncode)
    except Exception as exc:
        record.update(status="LAUNCH_FAILED", error=repr(exc), traceback=traceback.format_exc())
    record.update(ended_utc=datetime.now(timezone.utc).isoformat(),
                  inputs_unchanged=all(sha(p) == h for p, h in bindings.values()),
                  logs={k: dict(path=str(p), sha256=sha(p), bytes=p.stat().st_size)
                        for k, p in (("stdout", stdout), ("stderr", stderr)) if p.exists()})
    for name in ("emission-run.json", "manifest.json"):
        path = output / name
        if path.exists():
            record[name] = dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size)
    receipt.write_text(json.dumps(record, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(record))
    return record.get("exit_code", 1) if record["inputs_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

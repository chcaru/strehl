"""Metadata-only constructor; source/command freeze required before execution.

No subject imports, RAW/TIFF opens, subprocesses, or probe execution. The saved
snapshot reference is copied from authenticated native1 evidence, never hashed.
"""
import argparse
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat

ROOT = Path(__file__).resolve().parents[3]
HERE = ROOT / "experiments/m193c-output-grid"
DEST = HERE / "active-domain-probe-release-1.json"
RESERVE = HERE / "work/active-domain-probe-1-reservation.json"
OUTPUT = HERE / "active-domain-probe-1"
MIB = 1 << 20
PINS = {
    "native-derivative-release-1.json": "37f4f8ceb590dbff386f9a7a773d2f99381e8be481145f2dc9e0ec6896928dc2",
    "native-derivative-1/result.json": "4299877897694e655ef04f88001e6406058c1b2d0efddded6d525510fbc9dfe0",
    "independent-native-derivative-1-read.md": "82f9eea0f293b29454b6555dad01e49654b58ee42daa1e6d9ef73f0bb4f4d91f",
    "native-derivative-1/frame-00/independent/result.json": "754485f20e99c0511465da98c228554229c0ff8a6c6a187e8ae9f38443a2a2f4",
    "work/native-derivative-1-console.txt": "ca5f9f117157410846d788d424aa878524296851a5f2100b0b097d89c645c990",
    "work/native-derivative-1-outer.json": "45e398ad4bf9fe51d0095e6b7be8f4132e53828866a51193cabcf644f5e8ec13",
    "work/native-derivative-1-exit.txt": "f1b2f662800122bed0ff255693df89c4487fbdcf453d3524a42d4ec20c3d9c04",
}


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def path(value):
    p = Path(value)
    p = p if p.is_absolute() else ROOT / p
    p = p.resolve()
    need(p.is_relative_to(ROOT) and p.suffix.lower() not in (".arw", ".raw", ".tif", ".tiff", ".npy"), "metadata/source path only")
    return p


def binding(value, expected=None):
    p = path(value); before = p.stat(follow_symlinks=False)
    need(stat.S_ISREG(before.st_mode) and not before.st_file_attributes & 0x400 and before.st_size <= 64 * MIB, "ordinary bounded file")
    digest = hashlib.sha256(); size = 0
    with p.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        need((opened.st_dev, opened.st_ino) == (before.st_dev, before.st_ino), "opened identity")
        while chunk := stream.read(MIB):
            size += len(chunk); need(size <= 64 * MIB, "file growth bound"); digest.update(chunk)
    after = p.stat(follow_symlinks=False)
    need(all(getattr(before, k) == getattr(after, k) for k in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_file_attributes")) and size == before.st_size, "file changed")
    ref = dict(path=p.relative_to(ROOT).as_posix(), sha256=digest.hexdigest(), bytes=size)
    if expected is not None:
        need(type(expected) is str and re.fullmatch("[0-9a-f]{64}", expected) and ref["sha256"] == expected, "external pin")
    return ref


def checked(ref):
    need(type(ref) is dict and set(ref) == {"path", "sha256", "bytes"} and type(ref["bytes"]) is int, "closed typed FileRef")
    got = binding(ref["path"], ref["sha256"]); need(got["bytes"] == ref["bytes"], "bound extent"); return got


def read(ref, text_json=False):
    p = path(ref["path"]); need((p.suffix == ".json" or text_json and p.suffix == ".txt") and ref["bytes"] <= 4 * MIB, "bounded JSON")
    with p.open("rb") as stream: raw = stream.read(4 * MIB + 1)
    need(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "same-byte JSON")
    def pairs(rows):
        out = {}
        for k, v in rows: need(k not in out, "duplicate JSON key"); out[k] = v
        return out
    def number(s):
        n = float(s); need(math.isfinite(n), "finite JSON number"); return n
    return json.loads(raw, object_pairs_hook=pairs, parse_float=number, parse_constant=lambda s: need(False, s))


def payload(value):
    return (json.dumps(value, indent=2, allow_nan=False) + "\n").encode("utf8")


def write_new(p, raw):
    with p.open("xb") as stream:
        need(stream.write(raw) == len(raw), "complete metadata write"); stream.flush(); os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    for key in ("probe", "spec", "review"): parser.add_argument("--" + key + "-sha256", required=True)
    args = parser.parse_args()
    need(os.name == "nt" and Path.cwd().resolve() == ROOT and not any(p.exists() for p in (DEST, RESERVE, OUTPUT)), "Windows ROOT/fresh metadata and output")
    inputs = {}
    def add(ref):
        ref = checked(ref); need(inputs.setdefault(ref["path"], ref) == ref, "input collision"); return ref
    refs = {name: add(binding(HERE / name, sha)) for name, sha in PINS.items()}
    native = read(refs["native-derivative-release-1.json"]); failed = read(refs["native-derivative-1/result.json"])
    need(native["schema"] == "m193c-native-derivative-release-v1" and len(native["source_bindings"]) == 139, "original native source closure")
    need(failed["status"] == "REFUSED" and failed["attempted_original_index"] == 0 and failed["current_stage"] == "independent-child" and len(failed["rows"]) == 1 and failed["unvisited"] == [13, 26, 39, 52, 65, 78, 91, 104] and not failed["finalization_errors"], "actual first native refusal")
    need(failed["sources_before"] == failed["sources_after"] == native["source_bindings"] and failed["inputs_before"] == failed["inputs_after"] == native["inputs"], "native source/input stability")
    for ref in native["inputs"]: add(ref)
    row = failed["rows"][0]; primary = add(row["primary_receipt"]); request = read(add(row["read_request"]))
    independent = read(refs["native-derivative-1/frame-00/independent/result.json"])
    need(independent["status"] == "REFUSED" and "ValueError: independent active dimensions" in independent["error"] and not independent["finalization_errors"] and checked(independent["request"]) == checked(row["read_request"]), "actual independent cause/request")
    need(read(primary)["snapshot"] == request["snapshot"] == row["snapshot"] == independent["snapshot"] and row["snapshot_deleted"] is False, "retained snapshot references agree")
    snapshot = dict(row["snapshot"]); need(snapshot["path"] == str(HERE / "native-derivative-1/frame-00/DSC00016.ARW") and snapshot["bytes"] == 39030784 and snapshot["sha256"] == "35ccc60a2cadbcdc999fb6765a326f5baaa298776fb951d12287e05c5892ed36", "fixed saved snapshot authority")
    snapshot["path"] = "experiments/m193c-output-grid/native-derivative-1/frame-00/DSC00016.ARW"
    metadata = ["native-derivative-release-1.json", "independent-native-release-1-review.md", "independent-native-derivative-1-read.md", "work/native-derivative-1-console.txt", "work/native-derivative-1-exit.txt", "work/native-derivative-1-outer.json", "active-domain-probe.py", "active-domain-probe-preregister.md", "independent-active-domain-probe-source-review.md", "work/prepare-active-domain-probe-1.py"]
    pins = {"active-domain-probe.py": args.probe_sha256, "active-domain-probe-preregister.md": args.spec_sha256, "independent-active-domain-probe-source-review.md": args.review_sha256}
    inventory = [add(binding(HERE / name, pins.get(name))) for name in metadata]
    outer = read(refs["work/native-derivative-1-outer.json"]); console = read(refs["work/native-derivative-1-console.txt"], True)
    need(outer["exit_code"] == 1 and outer["dependency_error"] is None and outer["command"] == failed["invocation"] and outer["release_sha256"] == refs["native-derivative-release-1.json"]["sha256"] and console["status"] == "REFUSED" and console["error"] == failed["error"] and console["finalization_errors"] == [], "observed refusal, not new success")
    need(console["work_through_final_checks"]["cpu_seconds"] == 34.984375 and Decimal(str(outer["elapsed_wall_seconds"])) + Decimal(str(native["prior_work"]["wall_seconds"])) == Decimal("29.3349305") and console["work_through_final_checks"]["file_bytes"] == 238504151 and console["work_through_final_checks"]["metadata_bytes"] == 1675100, "actual carried work")
    adjacent = add(binding(HERE / "work/native-adjacent-dependencies-1.json")); need(outer["dependency_before"] == outer["dependency_after"] == read(adjacent)["files"], "actual adjacent endpoint observations")
    sources = dict(native["source_bindings"])
    for name in ("active-domain-probe.py", "active-domain-probe-preregister.md", "work/prepare-active-domain-probe-1.py"):
        ref = inputs[(HERE / name).relative_to(ROOT).as_posix()]; need(ref["path"] not in sources, "new source only"); sources[ref["path"]] = {k: ref[k] for k in ("sha256", "bytes")}
    reserve = dict(schema="m193c-probe-preparation-reservation-v1", files=inventory, observed_bytes=sum(ref["bytes"] for ref in inventory), release_upper_bytes=65536, reserved_bytes=MIB, scope="extra native/probe metadata reservation; no refund or write-I/O claim")
    reserve_raw = payload(reserve); need(reserve["observed_bytes"] + len(reserve_raw) + 65536 < MIB, "fixed metadata population fits reserve")
    write_new(RESERVE, reserve_raw); add(binding(RESERVE))
    py = read(add(native["reader"]["runtime"]))["python_executable"]["path"]
    def command(mode): return [py, "-B", "-X", "faulthandler", "-X", "pycache_prefix=" + str(OUTPUT / ("cache-" + mode)), str(HERE / "active-domain-probe.py"), "--release", str(DEST), "--release-sha256", "ACTUAL_RELEASE_SHA256"] + (["--worker"] if mode == "worker" else [])
    release = dict(schema="m193c-active-domain-probe-release-v1", sources=sources, inputs=list(inputs.values()), runtime=native["reader"]["runtime"], adjacent=adjacent, primary=primary, snapshot=snapshot, prior_work=dict(cpu_seconds=34.984375, wall_seconds=29.3349305, file_bytes=238504151+MIB, metadata_bytes=1675100+MIB), commands={mode: command(mode) for mode in ("parent", "worker")})
    for name, ref in sources.items(): checked(dict(path=name, **ref))
    for ref in inputs.values(): checked(ref)
    raw = payload(release); need(len(raw) <= 65536 and not OUTPUT.exists(), "release reservation/fresh output"); write_new(DEST, raw)
    print(json.dumps(dict(status="PREPARED_METADATA_ONLY", release=binding(DEST), reservation=binding(RESERVE), sources=len(sources), inputs=len(inputs)), indent=2), flush=True)


if __name__ == "__main__":
    main()

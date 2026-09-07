"""Authorized development RAW before/after byte lineage; no benchmark claims.

Uses exactly the existing coffee-bean first-20 registry input and sidecar.
Normalizes only the compiled Software stamp to the archived baseline value;
records actual prospective source hashes separately. No capture writes.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
import uuid

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
STACK = Path("D:/personal/macro/coffee-bean")
STAMP = "e93f0bde695961d53cbd66587a060a41552b4a63"
OLD = ROOT / "experiments/M192-m12-certify/recovery-20260906-163253/work/builds/measured/bin/strehl.exe"
OLD_HASH = "89482acd60c4e39a22f763b2e722754804430e955546ea96f7ae7ca4c7ea1032"
SIDECAR = ROOT / "crates/strehl-cli/tests/data/coffee-bean-20.warpmap.txt"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def manifest(paths):
    return [dict(path=str(p), bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns,
                 sha256=sha(p)) for p in paths]


def inventory():
    # pathlib enumeration includes hidden/system entries, unlike the default
    # Get-ChildItem behavior warned against by AGENTS rule 14.
    return [dict(name=p.name, bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns,
                 directory=p.is_dir()) for p in sorted(STACK.iterdir())]


def env_base(work):
    env = {k: v for k, v in os.environ.items() if not k.startswith("STREHL_")}
    for k in ["RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS"]:
        env.pop(k, None)
    env.update(STREHL_DEFECT="off", STREHL_PYRAMID_WORKERS="2", RAYON_NUM_THREADS="2",
               STREHL_CACHE_DIR=str(work / "cache"), TEMP=str(work / "temp"), TMP=str(work / "temp"))
    return env


def invoke(cmd, env, log):
    p = subprocess.run([str(a) for a in cmd], cwd=ROOT, env=env, capture_output=True)
    log.write_bytes(p.stdout + p.stderr)
    text = (p.stdout + p.stderr).decode("utf-8", "replace")
    record = dict(command=[str(a) for a in cmd], exit_code=p.returncode,
                  log=str(log.relative_to(ROOT)), log_sha256=sha(log))
    print(json.dumps(record), flush=True)
    if p.returncode:
        raise RuntimeError(f"command failed: {log}")
    return record, text


def main():
    work = HERE / "work" / ("independent-native-" + uuid.uuid4().hex[:12])
    for p in [work, work / "cache", work / "temp"]:
        p.mkdir(parents=True, exist_ok=False)
    evidence = dict(schema="m194-independent-native-v1", started_utc=datetime.now(timezone.utc).isoformat(),
                    work=str(work.relative_to(ROOT)), pass_=False,
                    normalized_software_stamp=STAMP,
                    stamp_scope="Comparison control only; prospective actual source separately hashed, not claimed to be baseline commit.")
    record_path = HERE / "independent-native.json"
    selected = sorted(p for p in STACK.iterdir() if p.suffix.lower() == ".arw")[:20]
    assert [p.name for p in selected] == [f"DSC{i:05d}.ARW" for i in range(16,36)]
    assert sha(OLD) == OLD_HASH
    evidence["input_before"] = manifest(selected)
    evidence["directory_before"] = inventory()
    tracked = subprocess.check_output(["git", "ls-files", "crates", "Cargo.toml", "Cargo.lock", "rust-toolchain.toml"], cwd=ROOT, text=True).splitlines()
    source_paths = [ROOT / p for p in tracked if (ROOT / p).is_file()]
    source_paths += [ROOT / "crates/strehl-cli/src/merge_cmd/production-truth.rs", HERE / "independent-controls.rs"]
    evidence["source_before"] = manifest(source_paths)
    evidence["actual_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    diff = subprocess.check_output(["git", "diff", STAMP, "--", "crates"], cwd=ROOT)
    (HERE / "independent-native-source.diff").write_bytes(diff)
    evidence["source_diff_sha256"] = sha(HERE / "independent-native-source.diff")
    sidecar_copy = work / "coffee-bean-20.warpmap.txt"
    shutil.copyfile(SIDECAR, sidecar_copy)
    evidence["sidecar_before"] = manifest([SIDECAR, sidecar_copy])
    evidence["baseline_binary"] = manifest([OLD])[0]
    env = env_base(work)
    # Record every named render setting found in our own project sources,
    # explicitly distinguishing cleared values from inherited settings.
    known_keys = set()
    for p in (ROOT / "crates").rglob("*.rs"):
        known_keys.update(re.findall(r"\bSTREHL_[A-Z0-9_]+\b", p.read_text(encoding="utf-8")))
    evidence["environment_policy"] = "all inherited STREHL_* removed; RUSTFLAGS/CARGO_ENCODED_RUSTFLAGS removed; overrides explicitly recorded"
    try:
        build_env = dict(env, STREHL_BUILD_ID=STAMP)
        build, text = invoke(["cargo", "build", "--release", "-p", "strehl-cli", "--bin", "strehl",
                              "--target-dir", "target/m194-independent-release"], build_env, HERE / "independent-native-build.log")
        build["rebuilt_cli"] = "Compiling strehl-cli" in text
        build["environment"] = {k: build_env.get(k) for k in sorted(known_keys)}
        assert build["rebuilt_cli"], "missing rebuild proof"
        evidence["build"] = build
        new = ROOT / "target/m194-independent-release/release/strehl.exe"
        evidence["prospective_binary"] = manifest([new])[0]
        evidence["versions"] = {}
        for label, binary in [("before",OLD),("after",new)]:
            _, version = invoke([binary,"--version"],env,work / f"{label}-version.log")
            evidence["versions"][label] = version.strip()
        assert evidence["versions"]["before"] == evidence["versions"]["after"]
        records = []
        for alignment in ["off","sidecar"]:
            pair = []
            for label,binary in [("before",OLD),("after",new)]:
                run_env = dict(env)
                if alignment == "off":
                    run_env["STREHL_ALIGN"] = "0"
                else:
                    run_env["STREHL_WARPMAP"] = str(sidecar_copy)
                output = work / f"{alignment}-{label}.tif"
                command = [binary,"stack",STACK,"--merge","pyramid","--limit","20",
                           "--pyramid-gate","2.0","--out",output]
                record,text = invoke(command,run_env,HERE / f"independent-native-{alignment}-{label}.log")
                record.update(alignment=alignment, arm=label,
                              environment={k: run_env.get(k) for k in sorted(known_keys)},
                              rayon_num_threads=run_env["RAYON_NUM_THREADS"],
                              temp=run_env["TEMP"],tmp=run_env["TMP"],
                              output=manifest([output])[0])
                assert "folded          : 20 / 20 frames" in text
                assert "ON (sidecar-override)" in text if alignment == "sidecar" else "alignment       : OFF" in text
                import tifffile
                with tifffile.TiffFile(output) as t:
                    page=t.pages[0]
                    record["tiff"] = dict(shape=list(page.shape), dtype=str(page.dtype),
                                          software=page.tags["Software"].value,
                                          pixels_sha256=hashlib.sha256(page.asarray().tobytes()).hexdigest())
                assert record["tiff"]["shape"] == [2344,3516,3]
                assert record["tiff"]["dtype"] == "uint16"
                pair.append(record)
                records.append(record)
            assert pair[0]["output"]["sha256"] == pair[1]["output"]["sha256"], f"{alignment} byte lineage changed"
            assert pair[0]["tiff"] == pair[1]["tiff"]
        evidence["runs"] = records
        evidence["pass_"] = True
    except Exception as e:
        evidence["error"] = repr(e)
        raise
    finally:
        evidence["input_after"] = manifest(selected)
        evidence["directory_after"] = inventory()
        evidence["source_after"] = manifest(source_paths)
        evidence["sidecar_after"] = manifest([SIDECAR,sidecar_copy])
        evidence["inputs_unchanged"] = evidence["input_before"] == evidence["input_after"]
        evidence["directory_unchanged"] = evidence["directory_before"] == evidence["directory_after"]
        # Another task can touch source mtimes without changing bytes; content
        # binding is the relevant build consistency assertion.
        evidence["source_content_unchanged"] = [(p["path"],p["sha256"]) for p in evidence["source_before"]] == [(p["path"],p["sha256"]) for p in evidence["source_after"]]
        evidence["sidecar_unchanged"] = evidence["sidecar_before"] == evidence["sidecar_after"]
        evidence["pass_"] &= all(evidence[k] for k in ["inputs_unchanged","directory_unchanged","source_content_unchanged","sidecar_unchanged"])
        record_path.write_text(json.dumps(evidence,indent=2) + "\n")
    return 0 if evidence["pass_"] else 1


if __name__ == "__main__":
    sys.exit(main())

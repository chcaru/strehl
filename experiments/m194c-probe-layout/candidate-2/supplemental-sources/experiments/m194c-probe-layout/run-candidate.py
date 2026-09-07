"""Reuse the frozen M194b forty-output runner with supplemental source bindings."""
from __future__ import annotations

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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE = ROOT / "experiments/m194b-known-scene"
GATE = ROOT / "crates/strehl-cli/src/merge_cmd/gatefloor.rs"


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, value, *, new=False):
    with Path(path).open("x" if new else "w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def supplemental():
    paths = list(HERE.glob("*.rs")) + [HERE / name for name in
             ("run-candidate.py", "compare-candidate.py", "comparison-preregister.md",
              "preregister.md", "legacy-source.json")]
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(paths)}


def check_supplemental(expected):
    if supplemental() != expected:
        raise ValueError("supplemental source set or bytes changed")
    # Every M194c Rust include, including the frozen sampler nested in a test,
    # must be in the attested set. Resolve relative to the including file.
    reached, pending = set(), [GATE]
    while pending:
        source = pending.pop()
        text = source.read_text(encoding="utf-8")
        for relative in re.findall(r'#\[path\s*=\s*"([^"]+)"\]', text):
            p = (source.parent / relative).resolve()
            if p.is_relative_to(HERE) and p not in reached:
                reached.add(p)
                pending.append(p)
        # This repository's external test includes use the explicit
        # CARGO_MANIFEST_DIR concat form. Match that form, not prose mentions.
        for relative in re.findall(
                r'include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)', text):
            p = (ROOT / "crates/strehl-cli" / relative.lstrip("/")).resolve()
            if p.is_relative_to(HERE) and p not in reached:
                reached.add(p)
                pending.append(p)
    attested_rs = {ROOT / p for p in expected if p.endswith(".rs")}
    if reached != attested_rs or not reached:
        raise ValueError(f"Rust include set differs: reached={reached}, attested={attested_rs}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    prior = json.loads((BASE / "baseline-1/run-index.json").read_text(encoding="utf-8"))
    fixed = {name: sha(BASE / name) for name in
             ("consumer-run.py", "run-baseline.py", "score.py", "score-benchmark.py",
              "producer-output-1/producer-result.json", "producer-commission-1/commission.json")}
    for name, h in fixed.items():
        committed = subprocess.check_output(["git", "show", "444eb759:" +
                            (BASE / name).relative_to(ROOT).as_posix()], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != h:
            raise ValueError(f"frozen M194b source changed: {name}")
    extra = supplemental()
    check_supplemental(extra)
    for path, digest in extra.items():
        dest = out / "supplemental-sources" / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, dest)
        if sha(dest) != digest:
            raise ValueError("source snapshot changed")
    journal = dict(schema="m194c-candidate-controller-v1", status="building",
                   command=sys.argv, started_utc=datetime.now(timezone.utc).isoformat(),
                   baseline_commit="444eb759be0358cda25e97d4375f977a039efe6a",
                   baseline_index_sha256=sha(BASE / "baseline-1/run-index.json"),
                   frozen_m194b_files=fixed, supplemental_before=extra,
                   supplemental_snapshots_root=str(out / "supplemental-sources"),
                   commands=[])
    write(out / "controller.json", journal, new=True)

    def invoke(command, name):
        check_supplemental(extra)
        if {p: sha(BASE / p) for p in fixed} != fixed:
            raise ValueError("frozen M194b files changed")
        log = out / (name + ".log")
        with log.open("xb") as f:
            p = subprocess.run(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        journal["commands"].append(dict(command=command, exit_code=p.returncode,
                                       log=str(log), log_sha256=sha(log)))
        write(out / "controller.json", journal)
        check_supplemental(extra)
        if p.returncode != 0:
            raise RuntimeError(f"{name} exit {p.returncode}; retain {log}")

    try:
        build = out / "build.json"
        invoke([sys.executable, "-X", "utf8", str(BASE / "consumer-run.py"),
                "build", "--build-record", str(build)], "build-controller")
        journal["build_sha256"] = sha(build)
        build_record = json.loads(build.read_text(encoding="utf-8"))
        baseline_build = json.loads(Path(prior["build_record"]["path"]).read_text(encoding="utf-8"))
        changed = [p for p in set(build_record["sources_after"]) | set(baseline_build["sources_after"])
                   if build_record["sources_after"].get(p) != baseline_build["sources_after"].get(p)]
        if changed != [GATE.relative_to(ROOT).as_posix()]:
            raise ValueError(f"product source delta is not solely gatefloor.rs: {changed}")
        journal["changed_compiler_inputs"] = changed
        journal["status"] = "rendering"
        write(out / "controller.json", journal)
        command = [sys.executable, "-X", "utf8", str(BASE / "run-baseline.py"),
                   "--build-record", str(build), "--build-record-sha", sha(build)]
        for flag, key in (("producer-result", "producer_result"),
                          ("producer-commission", "producer_commission")):
            command += ["--" + flag, prior[key]["path"], "--" + flag + "-sha", prior[key]["sha256"]]
        command += ["--out", str(out / "run")]
        invoke(command, "render-controller")
        index = out / "run/run-index.json"
        journal["index_sha256"] = sha(index)
        invoke([sys.executable, "-X", "utf8", str(BASE / "score-benchmark.py"),
                "--index", str(index), "--expected-index-sha", sha(index),
                "--out", str(out / "score.json")], "score-controller")
        journal.update(status="complete", score_sha256=sha(out / "score.json"),
                       supplemental_after=supplemental(),
                       completed_utc=datetime.now(timezone.utc).isoformat())
        write(out / "controller.json", journal)
        print(json.dumps(dict(status="complete", controller_sha256=sha(out / "controller.json"),
                              index_sha256=sha(index))))
    except Exception as exc:
        journal.update(status="failed", failure=f"{type(exc).__name__}: {exc}",
                       completed_utc=datetime.now(timezone.utc).isoformat())
        write(out / "controller.json", journal)
        raise


if __name__ == "__main__":
    main()

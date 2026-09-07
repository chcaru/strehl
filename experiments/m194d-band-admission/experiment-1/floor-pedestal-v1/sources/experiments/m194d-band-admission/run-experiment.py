"""Build one explicit-mode consumer, render both fixed matrices, bind all stages."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FIXED = ROOT / "experiments/m194b-known-scene"
BASELINE = ROOT / "experiments/m194c-probe-layout/candidate-2/run/run-index.json"
BASELINE_SHA = "71b2ba05ddc23fc78640aa1f9b53ea3b12ddac0f1fa955d1ee8cdf8428fda6ab"
BASELINE_COMMIT = "04128e041dabc0bdb86c64526cd8155dd0a0fd07"
PREREG_COMMIT = "5f55c9ee7dc15d47e04ded53cd11eea929e28fc2"
MODES = ("hard-floor", "floor-pedestal-v1")
ADAPTERS = ("consumer-run.py", "run-matrix.py", "score-benchmark.py",
            "run-experiment.py", "compare-experiment.py", "sparse-error.py")
PREREGS = ("implementation-plan.md", "implementation-preregister.md",
           "comparison-preregister.md", "adapter-lineage.json")
PRODUCT_CHANGES = {
    "crates/strehl-core/src/pyramid.rs",
    "crates/strehl-cli/src/merge_cmd.rs",
    "crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs",
}
NEW_PRODUCT = "crates/strehl-cli/src/merge_cmd/band-admission-benchmark.rs"


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write(path, value):
    with Path(path).open("w", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixed_sources():
    result = {str((HERE / name).relative_to(ROOT).as_posix()): sha(HERE / name)
              for name in ADAPTERS + PREREGS}
    for name in ("implementation-plan.md", "implementation-preregister.md", "comparison-preregister.md"):
        path = HERE / name
        committed = subprocess.check_output(["git", "show", PREREG_COMMIT + ":" + path.relative_to(ROOT).as_posix()], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != sha(path):
            raise ValueError("preregistration changed after its prospective commit")
    for name in ("compare-candidate.py", "run-candidate.py"):
        path = ROOT / "experiments/m194c-probe-layout" / name
        committed = subprocess.check_output(["git", "show", BASELINE_COMMIT + ":" + path.relative_to(ROOT).as_posix()], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != sha(path):
            raise ValueError("reused M194c comparison source changed")
        result[path.relative_to(ROOT).as_posix()] = sha(path)
    return result


def frozen_artifacts():
    result = {}
    for name in ("consumer-run.py", "run-baseline.py", "score.py", "score-benchmark.py",
                 "producer-output-1/producer-result.json", "producer-commission-1/commission.json"):
        path = FIXED / name
        committed = subprocess.check_output(["git", "show", "444eb759:" + path.relative_to(ROOT).as_posix()], cwd=ROOT)
        if hashlib.sha256(committed).hexdigest() != sha(path):
            raise ValueError(f"frozen M194b artifact changed: {path}")
        result[path.relative_to(ROOT).as_posix()] = sha(path)
    return result


def check_sources(expected):
    for path, digest in expected.items():
        if sha(ROOT / path) != digest:
            raise ValueError(f"frozen source changed: {path}")


def validate_external_includes(source_map):
    """Check this tree's explicit include forms using the including crate root.

    This is an attestation-set check, not a general Rust/cfg dependency parser.
    Core test includes are bound even though CLI dependency builds omit cfg(test).
    """
    pending = [(ROOT / path, ROOT / "crates" / Path(path).parts[1])
               for path in source_map if path.startswith("crates/") and path.endswith(".rs")]
    seen, reached = set(), set()
    while pending:
        source, crate = pending.pop()
        if (source, crate) in seen:
            continue
        seen.add((source, crate))
        text = source.read_text(encoding="utf-8")
        relatives = re.findall(
            r'^\s*include!\(concat!\(\s*env!\("CARGO_MANIFEST_DIR"\),\s*"([^"]+)"\s*\)\)',
            text, re.MULTILINE)
        targets = [(crate / relative.lstrip("/")).resolve() for relative in relatives]
        targets += [(source.parent / relative).resolve() for relative in
                    re.findall(r'^\s*#\[path\s*=\s*"([^"]+)"\]', text, re.MULTILINE)]
        for target in targets:
            if not target.is_relative_to(ROOT):
                raise ValueError("included source escaped project")
            relative = target.relative_to(ROOT).as_posix()
            if relative not in source_map:
                raise ValueError(f"unbound included Rust source: {relative}")
            if relative.startswith("experiments/"):
                reached.add(relative)
            pending.append((target, crate))
    attested = {p for p in source_map if p.startswith("experiments/") and p.endswith(".rs")}
    if reached != attested:
        raise ValueError(f"external Rust source set differs: missing={reached-attested}, extra={attested-reached}")


def source_delta(current, baseline):
    changed = {p for p in current.keys() & baseline.keys() if current[p] != baseline[p]}
    removed = baseline.keys() - current.keys()
    added = current.keys() - baseline.keys()
    if changed != PRODUCT_CHANGES or removed or NEW_PRODUCT not in added:
        raise ValueError(f"unregistered source delta: changed={changed}, removed={removed}, added={added}")
    allowed_extra = {NEW_PRODUCT}
    allowed_extra.update(p.relative_to(ROOT).as_posix()
                         for directory in (HERE, ROOT / "experiments/m194c-probe-layout")
                         for p in directory.glob("*.rs"))
    if not added <= allowed_extra:
        raise ValueError(f"unexpected new source bindings: {added - allowed_extra}")
    return dict(changed=sorted(changed), added=sorted(added), removed=sorted(removed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    if sha(BASELINE) != BASELINE_SHA:
        raise ValueError("M194c baseline index changed")
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    build_ref = baseline["build_record"]
    if sha(build_ref["path"]) != build_ref["sha256"]:
        raise ValueError("M194c baseline build changed")
    baseline_build = json.loads(Path(build_ref["path"]).read_text(encoding="utf-8"))
    fixed = frozen_artifacts()
    consumer = load_module("m194d_consumer", HERE / "consumer-run.py")
    validate_external_includes(consumer.sources())
    sources = consumer.sources() | fixed_sources() | fixed
    for path, digest in sources.items():
        snapshot = out / "sources" / path
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, snapshot)
        if sha(snapshot) != digest:
            raise ValueError("source changed during snapshot")
    journal = dict(schema="m194d-experiment-controller-v1", status="building",
                   started_utc=datetime.now(timezone.utc).isoformat(), command=sys.argv,
                   baseline_commit=BASELINE_COMMIT,
                   preregistration_commit=PREREG_COMMIT,
                   baseline_index=dict(path=str(BASELINE), sha256=BASELINE_SHA),
                   frozen_m194b=fixed, sources_before=sources,
                   source_snapshots_root=str(out / "sources"), commands=[], modes={})
    controller = out / "controller.json"
    write(controller, journal)

    def invoke(argv, label):
        check_sources(sources)
        log = out / (label + ".log")
        with log.open("xb") as f:
            child = subprocess.run(argv, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
        journal["commands"].append(dict(command=argv, exit_code=child.returncode,
                                        log=str(log), log_sha256=sha(log)))
        write(controller, journal)
        check_sources(sources)
        if child.returncode:
            raise RuntimeError(f"{label} failed with exit {child.returncode}")

    try:
        build = out / "build.json"
        invoke([sys.executable, "-X", "utf8", str(HERE / "consumer-run.py"),
                "build", "--build-record", str(build)], "build-controller")
        build_record = json.loads(build.read_text(encoding="utf-8"))
        journal["build_record"] = dict(path=str(build), sha256=sha(build))
        journal["source_delta"] = source_delta(build_record["sources_after"], baseline_build["sources_after"])
        journal["status"] = "rendering"
        write(controller, journal)
        for mode in MODES:
            argv = [sys.executable, "-X", "utf8", str(HERE / "run-matrix.py"),
                    "--admission", mode, "--build-record", str(build), "--build-record-sha", sha(build)]
            for flag, key in (("producer-result", "producer_result"), ("producer-commission", "producer_commission")):
                argv += ["--" + flag, baseline[key]["path"], "--" + flag + "-sha", baseline[key]["sha256"]]
            mode_out = out / mode
            argv += ["--out", str(mode_out)]
            invoke(argv, mode + "-render-controller")
            index = mode_out / "run-index.json"
            score = out / (mode + "-score.json")
            invoke([sys.executable, "-X", "utf8", str(HERE / "score-benchmark.py"),
                    "--index", str(index), "--expected-index-sha", sha(index),
                    "--out", str(score)], mode + "-score-controller")
            journal["modes"][mode] = dict(index=dict(path=str(index), sha256=sha(index)),
                                         score=dict(path=str(score), sha256=sha(score)))
            write(controller, journal)
        check_sources(sources)
        journal.update(status="complete", sources_after={p: sha(ROOT / p) for p in sources},
                       completed_utc=datetime.now(timezone.utc).isoformat())
        write(controller, journal)
        print(json.dumps(dict(status="complete", outputs=80, controller=str(controller), sha256=sha(controller))))
    except Exception as exc:
        journal.update(status="failed", failure=f"{type(exc).__name__}: {exc}",
                       completed_utc=datetime.now(timezone.utc).isoformat())
        write(controller, journal)
        raise


if __name__ == "__main__":
    main()

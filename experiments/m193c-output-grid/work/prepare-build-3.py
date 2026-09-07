"""Freeze a fresh build against the reviewed and commissioned drain helper."""
import ast
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"

def binding(path):
    raw = path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def ref(path):
    return dict(path=path.relative_to(root).as_posix(), **binding(path))

release = json.loads((here / "bridge-build-release-2.json").read_bytes())
changed_sources = set()
for name in release["source_bindings"]:
    current = binding(root / name)
    if current != release["source_bindings"][name]:
        changed_sources.add(name)
    release["source_bindings"][name] = current
assert changed_sources == {"experiments/m193c-output-grid/" + name for name in ("bounded-process.py", "bridge-build.py")}
release["inputs"] += [ref(here / name) for name in (
    "controller-amendment-3.md", "independent-controller-amendment-3-review.md",
    "controller-controls-4/result.json", "controller-controls-4-independent-read.md",
    "build-drain-repair-review.md", "bridge-build-2/result.json",
)]
control_bytes = (here / "controller-controls-4/result.json").read_bytes()
control_ref = next(row for row in release["inputs"] if row["path"] == "experiments/m193c-output-grid/controller-controls-4/result.json")
assert {k: control_ref[k] for k in ("sha256", "bytes")} == dict(sha256=hashlib.sha256(control_bytes).hexdigest(), bytes=len(control_bytes))
control = json.loads(control_bytes)
assert control["schema"] == "m193c-controller-controls-v1" and control["status"] == "PASS_OWNED_PROCESS_CONTROLS_ONLY"
assert [row["mode"] for row in control["cases"]] == [
    "valid", "nonzero", "exact-log", "overflow-log", "timeout", "nested-timeout", "memory-allowed", "memory",
    "late-log-binding", "changed-input", "restored", "drain-finish", "drain-persist", "drain-restored"]
assert all(row["passed"] is True and row["actual"]["terminal_job_accounting"] is True
           and row["actual"]["job_accounting"]["active_processes"] == 0 for row in control["cases"])
assert all(type(row["index"]) is int and row["index"] == index for index, row in enumerate(control["cases"]))
assert control["error"] is None and control["finalization_errors"] == []
expected_control_sources = {"experiments/m193c-output-grid/" + name for name in (
    "controller-controls.py", "controller-child.py", "bounded-process.py")}
expected_control_sources.add("experiments/m12-scorecard/m12-harness.py")
assert set(control["sources_before"]) == expected_control_sources
assert control["sources_before"] == control["sources_after"]
for name, wanted in control["sources_after"].items():
    assert binding(root / name) == wanted
release["commands"] = [[part.replace("build-2", "build-3").replace("release-2.json", "release-3.json")
                         for part in command] for command in release["commands"]]
release["build_command"] = [part.replace("build-2", "build-3") for part in release["build_command"]]
for item in release["inputs"]:
    assert ref(root / item["path"]) == item
destination = here / "bridge-build-release-3.json"
assert not destination.exists() and not (root / "target/m193c-output-grid-build-3").exists() and not (here / "bridge-build-3").exists()
destination.write_text(json.dumps(release, indent=2) + "\n", encoding="utf8", newline="\n")
ast.parse((here / "bridge-build.py").read_bytes())
paths = {destination.relative_to(root).as_posix()}
paths.update("experiments/m193c-output-grid/" + name for name in (
    "bridge-build.py", "build-drain-repair-review.md", "controller-controls-4-independent-read.md", "work/prepare-build-3.py"))
paths.update(path.relative_to(root).as_posix() for path in (here / "controller-controls-4").rglob("*") if path.is_file())
paths.update("experiments/m193c-output-grid/work/controller-controls-4-" + name for name in ("console.txt", "exit.txt", "outer.json"))
(here / "work/archive-build-3.nul").write_bytes(b"\0".join(name.encode("utf8") for name in sorted(paths)) + b"\0")
print(json.dumps(dict(release=ref(destination), archive_paths=len(paths)), indent=2))

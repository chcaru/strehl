"""Prepare new private releases only after commissioned controls and build3."""
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

def read(name):
    return json.loads((here / name).read_bytes())

build = read("bridge-build-3/result.json")
control = read("controller-controls-4/result.json")
assert build["status"] == "COMPLETE_COMPILED_TESTS_ONLY" and build["exit_code"] == 0
assert build["error"] is None and build["finalization_errors"] == []
assert control["status"] == "PASS_OWNED_PROCESS_CONTROLS_ONLY" and len(control["cases"]) == 14
assert all(row["passed"] is True for row in control["cases"])
assert control["error"] is None and control["finalization_errors"] == []
assert build["sources_before"] == build["sources_after"]
assert control["sources_before"] == control["sources_after"]
sources = {**build["sources_before"], **control["sources_before"]}
for name in ("bridge-build.py", "private-grid-run.py"):
    sources[(here / name).relative_to(root).as_posix()] = binding(here / name)
old_producer = read("private-grid-release-1.json")
assert set(sources) == set(old_producer["source_bindings"])
changed = {name for name in sources if sources[name] != old_producer["source_bindings"][name]}
assert changed == {"experiments/m193c-output-grid/" + name for name in (
    "bounded-process.py", "controller-child.py", "controller-controls.py", "bridge-build.py", "private-grid-run.py")}
for name, wanted in sources.items():
    assert binding(root / name) == wanted, name

replacements = {
    "bridge-build-2/result.json": "bridge-build-3/result.json",
    "controller-controls-3/result.json": "controller-controls-4/result.json",
    "bridge-build-2-independent-read.md": "bridge-build-3-independent-read.md",
    "private-grid-release-1.json": "private-grid-release-2.json",
}
def updated_inputs(rows):
    updated = {}
    for row in rows:
        old_path = root / row["path"]
        suffix = old_path.relative_to(here).as_posix()
        if suffix in replacements:
            item = ref(here / replacements[suffix])
        else:
            assert ref(old_path) == row, suffix
            item = row
        updated[item["path"]] = item
    for name in (
        "controller-amendment-3.md", "independent-controller-amendment-3-review.md",
        "controller-controls-4-independent-read.md", "build-drain-repair-review.md",
        "independent-private-campaign-1-read.md", "private-campaign-1/result.json",
    ):
        item = ref(here / name)
        updated[item["path"]] = item
    return list(updated.values())

producer = dict(old_producer)
producer["source_bindings"] = sources
producer["inputs"] = updated_inputs(old_producer["inputs"])
command = [part.replace("private-campaign-1", "private-campaign-2")
           .replace("private-grid-release-1.json", "private-grid-release-2.json")
           .replace("bridge-build-2", "bridge-build-3").replace("controller-controls-3", "controller-controls-4")
           for part in old_producer["commands"][0]]
command[command.index("--build-sha256") + 1] = ref(here / "bridge-build-3/result.json")["sha256"]
command[command.index("--controls-sha256") + 1] = ref(here / "controller-controls-4/result.json")["sha256"]
producer["commands"] = [command]
producer_path = here / "private-grid-release-2.json"
owner_path = here / "private-campaign-release-2.json"
assert not producer_path.exists() and not owner_path.exists() and not (here / "private-campaign-2").exists()
producer_path.write_text(json.dumps(producer, indent=2) + "\n", encoding="utf8", newline="\n")

old_owner = read("private-campaign-release-1.json")
owner = dict(old_owner)
owner_sources = {**old_owner["source_bindings"], **sources}
assert set(owner_sources) == set(old_owner["source_bindings"])
for name, wanted in owner_sources.items():
    assert binding(root / name) == wanted, name
owner["source_bindings"] = owner_sources
owner["inputs"] = updated_inputs(old_owner["inputs"])
owner["build"] = ref(here / "bridge-build-3/result.json")
owner["commands"] = {name: [part.replace("private-campaign-1", "private-campaign-2")
                                    .replace("private-campaign-release-1.json", "private-campaign-release-2.json")
                                    .replace("bridge-build-2", "bridge-build-3") for part in values]
                     for name, values in old_owner["commands"].items()}
owner["commands"]["grid_producer"] = [ref(producer_path)["sha256"] if part == "ACTUAL_EXECUTION_RELEASE_SHA256"
                                       else part for part in command]
assert binding(Path(owner["reader_runtime"]["path"])) == {key: owner["reader_runtime"][key] for key in ("sha256", "bytes")}
owner_path.write_text(json.dumps(owner, indent=2) + "\n", encoding="utf8", newline="\n")
print(json.dumps(dict(producer=ref(producer_path), owner=ref(owner_path), sources=len(owner_sources)), indent=2))

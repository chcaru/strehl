"""Freeze the process-only drain repair; retain the first private refusal."""
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

release = json.loads((here / "controller-controls-release-3.json").read_bytes())
for name in release["source_bindings"]:
    release["source_bindings"][name] = binding(root / name)
    ast.parse((root / name).read_bytes(), filename=name)
for name in (
    "controller-amendment-3.md", "independent-controller-amendment-3-review.md",
    "controller-controls-3/result.json", "independent-private-campaign-1-read.md",
    "private-campaign-1/result.json", "private-campaign-1/worker/grid/run-index.json",
):
    release["inputs"].append(ref(here / name))
release["commands"] = [[part.replace("controls-3", "controls-4").replace("release-3.json", "release-4.json")
                         for part in command] for command in release["commands"]]
for row in release["inputs"]:
    assert ref(root / row["path"]) == row
destination = here / "controller-controls-release-4.json"
assert not destination.exists() and not (here / "controller-controls-4").exists()
destination.write_text(json.dumps(release, indent=2) + "\n", encoding="utf8", newline="\n")
paths = {destination.relative_to(root).as_posix(), "experiments/m193c-output-grid/private-grid-run.py"}
paths.update(name for name in release["source_bindings"] if name.startswith("experiments/m193c-output-grid/"))
paths.update(row["path"] for row in release["inputs"])
paths.update(path.relative_to(root).as_posix() for path in (here / "private-campaign-1").rglob("*") if path.is_file())
paths.update("experiments/m193c-output-grid/work/private-campaign-1-" + name for name in (
    "console.txt", "exit.txt", "outer.json"))
paths.update("experiments/m193c-output-grid/" + name for name in (
    "work/prepare-controls-4.py", "independent-private-campaign-result-audit-plan.md"))
paths.update(("AGENTS.md", "docs/proposals/2026-09-sota-program.md", "docs/research/M193c-output-grid.md"))
(here / "work/archive-controls-4.nul").write_bytes(b"\0".join(name.encode("utf8") for name in sorted(paths)) + b"\0")
print(json.dumps(dict(release=ref(destination), archive_paths=len(paths)), indent=2))

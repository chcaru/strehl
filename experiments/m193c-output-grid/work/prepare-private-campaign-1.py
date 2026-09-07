"""Freeze the twelve-image private commands and bytes; no subject execution."""
import ast
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
here = root / "experiments/m193c-output-grid"
output = here / "private-campaign-1"
release_path = here / "private-campaign-release-1.json"

def binding(path):
    raw = path.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def ref(path):
    return dict(path=path.relative_to(root).as_posix(), **binding(path))

producer_path = here / "private-grid-release-1.json"
producer = json.loads(producer_path.read_bytes())
build = json.loads((here / "bridge-build-2/result.json").read_bytes())
sources = dict(producer["source_bindings"])
for name in (
    "private-campaign.py", "private-campaign-preregister.md",
    "independent-private-read.py", "private-reader-wrapper-preregister.md",
    "independent-grid-read.py", "private-reader-preregister.md",
    "independent-derivative-read.py", "independent-derivative-tiff.py",
    "independent-derivative-reader-preregister.md",
):
    path = here / name
    sources[path.relative_to(root).as_posix()] = binding(path)
    if path.suffix == ".py":
        ast.parse(path.read_bytes(), filename=str(path))
old_parser = root / "experiments/m194g-larger-pupil/independent-rgb-tiff.py"
sources[old_parser.relative_to(root).as_posix()] = binding(old_parser)
inputs = {row["path"]: row for row in producer["inputs"]}
for name in (
    "private-grid-release-1.json", "private-campaign-preregister.md",
    "private-reader-wrapper-preregister.md", "private-reader-preregister.md",
    "independent-derivative-reader-preregister.md",
    "independent-private-campaign-review.md", "independent-private-reader-wrapper-review.md",
    "independent-grid-source-review.md", "independent-derivative-reader-source-review.md",
    "independent-derivative-source-repair-review.md", "derivative-controls-preregister.md",
):
    row = ref(here / name)
    inputs[row["path"]] = row

def python_command(stage, script):
    return [sys.executable, "-B", "-X", "faulthandler", "-X",
            "pycache_prefix=" + str(output / ("cache-" + stage.replace("_", "-"))), str(here / script)]

commands = {}
for name in ("owner", "worker"):
    commands[name] = python_command(name, "private-campaign.py")
    if name == "worker":
        commands[name] += ["--worker"]
    commands[name] += ["--release", str(release_path), "--release-sha256",
                      "ACTUAL_EXECUTION_RELEASE_SHA256", "--output",
                      str(output if name == "owner" else output / "worker")]
commands["grid_producer"] = [binding(producer_path)["sha256"] if part == "ACTUAL_EXECUTION_RELEASE_SHA256"
                             else part for part in producer["commands"][0]]
for name, script, stem, token in (
    ("grid_reader", "independent-private-read.py", "grid-reader", "ACTUAL_GRID_REQUEST_SHA256"),
    ("derivative_reader", "independent-derivative-read.py", "derivative-reader", "ACTUAL_DERIVATIVE_REQUEST_SHA256"),
):
    commands[name] = python_command(name, script)
    if name == "derivative_reader":
        commands[name] += ["--private"]
    commands[name] += ["--request", str(output / "worker" / (stem + "-request.json")),
                      "--request-sha256", token, "--output", str(output / "worker" / stem)]
commands["derivative_producer"] = [str(root / build["test_executable"]["path"]), "--exact",
    "merge_cmd::production_truth::m193c_registration_derivative::m193c_derivative_private",
    "--ignored", "--test-threads=1", "--nocapture"]

release = dict(schema="m193c-private-campaign-release-v1", scope="private-twelve",
    source_bindings=sources, inputs=list(inputs.values()), commands=commands,
    build=ref(here / "bridge-build-2/result.json"),
    reader_runtime=dict(path=str(Path(sys.executable).resolve()), **binding(Path(sys.executable))))
for name, wanted in sources.items():
    assert binding(root / name) == wanted, name
for row in inputs.values():
    assert binding(root / row["path"]) == {k: row[k] for k in ("sha256", "bytes")}, row["path"]
assert not output.exists() and not release_path.exists()
release_path.write_text(json.dumps(release, indent=2) + "\n", encoding="utf8", newline="\n")
print(json.dumps(dict(release=ref(release_path), sources=len(sources), inputs=len(inputs)), indent=2))

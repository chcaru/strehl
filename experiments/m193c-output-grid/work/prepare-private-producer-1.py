"""Prepare only the fixed grid producer release; do not invoke image code."""
import ast
import hashlib
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
here = root/"experiments/m193c-output-grid"
def binding(p):
    raw = p.read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
def ref(p):
    return dict(path=p.relative_to(root).as_posix(), **binding(p))

build = json.loads((here/"bridge-build-2/result.json").read_bytes())
controls = json.loads((here/"controller-controls-3/result.json").read_bytes())
sources = {**build["sources_before"], **controls["sources_before"]}
for name in ("bridge-build.py", "private-grid-run.py"):
    p = here/name
    sources[p.relative_to(root).as_posix()] = binding(p)
    ast.parse(p.read_bytes(), filename=str(p))
inputs = [ref(here/name) for name in (
    "bridge-build-2/result.json", "controller-controls-3/result.json", "bridge-build-2-independent-read.md",
    "private-protocol.md", "execution-preregister.md", "independent-private-run-review.md",
    "independent-private-run-repair-review.md", "independent-parent-component-review.md")]
release_path = here/"private-grid-release-1.json"
release = dict(schema="m193c-execution-release-v1", scope="private-grid-run", source_bindings=sources, inputs=inputs,
    commands=[[sys.executable, "-X", "pycache_prefix=" + str(here/"private-campaign-1/cache-grid-producer"),
        "-B", "-X", "utf8", "-X", "faulthandler", str(here/"private-grid-run.py"),
        "--release", str(release_path), "--release-sha256", "ACTUAL_EXECUTION_RELEASE_SHA256",
        "--build", str(here/"bridge-build-2/result.json"), "--build-sha256", ref(here/"bridge-build-2/result.json")["sha256"],
        "--controls", str(here/"controller-controls-3/result.json"), "--controls-sha256", ref(here/"controller-controls-3/result.json")["sha256"],
        "--output", str(here/"private-campaign-1/worker/grid")]])
for name, wanted in sources.items():
    assert binding(root/name) == wanted
assert not release_path.exists()
release_path.write_text(json.dumps(release, indent=2)+"\n", encoding="utf8", newline="\n")
print(json.dumps(dict(release=ref(release_path), sources=len(sources)), indent=2))

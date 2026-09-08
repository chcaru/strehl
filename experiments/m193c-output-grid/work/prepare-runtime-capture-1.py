"""Freeze dependency capture after actual independently read private2 admission."""
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

def checked_json(path):
    raw = path.read_bytes()
    return json.loads(raw), dict(path=path.relative_to(root).as_posix(), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

private, private_ref = checked_json(here / "private-campaign-2/result.json")
gate, gate_ref = checked_json(here / "private-campaign-2/derivative-private-admission.json")
owner, owner_ref = checked_json(here / "private-campaign-release-2.json")
assert private["status"] == "PASS_M193C_PRIVATE_STAGE_ONLY" and private["error"] is None and private["finalization_errors"] == []
assert gate["status"] == "PASS_REGISTRATION_DERIVATIVE_PRIVATE_ONLY" and gate["error"] is None and gate["finalization_errors"] == []
assert private["derivative_admission"] == gate_ref and private["build"] == gate["build"] == owner["build"]
assert private["derivative_read"] == gate["independent_read"]
assert private["sources_before"] == private["sources_after"] == owner["source_bindings"]
assert private["inputs_before"] == private["inputs_after"] == owner["inputs"]
assert private["execution_release"]["sha256"] == owner_ref["sha256"]
outer = json.loads((here / "work/private-campaign-2-outer.json").read_bytes())
assert type(outer["exit_code"]) is int and outer["exit_code"] == 0 and outer["release_sha256"] == owner_ref["sha256"]
sources = dict(owner["source_bindings"])
for name in ("runtime-capture.py", "runtime-capture-preregister.md"):
    sources[(here / name).relative_to(root).as_posix()] = binding(here / name)
for name, expected in sources.items():
    assert binding(root / name) == expected, name
inputs = [private_ref, gate_ref, owner_ref, owner["build"], gate["private_result"], gate["independent_read"]]
inputs += [ref(here / name) for name in (
    "independent-private-campaign-2-read.md", "independent-runtime-capture-review.md",
    "bridge-build-3-independent-read.md", "controller-controls-4-independent-read.md",
    "private-campaign-2/artifact-index.json", "work/private-campaign-2-console.txt",
    "work/private-campaign-2-exit.txt", "work/private-campaign-2-outer.json",
)]
assert len({str((root / item["path"]).resolve()) for item in inputs}) == len(inputs)
for item in inputs:
    path = Path(item["path"])
    path = path if path.is_absolute() else root / path
    assert binding(path) == {key: item[key] for key in ("sha256", "bytes")}
python_ref = owner["reader_runtime"]
python_path = Path(python_ref["path"])
assert binding(python_path) == {key: python_ref[key] for key in ("sha256", "bytes")}
output = here / "runtime-capture-1"
runtime = here / "derivative-runtime-1.json"
destination = here / "runtime-capture-release-1.json"
commands = dict(
    parent=[str(python_path), "-B", "-X", "faulthandler", "-X", "pycache_prefix=" + str(output / "cache-parent"),
            str(here / "runtime-capture.py"), "--release", str(destination), "--release-sha256",
            "ACTUAL_EXECUTION_RELEASE_SHA256", "--output", str(output)],
    reader=[str(python_path), "-B", "-X", "faulthandler", "-X", "pycache_prefix=" + str(output / "cache-reader"),
            str(here / "independent-derivative-read.py"), "--capture-runtime", str(runtime)])
release = dict(schema="m193c-runtime-capture-release-v1", scope="dependency-runtime-only", source_bindings=sources,
    inputs=inputs, commands=commands, build=owner["build"], private_admission=gate_ref,
    independent_review=ref(here / "independent-private-campaign-2-read.md"), python_executable=python_ref)
assert not destination.exists() and not output.exists() and not runtime.exists()
destination.write_text(json.dumps(release, indent=2) + "\n", encoding="utf8", newline="\n")
print(json.dumps(dict(release=ref(destination), sources=len(sources), inputs=len(inputs)), indent=2))

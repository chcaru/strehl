"""Link the narrow cache replay to a root-frozen CLI rlib, without Cargo."""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import subprocess
import os
import re

parser = argparse.ArgumentParser()
parser.add_argument("--fingerprint", required=True, type=Path)
parser.add_argument("--out", required=True, type=Path)
parser.add_argument("--source", type=Path)
parser.add_argument("--build-id", required=True)
parser.add_argument("--bind-source", type=Path, action="append", default=[])
parser.add_argument("--test", action="store_true")
args = parser.parse_args()
args.out.mkdir(parents=True, exist_ok=False)
source = (args.source or Path(__file__).with_name("native-replay.rs")).resolve()
metadata = json.loads(args.fingerprint.read_text())
release = args.fingerprint.parent.parent.parent
dependencies = release / "deps"
cli_key = args.fingerprint.parent.name.removeprefix("strehl-cli-")
cli = dependencies / ("libstrehl_cli-" + cli_key + ".rlib")
assert cli.is_file(), cli
externs = {"strehl_cli": cli}
for _, name, _, value in metadata["deps"]:
    if name not in {"strehl_core", "serde", "serde_json", "rayon", "anyhow", "sha2", "tiff", "strehl_edit", "clap"}:
        continue
    digest = struct.pack("<Q", value).hex()
    roots = [p for p in (release / ".fingerprint").iterdir()
             if (p / ("lib-" + name)).is_file()
             and (p / ("lib-" + name)).read_text().strip() == digest]
    assert len(roots) == 1, (name, roots)
    key = roots[0].name.rsplit("-", 1)[1]
    externs[name] = dependencies / ("lib" + name + "-" + key + ".rlib")
assert len(externs) == 10, externs
exe = args.out / (source.stem + ".exe")
command = ["rustc", "--edition=2024", "-C", "opt-level=3", "-C", "lto=thin", "-C", "codegen-units=1", str(source),
           "-L", "dependency=" + str(dependencies.resolve()), "-o", str(exe)]
if args.test:
    command += ["--test"]
for name, path in externs.items():
    command += ["--extern", name + "=" + str(path.resolve())]
def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def include_closure(initial):
    root = Path.cwd().resolve()
    pending = [Path(p).resolve() for p in initial]
    found = set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        assert path.is_relative_to(root) and path.is_file(), path
        found.add(path)
        assert len(found) <= 1024
        if path.suffix == ".rs":
            content = path.read_text(encoding="utf-8")
            children = re.findall(r'#\[path\s*=\s*"([^"]+)"\]', content)
            children += re.findall(r'include_(?:bytes|str)!\(\s*"([^"]+)"\s*\)', content)
            pending.extend((path.parent / child).resolve() for child in children)
    return sorted(found)

bound_sources = include_closure([source, *args.bind_source])
record = {"command": command, "harness_sha256": sha(source),
          "included_sources": {str(p): sha(p) for p in bound_sources},
          "source_binding": "recursive local path and included file closure; pre/post hashes",
          "fingerprint": str(args.fingerprint), "fingerprint_sha256": sha(args.fingerprint),
          "libraries": {name: {"file": str(p), "sha256": sha(p)} for name, p in externs.items()}}
with (args.out / "build.log").open("wb") as log:
    compiled_environment = {"STREHL_BUILD_ID":args.build_id,
                            "CARGO_MANIFEST_DIR":str(Path("crates/strehl-cli").resolve())}
    environment = dict(os.environ, **compiled_environment)
    record["compile_environment"] = compiled_environment
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=environment)
record["exit_code"] = result.returncode
record["sources_unchanged_during_build"] = all(sha(p) == record["included_sources"][str(p)] for p in bound_sources)
record["libraries_unchanged_during_build"] = all(sha(p) == record["libraries"][name]["sha256"] for name, p in externs.items())
record["fingerprint_unchanged_during_build"] = sha(args.fingerprint) == record["fingerprint_sha256"]
if not all(record[k] for k in ["sources_unchanged_during_build", "libraries_unchanged_during_build", "fingerprint_unchanged_during_build"]):
    record["exit_code"] = 1
if result.returncode == 0:
    record["executable_sha256"] = sha(exe)
(args.out / "build-receipt.json").write_text(json.dumps(record, indent=2) + "\n")
raise SystemExit(record["exit_code"])

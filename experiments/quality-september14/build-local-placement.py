"""Fresh bounded build of the actual local placement consumer tests; no RAW run."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("placement_build_bounds", ROOT / "experiments/m193c-output-grid/bounded-process.py")
bounds = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = bounds
spec.loader.exec_module(bounds)


def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def binding(path):
    return dict(path=str(path), **bounds.binding(path))


def main():
    out = HERE / "local-placement-build-2"
    out.mkdir()
    prior = json.loads((HERE / "matched-source-build-sources.json").read_text())
    paths = {ROOT / row["path"] for row in prior}
    paths.update(HERE / name for name in ("local-placement-consumer-tests.rs", "build-local-placement.py"))
    paths.update(ROOT / name for name in ("crates/strehl-cli/src/merge_cmd.rs", "crates/strehl-cli/src/image_out.rs", "crates/strehl-core/src/demosaic.rs", "Cargo.lock"))
    # Establish a fresh compiler input after the author has frozen this source.
    (HERE / "local-placement-consumer-tests.rs").touch()
    sources = [binding(path) for path in sorted(paths)]
    command = ["cargo", "test", "-p", "strehl-cli", "--bin", "strehl", "--no-run", "--release",
        "--features", "native-pyramid-profile,native-gpu-gather,native-direct-planes", "--jobs", "2",
        "--target-dir", str(ROOT / "target/native-pyramid-profile"), "--message-format=json-render-diagnostics",
        "--locked", "--offline"]
    env, removed = bounds.clean_environment(dict(RAYON_NUM_THREADS="8", CARGO_INCREMENTAL="0").items())
    save(out / "invocation.json", dict(command=command, source_files=sources, removed_environment=removed,
        scope="Compile test binary only. No RAW decoding, image experiment or timing comparison."))
    api = bounds.load_job_api(bounds.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
    result = bounds.run(command, env, ROOT, out / "compile.log", api=api,
        wall_seconds=600, cpu_seconds=1800, log_bytes=16 << 20, committed_bytes=8 << 30)
    save(out / "build-result.json", result)
    print(json.dumps({key: result[key] for key in ("exit_code", "error", "wall_seconds")}), flush=True)
    assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"]
    assert not result["cleanup_errors"]
    log = (out / "compile.log").read_text(encoding="utf-8", errors="replace")
    assert "Compiling strehl-cli" in log
    found = []
    for line in log.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if (row.get("reason") == "compiler-artifact" and row.get("executable") and
                row.get("target", {}).get("name") == "strehl" and row["profile"]["test"]):
            found.append(row["executable"])
    assert len(found) == 1, found
    exe = out / "cli-tests.exe"
    shutil.copyfile(found[0], exe)
    for source in sources:
        assert binding(Path(source["path"])) == source
    save(out / "executable.json", binding(exe))
    print(json.dumps(binding(exe)), flush=True)


if __name__ == "__main__":
    main()

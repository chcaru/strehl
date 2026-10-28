"""Root build and freeze of the separate fixed flat60 exporter."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "outputs/raw-quality-2026-10-26/flat-export-build-1"


def ref(path):
    path = Path(path)
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2)
        f.write("\n")


def main():
    assert not OUT.exists()
    # Do not invalidate the concurrently running full-photograph source bindings.
    prior = json.loads((ROOT / "outputs/raw-quality-2026-10-26/green-phase-build-4/sources.json").read_text())
    assert all(ref(row["path"]) == row for row in prior)
    extra = [ROOT / p for p in (
        "crates/strehl-cli/examples/flat-batch-develop.rs",
        "experiments/raw-quality-2026-10-26/flat-comparator/flat-export-config.json",
        "experiments/raw-quality-2026-10-26/flat-comparator/run-flat.py",
        "experiments/raw-quality-2026-10-26/flat-comparator/build-exporter.py")]
    bindings = prior + [ref(p) for p in extra]
    assert ref(extra[0])["sha256"] == "8c9a3b26d6b8416cb216b26670ba1537fe5fc2de6bfbf3b195645f866fe3a47e"
    assert ref(extra[1])["sha256"] == "48d5a0acbf59557d4743ca197b9eb8d0c99671f325064ae20be1180c22489cd5"
    OUT.mkdir()
    save(OUT / "sources.json", bindings)
    command = ["cargo", "build", "--locked", "--offline", "--release", "-p", "strehl-cli", "--example", "flat-batch-develop"]
    env = os.environ.copy()
    env["CARGO_BUILD_JOBS"] = "4"
    save(OUT / "invocation.json", dict(command=command, cwd=str(ROOT), environment={"CARGO_BUILD_JOBS": "4"},
         overlap="Frozen green-phase full299 process; build timing is operational only."))
    start = time.monotonic()
    with (OUT / "build.log").open("wb") as log:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=False)
    save(OUT / "process.json", dict(exit_code=result.returncode, wall_seconds=time.monotonic()-start))
    lines = (OUT / "build.log").read_text(errors="replace")
    print("\n".join(line for line in lines.splitlines() if "Compiling" in line or "Finished" in line or "error" in line))
    assert result.returncode == 0 and "Compiling strehl-cli" in lines and "Finished" in lines
    assert all(ref(row["path"]) == row for row in bindings)
    built = ROOT / "target/release/examples/flat-batch-develop.exe"
    frozen = OUT / "flat-batch-develop.exe"
    shutil.copy2(built, frozen)
    assert ref(built)["sha256"] == ref(frozen)["sha256"]
    save(OUT / "executable.json", ref(frozen))
    print(json.dumps(ref(frozen)))


if __name__ == "__main__":
    main()

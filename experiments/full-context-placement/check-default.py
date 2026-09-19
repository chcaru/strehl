"""Compile-check the normal feature set; no image or RAW run."""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("placement_runner", HERE / "run.py")
runner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runner
spec.loader.exec_module(runner)
out = HERE / "default-check-2"
out.mkdir()
(runner.ROOT / "crates/strehl-cli/src/merge_cmd.rs").touch()
command = ["cargo", "check", "-p", "strehl-cli", "--bin", "strehl", "--jobs", "2",
           "--target-dir", str(runner.ROOT / "target/native-pyramid-profile"), "--locked", "--offline", "--message-format=json-render-diagnostics"]
runner.job(command, dict(RAYON_NUM_THREADS="2", CARGO_INCREMENTAL="0"), out)
log = (out / "process.log").read_text(encoding="utf-8", errors="replace")
artifacts = [json.loads(line) for line in log.splitlines() if line.startswith("{")]
assert any(r.get("reason") == "compiler-artifact" and r.get("target", {}).get("name") == "strehl"
           and r["target"]["kind"] == ["bin"] and r["fresh"] is False and r["features"] == [] for r in artifacts)
assert "Checking strehl-cli" in log or "Compiling strehl-cli" in log

"""Run the frozen source143 production gather, then independently verify its input."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN = ROOT / "outputs/raw-quality-2026-10-26"
OUT = CAMPAIGN / "source143-gather-job-1"
CAPTURE = CAMPAIGN / "weevil-source143-gather-ca-off"
spec = importlib.util.spec_from_file_location("gather143_bounded", ROOT / "experiments/m193c-output-grid/bounded-process.py")
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)


def ref(path):
    return {"path": str(Path(path).resolve()), **b.binding(path)}


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


assert not OUT.exists() and not CAPTURE.exists()
OUT.mkdir()
build = CAMPAIGN / "source143-lib-build.jsonl"
rows = [json.loads(line) for line in build.read_text().splitlines() if line.startswith("{")]
assert any(row.get("reason") == "build-finished" and row.get("success") for row in rows)
artifacts = [row["executable"] for row in rows if row.get("reason") == "compiler-artifact"
             and row.get("executable") and row.get("target", {}).get("name") == "strehl_cli"
             and row.get("profile", {}).get("test")]
assert len(artifacts) == 1
exe = Path(artifacts[0])
harness = ROOT / "experiments/raw-quality-2026-10-26/insect-consumer-spread/capture-gather143.rs"
assert b.binding(harness)["sha256"] == "139ff0ad2b92752ad70a18198b5526fd1ade7a9abde148b5b9f55f4780cce5eb"
fields = dict(STREHL_FIX_CA="off", STREHL_ALIGN="1", STREHL_FULLRES_GATHER="1",
              RAYON_NUM_THREADS="4", STREHL_WEEVIL_CAPTURE_OUT=str(CAPTURE))
env, removed = b.clean_environment(fields.items())
command = [str(exe), "align_cmd::weevil_source143_capture_gather_ca_off::capture_weevil_source143_actual_ca_off_gather",
           "--ignored", "--exact", "--nocapture", "--test-threads=1"]
save(OUT / "invocation.json", dict(command=command, environment=fields, removed_environment=removed,
     executable=ref(exe), harness=ref(harness), runner=ref(__file__), build_log=ref(build),
     scope="One actual production source gather. No photographic quality claim."))
api = b.load_job_api(b.binding(ROOT / "experiments/m12-scorecard/m12-harness.py"))
result = b.run(command, env, ROOT, OUT / "process.log", api=api,
               wall_seconds=180, cpu_seconds=600, log_bytes=8 << 20, committed_bytes=4 << 30)
save(OUT / "process.json", result)
assert result["exit_code"] == 0 and result["error"] is None, result
log = (OUT / "process.log").read_text()
assert "running 1 test" in log and "1 passed; 0 failed" in log
capture_path = CAPTURE / "capture.json"
capture = json.loads(capture_path.read_text())
assert capture["status"] == "SOURCE143_ACTUAL_CA_OFF_GATHER_CAPTURED_NO_QUALITY_CLAIM"

# This is a second decoder's original active-area crop, never a replacement gather.
import numpy as np
import rawpy
source = Path(capture["source"]["path"])
before = ref(source)
mtime = source.stat().st_mtime_ns
assert before["sha256"] == capture["source"]["sha256"]
with rawpy.imread(str(source)) as raw:
    original = raw.raw_image_visible.copy()
    pattern = raw.raw_pattern.copy()
    black = list(raw.black_level_per_channel)
    white = int(raw.white_level)
assert original.dtype == np.uint16
x, y, width, height = capture["original"]["native_crop_xywh"]
expected = original[y:y+height, x:x+width]
actual_path = CAPTURE / "original-crop.u16le"
assert ref(actual_path)["sha256"] == capture["original"]["sha256"]
actual = np.memmap(actual_path, dtype="<u2", mode="r", shape=(height, width))
phases = {}
for name, dy, dx in (("R", 0, 0), ("G1", 0, 1), ("G2", 1, 0), ("B", 1, 1)):
    diff = expected[dy::2, dx::2].astype(np.int32) - actual[dy::2, dx::2].astype(np.int32)
    phases[name] = dict(samples=int(diff.size), different=int(np.count_nonzero(diff)),
                        max_abs_dn=int(np.max(np.abs(diff))))
assert ref(source) == before and source.stat().st_mtime_ns == mtime
save(OUT / "independent-decode.json", dict(source=before, source_mtime_ns=mtime,
     rawpy_version=rawpy.__version__, libraw_version=rawpy.libraw_version,
     rawpy_active_shape=list(original.shape), native_original=ref(actual_path),
     crop_xywh=[x, y, width, height], rawpy_pattern=pattern.tolist(),
     rawpy_black=black, rawpy_white=white, phases=phases,
     copied_inside_context=True, original_unchanged=True,
     scope="Original interior sensor crop only; no gathered-array equality claim."))
assert all(row["different"] == 0 for row in phases.values())
save(OUT / "completion.json", dict(status="ACTUAL_GATHER_CAPTURE_AND_INDEPENDENT_ORIGINAL_DECODE_VERIFIED",
     capture=ref(capture_path), independent_decode=ref(OUT / "independent-decode.json")))
print(json.dumps(dict(status="VERIFIED", capture=ref(capture_path), process_seconds=result["wall_seconds"], phases=phases)))

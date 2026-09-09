"""Fixed five-file diagnostic driver; all children use the existing bounded job tool."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj

m = module("stroke_process", ROOT / "experiments/m193c-output-grid/bounded-process.py")
author = module("stroke_inspection", HERE / "inspect.py")

def ref(path):
    return dict(path=str(path.resolve()), **m.binding(path))

def save(path, value):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")

assert sys.argv[1:] == [], "fixed single allocation"
author.fixed()
inputs = [record for i in author.INDICES for _, record in
          (author.input_path(i, ".ARW"), author.input_path(i, ".tif"))]
helper = ROOT / "experiments/m12-scorecard/m12-harness.py"
api = m.load_job_api(m.binding(helper))
out = HERE / "run-1"
out.mkdir()
(out / "controls").mkdir()
(out / "secondary").mkdir()
save(out / "plan.json", dict(
    revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    runner=ref(Path(__file__)), python=ref(Path(sys.executable)),
    helpers=[ref(helper), ref(ROOT / "experiments/m193c-output-grid/bounded-process.py")],
    sources=author.source_bindings(), inputs=inputs,
    secondary_caller_commit="052697263a1eb35a05426b3ab2b454c62da25d06",
    secondary_manifest=ref(ROOT / "experiments/m61-ptc-high-iso/decode-check/Cargo.toml"),
    secondary_scope="Existing held executable, not rebuilt. Current caller binding is descriptive; exact independent ROI equality admits decoded samples.",
    limits=dict(per_child_wall_seconds=60, per_child_cpu_seconds=60,
                per_child_commit_bytes=1<<30, aggregate_cpu_seconds=120,
                retained_output_bytes=64<<20)))
records = []
def run(label, argv):
    spent = sum(v["cpu_seconds"] for v in records)
    assert spent < 120
    env, removed = m.clean_environment([("OPENBLAS_NUM_THREADS", "1"), ("OMP_NUM_THREADS", "1"), ("RAYON_NUM_THREADS", "4")])
    save(out / (label+"-invocation.json"), dict(command=argv, removed_environment=removed,
         overrides=dict(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", RAYON_NUM_THREADS="4")))
    result = m.run(argv, env, ROOT, out / (label+".log"), api=api,
        wall_seconds=60, cpu_seconds=min(60, 120-spent), log_bytes=1<<20, committed_bytes=1<<30)
    save(out / (label+"-process.json"), result)
    print(json.dumps(dict(label=label, exit_code=result["exit_code"], error=result["error"],
                         wall_seconds=result["wall_seconds"])), flush=True)
    assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"], "preserve failure; no automatic retry"
    records.append(dict(label=label, wall_seconds=result["wall_seconds"],
        cpu_seconds=result["job_accounting"]["total_cpu_100ns"]/1e7,
        peak_job_commit_bytes=result["job_memory"]["peak_job_memory_used_bytes"]))
    assert sum(v["cpu_seconds"] for v in records) <= 120
    assert sum(p.stat().st_size for p in out.rglob("*") if p.is_file()) <= 64<<20

py = [sys.executable, "-I", "-B", str(HERE / "inspect.py")]
run("controls", py + ["controls", "--out", str(out / "controls")])
controls = json.loads((out / "controls/controls.json").read_text(encoding="utf-8"))
assert controls["result"]["status"] == "PASS"
for index in author.INDICES:
    raw, _ = author.input_path(index, ".ARW")
    assert not (out / "secondary" / f"rawler-frame-{index}.bin").exists()
    run(f"secondary-{index}", [str(author.SECONDARY), str(raw), str(out / "secondary"),
        f"frame-{index}", "1304", "112", "456", "640"])
    run(f"primary-{index}", py + ["primary", "--index", str(index), "--out", str(out)])
run("analysis", py + ["analyze", "--out", str(out), "--secondary", str(out / "secondary")])
for index in author.INDICES:
    author.input_path(index, ".ARW")
    author.input_path(index, ".tif")
save(out / "completion.json", dict(status="COMPLETE_PENDING_INDEPENDENT_INTERPRETATION",
    steps=records, aggregate_cpu_seconds=sum(v["cpu_seconds"] for v in records),
    original_metadata_unchanged=True, diagnostic=ref(out / "result.json")))

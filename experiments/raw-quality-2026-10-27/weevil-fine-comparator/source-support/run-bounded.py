"""Root-authorized tiny cached-image exports, each at most60s/2GiB."""
from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
HELPER = ROOT / "experiments/m193c-output-grid/bounded-process.py"
spec = importlib.util.spec_from_file_location("weevil_source_support_bound", HELPER)
b = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = b
spec.loader.exec_module(b)
stage = sys.argv[1]
assert stage in ("overviews", "crops")
out = HERE / (stage+"-job")
out.mkdir()
env, removed = b.clean_environment((("OMP_NUM_THREADS","1"),("OPENBLAS_NUM_THREADS","1")))
cmd = [sys.executable,"-B","-X","faulthandler",str(HERE/"export-source-views.py"),stage]
api = b.load_job_api(b.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
result = b.run(cmd,env,ROOT,out/"process.log",api=api,wall_seconds=60,cpu_seconds=120,
               log_bytes=1<<20,committed_bytes=2<<30)
(out/"process.json").write_text(json.dumps(result,indent=2)+"\n")
assert result["exit_code"] == 0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"]
print(json.dumps({k:result[k] for k in ("exit_code","wall_seconds","job_memory")}))

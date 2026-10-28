"""Root-authorized single bounded locator run; no original RAW access."""
from pathlib import Path
import importlib.util
import json
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUT=HERE/"source-locator-1"
PROCESS=HERE/"source-locator-process-1"
HELPER=ROOT/"experiments/m193c-output-grid/bounded-process.py"
spec=importlib.util.spec_from_file_location("photo_locator_bounded",HELPER)
b=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=b
spec.loader.exec_module(b)
PROCESS.mkdir(exist_ok=False)
command=[sys.executable,"-B","-X","faulthandler",str(HERE/"locate-sources.py"),
         "--sources-json",str(ROOT/"outputs/raw-quality-2026-10-26/weevil-107-tiff-export/receipt.json"),
         "--encoding","srgb","--out",str(OUT)]
fields={"OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","RAYON_NUM_THREADS":"4"}
env,removed=b.clean_environment(fields.items())
harness=ROOT/"experiments/m12-scorecard/m12-harness.py"
(PROCESS/"invocation.json").write_text(json.dumps({"command":command,"fields":fields,"removed_environment":removed,
    "script":b.binding(HERE/"locate-sources.py"),"helper":b.binding(HELPER),"harness":b.binding(harness),
    "limits":{"wall_seconds":180,"cpu_seconds":360,"committed_bytes":4<<30}},indent=2)+"\n")
result=b.run(command,env,ROOT,PROCESS/"process.log",api=b.load_job_api(b.binding(harness)),
    wall_seconds=180,cpu_seconds=360,committed_bytes=4<<30,log_bytes=4<<20)
(PROCESS/"process.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps(result,indent=2))
assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"]
receipt=json.loads((OUT/"locator.json").read_text())
print(json.dumps(receipt["intervals"],indent=2))

"""Generate complete independent float references, never CFA authority by itself."""
import os
for key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[key] = "2"
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import traceback
import numpy as np
import scipy

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("independent_model", HERE/"independent-model.py")
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--controls",type=Path,required=True)
    ap.add_argument("--controls-sha256",required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    result = dict(schema="m194e-independent-reference-v1",status="RUNNING",argv=sys.argv,
                  python=sys.version,numpy=np.__version__,scipy=scipy.__version__,
                  frames=[],budgets={},sources={},actual_peak_explicit_ndarray_bytes=0)
    try:
        if sha(args.controls) != args.controls_sha256:
            raise m.Refusal("reference instrument controls hash mismatch")
        controls = json.loads(args.controls.read_text(encoding="utf8"))
        if controls["status"] != "PASS_REFERENCE_INSTRUMENT_ONLY" or not controls["source_unchanged"]:
            raise m.Refusal("instrument controls did not pass")
        for name,value in controls["sources"].items():
            if sha(HERE/name) != value:
                raise m.Refusal("instrument source changed: "+name)
        result["controls"] = dict(path=str(args.controls.resolve()),sha256=args.controls_sha256)
        for name in ("independent-model.py","independent-controls.py","independent-reference.py","independent-design.md"):
            shutil.copyfile(HERE/name,args.output/name)
            result["sources"][name] = sha(HERE/name)
        scene = m.intended_scene()
        for arm,eps in (("primary",.000125),("refined",.0000078125)):
            budget = m.Budget()
            result["budgets"][arm] = budget.receipt()
            for index,focus in enumerate((.5,.625,.75,.875,1.)):
                values = np.empty((48,64),dtype="<f8")
                indicators = np.empty_like(values)
                result["actual_peak_explicit_ndarray_bytes"] = max(result["actual_peak_explicit_ndarray_bytes"],values.nbytes+indicators.nbytes)
                assert result["actual_peak_explicit_ndarray_bytes"] <= 32*1024*1024
                for y in range(48):
                    for x in range(64):
                        values[y,x],rec = m.render(scene,m.Frame(focus,12.),(x,y),eps=eps,budget=budget)
                        indicators[y,x] = rec["absolute_error_indicator_e"]
                array_path = args.output/f"{arm}-{index}.npy"
                error_path = args.output/f"{arm}-{index}-indicators.npy"
                np.save(array_path,values,allow_pickle=False)
                np.save(error_path,indicators,allow_pickle=False)
                item = dict(arm=arm,index=index,inverse_focus=focus,shape=[48,64],dtype="<f8",
                            array=dict(path=array_path.name,bytes=array_path.stat().st_size,sha256=sha(array_path)),
                            indicators=dict(path=error_path.name,bytes=error_path.stat().st_size,sha256=sha(error_path)),
                            max_error_indicator_e=float(indicators.max()),min_e=float(values.min()),max_e=float(values.max()))
                result["frames"].append(item)
                result["budgets"][arm] = budget.receipt()
                (args.output/"partial.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf8")
                print(json.dumps(dict(arm=arm,frame=index,budget=budget.receipt())),flush=True)
                del values,indicators
        result["refinement"] = []
        for index in range(5):
            primary = np.load(args.output/f"primary-{index}.npy",allow_pickle=False)
            refined = np.load(args.output/f"refined-{index}.npy",allow_pickle=False)
            delta = primary-refined
            maximum = float(np.max(np.abs(delta)))
            rms = float(np.sqrt(np.mean(delta*delta)))
            result["actual_peak_explicit_ndarray_bytes"] = max(result["actual_peak_explicit_ndarray_bytes"],5*delta.nbytes)
            result["refinement"].append(dict(index=index,maximum_e=maximum,rms_e=rms,passed=maximum<=.0005))
            if maximum > .0005:
                raise m.Refusal("whole-frame independent refinement failed")
            del primary,refined,delta
        result["status"] = "PASS_COMPLETE_REFERENCE_ONLY"
    except Exception as exc:
        result["status"] = "UNCOMMISSIONED_NUMERICS" if isinstance(exc,m.Refusal) else "INSTRUMENT_INVALID"
        result["exception"] = str(exc)
        result["traceback"] = traceback.format_exc()
    finally:
        result["source_unchanged"] = all(sha(HERE/k)==v for k,v in result["sources"].items())
        (args.output/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False),encoding="utf8")
        print(json.dumps(dict(status=result["status"],source_unchanged=result["source_unchanged"])))
    return 0 if result["status"] == "PASS_COMPLETE_REFERENCE_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())

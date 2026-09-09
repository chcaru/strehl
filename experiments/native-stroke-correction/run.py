"""One saved-patch proposal, then at most one held native RAW intervention."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec);sys.modules[name]=obj;spec.loader.exec_module(obj)
    return obj
m=module("correction_process",ROOT/"experiments/m193c-output-grid/bounded-process.py")
def ref(path):return dict(path=str(path.resolve()),**m.binding(path))
def read(path):return json.loads(path.read_text(encoding="utf-8"))
def save(path,value):
    with path.open("x",encoding="utf-8") as stream:
        json.dump(value,stream,indent=2,allow_nan=False);stream.write("\n")
assert sys.argv[1:] in (["propose"],["render"])
stage=sys.argv[1]
out=HERE/("run-1" if stage=="propose" else "render-1");out.mkdir()
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
sources=[ref(p) for p in sorted(HERE.glob("*.py"))]+[ref(HERE/"charter.md"),ref(HERE/"design.md")]
save(out/"execution.json",dict(stage=stage,sources=sources,
    revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    helper=ref(ROOT/"experiments/m193c-output-grid/bounded-process.py"),python=ref(Path(sys.executable))))
records=[]
def run(label,argv,fields,wall,cpu,commit):
    env,removed=m.clean_environment(fields)
    save(out/(label+"-invocation.json"),dict(command=argv,overrides=dict(fields),removed_environment=removed))
    result=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=wall,cpu_seconds=cpu,log_bytes=4<<20,committed_bytes=commit)
    save(out/(label+"-process.json"),result)
    print(json.dumps(dict(label=label,exit_code=result["exit_code"],error=result["error"],wall_seconds=result["wall_seconds"])),flush=True)
    assert result["exit_code"]==0 and result["error"] is None and result["terminal_job_accounting"] and not result["cleanup_errors"],"preserve failure; no automatic retry"
    records.append(dict(label=label,wall_seconds=result["wall_seconds"],
        cpu_seconds=result["job_accounting"]["total_cpu_100ns"]/1e7,
        peak_job_commit_bytes=result["job_memory"]["peak_job_memory_used_bytes"]))
    return result
if stage=="propose":
    argv=[sys.executable,"-I","-B",str(HERE/"propose.py")]
    fields=[("OPENBLAS_NUM_THREADS","1"),("OMP_NUM_THREADS","1")]
    run("controls",argv+["controls","--out",str(out/"controls")],fields,60,30,1<<30)
    run("proposal",argv+["propose","--out",str(out)],fields,60,30,1<<30)
    proposal=read(out/"proposal.json")
    assert isinstance(proposal["proceed_to_render"],bool)
    assert sum(v["cpu_seconds"] for v in records)<=60
    assert sum(p.stat().st_size for p in out.rglob("*") if p.is_file())<=64<<20
    save(out/"completion.json",dict(status="PROPOSAL_COMPLETE",proceed_to_render=proposal["proceed_to_render"],steps=records))
else:
    proposal=read(HERE/"run-1/proposal.json")
    assert proposal["proceed_to_render"] is True,"declined proposal cannot render"
    assert read(HERE/"run-1/execution.json")["sources"]==sources
    sidecar=HERE/"run-1/nominated-map.txt"
    assert sidecar.is_file()
    assert ref(sidecar)==proposal["map"], "sidecar differs from admitted proposal"
    product=ROOT/"experiments/native-product-comparison/run-1"
    prior=read(product/"plan.json")
    native=Path(prior["native"]["path"]);warp=Path(prior["map"]["path"])
    assert ref(native)==prior["native"] and ref(warp)==prior["map"]
    baseline=read(product/"native-output.json")
    assert ref(Path(baseline["output"]["path"]))==baseline["output"]
    for item in prior["inputs"]:
        st=Path(item["path"]).stat()
        assert st.st_size==item["bytes"] and st.st_mtime_ns==item["mtime_ns"]
    old=prior["plans"][0]
    argv=old["command"].copy()
    final=out/"corrected-coffee-bean.tiff"
    assert argv[-2]=="--out";argv[-1]=str(final)
    fields=[(k,v) for k,v in old["fields"] if k!="STREHL_DEFECT"]
    fields += [("STREHL_DEFECT","on"),("STREHL_DEFECT_MAP",str(sidecar)),("STREHL_DEFECT_ARM","dust")]
    save(out/"plan.json",dict(original_plan=ref(product/"plan.json"),baseline=baseline,
        native=ref(native),map=ref(warp),sidecar=ref(sidecar),proposal=ref(HERE/"run-1/proposal.json"),
        changes=["fresh output path","one nominated defect sidecar with unchanged validation"],
        validator_indices=[0,15,30,45,59,74,89,104],
        scope="one existing-feature causal/visual intervention; gain-squared variance propagation incomplete; no default/noise/SOTA promotion"))
    run("native",argv,fields,600,900,4<<30)
    assert final.stat().st_size<=256<<20
    import hashlib
    import tifffile
    import numpy as np
    with tifffile.TiffFile(final) as tf:
        pix=tf.asarray()
        assert pix.dtype==np.uint16 and list(pix.shape)==baseline["decoded"]["shape"]
        decoded=dict(shape=list(pix.shape),dtype=str(pix.dtype),bytes=pix.nbytes,
            sha256=hashlib.sha256(pix.tobytes(order="C")).hexdigest())
    del pix
    for item in prior["inputs"]:
        st=Path(item["path"]).stat()
        assert st.st_size==item["bytes"] and st.st_mtime_ns==item["mtime_ns"]
    save(out/"completion.json",dict(status="CORRECTED_PHOTOGRAPH_PENDING_INDEPENDENT_REVIEW",steps=records,
        output=ref(final),decoded=decoded,original_metadata_unchanged=True))

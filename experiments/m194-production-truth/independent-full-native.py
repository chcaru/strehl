"""One final native developed-output arm against the completed M192d baseline.

Preregistered by root after finding that binned registry TIFFs do not exercise
RAW WB/XYZ metadata handoff into fullres MHC/linear-sRGB. No timing admission.
"""
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import uuid
import tifffile

HERE=Path(__file__).resolve().parent
api=runpy.run_path(str(HERE/"independent-native.py"))
ROOT=api["ROOT"]
sha=api["sha"]
manifest=api["manifest"]
REF=ROOT/"experiments/m192d-production-rehearsal/out-20260907-090514-892948"
STACK=Path("D:/personal/macro/bee-1-cpl")


def tiff(path):
    with tifffile.TiffFile(path) as f:
        p=f.pages[0]
        return dict(output_bytes=path.stat().st_size,output_sha256=sha(path).upper(),
                    pixel_sha256=hashlib.sha256(p.asarray().tobytes()).hexdigest().upper(),
                    shape=list(p.shape),dtype=str(p.dtype),bits_per_sample=p.bitspersample,
                    samples_per_pixel=p.samplesperpixel,software=p.tags["Software"].value)


def main():
    native_path=HERE/"independent-native.json"
    native=json.loads(native_path.read_text())
    assert native["pass_"] and "pre_cleanup" in native
    source_paths=[Path(x["path"]) for x in native["source_after"]]
    current=manifest(source_paths)
    assert [(x["path"],x["sha256"]) for x in current]==[(x["path"],x["sha256"]) for x in native["source_after"]]
    binary=Path(native["prospective_binary"]["path"])
    assert sha(binary)==native["prospective_binary"]["sha256"]
    refpath=REF/"00-record.json"
    reference=json.loads(refpath.read_text())
    assert reference["returncode"]==0 and reference["identity_matches"]
    assert reference["binary_sha256"].lower()==api["OLD_HASH"]
    before_output=Path(reference["output_path"])
    before_tiff=tiff(before_output)
    assert before_tiff==reference["tiff"]
    work=HERE/"work"/("independent-full-native-"+uuid.uuid4().hex[:12])
    work.mkdir()
    for name in ["cache","temp"]: (work/name).mkdir()
    sidecar=work/"n33.warpmap.txt"
    source_sidecar=Path(reference["environment"]["STREHL_WARPMAP"])
    shutil.copyfile(source_sidecar,sidecar)
    assert sha(sidecar).upper()==reference["sidecar_sha256"]
    selected=sorted(p for p in STACK.iterdir() if p.suffix.lower()==".arw")[:33]
    assert [p.name for p in selected]==[f"DSC{i:05d}.ARW" for i in range(1,34)]
    inputs_before=manifest(selected)
    original_inputs=json.loads((REF/"inputs-before.json").read_text())
    assert [(x["path"],x["bytes"],x["sha256"].upper()) for x in inputs_before]==[(x["path"],x["bytes"],x["sha256"].upper()) for x in original_inputs]
    inventory=lambda:[dict(name=p.name,bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,directory=p.is_dir()) for p in sorted(STACK.iterdir())]
    directory_before=inventory()
    clear_threads={"MKL_NUM_THREADS","NUMEXPR_NUM_THREADS","OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","RAYON_NUM_THREADS"}
    env={k:v for k,v in os.environ.items() if not k.startswith("STREHL_") and k not in clear_threads}
    env.update(STREHL_PYRAMID_WORKERS="8",STREHL_WARPMAP=str(sidecar),STREHL_CACHE_DIR=str(work/"cache"),TEMP=str(work/"temp"),TMP=str(work/"temp"))
    # Apply the exact known suffix explicitly; never execute an artifact's
    # arbitrary command. Only binary/output/isolated state paths differ.
    output=work/"output.tiff"
    cmd=[binary,"stack",STACK,"--limit","33","--out",output,"--merge","pyramid","--pyramid-gate","2.0","--resampler","catmull-rom","--cover","scale","--linear-srgb","--demosaic"]
    assert [str(x) for x in cmd[1:6]]==reference["argv"][1:6]
    assert [str(x) for x in cmd[7:]]==reference["argv"][7:]
    evidence=dict(schema="m194-independent-full-native-v1",reference_record=manifest([refpath])[0],
                  reference_tiff=before_tiff,reference_output=manifest([before_output])[0],
                  final_native_lineage=manifest([native_path])[0],binary=native["prospective_binary"],
                  source_before=current,input_before=inputs_before,directory_before=directory_before,
                  sidecar_before=manifest([source_sidecar,sidecar]),
                  environment={k:env.get(k) for k in sorted(set(reference["environment"])|set(native["build"]["environment"]))},
                  environment_policy="clear all inherited STREHL_* and five named thread controls; same registered N33W8 settings; isolated paths")
    try:
        record,text=api["invoke"](cmd,env,HERE/"independent-full-native.log")
        evidence["run"]=record
        assert "folded          : 33 / 33 frames" in text
        assert "ON (sidecar-override)" in text and "reference frame 16, 33 placed / 0 refused" in text
        assert "8 execution threads" in text
        evidence["tiff"]=tiff(output)
        evidence["output"]=manifest([output])[0]
        assert evidence["tiff"]==before_tiff
        evidence["pass_"]=True
    finally:
        evidence["input_after"]=manifest(selected)
        evidence["directory_after"]=inventory()
        evidence["source_after"]=manifest(source_paths)
        evidence["sidecar_after"]=manifest([source_sidecar,sidecar])
        evidence["inputs_unchanged"]=evidence["input_before"]==evidence["input_after"]
        evidence["directory_unchanged"]=evidence["directory_before"]==evidence["directory_after"]
        evidence["sources_unchanged"]=[(x["path"],x["sha256"]) for x in evidence["source_before"]]==[(x["path"],x["sha256"]) for x in evidence["source_after"]]
        evidence["sidecars_unchanged"]=evidence["sidecar_before"]==evidence["sidecar_after"]
        evidence["pass_"]=evidence.get("pass_",False) and all(evidence[k] for k in ["inputs_unchanged","directory_unchanged","sources_unchanged","sidecars_unchanged"])
        (HERE/"independent-full-native.json").write_text(json.dumps(evidence,indent=2)+"\n")
    assert evidence["pass_"]
    print(json.dumps({"pass":True,"tiff":evidence["tiff"],"input_count":len(selected)}))


if __name__=="__main__": main()

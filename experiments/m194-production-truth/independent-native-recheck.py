"""Rebuild final cleanup and compare only its two after arms to frozen before TIFFs."""
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import tifffile

HERE=Path(__file__).resolve().parent
api=runpy.run_path(str(HERE/"independent-native.py"))
ROOT=api["ROOT"]
sha=api["sha"]
manifest=api["manifest"]


def main():
    previous=HERE/"independent-native-pre-cleanup.json"
    evidence=json.loads(previous.read_text())
    assert evidence["pass_"]
    work=ROOT/evidence["work"]
    selected=[Path(x["path"]) for x in evidence["input_before"]]
    assert manifest(selected)==evidence["input_before"]
    assert api["inventory"]()==evidence["directory_before"]
    assert sha(work/"prospective-pre-cleanup.exe")==evidence["prospective_binary"]["sha256"]
    sources=[Path(x["path"]) for x in evidence["source_before"]]
    evidence["source_before"]=manifest(sources)
    evidence["actual_head"]=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    evidence["pre_cleanup"]={"record":previous.name,"sha256":sha(previous),
                             "binary_archive":str((work/"prospective-pre-cleanup.exe").relative_to(ROOT)),
                             "scope":"Only new source cleanup; rerun final candidate after arms, retain the same observed before TIFFs."}
    olddiff=HERE/"independent-native-source.diff"
    (HERE/"independent-native-source-pre-cleanup.diff").write_bytes(olddiff.read_bytes())
    olddiff.write_bytes(subprocess.check_output(["git","diff",api["STAMP"],"--","crates"],cwd=ROOT))
    evidence["source_diff_sha256"]=sha(olddiff)
    env=api["env_base"](work)
    known=set(evidence["build"]["environment"])
    buildenv=dict(env,STREHL_BUILD_ID=api["STAMP"])
    build,text=api["invoke"](["cargo","build","--release","-p","strehl-cli","--bin","strehl",
                               "--target-dir","target/m194-independent-release"],buildenv,HERE/"independent-native-final-build.log")
    assert "Compiling strehl-cli" in text
    build.update(rebuilt_cli=True,environment={k:buildenv.get(k) for k in sorted(known)})
    evidence["build"]=build
    binary=ROOT/"target/m194-independent-release/release/strehl.exe"
    evidence["prospective_binary"]=manifest([binary])[0]
    records=[]
    for alignment in ["off","sidecar"]:
        before=next(x for x in evidence["runs"] if x["alignment"]==alignment and x["arm"]=="before")
        assert sha(Path(before["output"]["path"]))==before["output"]["sha256"]
        runenv=dict(env)
        if alignment=="off": runenv["STREHL_ALIGN"]="0"
        else: runenv["STREHL_WARPMAP"]=str(work/"coffee-bean-20.warpmap.txt")
        output=work/f"{alignment}-after-final.tif"
        assert not output.exists(), "retain previous final results; use a fresh revision for another rerun"
        command=[binary,"stack",api["STACK"],"--merge","pyramid","--limit","20","--pyramid-gate","2.0","--out",output]
        record,text=api["invoke"](command,runenv,HERE/f"independent-native-{alignment}-after-final.log")
        assert "folded          : 20 / 20 frames" in text
        assert "ON (sidecar-override)" in text if alignment=="sidecar" else "alignment       : OFF" in text
        with tifffile.TiffFile(output) as f:
            p=f.pages[0]
            tiff=dict(shape=list(p.shape),dtype=str(p.dtype),software=p.tags["Software"].value,
                      pixels_sha256=hashlib.sha256(p.asarray().tobytes()).hexdigest())
        record.update(arm="after",alignment=alignment,output=manifest([output])[0],tiff=tiff,
                      environment={k:runenv.get(k) for k in sorted(known)},rayon_num_threads=runenv["RAYON_NUM_THREADS"],
                      temp=runenv["TEMP"],tmp=runenv["TMP"],execution_disposition="final-source candidate compared with preserved baseline")
        assert before["output"]["sha256"]==record["output"]["sha256"]
        assert before["tiff"]==record["tiff"]
        records.extend([before,record])
    evidence["runs"]=records
    evidence["input_after"]=manifest(selected)
    evidence["directory_after"]=api["inventory"]()
    evidence["source_after"]=manifest(sources)
    evidence["sidecar_after"]=manifest([api["SIDECAR"],work/"coffee-bean-20.warpmap.txt"])
    evidence["inputs_unchanged"]=evidence["input_before"]==evidence["input_after"]
    evidence["directory_unchanged"]=evidence["directory_before"]==evidence["directory_after"]
    evidence["source_content_unchanged"]=[(x["path"],x["sha256"]) for x in evidence["source_before"]]==[(x["path"],x["sha256"]) for x in evidence["source_after"]]
    evidence["sidecar_unchanged"]=evidence["sidecar_before"]==evidence["sidecar_after"]
    evidence["pass_"]=all(evidence[k] for k in ["inputs_unchanged","directory_unchanged","source_content_unchanged","sidecar_unchanged"])
    (HERE/"independent-native.json").write_text(json.dumps(evidence,indent=2)+"\n")
    assert evidence["pass_"]
    print(json.dumps({"pass":True,"native_pairs":2,"final_binary":evidence["prospective_binary"]["sha256"]}))


if __name__=="__main__": main()

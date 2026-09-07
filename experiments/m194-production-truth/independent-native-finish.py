"""Recover only the missing fourth render after the first driver's banner typo.

First three exit-0 executions and log hashes were returned by the tool before
the banner assertion failed. Require those exact original logs/binaries and
unchanged inputs/sources before reusing their outputs. No thresholds change.
"""
import hashlib
import json
from pathlib import Path
import runpy
import tifffile

HERE=Path(__file__).resolve().parent
api=runpy.run_path(str(HERE/"independent-native.py"))
ROOT=api["ROOT"]
sha=api["sha"]
manifest=api["manifest"]


def main():
    record_path=HERE/"independent-native.json"
    first=HERE/"independent-native-initial.json"
    assert not first.exists(), "do not overwrite first-attempt evidence"
    first.write_bytes(record_path.read_bytes())
    evidence=json.loads(first.read_text())
    assert evidence["error"]=="AssertionError()"
    for key in ["inputs_unchanged","directory_unchanged","source_content_unchanged","sidecar_unchanged"]:
        assert evidence[key]
    selected=[Path(x["path"]) for x in evidence["input_before"]]
    assert manifest(selected)==evidence["input_before"]
    assert api["inventory"]()==evidence["directory_before"]
    sources=[Path(x["path"]) for x in evidence["source_before"]]
    assert [(x["path"],x["sha256"]) for x in manifest(sources)]==[(x["path"],x["sha256"]) for x in evidence["source_before"]]
    work=ROOT/evidence["work"]
    binaries={"before":Path(evidence["baseline_binary"]["path"]),"after":Path(evidence["prospective_binary"]["path"])}
    for label,key in [("before","baseline_binary"),("after","prospective_binary")]:
        assert sha(binaries[label])==evidence[key]["sha256"]
    log_hashes={
        ("off","before"):"55e6c0ceb67c764a298597831ada32aa7c32e8e3468ef6873ef25a67b9a7cf21",
        ("off","after"):"6307b9922ab5513fd2a606f0460eb9aceecadd0343277b96ced34121911887e8",
        ("sidecar","before"):"d9b07c31e000d0df1787b7866258112c18c43c9367436c2080c9db9240e3968e",
    }
    known=set(evidence["build"]["environment"])
    records=[]
    for alignment in ["off","sidecar"]:
        for label,binary in binaries.items():
            env=api["env_base"](work)
            if alignment=="off": env["STREHL_ALIGN"]="0"
            else: env["STREHL_WARPMAP"]=str(work/"coffee-bean-20.warpmap.txt")
            output=work/f"{alignment}-{label}.tif"
            log=HERE/f"independent-native-{alignment}-{label}.log"
            command=[binary,"stack",api["STACK"],"--merge","pyramid","--limit","20","--pyramid-gate","2.0","--out",output]
            if (alignment,label) in log_hashes:
                assert sha(log)==log_hashes[(alignment,label)]
                text=log.read_text(encoding="utf-8")
                record=dict(command=[str(x) for x in command],exit_code=0,
                            log=str(log.relative_to(ROOT)),log_sha256=sha(log),
                            execution_disposition="reused first-attempt completed execution, observed exit0")
            else:
                assert not output.exists()
                record,text=api["invoke"](command,env,log)
                record["execution_disposition"]="missing fourth execution completed by recovery driver"
            assert "folded          : 20 / 20 frames" in text
            assert "ON (sidecar-override)" in text if alignment=="sidecar" else "alignment       : OFF" in text
            with tifffile.TiffFile(output) as f:
                p=f.pages[0]
                tiff=dict(shape=list(p.shape),dtype=str(p.dtype),software=p.tags["Software"].value,
                          pixels_sha256=hashlib.sha256(p.asarray().tobytes()).hexdigest())
            assert tiff["shape"]==[2344,3516,3] and tiff["dtype"]=="uint16"
            record.update(arm=label,alignment=alignment,output=manifest([output])[0],tiff=tiff,
                          environment={k:env.get(k) for k in sorted(known)},rayon_num_threads=env["RAYON_NUM_THREADS"],temp=env["TEMP"],tmp=env["TMP"])
            records.append(record)
    for a,b in [records[:2],records[2:]]:
        assert a["output"]["sha256"]==b["output"]["sha256"]
        assert a["tiff"]==b["tiff"]
    evidence["runs"]=records
    evidence["recovery"]={"initial_record":first.name,"initial_sha256":sha(first),
                          "correction":"Registry disposition on-sidecar-override is not log syntax; actual banner ON (sidecar-override). No product change.",
                          "rerun_scope":"Only fourth (sidecar after) execution; first three exit0 logs/binaries/input/source hashes validated and reused."}
    evidence.pop("error")
    evidence["input_after"]=manifest(selected)
    evidence["directory_after"]=api["inventory"]()
    evidence["source_after"]=manifest(sources)
    evidence["inputs_unchanged"]=evidence["input_before"]==evidence["input_after"]
    evidence["directory_unchanged"]=evidence["directory_before"]==evidence["directory_after"]
    evidence["source_content_unchanged"]=[(x["path"],x["sha256"]) for x in evidence["source_before"]]==[(x["path"],x["sha256"]) for x in evidence["source_after"]]
    evidence["pass_"]=all(evidence[k] for k in ["inputs_unchanged","directory_unchanged","source_content_unchanged","sidecar_unchanged"])
    assert evidence["pass_"]
    record_path.write_text(json.dumps(evidence,indent=2)+"\n")
    print(json.dumps({"pass":True,"native_pairs":2,"outputs":[{"alignment":r["alignment"],"arm":r["arm"],"sha256":r["output"]["sha256"]} for r in records]}))


if __name__=="__main__": main()

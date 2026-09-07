"""Causal control for the retained measured-floor storage-layout failure."""
import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    build=HERE/"consumer-build-2.json"; build_hash=sha(build)
    record=json.loads(build.read_text())
    work=HERE/"work"/("independent-padding-isolation-"+uuid.uuid4().hex[:10]);work.mkdir(parents=True)
    base=HERE/"work/independent-consumer-8240dcbdf7/baseline"
    rows=[];checks={};outputs={};plans={}
    for mode in ["measured","white"]:
        for layout in ["original","padded"]:
            m=base/("manifest.json" if layout=="original" else "padding.json")
            d=work/(mode+"-"+layout);d.mkdir()
            prefix=[sys.executable,"-B",str(HERE/"consumer-run.py")]
            flags=["--build-record",str(build),"--build-sha256",build_hash,"--manifest",str(m),"--manifest-sha256",sha(m),"--plan",str(d/"plan.json")]
            if mode=="white":flags +=["--diagnostic-white-floor"]
            for stage in ["plan","render"]:
                argv=prefix+[stage]+flags+["--log",str(d/(stage+"-command.log"))]
                if stage=="render":argv +=["--plan-sha256",sha(d/"plan.json"),"--subset","all","--output",str(d/"output.tif"),"--receipt",str(d/"receipt.json")]
                p=subprocess.run(argv,cwd=ROOT,capture_output=True)
                (d/(stage+"-driver.log")).write_bytes(p.stdout+p.stderr)
                rows.append(dict(argv=argv,exit_code=p.returncode,log=str(d/(stage+"-driver.log"))))
                assert p.returncode==0
            plans[(mode,layout)]=json.loads((d/"plan.json").read_text())
            outputs[(mode,layout)]=tifffile.imread(d/"output.tif")
    measured_delta=outputs[("measured","original")].astype(int)-outputs[("measured","padded")].astype(int)
    checks["measured-floor-reproduces-padding-failure"]=np.any(measured_delta!=0)
    checks["white-floor-padding-exact-TIFF"]=sha(work/"white-original/output.tif")==sha(work/"white-padded/output.tif")
    checks["white-floor-actually-changes-output"]=not np.array_equal(outputs[("measured","original")],outputs[("white","original")])
    checks["final-source-preserves-build1-original-TIFF"]=sha(work/"measured-original/output.tif")==sha(HERE/"work/independent-consumer-8240dcbdf7/full/output.tiff")
    checks["final-source-preserves-build1-padded-TIFF"]=sha(work/"measured-padded/output.tif")==sha(HERE/"work/independent-consumer-8240dcbdf7/padding-render/output.tiff")
    spec=importlib.util.spec_from_file_location("independent_padding_driver",HERE/"consumer-run.py")
    driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
    env=driver.controlled_env()
    env.update(STREHL_M194B_MODE="render",STREHL_M194B_MANIFEST=str(base/"manifest.json"),STREHL_M194B_MANIFEST_SHA256=sha(base/"manifest.json"),STREHL_M194B_PLAN=str(work/"measured-original/plan.json"),STREHL_M194B_PLAN_SHA256=sha(work/"measured-original/plan.json"),STREHL_M194B_SUBSET="all")
    command=[record["test_executable"]["path"],"--exact",driver.TEST,"--ignored","--test-threads=1","--nocapture"]
    for name, updates in [("unmarked-white",{"STREHL_GATE_FLOOR":"white"}), ("unpaired-marker",{"STREHL_M194B_DIAGNOSTIC":"white-floor-isolation"}), ("unknown-marker",{"STREHL_M194B_DIAGNOSTIC":"bogus"}), ("ordinary-plan-under-white",{"STREHL_GATE_FLOOR":"white","STREHL_M194B_DIAGNOSTIC":"white-floor-isolation"})]:
        d=work/name;d.mkdir();e=dict(env,**updates,STREHL_M194B_OUTPUT=str(d/"output.tif"),STREHL_M194B_RECEIPT=str(d/"receipt.json"))
        p=subprocess.run(command,cwd=ROOT,env=e,capture_output=True);(d/"command.log").write_bytes(p.stdout+p.stderr)
        checks["refuse-"+name]=p.returncode!=0 and not(d/"output.tif").exists()
        rows.append(dict(argv=command,environment={k:v for k,v in e.items() if k.startswith("STREHL_") or k=="RAYON_NUM_THREADS"},exit_code=p.returncode,log=str(d/"command.log")))
    checks={k:bool(v) for k,v in checks.items()}
    result=dict(schema="m194b-independent-padding-isolation-v1",pass_=all(checks.values()),checks=checks,work=str(work),build_sha256=build_hash,commands=rows,measured_changed_components=int(np.sum(measured_delta!=0)),measured_max_abs_lsb=int(np.max(abs(measured_delta))),scope="white-floor is a causal control, not baseline/candidate admission; measured-floor storage dependence remains")
    (HERE/"independent-padding-isolation.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result));assert result["pass_"]


if __name__=="__main__":main()

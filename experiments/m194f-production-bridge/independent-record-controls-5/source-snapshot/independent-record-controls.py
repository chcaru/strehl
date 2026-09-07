"""Fixture-only commissioning of final actual private-record and plan readers."""
import argparse
import copy
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import traceback

import numpy as np
import tifffile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value)
    return value
V=module("m194f_independent_verify",HERE/"independent-verify.py")
R=V.R


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    files=out/"fixtures";files.mkdir();snap=out/"source-snapshot";snap.mkdir()
    sources=[Path(__file__),HERE/"independent-verify.py",HERE/"independent-reader.py",HERE/"independent-record-controls-preregister.md"]
    before={p.relative_to(ROOT).as_posix():V.sha(p) for p in sources}
    for p in sources:shutil.copyfile(p,snap/p.name)
    result=dict(schema="m194f-independent-record-controls-v1",status="RUNNING",fixture_only=True,
                orig_argv=sys.orig_argv,executable=sys.executable,python=sys.version,xoptions=sys._xoptions,
                numpy=np.__version__,tifffile=tifffile.__version__,source_before=before,
                thread_environment={k:os.environ.get(k) for k in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS")},
                started_utc=datetime.now(timezone.utc).isoformat(),cases=[])
    start,cpu=time.perf_counter(),time.process_time()
    def case(name,fn,refuse=False):
        try:
            detail=fn();rec=dict(name=name,passed=not refuse,expected_refusal=refuse,detail=detail)
        except R.Refusal as error:rec=dict(name=name,passed=refuse,expected_refusal=refuse,refusal=str(error))
        except Exception as error:rec=dict(name=name,passed=False,expected_refusal=refuse,error=repr(error),traceback=traceback.format_exc())
        result["cases"].append(rec);print(json.dumps(rec,allow_nan=False),flush=True)
    def write(name,pixels,kind):
        path=files/(name+".tiff")
        tifffile.imwrite(path,pixels,photometric="rgb" if kind=="rgb" else "minisblack",metadata=None,
                         description=R.DESCRIPTION if kind=="rgb" else None,software=R.SOFTWARE if kind=="rgb" else False,
                         resolution=(1,1),resolutionunit="NONE",compression=None,rowsperstrip=5)
        return dict(path=str(path),sha256=V.sha(path),bytes=path.stat().st_size,width=pixels.shape[1],height=pixels.shape[0],
                    channels=3 if kind=="rgb" else 1,sample_type="u16",pixel_sha256_le=R.digest(pixels.astype("<u2").tobytes()),
                    software=R.SOFTWARE if kind=="rgb" else None)
    y,x=np.mgrid[:32,:48]
    rgb={s:R.quantize(R.oracle(s,x+6,y+10)) for s in ("constant","affine")}
    changed=R.oracle("affine",x+6,y+10);changed[16,23,1]+=64;rgb["mutation"]=R.quantize(changed)
    b,s,g=R.rank_oracle();sg=g.copy();sg.flat[0]=65535;ss=s.copy();ss.flat[0]=0
    private=dict(schema="m194f-private-controls-v1",status="complete",fixture_only=True,
                 rgb={k:write(k,v,"rgb") for k,v in rgb.items()},rgb_successful_decode_counts={k:[1]*5 for k in rgb},
                 gray=dict(rank=write("rank",g,"gray"),sentinel=write("sentinel",sg,"gray")),
                 crop_quad=dict(x=3,y=5,width=24,height=16),canonical_native_offset=[6,10],oracle_output_window=[14,14,34,18],
                 confidence_component=dict(native=[32,16],quad=[16,8],input_green_dn=[100,200,200,400,500],
                 merged_luma_dn=[99,100,200,201,300,400,500,501]*16,below=b.ravel().tolist(),seen=s.ravel().tolist(),
                 sentinel_below=b.ravel().tolist(),sentinel_seen=ss.ravel().tolist(),successful_decode_counts=[1]*5,
                 sentinel_index=0,reached_zero_index=1))
    def exercise(name,value):
        (files/(name+".json")).write_text(json.dumps(value,indent=2)+"\n",encoding="utf-8")
        evidence=V.verify_private(value)
        return {k:v["oracle"] for k,v in evidence.items()}
    case("private-complete-valid",lambda:exercise("valid",private))
    equivalent=copy.deepcopy(private)
    for key in ("input_green_dn","merged_luma_dn"):
        equivalent["confidence_component"][key]=[float(v) for v in equivalent["confidence_component"][key]]
    case("private-exact-float-DN-valid",lambda:exercise("float-dn",equivalent))
    extended=copy.deepcopy(private)
    for section in ("rgb","gray"):
        for record in extended[section].values():record["path"]="\\\\?\\"+record["path"]
    case("private-extended-Windows-paths-valid",lambda:exercise("extended-paths",extended))
    local=files/"path-control.txt";local.write_text("private path fixture",encoding="utf-8")
    case("extended-local-same-file",lambda:R.require(V.artifact_path("\\\\?\\"+str(local)) == local.resolve(),"extended path identity"))
    outside=str(ROOT.parent/"OUTSIDE-M194F-PATH-CONTROL-NONEXISTENT")
    case("ordinary-outside-root",lambda:V.artifact_path(outside),True)
    case("extended-outside-root",lambda:V.artifact_path("\\\\?\\"+outside),True)
    case("extended-UNC-refused",lambda:V.artifact_path("\\\\?\\UNC\\example\\share\\file"),True)
    mutations={
        "missing-scene":lambda p:p["rgb"].pop("constant"),
        "substitute-scene":lambda p:p["rgb"].update(constant=p["rgb"]["affine"]),
        "false-origin":lambda p:p.update(canonical_native_offset=[8,10]),
        "swap-crop":lambda p:p["crop_quad"].update(x=5,y=3),
        "wrong-window":lambda p:p.update(oracle_output_window=[13,14,33,18]),
        "wrong-dimensions":lambda p:p["rgb"]["affine"].update(width=47),
        "wrong-receipt-hash":lambda p:p["rgb"]["affine"].update(pixel_sha256_le="0"*64),
        "wrong-gray-software":lambda p:p["gray"]["rank"].update(software=R.SOFTWARE),
        "mutation-noop":lambda p:p["rgb"].update(mutation=p["rgb"]["affine"]),
        "rgb-decode-counter":lambda p:p["rgb_successful_decode_counts"].update(affine=[0]*5),
        "below-tie":lambda p:p["confidence_component"]["below"].__setitem__(2,3),
        "seen-count":lambda p:p["confidence_component"]["seen"].__setitem__(2,4),
        "component-decode-counter":lambda p:p["confidence_component"].update(successful_decode_counts=[2]*5),
        "red-luma":lambda p:p["confidence_component"].update(input_green_dn=[700]*5),
        "luma-bool":lambda p:p["confidence_component"]["merged_luma_dn"].__setitem__(0,True),
        "missing-unseen-state":lambda p:p["confidence_component"]["sentinel_seen"].__setitem__(0,5),
        "relocated-unseen":lambda p:p["confidence_component"].update(sentinel_index=53),
        "false-genuine":lambda p:p.update(fixture_only=False),
        "false-complete":lambda p:p.update(status="partial"),
    }
    for name,mutate in mutations.items():
        p=copy.deepcopy(private);mutate(p)
        case(name,lambda p=p,name=name:exercise(name,p),True)
    wrong_rgb=rgb["affine"].copy();wrong_rgb[15,20,2]+=200
    wrong_scale=np.floor(g.astype(float)*65535/1000+.5).astype(np.uint16)
    reached=sg.copy();reached.flat[1]=65535
    for name,section,key,payload,kind in (("rehashed-wrong-rgb","rgb","affine",wrong_rgb,"rgb"),
                                         ("rehashed-gray-scale","gray","rank",wrong_scale,"gray"),
                                         ("rehashed-sentinel-missing","gray","sentinel",g,"gray"),
                                         ("rehashed-reached-zero","gray","sentinel",reached,"gray")):
        p=copy.deepcopy(private);p[section][key]=write(name,payload,kind)
        case(name,lambda p=p,name=name:exercise(name,p),True)
    binding=files/"binding.bin";binding.write_bytes(b"PRIVATE CONTRACT FIXTURE, NO AUTHORITY")
    build=dict(test_executable=dict(sha256="1"*64,bytes=123))
    run=dict(observer="count",confidence=False,exposure=0,wb_mode="baseline")
    plan=dict(schema="m194f-consumer-plan-v1",authority=V.AUTHORITY,full_native=[64,48],full_quad=[32,24],
              environment=V.BASE_ENV,reference_original_index=2,reference_local_index=2,output_channels=3,
              crop_quad=dict(x=1,y=1,width=30,height=22),canonical_native_offset=[2,2],output_native=[60,44],cover_fit=dict(kind="Crop"),
              level_sizes=[[30,22],[15,11]],placements=[dict(original_index=i,local_index=i,quad_similarity=dict(a_re=1.0,a_im=0.0,b_re=0.0,b_im=0.0)) for i in range(5)],
              wb_mode="baseline",frame_wb_f32=[float(np.float32(4/3)),1.0,float(np.float32(5/3))],
              wb_f32=[float(np.float32(4/3)),1.0,float(np.float32(5/3))],normalization=dict(tiff_u16_to_dn=R.RANGE/65535,second_black_subtraction=False,input_rounding="ties-to-even",output_rounding="half-up after clipping"),
              noise=dict(gain_dn_per_e=.25,read_noise_e=4,black=512,white=15360,iso=160,prnu=False,provenance="Fallback: injected synthetic algorithm coefficients; noise draws off"),
              config=dict(merge="Pyramid",bands=3,gate=2.0,exponent=2.0,select="SoftPower",base="Mean",admission="HardFloor",mean_coarse=0,hull="InputRange",resampler="CatmullRom",demosaic="MHC",space="CameraLinear",fullres_gather=True,auto_exposure=False,photometric="Off",gate_floor_enabled=True,measured_floor_bands=0,floor_fallback="empty measured beta; existing per-band fixed beta",ca="off",defect="off",restoration="unset",confidence=False,exposure_stops=0),
              observer=dict(mode="count",excludes_planning_reads=True,excludes_raw_prologue=True),
              build=dict(test_executable_sha256="1"*64,bytes=123),input_bindings=dict(fixture=dict(path=str(binding),sha256=V.sha(binding),bytes=binding.stat().st_size)))
    def plan_case(name,p,settings=None):
        (files/("plan-"+name+".json")).write_text(json.dumps(p,indent=2)+"\n",encoding="utf-8")
        return V.check_plan(p,run if settings is None else settings,build)
    case("plan-valid-fixture-only",lambda:plan_case("valid",plan))
    p_mutations={
        "origin":lambda p:p.update(canonical_native_offset=[3,2]),
        "extent":lambda p:p.update(output_native=[62,44]),
        "gauge":lambda p:p.update(reference_original_index=0),
        "wb":lambda p:p.update(wb_f32=[1.,1.,1.]),
        "noise":lambda p:p["noise"].update(gain_dn_per_e=.5),
        "double-black":lambda p:p["normalization"].update(second_black_subtraction=True),
        "scale":lambda p:p["normalization"].update(tiff_u16_to_dn=15360/65535),
        "nonidentity":lambda p:p["placements"][1]["quad_similarity"].update(a_re=1.01),
        "frame-count":lambda p:p["placements"].pop(),
        "floor":lambda p:p["config"].update(measured_floor_bands=1),
        "levels":lambda p:p["level_sizes"].append([8,6]),
        "admission":lambda p:p["config"].update(admission="FloorPedestalV1"),
        "gate":lambda p:p["config"].update(gate=3.0),
        "observer":lambda p:p["observer"].update(mode="off"),
        "build":lambda p:p["build"].update(test_executable_sha256="0"*64),
    }
    for name,mutate in p_mutations.items():
        p=copy.deepcopy(plan);mutate(p)
        case("plan-"+name,lambda p=p,name=name:plan_case(name,p),True)
    red_plan=copy.deepcopy(plan);red_plan.update(wb_mode="red-double",wb_f32=[float(np.float32(8/3)),1.0,float(np.float32(5/3))])
    red_run=dict(run,wb_mode="red-double")
    case("plan-red-writer-WB-valid",lambda:plan_case("red-wb-valid",red_plan,red_run))
    for name,mutate in {
        "stale-prepared-WB":lambda p:p.update(wb_f32=plan["wb_f32"].copy()),
        "changed-frame-WB":lambda p:p.update(frame_wb_f32=p["wb_f32"].copy()),
        "stale-WB-mode":lambda p:p.update(wb_mode="baseline"),
        "green-renormalization":lambda p:p["wb_f32"].__setitem__(1,2.0),
    }.items():
        p=copy.deepcopy(red_plan);mutate(p)
        case("plan-"+name,lambda p=p,name=name:plan_case(name,p,red_run),True)
    p=copy.deepcopy(plan);p["config"]["exposure_stops"]=1
    case("plan-old-exposure-refuses",lambda:plan_case("old-exposure",p,dict(run,exposure=1)),True)
    p=copy.deepcopy(plan);p["wb_mode"]="unknown"
    case("plan-unknown-WB-mode",lambda:plan_case("unknown-wb",p,dict(run,wb_mode="unknown")),True)
    # Deliberately fake wrapper, never a real compiler/optical authority.
    private_path=files/"valid.json"
    private_ref=dict(path=private_path.relative_to(ROOT).as_posix(),sha256=V.sha(private_path),bytes=private_path.stat().st_size)
    fake_exe=dict(path=str(files/"NOT-A-REAL-EXECUTABLE.exe"),sha256="3"*64,bytes=9)
    fake_build=dict(test_executable=fake_exe,sources_after={"fixture": "4"*64})
    fake_drivers={"fixture-driver":"5"*64}
    log=files/"fixture-only-command.log"
    log.write_text("FIXTURE ONLY, NOT AN EXECUTED TEST\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 17 filtered out; finished in 0.01s\n",encoding="utf-8")
    wrapper=dict(schema="m194f-private-command-v1",command=[fake_exe["path"],"--exact",V.PRIVATE_TEST,"--ignored","--test-threads=1","--nocapture"],
                 interpreter_argv=["FIXTURE ONLY"],started_utc="fixture",ended_utc="fixture",exit_code=0,passed=True,
                 log=str(log),log_sha256=V.sha(log),build_sha256="6"*64,test_executable=fake_exe,
                 sources_before=dict(fake_build["sources_after"]),sources_after=dict(fake_build["sources_after"]),
                 driver_before=dict(fake_drivers),driver_after=dict(fake_drivers),environment=dict(V.BASE_ENV,STREHL_M194F_PRIVATE_OUTPUT=str(files)),
                 result=str(private_path),result_sha256=private_ref["sha256"])
    def wrapper_case(name,record):
        (files/("wrapper-"+name+".json")).write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
        V.check_private_command(record,private_ref,fake_build,"6"*64,fake_drivers)
    case("wrapper-valid-fixture-only",lambda:wrapper_case("valid",wrapper))
    w_mutations={
        "test-name":lambda w:w["command"].__setitem__(2,"no-such-test"),
        "executable":lambda w:w["test_executable"].update(sha256="0"*64),
        "build":lambda w:w.update(build_sha256="0"*64),
        "source-before":lambda w:w["sources_before"].update(fixture="0"*64),
        "source-after":lambda w:w["sources_after"].update(fixture="0"*64),
        "driver-before":lambda w:w["driver_before"].update(fixture="0"*64),
        "driver-after":lambda w:w["driver_after"].update(fixture="0"*64),
        "result-hash":lambda w:w.update(result_sha256="0"*64),
        "output-root":lambda w:w["environment"].update(STREHL_M194F_PRIVATE_OUTPUT=str(out)),
        "extra-env":lambda w:w["environment"].update(STREHL_GATE_FLOOR="debug"),
        "exit":lambda w:w.update(exit_code=1),
        "partial":lambda w:w.update(passed=False),
        "extra-key":lambda w:w.update(extra="unregistered"),
    }
    for name,mutate in w_mutations.items():
        w=copy.deepcopy(wrapper);mutate(w)
        case("wrapper-"+name,lambda w=w,name=name:wrapper_case(name,w),True)
    zero_log=files/"fixture-only-zero-test.log"
    zero_log.write_text("test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 17 filtered out; finished in 0.01s\n",encoding="utf-8")
    w=copy.deepcopy(wrapper);w.update(log=str(zero_log),log_sha256=V.sha(zero_log))
    case("wrapper-actual-zero-tests",lambda:wrapper_case("zero-tests",w),True)
    result.update(source_after={p.relative_to(ROOT).as_posix():V.sha(p) for p in sources},wall_seconds=time.perf_counter()-start,
                  cpu_seconds=time.process_time()-cpu,ended_utc=datetime.now(timezone.utc).isoformat())
    result["source_unchanged"]=result["source_before"]==result["source_after"]
    result["passed"]=sum(c["passed"] for c in result["cases"]);result["count"]=len(result["cases"])
    result["status"]="PASS_RECORD_INSTRUMENT_ONLY" if result["passed"]==result["count"] and result["source_unchanged"] else "FAIL_RECORD_INSTRUMENT"
    (out/"result.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    print(json.dumps(dict(status=result["status"],passed=result["passed"],count=result["count"],sha256=V.sha(out/"result.json"))))
    return 0 if result["status"].startswith("PASS") else 1


if __name__=="__main__":raise SystemExit(main())

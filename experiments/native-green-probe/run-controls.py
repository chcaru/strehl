"""Run the independent green-probe controls with existing bounded native process tools."""
from pathlib import Path
import importlib.util,json,sys,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
p=ROOT/"experiments/m193c-output-grid/bounded-process.py";s=importlib.util.spec_from_file_location("green_probe_control_process",p);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def save(p,v):
    with p.open("x",encoding="utf-8") as f:json.dump(v,f,indent=2);f.write("\n")
api=m.load_job_api(m.binding(ROOT/"experiments/m12-scorecard/m12-harness.py"))
assert sys.argv[1:] in ([], ["--revised-power"], ["--writeback"], ["--direct-planes"]), "only fixed control revisions are supported"
writeback=sys.argv[1:]==["--writeback"]
direct_planes=sys.argv[1:]==["--direct-planes"]
if direct_planes:HERE=ROOT/"experiments/native-direct-planes"
if writeback:HERE=ROOT/"experiments/native-parallel-writeback"
revised=sys.argv[1:]==["--revised-power"]
exe=HERE/("build-2/cli-tests.exe" if revised else "build-1/cli-tests.exe");assert m.binding(exe)["sha256"]==json.loads((exe.parent/"executables.json").read_text(encoding="utf-8"))["cli-tests"]["sha256"]
out=HERE/("controls-2" if revised else "controls-1");out.mkdir()
pairs=[]
for demosaic in ("malvar","directional"):
 for fullres in ("1","0"):
    previous=None
    for arm in (("off","rounded","float") if direct_planes else (("serial","parallel") if writeback else ("rgb","green"))):
        label=f"{demosaic}-fullres{fullres}-{arm}";dest=out/label
        assert not dest.exists()
        fields=[("STREHL_GREEN_PROBE_OUTPUT",str(dest)),("STREHL_PYRAMID_PROFILE","off"),("RAYON_NUM_THREADS","4"),("STREHL_PYRAMID_WORKERS","4"),("STREHL_DEMOSAIC",demosaic),("STREHL_FULLRES_GATHER",fullres),("STREHL_PROBE_GATHER","green" if (writeback or direct_planes) else arm)]
        if writeback:fields.append(("STREHL_WARP_WRITEBACK",arm))
        if direct_planes:fields.append(("STREHL_DIRECT_PLANES",arm))
        env,removed=m.clean_environment(fields)
        test_filter="merge_cmd::gatefloor::native_parallel_writeback_independent_tests::independent_parallel_writeback_controls" if writeback else "merge_cmd::gatefloor::native_green_probe_independent_tests::independent_green_probe_controls"
        if direct_planes:test_filter="merge_cmd::gatefloor::native_direct_planes_independent_tests::independent_direct_planes_controls"
        argv=[str(exe),test_filter,"--exact","--nocapture","--test-threads=1"]
        save(out/(label+"-invocation.json"),dict(command=argv,executable=m.binding(exe),environment_overrides=dict(fields),removed_environment=removed,revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()))
        r=m.run(argv,env,ROOT,out/(label+".log"),api=api,wall_seconds=60,cpu_seconds=180,log_bytes=2<<20,committed_bytes=2<<30)
        save(out/(label+"-process.json"),r)
        print(json.dumps(dict(label=label,exit_code=r["exit_code"],error=r["error"],wall_seconds=r["wall_seconds"])),flush=True)
        assert r["exit_code"]==0 and r["error"] is None and r["terminal_job_accounting"] and not r["cleanup_errors"]
        result=json.loads((dest/"result.json").read_text(encoding="utf-8"))
        if writeback:
            direct=json.loads((dest/"writeback-result.json").read_text(encoding="utf-8"))
            assert direct["requested_writeback"]==arm and direct["direct_comparisons"]==2304 and direct["wrong_stride_phase_and_coverage_controls_live"]
        if direct_planes:
            direct=json.loads((dest/"direct-planes-result.json").read_text(encoding="utf-8"))
            assert direct["requested_mode"]==arm and direct["old_scalar_comparisons"]==2304
            assert direct["actual_fractional_changed_sites"]>0 and direct["rounded_crop_green_allcolour_source_storage_controls"]
            log=(out/(label+".log")).read_text(encoding="utf-8")
            assert "1 passed" in log and "NATIVE_DIRECT_PLANES" in log
        if previous is None:previous=(dest,result)
        else:
            equal_measurements=result["measurements"]==previous[1]["measurements"]
            equal_tiffs={name:(dest/name).read_bytes()==(previous[0]/name).read_bytes() for name in ("whole.tif","crop.tif")}
            must_equal=not direct_planes or arm=="rounded" or fullres=="0"
            if must_equal:
                assert equal_measurements,"green beta/measurement bytes differ"
                assert all(equal_tiffs.values()),"whole output bytes differ"
            pairs.append(dict(demosaic=demosaic,fullres=fullres,arm=arm,measurements_equal=equal_measurements,tiffs_equal=equal_tiffs,required_equal=must_equal,whole_tiff=m.binding(dest/"whole.tif"),crop_tiff=m.binding(dest/"crop.tif")))
save(out/"results.json",dict(status="TWELVE_DIRECT_PLANES_CONTROLS_PASS" if direct_planes else ("EIGHT_WRITEBACK_CONTROLS_PASS" if writeback else "EIGHT_GREEN_PROBE_CONTROLS_PASS"),pairs=pairs,scope="exact generated green/beta and whole/crop output controls; no photographic-quality or speed claim"))
print(json.dumps(dict(status="CONTROLS_PASS",pairs=len(pairs))),flush=True)


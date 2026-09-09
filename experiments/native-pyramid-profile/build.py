"""Compile current CLI and its tiny profiler control; reuse the existing bounded builder."""
from pathlib import Path
import importlib.util,json,sys,hashlib,shutil,subprocess,argparse
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
p=ROOT/"experiments/m194h-pedestal-causality/bounded-build-process.py"
spec=importlib.util.spec_from_file_location("phase_profile_build",p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def ref(p):
    raw=p.read_bytes();return dict(path=str(p.relative_to(ROOT)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def save(p,x):
    with p.open("x",encoding="utf-8") as f:json.dump(x,f,indent=2);f.write("\n")
job=ROOT/"experiments/m12-scorecard/m12-harness.py"
api=m.load_job_api({k:v for k,v in ref(job).items() if k!="path"})
parser=argparse.ArgumentParser();parser.add_argument("--output-dir",type=Path,default=HERE/"build-1");parser.add_argument("--boundary-radiance",action="store_true");parser.add_argument("--direct-planes",action="store_true");parser.add_argument("--correction-variance",action="store_true");parser.add_argument("--green-cue",action="store_true");parser.add_argument("--gpu-gather",action="store_true");args=parser.parse_args()
assert not (args.boundary_radiance and args.direct_planes),"one fixed development feature per build"
features="native-pyramid-profile,native-boundary-radiance" if args.boundary_radiance else "native-pyramid-profile"
if args.direct_planes:features="native-pyramid-profile,native-direct-planes"
if args.correction_variance:
    assert args.direct_planes and not args.boundary_radiance, "fixed correction transfer uses direct-planes fixture"
    features+=",native-correction-variance"
if args.green_cue:
    assert not (args.boundary_radiance or args.direct_planes or args.correction_variance), "green cue is one separate fixed candidate"
    features+=",native-green-cue"
if args.gpu_gather:
    assert not (args.boundary_radiance or args.direct_planes or args.correction_variance or args.green_cue), "GPU gather is one separate candidate"
    features+=",native-gpu-gather"
out=args.output_dir.resolve();assert out.is_relative_to(ROOT);out.mkdir()
env,removed=m.clean_environment([("RAYON_NUM_THREADS","8"),("CARGO_INCREMENTAL","0")])
argv=["cargo","test","-p","strehl-cli","--bin","strehl","--test","byte-freeze","--no-run","--release","--features",features,"--jobs","2","--target-dir",str(ROOT/"target/native-pyramid-profile"),"--message-format=json-render-diagnostics","--locked","--offline"]
save(out/"invocation.json",dict(command=argv,revision=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),environment_overrides={"RAYON_NUM_THREADS":"8","CARGO_INCREMENTAL":"0"},removed_environment=removed,source_files=[ref(ROOT/p) for p in ["crates/strehl-cli/Cargo.toml","crates/strehl-cli/src/merge_cmd.rs","experiments/native-pyramid-profile/implementation.rs","experiments/native-pyramid-profile/build.py","crates/strehl-cli/src/merge_cmd/gatefloor.rs","crates/strehl-cli/src/align_cmd.rs","crates/strehl-core/src/demosaic.rs"]+(["experiments/native-boundary-radiance/implementation.rs","experiments/native-boundary-radiance/independent-tests.rs","experiments/native-boundary-radiance/source-hook.rs","experiments/native-boundary-radiance/bridge.rs","crates/strehl-cli/src/merge_cmd/noise-pupil-bridge.rs","crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs"] if args.boundary_radiance else [])+(["experiments/native-direct-planes/implementation.rs","experiments/native-direct-planes/independent-tests.rs","experiments/native-parallel-writeback/independent-tests.rs","experiments/native-green-probe/independent-tests.rs","experiments/native-direct-planes/bridge.rs","experiments/native-direct-planes/bridge-controls.rs","crates/strehl-cli/src/merge_cmd/known-scene-benchmark.rs"] if args.direct_planes else [])+(["experiments/native-correction-variance/core-bridge.rs","experiments/native-correction-variance/implementation.rs","experiments/native-correction-variance/independent-controls.rs","crates/strehl-core/Cargo.toml","crates/strehl-core/src/pyramid.rs"] if args.correction_variance else [])+(["crates/strehl-core/Cargo.toml","crates/strehl-core/src/pyramid.rs","Cargo.lock","experiments/native-green-cue/implementation.rs","experiments/native-green-cue/independent-controls.rs","experiments/native-green-cue/design.md","experiments/native-green-cue/charter.md"] if args.green_cue else [])+(['Cargo.toml', 'Cargo.lock', 'crates/strehl-core/Cargo.toml', 'crates/strehl-core/src/align.rs', 'crates/strehl-core/src/optics.rs', 'experiments/native-gpu-gather/Cargo.toml', 'experiments/native-gpu-gather/src/lib.rs', 'experiments/native-gpu-gather/src/strict-spirv.rs', 'experiments/native-gpu-gather/src/gather.wgsl', 'experiments/native-gpu-gather/cpu-bridge.rs', 'experiments/native-gpu-gather/independent-tests.rs', 'experiments/native-gpu-gather/independent-design.md', 'experiments/native-gpu-gather/charter.md', 'experiments/m194c-probe-layout/independent-tests.rs'] if args.gpu_gather else [])],scope="release compile only; existing integration test is compiled to obtain CLI artifact and is not executed"))
r=m.run(argv,env,ROOT,out/"compile.log",api=api,wall_seconds=600,cpu_seconds=1800,log_bytes=16<<20,committed_bytes=(8 if args.gpu_gather else 4)<<30)
save(out/"build-result.json",r)
print(json.dumps(dict(exit_code=r["exit_code"],error=r["error"],wall_seconds=r["wall_seconds"])),flush=True)
assert r["exit_code"]==0 and r["error"] is None
log=(out/"compile.log").read_text(encoding="utf-8",errors="replace")
assert "Compiling strehl-cli" in log
artifacts={}
for line in log.splitlines():
    try:a=json.loads(line)
    except ValueError:continue
    if a.get("reason")=="compiler-artifact" and a.get("executable") and a.get("target",{}).get("name")=="strehl":
        key="cli-tests" if a["profile"]["test"] else "strehl"
        assert key not in artifacts
        exe=out/(key+".exe");shutil.copyfile(a["executable"],exe);artifacts[key]=ref(exe)
save(out/"executables.json",artifacts)
assert set(artifacts)=={"cli-tests","strehl"},artifacts
print(json.dumps(dict(compiled_cli=True,artifacts=artifacts)),flush=True)

"""Independent direct source/log/binary read for the final fixed candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE=HERE.parent/"m194b-known-scene"


def sha(path):
    with Path(path).open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding="utf-8"))
def committed(path):return subprocess.check_output(["git","show","444eb759:"+path],cwd=ROOT)


def main():
    ap=argparse.ArgumentParser();ap.add_argument("--controller",type=Path,required=True);ap.add_argument("--sha256",required=True);args=ap.parse_args()
    p=args.controller.resolve();assert sha(p)==args.sha256
    record=load(p);build_path=p.parent/"build.json";assert sha(build_path)==record["build_sha256"]
    build=load(build_path);assert build["sources_before"]==build["sources_after"]
    old_index=load(BASE/"baseline-1/run-index.json");old_build=load(old_index["build_record"]["path"])
    actual_changed=sorted(k for k in set(build["sources_after"])|set(old_build["sources_after"]) if build["sources_after"].get(k)!=old_build["sources_after"].get(k))
    gate="crates/strehl-cli/src/merge_cmd/gatefloor.rs"
    assert actual_changed==[gate]
    assert all(sha(ROOT/k)==h for k,h in build["sources_after"].items())
    extra=record["supplemental_before"];assert extra==record["supplemental_after"]
    assert all(sha(ROOT/k)==h and sha(Path(record["supplemental_snapshots_root"])/k)==h for k,h in extra.items())
    rs={k for k in extra if k.endswith(".rs")}
    prefix="experiments/m194c-probe-layout/"
    assert rs=={prefix+n for n in ("author-tests.rs","independent-tests.rs","legacy-fill-noise.rs")}
    # Directly inspect this actual include form, independently of controller regex.
    compact=lambda q:"".join(Path(q).read_text().split())
    for n in ("author-tests.rs","independent-tests.rs"):
        assert 'include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../'+prefix+n+'"));' in compact(ROOT/gate)
    assert 'include!(concat!(env!("CARGO_MANIFEST_DIR"),"/../../'+prefix+'legacy-fill-noise.rs"));' in compact(HERE/"author-tests.rs")
    original=committed(gate).decode();legacy=(HERE/"legacy-fill-noise.rs").read_text()
    assert original[original.index("fn fill_noise("):]==legacy
    # Arithmetic body changes only its destination iterator, not RNG/draw math.
    current=(ROOT/gate).read_text();start=current.index("    // SplitMix64.")
    end=current.index("\n#[cfg(test)]",start)
    new_body=current[start:end].strip().replace("for d in data {","for d in data.iter_mut() {")
    old_body=original[original.index("    // SplitMix64."):].strip()
    assert new_body==old_body
    frozen={}
    for name,h in record["frozen_m194b_files"].items():
        rel="experiments/m194b-known-scene/"+name
        assert sha(BASE/name)==h==hashlib.sha256(committed(rel)).hexdigest();frozen[name]=h
    log_path=Path(build["log"]);assert sha(log_path)==build["log_sha256"]
    log=log_path.read_text();assert "Compiling strehl-cli" in log
    events=[json.loads(line) for line in log.splitlines() if line.startswith('{"reason":')]
    artifacts=[e for e in events if e["reason"]=="compiler-artifact" and e.get("target",{}).get("name")=="strehl" and e.get("executable")]
    assert len(artifacts)==1 and artifacts[0]["fresh"] is False
    assert Path(artifacts[0]["executable"]).resolve()==Path(build["compiler_artifact"]["path"]).resolve()
    assert any(e.get("reason")=="build-finished" and e.get("success") is True for e in events)
    binaries={}
    for name in ["compiler_artifact","test_executable"]:
        b=build[name];bp=Path(b["path"]);assert sha(bp)==b["sha256"] and bp.stat().st_size==b["bytes"];binaries[name]=b
    assert binaries["compiler_artifact"]["sha256"]==binaries["test_executable"]["sha256"]
    original_binary=Path(old_build["test_executable"]["path"])
    assert sha(original_binary)==old_build["test_executable"]["sha256"]=="92d2a31b03152c88060d7c2355b6071acf73e74450ca1cd3606f85f6ee814dc5"
    assert original_binary!=Path(build["test_executable"]["path"])
    assert sha(p)==args.sha256 and all(sha(ROOT/k)==h for k,h in extra.items())
    out=dict(schema="m194c-independent-comparison-provenance-v1",pass_=True,controller_sha256=args.sha256,
             changed_tracked_compiler_inputs=actual_changed,tracked_source_count=len(build["sources_after"]),
             extra_source_count=len(extra),external_rust=sorted(rs),supplemental=extra,
             actual_compilation_line=True,actual_fresh_compiler_artifact=True,actual_binary_bindings=binaries,
             legacy_draw_arithmetic_text_unchanged=True,frozen_m194b_files=frozen,baseline_binary_unchanged=True,
             scope="actual recorded source, byte snapshots, compiler log, compiler artifact and copied executable; independent of controller's booleans")
    (HERE/"independent-comparison-provenance.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(dict(pass_=True,tracked_source_count=out["tracked_source_count"],extra_source_count=len(extra),binary_sha256=build["test_executable"]["sha256"])))


if __name__=="__main__":main()

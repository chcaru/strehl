"""Read-only exact-core mask response; not photographic tail attribution."""
from pathlib import Path
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "mask-membership-1"

def bind(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

def main():
    OUT.mkdir()
    source = (HERE / "implementation.rs").read_text()
    start = source.index("pub(crate) const SEGMENTS:")
    end = source.index("fn digest(")
    geometry = source[start:end]
    body = r'''
use strehl_core::pyramid::{level_sizes,Pyramid,Workspace};
use strehl_core::pyramid::donor_consistency_diagnostic::DonorBlend;
fn main() {
 let sizes=level_sizes(3460,2306,7);let masks=fixed_masks(3460,2306,[0,0]);
 let mix=DonorBlend::new(&sizes,4,&masks);let mut ws=Workspace::new(&sizes);
 let points=[("facet-core",2624,2906),("facet-fan",2602,2945),
 ("dark-core",3080,2150),("dark-fan",3102,2203),("nearby",3240,2070)];
 for k in 0..sizes.len()-1 {
  let mut p=Pyramid::zeros(&sizes);p.level_mut(k).copy_from_slice(mix.coverage().level(k));
  let up=p.collapse(&mut ws);
  for &(name,x,y) in &points {let j=(y/2)*3460+x/2;
   println!("{}",serde_json::json!({"point":name,"output_native_xy":[x,y],
    "level":k,"effective_weight_for_constant_coefficient":up[j],
    "native_mask":mix.coverage().level(0)[j]}));
  }
 }
}
'''
    harness = OUT / "membership.rs"
    harness.write_text(geometry + body)
    libraries = {}
    for line in (HERE / "build-2/process.log").read_text().splitlines():
        try: row = json.loads(line)
        except ValueError: continue
        name = row.get("target", {}).get("name")
        if row.get("reason") == "compiler-artifact" and name in ("strehl_core", "serde_json"):
            libraries[name] = Path(next(v for v in row["filenames"] if v.endswith(".rlib")))
    assert len(libraries) == 2
    prior = json.loads((HERE / "build-2/sources.json").read_text())
    for relative in ("crates/strehl-core/src/pyramid.rs", "experiments/donor-consistency/core-bridge.rs"):
        path = ROOT / relative
        record = next(r for r in prior if Path(r["path"]) == path)
        assert bind(path)["sha256"] == record["sha256"]
    command = ["rustc", "--edition=2021", "-O", "-C", "lto=thin", str(harness),
        "-L", "dependency=" + str(libraries["strehl_core"].parent), "-o", str(OUT / "membership.exe")]
    for name, path in libraries.items(): command += ["--extern", name + "=" + str(path)]
    compiled = subprocess.run(command, capture_output=True, text=True, timeout=90)
    (OUT / "compile.log").write_text(compiled.stdout + compiled.stderr)
    assert compiled.returncode == 0, compiled.stderr
    run = subprocess.run([str(OUT / "membership.exe")], capture_output=True, text=True, timeout=60)
    (OUT / "process.log").write_text(run.stdout + run.stderr)
    assert run.returncode == 0, run.stderr
    records = [json.loads(line) for line in run.stdout.splitlines()]
    assert len(records) == 35
    result = {"scope": "Exact production collapse of one mask level carrying unit AC; not actual image coefficients or a quality metric",
        "sources": [bind(Path(__file__)), bind(harness), bind(HERE / "implementation.rs")],
        "libraries": [bind(v) for v in libraries.values()], "command": command, "records": records}
    (OUT / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(records))

if __name__ == "__main__": main()

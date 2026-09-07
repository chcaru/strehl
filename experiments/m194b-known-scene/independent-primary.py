"""Read actual primary CFA/cache package against independent model references."""
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    package = HERE / "producer-output-1"
    result = json.loads((package / "producer-result.json").read_text())
    commission_path = HERE / "producer-commission-1/commission.json"
    commission = json.loads(commission_path.read_text())
    spec = importlib.util.spec_from_file_location("independent_primary_optics", HERE / "independent-optics.py")
    optical = importlib.util.module_from_spec(spec); spec.loader.exec_module(optical)
    before = {p.relative_to(package).as_posix(): sha(p) for p in package.rglob("*") if p.is_file()}
    checks = {"terminal-package": result["status"] == "complete" and result["refused_scenes"] == {},
              "commission-binding": result["commission_sha256"] == sha(commission_path),
              "producer-sources-unchanged": result["sources_before"] == result["sources_after"],
              "commission-sources-unchanged": commission["source_before"] == commission["source_after"],
              "primary-seven-groups-pass": len(commission["groups"]) == 7 and all(v["status"] == "pass" for v in commission["groups"].values())}
    for p, h in result["sources_before"].items(): checks["source:"+p] = sha(ROOT / p) == h
    inputs = {}; manifests = {}; caches = {}
    for item in result["manifests"]:
        p = package / item["path"]; m = json.loads(p.read_text()); key = (m["scene"], m["repeat"])
        assert sha(p) == item["sha256"] and key not in manifests
        manifests[key] = m
        frames = []
        for i, f in enumerate(m["frames"]):
            path = p.parent / f["path"]
            assert i == f["index"] and path.stat().st_size == 153600 == f["bytes"] and sha(path) == f["sha256"]
            frames.append(np.frombuffer(path.read_bytes(), dtype="<u2").reshape(240, 320))
        assert len(frames) == 9
        inputs[key] = np.stack(frames)
        cache = package / (m["scene"] + "-expected-electrons.npy")
        assert sha(cache) == m["producer"]["expected_electrons_sha256"]
        if m["scene"] not in caches: caches[m["scene"]] = np.load(cache, allow_pickle=False)
    expected_keys = {(scene, seed) for scene in ["flat", "plane"] for seed in [None,701,709,719,727,733,739,743,751]} | {("color",None),("color-null",None)}
    checks["actual-20-cases-180-CFA-bindings"] = set(manifests) == expected_keys
    checks["actual-four-expected-array-shapes"] = all(v.shape == (9,240,320) and v.dtype == np.float64 and np.isfinite(v).all() for v in caches.values())
    checks["all-noiseoff-quantized-cache-bytes"] = all(np.array_equal(inputs[(scene,None)], np.rint(e*.25+512).clip(0,15360).astype("<u2")) for scene,e in caches.items())
    y,x = np.indices((240,320),dtype=float)
    roi = (x>=64)&(x<256)&(y>=64)&(y<176)
    cf = np.ones(x.shape); cf[::2,::2]=.75; cf[1::2,1::2]=.6
    wb = np.ones(x.shape); wb[::2,::2]=float(np.float32(4/3)); wb[1::2,1::2]=float(np.float32(5/3))
    rows=[]
    for k in range(9):
        s=manifests[("plane",None)]["geometry"]["frames"][k]["scale"]
        qx=183+(x-183)/s; qy=101+(y-101)/s
        field=np.full(x.shape,12000.)
        for amp,fx,fy,phase in [(1800.,1/16,1/24,.2),(900.,1/8,-1/16,1.1)]:
            freq=np.hypot(fx,fy)/s
            transfer=optical.pupil_overlap(freq,5.12/(.535*16))*optical.disc_cosine(freq,1.5*abs(k-4))
            offsets=(np.arange(4)+.5)/4-.5
            aperture=sum(np.exp(2j*np.pi*(fx*a+fy*b)/s) for a in offsets for b in offsets)/16
            field+=amp*transfer*np.real(aperture*np.exp(1j*(2*np.pi*(fx*qx+fy*qy)+phase)))
        delta=(caches["plane"][k]-field*cf)*.25*wb
        parities=[]
        for dy,dx in [(0,0),(0,1),(1,0),(1,1)]:
            v=delta[dy::2,dx::2][roi[dy::2,dx::2]]
            parities.append(dict(rms_dn=float(np.sqrt(np.mean(v*v))),max_abs_dn=float(np.max(abs(v)))))
        rows.append(dict(original_index=k,scale=s,parities=parities))
    checks["primary-actual-cache-independent-disc-pupil-cell"] = max(p["rms_dn"] for r in rows for p in r["parities"]) <= .5
    noise=[]
    for scene in ["flat","plane"]:
        cube=np.stack([inputs[(scene,seed)].astype(float) for seed in [701,709,719,727,733,739,743,751]])
        expected_var=.25**2*(caches[scene]+16)+1/12
        variance=cube.var(axis=0,ddof=1)
        ratios=[]
        for dy,dx in [(0,0),(0,1),(1,0),(1,1)]:
            ratios.append(float(variance[:,dy::2,dx::2].mean()/expected_var[:,dy::2,dx::2].mean()))
        noise.append(dict(scene=scene,temporal_variance_ratio_by_CFA=ratios,repeat_count=8))
    # Same independently preregistered 2% finite noise-model component check;
    # this is across actual emitted input repetitions, never spatial texture SD.
    checks["actual-primary-repeat-noise-law"] = max(abs(r-1) for row in noise for r in row["temporal_variance_ratio_by_CFA"]) <= .02
    after={p.relative_to(package).as_posix():sha(p) for p in package.rglob("*") if p.is_file()}
    checks["package-bytes-unchanged"] = before == after
    checks={k:bool(v) for k,v in checks.items()}
    out=dict(schema="m194b-independent-primary-v1",pass_=all(checks.values()),checks=checks,
             producer_result_sha256=sha(package/"producer-result.json"),commission_sha256=sha(commission_path),
             package_files_sha256=before,cache_agreement=rows,actual_repeat_noise=noise,
             scope="fixed synthetic primary input package and mathematical model; no physical calibration")
    (HERE/"independent-primary.json").write_text(json.dumps(out,indent=2)+"\n")
    print(json.dumps(dict(pass_=out["pass_"],checks=checks,max_cache_rms_dn=max(p["rms_dn"] for r in rows for p in r["parities"]),noise=noise)))
    if not out["pass_"]:raise SystemExit(1)


if __name__=="__main__":main()

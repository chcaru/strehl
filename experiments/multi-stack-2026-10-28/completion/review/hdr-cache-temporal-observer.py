"""Cache-only original-CFA temporal observer; no RAW decoder or render entry point."""
from pathlib import Path
import argparse, hashlib, json, os, struct, subprocess, sys, time, tomllib
import psutil
import numpy as np
from scipy.ndimage import gaussian_filter

ROOT = Path(__file__).resolve().parents[4]
CACHE = ROOT / "outputs/multi-stack/hdr-source-cache"
RENDER = ROOT / "outputs/multi-stack/slide-hdr-pair-6"
GUIDES = [20, 23, 27, 31, 35, 39, 42]
VALIDATE = [22, 40]
MEASURE = [24, 25, 26, 28, 29, 30, 32, 33, 34, 36, 37, 38]
OFFSETS = [(0, 0), (0, 1), (1, 1), (1, 0)]  # R,G1,B,G2
MEMORY_LIMIT = 2 * 1024**3
PEAK_PRIVATE = 0

def memory_check():
    global PEAK_PRIVATE
    m=psutil.Process().memory_info()
    used=getattr(m,"private",m.rss)
    PEAK_PRIVATE=max(PEAK_PRIVATE,used)
    assert used <= MEMORY_LIMIT, "observer exceeded 2 GiB resident/private budget"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")

def bits_float(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]

def temporal_variance(a):
    return np.var(a, axis=0, ddof=1, dtype=np.float64).mean(axis=(-2, -1))

def commission():
    rng = np.random.default_rng(2026102841)
    x = (100 + rng.normal(0, 20, (64, 1, 64, 64))).astype(np.float32)
    y = (100 + rng.normal(0, 10, x.shape)).astype(np.float32)
    arms = [x, y, (x+y)*0.5, x*0.2+y*0.8, x.copy()]
    measured = [float(temporal_variance(a)[0]) for a in arms]
    expected = [400., 100., 125., 80., 400.]
    assert all(abs(a/b-1) < .02 for a,b in zip(measured,expected))
    yy, xx = np.mgrid[:64,:64]
    signal = (100 + 10*np.sin(2*np.pi*xx/8) + 8*np.cos(2*np.pi*yy/13)).astype(np.float32)
    def signal_error(a):
        return float(np.sqrt(np.mean((a-signal)**2)))
    foils = {"identity": signal, "blur": gaussian_filter(signal, 1.0),
             "sharpen": signal+0.5*(signal-gaussian_filter(signal,1.0)),
             "constant": np.full_like(signal,100), "shift": np.roll(signal,1,axis=1)}
    errors = {k:signal_error(v) for k,v in foils.items()}
    assert errors["identity"] == 0 and all(v > .5 for k,v in errors.items() if k!="identity")
    return {"seed":2026102841,"temporal_expected":expected,"temporal_measured":measured,
            "signal_foil_rmse":errors,"scope":"observer mechanics, not product or camera validation"}

def historical_decoder_binding():
    revision="ef65505013585abcc86b1410e4bf902bf34ed479"
    def blob(path):
        return subprocess.check_output(["git","-C",str(ROOT),"--work-tree="+str(ROOT),
            "show",revision+":"+path])
    lock=blob("Cargo.lock").replace(b"\r\n",b"\n")
    raw=blob("crates/strehl-raw/src/lib.rs").replace(b"\r\n",b"\n")
    current_raw=(ROOT/"crates/strehl-raw/src/lib.rs").read_bytes()
    assert current_raw.replace(b"\r\n",b"\n")==raw
    old=tomllib.loads(lock.decode()); current=tomllib.loads((ROOT/"Cargo.lock").read_text())
    old_core=next(p for p in old["package"] if p["name"]=="strehl-core")
    current_core=next(p for p in current["package"] if p["name"]=="strehl-core")
    assert set(current_core["dependencies"])-set(old_core["dependencies"])=={"sha2"}
    assert not(set(old_core["dependencies"])-set(current_core["dependencies"]))
    current_core["dependencies"]=old_core["dependencies"]
    assert current==old, "historical decoder reuse needs a new dependency audit"
    lock=lock.replace(b"\n",b"\r\n"); raw=raw.replace(b"\n",b"\r\n")
    decoder=hashlib.sha256(b"strehl-original-active-cfa-v1"+lock+raw).hexdigest()
    assert decoder=="c6fa0bc876fd2934faedea72a6e545c8bc2e2d3a812650c4726716216f0ce5bd"
    proof={"revision":revision,"materialized_line_endings":"CRLF for both files",
        "cargo_lock_sha256":hashlib.sha256(lock).hexdigest(),"raw_lib_sha256":hashlib.sha256(raw).hexdigest(),
        "decoder_key":decoder,"current_raw_normalized_equal":True,
        "only_current_lock_change":"sha2 added to strehl-core dependencies; all other parsed TOML equal",
        "policy":"historical cache read only; no relabel, rewrite or decoder fallback"}
    return decoder,proof

def cache_index(identities):
    wanted = {s["sha256"]:s for s in identities}
    decoder, proof = historical_decoder_binding()
    result = {}
    for path in sorted(CACHE.glob("*.cfa")):
        with path.open("rb") as f:
            prefix = f.read(12)
            assert prefix[:8] == b"STRHCFA1"
            n = struct.unpack("<I",prefix[8:])[0]
            assert 0 < n <= 256*1024
            raw_header = f.read(n)
            header = json.loads(raw_header)
        source = header["source"]
        if source["sha256"] not in wanted:
            continue
        assert source == wanted[source["sha256"]]
        assert header["decoder_key"] == decoder and header["version"] == 1 and header["cfa"] == "RGGB"
        g=header["geometry"]
        assert (g["width"],g["height"],g["active_x"],g["active_y"]) == (7032,4688,0,0)
        assert g["stride"] >= g["width"] and g["buffer_height"] >= g["height"]
        expected=12+n+g["width"]*g["height"]*2+32
        assert path.stat().st_size == expected
        assert source["sha256"] not in result
        result[source["sha256"]] = (path,header,raw_header,12+n)
    assert len(result)==len(identities)
    return result, decoder, proof

def check_stamp(source):
    stat=Path(source["path"]).stat()
    assert stat.st_size == source["bytes"] and stat.st_mtime_ns == source["modified_unix_nanos"]

def load_tiles(global_index, identities, index, tiles, receipts):
    source=identities[global_index]
    check_stamp(source)
    path,h,raw_header,offset=index[source["sha256"]]
    size=h["geometry"]["width"]*h["geometry"]["height"]*2
    digest=hashlib.sha256(raw_header)
    with path.open("rb") as f:
        f.seek(offset)
        left=size
        while left:
            block=f.read(min(left,1024*1024)); assert block
            digest.update(block); left-=len(block)
        assert digest.digest()==f.read(32) and not f.read(1)
    black=bits_float(h["metadata"]["black_bits"])
    white=bits_float(h["metadata"]["white_bits"])
    assert (black,white)==(512.,15360.)
    raw=np.memmap(path,dtype="<u2",mode="r",offset=offset,shape=(4688,7032))
    values=np.empty((len(tiles),4,80,80),np.float32)
    clipped=np.zeros(len(tiles),bool)
    for k,(x,y) in enumerate(tiles):
        crop=raw[2*(y-8):2*(y+72),2*(x-8):2*(x+72)]
        assert crop.shape==(160,160)
        clipped[k]=np.any(crop>=white)
        for c,(dy,dx) in enumerate(OFFSETS):
            values[k,c]=crop[dy::2,dx::2].astype(np.float32)-black
    del raw
    check_stamp(source)
    receipts.append({"global_index":global_index,"source":source,"cache":str(path),
                     "header_payload_sha256":digest.hexdigest(),"samples":size//2,
                     "black":black,"white":white})
    memory_check()
    return values,clipped

def predicted_variance(signal, model):
    return np.stack([float(p["gain_dn_per_e"])*np.maximum(signal[c],0)+
        (float(p["gain_dn_per_e"])*float(p["read_noise_e"]))**2 for c,p in enumerate(model)])

def channels(a):
    # Add green luma as a separately modeled quantity.
    return np.concatenate((a,((a[:,1]+a[:,3])*np.float32(.5))[:,None]),axis=1)

def channel_variance(v):
    return np.concatenate((v,((v[1]+v[3])*.25)[None]),axis=0)

def bootstrap_ratios(arms, seed):
    # Whole paired trial resampling plus 16x16-quad spatial blocks. All arms use
    # identical resampling indices. No interpolated-pixel independence premise.
    rng=np.random.default_rng(seed)
    trials,colors,h,w=arms[0].shape
    assert (h,w)==(64,64)
    counts_t=rng.multinomial(trials,np.full(trials,1/trials),size=400).astype(np.float64)
    counts_b=rng.multinomial(16,np.full(16,1/16),size=400).astype(np.float64)
    memory_check()
    all_estimates=[]
    for a in arms:
        # Center once for stable Gram arithmetic; bootstrap recenters again.
        z=(a.astype(np.float64)-a.mean(axis=0,dtype=np.float64))
        z=z.reshape(trials,colors,4,16,4,16).transpose(1,2,4,0,3,5).reshape(colors,16,trials,256)
        gram=np.einsum("cbtp,cbup->cbtu",z,z,optimize=True)
        g=np.einsum("kb,cbtu->kctu",counts_b,gram,optimize=True)
        diagonal=np.einsum("kt,kctt->kc",counts_t,g,optimize=True)
        square=np.einsum("kt,kctu,ku->kc",counts_t,g,counts_t,optimize=True)/trials
        all_estimates.append(np.maximum((diagonal-square)/((trials-1)*4096),0))
    ratios={}
    for ai,name in [(2,"equal"),(3,"precision")]:
        for ri,ref in [(0,"short"),(1,"long")]:
            r=all_estimates[ai]/np.maximum(all_estimates[ri],1e-30)
            ratios[name+"_over_"+ref]=np.quantile(r,[.025,.975],axis=0).T.tolist()
    return ratios

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    out=args.out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    began=time.time()
    identities=json.loads((RENDER/"source-identities.json").read_text())
    calibration=json.loads((RENDER/"calibration.json").read_text())
    photometry=json.loads((RENDER/"photometry.json").read_text())
    gains=np.array(photometry["calibrated_gains"],np.float32)
    tiles=[(x,y) for y in range(160,2250,256) for x in range(160,3370,256)]
    selected=sorted(set(GUIDES+VALIDATE+MEASURE+[i+62 for i in GUIDES+VALIDATE+MEASURE]))
    protocol={"schema":"strehl.independent-hdr-cache-temporal-observer.v1","script_sha256":sha(Path(__file__)),
        "command":sys.argv,"guides_short":GUIDES,"validation_short":VALIDATE,"measurement_short":MEASURE,
        "long_global_offset":62,"tiles_quad_xy":tiles,"interior_quad_size":64,"guide_halo_quad":8,
        "gauge":"unwarped original same-index CFA planes; no interpolation, no output pixels",
        "gains_fixed_from_existing_photometry":gains.tolist(),"gain_uncertainty":"conditioned on fixed existing calibration",
        "qualification_before_measurement":True,"guide_smoothing_sigma_quad":3.0,
        "guide_range_p95_sigma_max":.5,"validation_difference_p95_sigma_max":.35,
        "guide_gradient_p95_sigma_max":.15,"mean_drift_sigma_max":.25,
        "radiometric_mean_gap_combined_sigma_max":.25,
        "signal_minimum_dn":64.,"workers":1,"memory_limit_bytes":MEMORY_LIMIT,
        "inputs":{name:sha(RENDER/name) for name in ["source-identities.json","calibration.json","photometry.json","alignment.json"]},
        "original_sha256_not_rehashed":"original byte length+mtime rechecked; cache full payload and header digest verified",
        "limit":"flat original-sample observer, not full product/pyramid/noise or resolved-detail proof"}
    save(out/"protocol-frozen.json",protocol)
    save(out/"observer-commission.json",commission())
    print("Flat-first observer controls passed; protocol frozen.",flush=True)
    index,decoder,decoder_proof=cache_index([identities[i] for i in selected])
    save(out/"historical-decoder-binding.json",decoder_proof)
    receipts=[]
    guides=[]; validations=[]; clip_guides=[]; clip_validation=[]
    for base,target,clips in [(GUIDES,guides,clip_guides),(VALIDATE,validations,clip_validation)]:
        for offset in [0,62]:
            loaded=[load_tiles(i+offset,identities,index,tiles,receipts) for i in base]
            target.append(np.stack([a for a,b in loaded]))
            clips.append(np.any(np.stack([b for a,b in loaded]),axis=0))
            print("Loaded",len(base),"guide/validation originals at offset",offset,flush=True)
    qualified=np.ones(len(tiles),bool); per_tile=[{"quad_xy":xy,"qualification":[]} for xy in tiles]
    means=[]; predictions=[]
    for pass_id in range(2):
        # Explicitly filter only the two spatial plane axes.
        smooth=gaussian_filter(guides[pass_id],sigma=(0,0,0,3,3),mode="reflect")[...,8:-8,8:-8]
        validate=gaussian_filter(validations[pass_id],sigma=(0,0,0,3,3),mode="reflect")[...,8:-8,8:-8]
        mean=smooth.mean(axis=0)
        variance=np.stack([predicted_variance(m,calibration[pass_id]["noise_planes"]) for m in mean])
        means.append(mean); predictions.append(variance)
        for k in range(len(tiles)):
            sd=np.sqrt(np.maximum(variance[k],1e-20))
            range_score=np.quantile(np.ptp(smooth[:,k],axis=0)/sd,.95,axis=(-2,-1))
            validation_score=np.quantile(np.max(np.abs(validate[:,k]-mean[k]),axis=0)/sd,.95,axis=(-2,-1))
            gradient=np.maximum(np.abs(np.diff(mean[k],axis=-1,append=mean[k][...,-1:])),
                np.abs(np.diff(mean[k],axis=-2,append=mean[k,:,-1:,:])))
            gradient_score=np.quantile(gradient/sd,.95,axis=(-2,-1))
            frame_means=np.concatenate((smooth[:,k].mean(axis=(-2,-1)),validate[:,k].mean(axis=(-2,-1))))
            drift=np.ptp(frame_means,axis=0)/sd.mean(axis=(-2,-1))
            allowed=not(clip_guides[pass_id][k] or clip_validation[pass_id][k])
            allowed &= bool(np.all(mean[k].mean(axis=(-2,-1))>64))
            allowed &= bool(np.all(range_score<=.5) and np.all(validation_score<=.35)
                and np.all(gradient_score<=.15) and np.all(drift<=.25))
            qualified[k] &= allowed
            per_tile[k]["qualification"].append({"pass":pass_id,"accepted":bool(allowed),
                "range_p95_sigma":range_score.tolist(),"validation_p95_sigma":validation_score.tolist(),
                "gradient_p95_sigma":gradient_score.tolist(),"mean_drift_sigma":drift.tolist(),
                "mean_dn":mean[k].mean(axis=(-2,-1)).tolist(),
                "clipped":bool(clip_guides[pass_id][k] or clip_validation[pass_id][k])})
    for k in range(len(tiles)):
        gap=np.abs(means[0][k].mean(axis=(-2,-1))*gains[0]-means[1][k].mean(axis=(-2,-1)))
        sd=np.sqrt((predictions[0][k]*gains[0]**2+predictions[1][k]).mean(axis=(-2,-1)))
        score=gap/sd
        per_tile[k]["radiometric_gap_combined_sigma"]=score.tolist()
        qualified[k] &= bool(np.all(score<=.25))
        per_tile[k]["accepted_before_measurement"]=bool(qualified[k])
    chosen=np.flatnonzero(qualified).tolist()
    save(out/"source-only-qualification.json",{"decoder_key":decoder,"tiles":per_tile,"accepted_indices":chosen,
        "guide_and_validation_receipts":receipts.copy(),"measurement_loaded":False})
    print("Source-only qualification frozen:",len(chosen),"of",len(tiles),"tiles.",flush=True)
    # Preserve all source-only refusals. A failure here is evidence about this
    # observer/data scope, not permission to abandon the requested product benefit.
    if not chosen:
        save(out/"result.json",{"status":"no qualified source-flat support","raw_decodes":0,
            "elapsed_seconds":time.time()-began,"qualification":"source-only-qualification.json"})
        return
    measurement=[]; measurement_clip=[]
    chosen_tiles=[tiles[k] for k in chosen]
    for offset in [0,62]:
        loaded=[load_tiles(i+offset,identities,index,chosen_tiles,receipts) for i in MEASURE]
        measurement.append(np.stack([a[...,8:-8,8:-8] for a,b in loaded]))
        measurement_clip.append(np.any(np.stack([b for a,b in loaded]),axis=0))
    results=[]
    for local,k in enumerate(chosen):
        short=channels(measurement[0][:,local]*gains[0])
        long=channels(measurement[1][:,local])
        vs=channel_variance(predictions[0][k]*gains[0]**2)
        vl=channel_variance(predictions[1][k])
        weight=vl[4]/(vs[4]+vl[4])
        equal=(short+long)*np.float32(.5)
        precision=short*weight+long*(np.float32(1)-weight)
        arms=[short,long,equal,precision]
        measured=[temporal_variance(a).tolist() for a in arms]
        expected=[vs.mean(axis=(-2,-1)),vl.mean(axis=(-2,-1)),((vs+vl)*.25).mean(axis=(-2,-1)),
                  (weight**2*vs+(1-weight)**2*vl).mean(axis=(-2,-1))]
        covariance=((short-short.mean(axis=0))*(long-long.mean(axis=0))).sum(axis=0,dtype=np.float64)/(len(MEASURE)-1)
        correlation=covariance.mean(axis=(-2,-1))/np.sqrt(np.array(measured[0])*np.array(measured[1]))
        rec={"tile_index":k,"quad_xy":tiles[k],"channels":["R","G1","B","G2","green_luma"],
            "variance_order":["short","long","equal","precision"],"measured_temporal_variance":measured,
            "injected_model_variance":[e.tolist() for e in expected],
            "precision_short_weight_mean":float(weight.mean()),"paired_temporal_correlation":correlation.tolist(),
            "measurement_clipped":bool(measurement_clip[0][local] or measurement_clip[1][local]),
            "ratio_intervals_paired_temporal_and_spatial_bootstrap":bootstrap_ratios(arms,2026102850+k),
            "measurement_frame_mean_range_dn":[np.ptp(a.mean(axis=(-2,-1)),axis=0).tolist() for a in [short,long]]}
        results.append(rec)
    save(out/"result.json",{"status":"complete","raw_decodes":0,"source_cache_reads":len(receipts),
        "receipts":receipts,"qualified_tile_count":len(chosen),"tiles":results,"elapsed_seconds":time.time()-began,
        "scope":protocol["limit"],"gain_uncertainty":protocol["gain_uncertainty"],
        "sampled_peak_private_bytes":PEAK_PRIVATE,"bootstrap_replicates":400,"spatial_block_quad":16,"temporal_trials":len(MEASURE)})
    print("Completed",len(results),"qualified flat tiles; no RAW decode.",flush=True)

if __name__=="__main__":
    main()

"""Bounded, independently decoded HDR screen. Never imports production RAW code."""
import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "1"
import argparse
import gc
import hashlib
import json
import platform
import struct
import sys
import threading
import time
from pathlib import Path

import numpy as np
import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = HERE / "hdr-preflight-manifest.json"
OUT = ROOT / "outputs/multi-stack/hdr-preflight"
LIMIT = 1024 ** 3


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def digest_array(a):
    h = hashlib.sha256()
    for y in range(0, a.shape[0], 128):
        h.update(np.asarray(a[y:y+128], dtype="<u2", order="C").tobytes())
    return h.hexdigest()


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def file_stat(path):
    s = Path(path).stat()
    return {"bytes": s.st_size, "mtime_ns": s.st_mtime_ns}


def assert_unique(sources):
    hashes = [s["expected_sha256"] for s in sources]
    if len(set(hashes)) != len(hashes):
        raise ValueError("duplicate source independence")


def site_statistics(a, black, white):
    hist = np.zeros(65536, dtype=np.int64)
    for y in range(0, a.shape[0], 128):
        hist += np.bincount(a[y:y+128].ravel(), minlength=65536)
    cdf = np.cumsum(hist)
    total = int(cdf[-1])
    def quantile(p):
        return int(np.searchsorted(cdf, max(1, int(np.ceil(p * total)))))
    nonzero = np.flatnonzero(hist)
    return {"samples": total, "min": int(nonzero[0]), "max": int(nonzero[-1]),
            "black": float(black), "white": float(white),
            "at_or_above_white": int(hist[int(np.ceil(white)):].sum()),
            "within_white_dn": {str(d): int(hist[max(0, int(np.ceil(white-d))):].sum()) for d in [1,4,16]},
            "black_subtracted_quantiles_nearest_rank": {str(p): quantile(p)-float(black) for p in [.001,.01,.5,.99,.999]},
            "highest_32_occupied_bins": [[int(v),int(hist[v])] for v in nonzero[-32:]]}


def block_maps(a, white, cell=32):
    ys = np.arange(0, a.shape[0], cell)
    xs = np.arange(0, a.shape[1], cell)
    counts = np.diff(np.r_[ys,a.shape[0]])[:,None] * np.diff(np.r_[xs,a.shape[1]])[None,:]
    sums = np.add.reduceat(np.add.reduceat(a, ys, axis=0, dtype=np.uint64), xs, axis=1, dtype=np.uint64)
    clips = np.add.reduceat(np.add.reduceat(a >= white, ys, axis=0, dtype=np.uint32), xs, axis=1, dtype=np.uint32)
    return sums/counts, clips, counts


def compare_arrays(a, ageom, apattern, b, bgeom, bpattern):
    ax, ay = ageom["active_x"], ageom["active_y"]
    bx, by = bgeom["active_x"], bgeom["active_y"]
    left,top = max(ax,bx),max(ay,by)
    right,bottom = min(ax+a.shape[1],bx+b.shape[1]),min(ay+a.shape[0],by+b.shape[0])
    if right <= left or bottom <= top:
        raise ValueError("no absolute sensor overlap")
    for dy in range(2):
        for dx in range(2):
            if apattern[(top+dy-ay)%2][(left+dx-ax)%2] != bpattern[(top+dy-by)%2][(left+dx-bx)%2]:
                raise ValueError("CFA phase disagreement in absolute sensor coordinates")
    mismatches,max_delta,total = 0,0,0
    per_site = [{"mismatches":0,"max_absolute_dn":0,"samples":0} for _ in range(4)]
    for y in range(top,bottom,128):
        end = min(bottom,y+128)
        aa = a[y-ay:end-ay,left-ax:right-ax]
        bb = b[y-by:end-by,left-bx:right-bx]
        d = aa.astype(np.int32)-bb
        mismatches += int(np.count_nonzero(d)); max_delta=max(max_delta,int(np.abs(d).max()));total+=d.size
        for sy in range(2):
            for sx in range(2):
                z=d[sy::2,sx::2]; i=((y+sy-top)%2)*2+sx
                per_site[i]["mismatches"]+=int(np.count_nonzero(z))
                per_site[i]["max_absolute_dn"]=max(per_site[i]["max_absolute_dn"],int(np.abs(z).max(initial=0)))
                per_site[i]["samples"]+=z.size
    return {"overlap_xywh":[left,top,right-left,bottom-top],"samples":total,
            "mismatches":mismatches,"max_absolute_dn":max_delta,"per_overlap_site":per_site,
            "exact":mismatches==0}


def controls():
    a=np.array([[9,19,10,20],[29,39,30,40],[100,200,101,201],[300,400,301,401]],dtype=np.uint16)
    blacks=[10,20,30,40];whites=[100,200,300,400]
    for k in range(4):
        v=a[k//2::2,k%2::2];s=site_statistics(v,blacks[k],whites[k])
        assert s["samples"]==4 and s["min"]==blacks[k]-1 and s["at_or_above_white"]==2
        assert s["black_subtracted_quantiles_nearest_rank"]["0.001"]==-1
        mean,clips,n=block_maps(v,whites[k],2)
        assert int(clips[0,0])==2 and int(n[0,0])==4 and float(mean[0,0])==float(v.astype(np.float64).mean())
    g={"active_x":11,"active_y":7};pattern=[["R","G"],["G","B"]]
    assert compare_arrays(a,g,pattern,a,g,pattern)["exact"]
    try: compare_arrays(a,g,pattern,a,g,[["G","R"],["B","G"]])
    except ValueError: pass
    else: raise AssertionError("CFA phase foil accepted")
    try: compare_arrays(a,g,pattern,a,{"active_x":12,"active_y":7},pattern)
    except ValueError: pass
    else: raise AssertionError("wrong active offset accepted")
    # Even-offset foil keeps phase, but absolute-coordinate sample comparison fails.
    assert not compare_arrays(a,g,pattern,a,{"active_x":13,"active_y":7},pattern)["exact"]
    try: assert_unique([{"expected_sha256":"same"},{"expected_sha256":"same"}])
    except ValueError: pass
    else: raise AssertionError("duplicate identity accepted")
    return {"status":"PASS","tests":["per-color black/white and exact clipping", "negative black-subtracted values preserved", "block map exact counts", "identity absolute-coordinate decode", "wrong CFA phase refusal", "odd offset phase refusal", "even offset value mismatch", "copied source identity refusal"]}


def decode():
    import rawpy
    manifest=json.loads(MANIFEST.read_text()); assert_unique(manifest["sources"])
    assert len(manifest["sources"])==9
    if OUT.exists(): raise FileExistsError("fresh output required")
    OUT.mkdir(parents=True)
    write_json(OUT/"controls.json",controls())
    records=[]
    for source in manifest["sources"]:
        path=Path(source["path"]); before=file_stat(path)
        whole=digest_file(path)
        if whole!=source["expected_sha256"]: raise ValueError("frozen whole-file identity changed")
        start=time.perf_counter()
        with rawpy.imread(str(path)) as raw:
            visible=raw.raw_image_visible
            if visible.dtype!=np.uint16 or visible.ndim!=2: raise ValueError("expected u16 CFA")
            active=visible.copy(order="C")
            assert active.flags.owndata and not np.shares_memory(active,visible)
            sizes=raw.sizes
            geometry={"active_x":int(sizes.left_margin),"active_y":int(sizes.top_margin),"width":int(sizes.width),"height":int(sizes.height),"raw_width":int(sizes.raw_width),"raw_height":int(sizes.raw_height),"flip":int(sizes.flip)}
            indices=raw.raw_colors_visible[:2,:2].copy().tolist()
            desc=raw.color_desc.decode("ascii").rstrip("\x00")
            pattern=[[desc[i] for i in row] for row in indices]
            blacks=list(map(float,raw.black_level_per_channel))
            camera_white=raw.camera_white_level_per_channel
            whites=list(map(float,camera_white)) if camera_white is not None else None
            scalar_white=float(raw.white_level)
            wb=list(map(float,raw.camera_whitebalance))
            matrix=np.asarray(raw.rgb_xyz_matrix).tolist()
            inside_sha=digest_array(active)
        del visible
        assert digest_array(active)==inside_sha
        assert list(active.shape)==[geometry["height"],geometry["width"]]
        key=f'{source["bracket"]}-{source["index"]:04d}'
        npy=OUT/f"{key}-active-u16.npy"
        np.save(npy,active,allow_pickle=False)
        back=np.load(npy,mmap_mode="r",allow_pickle=False)
        assert back.dtype==np.uint16 and back.shape==active.shape and digest_array(back)==inside_sha
        del back
        stats=[];maps={}
        for dy in range(2):
            for dx in range(2):
                c=indices[dy][dx];site=dy*2+dx
                white=whites[c] if whites and whites[c]>0 else scalar_white
                plane=active[dy::2,dx::2]
                item=site_statistics(plane,blacks[c],white)
                item.update({"site_xy":[dx,dy],"rawpy_color_index":c,"color":pattern[dy][dx]})
                item["at_or_above_scalar_white"]=int(np.count_nonzero(plane>=scalar_white))
                stats.append(item)
                mean,clip,count=block_maps(plane,white)
                maps[f"site{site}_mean"]=mean.astype(np.float32)
                maps[f"site{site}_clipped"]=clip
                maps[f"site{site}_count"]=count
        np.savez(OUT/f"{key}-blocks.npz",**maps)
        descriptor={"geometry":geometry,"pattern":pattern,"dtype":"little-endian-u16-row-major","payload_sha256":inside_sha}
        bound=hashlib.sha256(json.dumps(descriptor,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        record={"source":source,"whole_sha256":whole,"stat_before":before,"stat_after":file_stat(path),"active":descriptor,"active_identity_sha256":bound,"active_file":npy.name,"active_file_sha256":digest_file(npy),"rawpy_indices":indices,"color_description":desc,"black_per_color":blacks,"white_scalar":scalar_white,"white_per_color":whites,"camera_whitebalance":wb,"rgb_xyz_matrix":matrix,"sites":stats,"elapsed_seconds":time.perf_counter()-start}
        assert record["stat_before"]==record["stat_after"]
        write_json(OUT/f"{key}.json",record)
        records.append(record)
        print(json.dumps({"source":key,"shape":active.shape,"black":blacks,"white":whites or scalar_white,"clip_counts":[s["at_or_above_white"] for s in stats],"active_sha":inside_sha,"seconds":record["elapsed_seconds"]}),flush=True)
        del active,plane,maps
        gc.collect()
        if psutil.Process().memory_info().rss>LIMIT: raise MemoryError("process memory exceeded 1 GiB")
    report={"schema":"strehl.hdr-preflight.stage-a.v1","status":"PASS_INDEPENDENT_DECODE_CROSS_DECODER_PENDING","manifest_sha256":digest_file(MANIFEST),"rawpy":rawpy.__version__,"libraw":rawpy.libraw_version,"records":records}
    write_json(OUT/"stage-a.json",report)
    return {"records":len(records),"total_original_bytes":sum(r["stat_before"]["bytes"] for r in records),"active_bytes":sum(r["active"]["geometry"]["width"]*r["active"]["geometry"]["height"]*2 for r in records)}


def read_cache_header(path):
    with path.open("rb") as f:
        prefix=f.read(12)
        if len(prefix)!=12 or prefix[:8]!=b"STRHCFA1": raise ValueError("cache magic")
        size=struct.unpack("<I",prefix[8:])[0]
        if not 0<size<=256*1024: raise ValueError("cache header size")
        data=f.read(size)
        header=json.loads(data)
    return header,data,12+size


def compare_cache(cache):
    stage=json.loads((OUT/"stage-a.json").read_text())
    wanted={r["whole_sha256"]:r for r in stage["records"]}
    matches={}
    for path in cache.glob("*.cfa"):
        h,raw,offset=read_cache_header(path)
        if h["source"]["sha256"] in wanted:
            if h["source"]["sha256"] in matches: raise ValueError("ambiguous duplicate cache entry")
            matches[h["source"]["sha256"]]=(path,h,raw,offset)
    if set(wanted)!=set(matches): raise ValueError(f"cache missing {len(set(wanted)-set(matches))} frozen sources")
    results=[]
    for sha,r in wanted.items():
        path,h,raw,offset=matches[sha];g=h["geometry"];n=g["width"]*g["height"]*2
        if path.stat().st_size != offset+n+32: raise ValueError("cache envelope length")
        digest=hashlib.sha256(raw)
        with path.open("rb") as f:
            f.seek(offset);left=n
            while left:
                block=f.read(min(left,1024*1024)); assert block
                digest.update(block);left-=len(block)
            if f.read(32)!=digest.digest(): raise ValueError("cache metadata/payload checksum")
        a=np.load(OUT/r["active_file"],mmap_mode="r",allow_pickle=False)
        b=np.memmap(path,mode="r",dtype="<u2",offset=offset,shape=(g["height"],g["width"]))
        assert h["cfa"]=="RGGB"
        result=compare_arrays(a,r["active"]["geometry"],r["active"]["pattern"],b,g,[["R","G"],["G","B"]])
        result.update({"source":r["source"],"cache_file":str(path),"cache_geometry":g,"rawpy_geometry":r["active"]["geometry"],"cache_decoder_key":h["decoder_key"],"cache_envelope_verified":True,"cache_black":struct.unpack("<f",struct.pack("<I",h["metadata"]["black_bits"]))[0],"cache_white":struct.unpack("<f",struct.pack("<I",h["metadata"]["white_bits"]))[0]})
        result["rawpy_counts_at_cache_white"]=[int(np.count_nonzero(a[dy::2,dx::2]>=result["cache_white"])) for dy in range(2) for dx in range(2)]
        results.append(result)
        print(json.dumps({"path":str(path),"exact":result["exact"],"mismatches":result["mismatches"],"max_absolute_dn":result["max_absolute_dn"],"overlap":result["overlap_xywh"]}),flush=True)
        del a,b
    report={"schema":"strehl.hdr-preflight.cross-decoder.v1","all_exact":all(r["exact"] for r in results),"results":results}
    write_json(OUT/"cross-decoder.json",report)
    if not report["all_exact"]: raise ValueError("independent decoder sample mismatch; numeric cross-decoder claims blocked")
    return {"compared":len(results),"all_exact":True}



def compare_strips():
    import rawpy
    comparison=json.loads((OUT/"cross-decoder.json").read_text())
    results=[]
    for r in comparison["results"]:
        path=Path(r["source"]["path"]);before=file_stat(path)
        if digest_file(path)!=r["source"]["expected_sha256"]: raise ValueError("frozen strip source changed")
        with rawpy.imread(str(path)) as raw:
            strip=raw.raw_image[0:4688,7028:7032].copy(order="C")
            assert strip.shape==(4688,4) and strip.dtype==np.uint16 and strip.flags.owndata
            raw_shape=list(raw.raw_image.shape)
            visible_shape=list(raw.raw_image_visible.shape)
        cache=Path(r["cache_file"]);h,_,offset=read_cache_header(cache);g=h["geometry"]
        a=np.memmap(cache,dtype="<u2",mode="r",offset=offset,shape=(g["height"],g["width"]))
        b=a[0:4688,7028:7032]
        mismatch=int(np.count_nonzero(strip!=b));max_delta=int(np.abs(strip.astype(np.int32)-b).max())
        assert before==file_stat(path)
        result={"source":r["source"],"rawpy_raw_shape":raw_shape,"rawpy_visible_shape":visible_shape,"absolute_rectangle_xywh":[7028,0,4,4688],"samples":strip.size,"mismatches":mismatch,"max_absolute_dn":max_delta,"exact":mismatch==0,"min":int(strip.min()),"max":int(strip.max()),"unique_values":int(np.unique(strip).size),"strip_sha256":digest_array(strip),"classification":"independently matching heterogeneous original decoded sensor codes; excluded from LibRaw visible crop; optical-active semantics not established"}
        results.append(result);print(json.dumps(result),flush=True)
        del strip,a,b
        gc.collect()
    write_json(OUT/"extra-strip-comparison.json",{"results":results,"all_exact":all(r["exact"] for r in results),"statistics_domain":"only shared absolute [0,7028)x[0,4688)"})
    if not all(r["exact"] for r in results): raise ValueError("strip mismatch")
    return {"compared":len(results),"all_exact":True,"extra_decodes_authorized_by_root":9}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("command",choices=["controls","decode","compare-cache","compare-strips"]);parser.add_argument("--cache",type=Path)
    args=parser.parse_args(); start=time.perf_counter(); proc=psutil.Process(); initial=proc.memory_info();peak=[initial.rss,getattr(initial,"private",0)];stop=threading.Event()
    def monitor():
        while not stop.wait(.1):
            m=proc.memory_info();peak[0]=max(peak[0],m.rss);peak[1]=max(peak[1],getattr(m,"private",0))
    thread=threading.Thread(target=monitor,daemon=True);thread.start()
    status=0;result=None;error=None
    try:
        if args.command=="controls": result=controls();print(json.dumps(result),flush=True)
        elif args.command=="decode": result=decode()
        elif args.command=="compare-strips": result=compare_strips()
        else:
            if args.cache is None: raise ValueError("--cache required")
            result=compare_cache(args.cache)
    except Exception as exc:
        import traceback
        status=1;error=repr(exc);traceback.print_exc()
    finally:
        stop.set();thread.join();m=proc.memory_info();peak[0]=max(peak[0],m.rss);peak[1]=max(peak[1],getattr(m,"private",0))
        receipt={"command":[sys.executable,"-X","faulthandler","-I",*sys.argv],"cwd":str(Path.cwd()),"script_sha256":digest_file(__file__),"manifest_sha256":digest_file(MANIFEST),"python":sys.version,"numpy":np.__version__,"platform":platform.platform(),"environment":{k:os.environ.get(k) for k in ["OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","NUMEXPR_NUM_THREADS","RAYON_NUM_THREADS"]},"compute_workers":1,"monitor_threads":1,"wall_seconds":time.perf_counter()-start,"sampled_peak_rss":peak[0],"sampled_peak_private":peak[1],"memory_reservation_bytes":LIMIT,"memory_reservation_exceeded":peak[0]>LIMIT or peak[1]>LIMIT,"exit_code":status,"result":result,"error":error}
        print(json.dumps(receipt),flush=True)
        if OUT.exists():
            path=OUT/f"{args.command}-receipt.json"
            if not path.exists(): write_json(path,receipt)
    return status


if __name__=="__main__": raise SystemExit(main())
